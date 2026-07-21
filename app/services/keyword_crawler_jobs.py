from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.schemas.keyword_rankings import (
    KeywordCrawlerRequest,
    KeywordIndustryCreate,
    KeywordVideoImportRequest,
)
from app.schemas.task import TaskProgress, TaskResponse
from app.services import keyword_rankings
from app.workers.tasks import (
    create_task,
    set_task_failed,
    set_task_progress,
    set_task_result,
    set_task_running,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CRAWLER_SCRIPT = SCRIPTS_DIR / "douyin_ai_crawler_v5_3.py"
BASE_CONFIG = SCRIPTS_DIR / "config.json"
OUTPUT_DIR = PROJECT_ROOT / "storage" / "keyword_crawler"
DEFAULT_INDUSTRY_NAME = "贷款"


def enqueue_keyword_crawl(payload: KeywordCrawlerRequest) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            total_rows=payload.max_videos,
            current_message="等待开始在线爬取",
        )
    )
    thread = threading.Thread(
        target=run_keyword_crawl_task,
        args=(task.task_id, payload),
        daemon=True,
    )
    thread.start()
    return task


def run_keyword_crawl_task(task_id: str, payload: KeywordCrawlerRequest) -> None:
    try:
        set_task_running(
            task_id,
            TaskProgress(
                phase="starting",
                total_rows=payload.max_videos,
                percent=1,
                current_message="正在启动抖音爬取",
            ),
        )
        output_csv = _run_crawler_process(task_id, payload)
        set_task_progress(
            task_id,
            TaskProgress(
                phase="importing",
                total_rows=payload.max_videos,
                percent=95,
                current_message="爬取完成，正在导入关键词榜单",
            ),
        )
        csv_text = output_csv.read_text(encoding="utf-8-sig")
        industry_id = _resolve_industry_id(payload.industry_id)
        result = keyword_rankings.import_keyword_videos(
            KeywordVideoImportRequest(
                industry_id=industry_id,
                keyword=payload.keyword.strip(),
                csv_text=csv_text,
            )
        )
        if result is None:
            raise RuntimeError("关键词行业不存在，无法导入爬取结果")
        set_task_progress(
            task_id,
            TaskProgress(
                phase="finished",
                total_rows=max(result.video_count, 1),
                current_row=result.video_count,
                processed_count=result.video_count,
                success_count=result.created_count + result.updated_count,
                failed_count=result.failed_count,
                percent=100,
                current_message="爬取结果已导入关键词榜单",
            ),
        )
        set_task_result(
            task_id,
            {
                "industry_id": result.industry_id,
                "keyword_id": result.keyword_id,
                "keyword": result.keyword,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
                "failed_count": result.failed_count,
                "video_count": result.video_count,
                "output_csv": str(output_csv),
            },
        )
    except Exception as exc:
        set_task_failed(
            task_id,
            str(exc),
            TaskProgress(
                phase="failed",
                total_rows=payload.max_videos,
                percent=0,
                current_message="在线爬取失败",
            ),
        )


def _run_crawler_process(task_id: str, payload: KeywordCrawlerRequest) -> Path:
    if not CRAWLER_SCRIPT.exists():
        raise FileNotFoundError(f"爬虫脚本不存在：{CRAWLER_SCRIPT}")
    if not BASE_CONFIG.exists():
        raise FileNotFoundError(f"爬虫配置不存在：{BASE_CONFIG}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_csv = OUTPUT_DIR / f"{task_id}.csv"
    config_path = _write_task_config(payload, output_csv)
    env = os.environ.copy()
    env["DOUYIN_CRAWLER_CONFIG"] = str(config_path)
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [sys.executable, str(CRAWLER_SCRIPT)],
        cwd=str(SCRIPTS_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert process.stdout is not None
    last_lines: list[str] = []
    for line in process.stdout:
        text = line.strip()
        if text:
            last_lines = (last_lines + [text])[-8:]
        if text.startswith("CRAWLER_PROGRESS "):
            _apply_crawler_progress(task_id, payload.max_videos, text)
    exit_code = process.wait()
    if exit_code != 0:
        details = "\n".join(last_lines[-4:])
        raise RuntimeError(f"爬虫执行失败，退出码 {exit_code}。{details}")
    if not output_csv.exists():
        raise RuntimeError("爬虫完成但没有生成 CSV 文件")
    return output_csv


def _write_task_config(payload: KeywordCrawlerRequest, output_csv: Path) -> Path:
    config = json.loads(BASE_CONFIG.read_text(encoding="utf-8"))
    config["keyword"] = payload.keyword.strip()
    config["min_likes"] = payload.min_likes
    config["max_videos"] = payload.max_videos
    config["output_csv"] = str(output_csv)
    fd, raw_path = tempfile.mkstemp(prefix="douyin_crawler_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
    return Path(raw_path)


def _apply_crawler_progress(task_id: str, max_videos: int, line: str) -> None:
    try:
        payload: dict[str, Any] = json.loads(line.removeprefix("CRAWLER_PROGRESS ").strip())
    except json.JSONDecodeError:
        return
    phase = str(payload.get("phase") or "running")
    saved_count = int(payload.get("saved_count") or 0)
    eligible_count = int(payload.get("eligible_count") or 0)
    target_count = int(payload.get("target_count") or max_videos or 1)
    if phase == "scrolling":
        current = min(eligible_count, target_count)
        percent = min(70, _percent(current, target_count))
    elif phase in {"processing", "saving"}:
        current = saved_count
        percent = min(94, _percent(current, target_count))
    elif phase == "finished":
        current = saved_count
        percent = 94
    else:
        current = max(saved_count, eligible_count)
        percent = min(94, _percent(current, target_count))
    set_task_progress(
        task_id,
        TaskProgress(
            phase=phase,
            current_row=current,
            total_rows=max(target_count, 1),
            processed_count=current,
            success_count=saved_count,
            percent=percent,
            current_message=str(payload.get("message") or "正在在线爬取"),
        ),
    )


def _percent(current: int, total: int) -> int:
    if total <= 0:
        return 0
    return max(0, min(100, round(current / total * 100)))


def _resolve_industry_id(industry_id: str | None) -> str:
    if industry_id and keyword_rankings.get_industry(industry_id) is not None:
        return industry_id
    industries = keyword_rankings.list_industries(page=1, page_size=100).items
    active = next((item for item in industries if item.status == "active"), None)
    if active is not None:
        return active.id
    if industries:
        return industries[0].id
    created = keyword_rankings.create_industry(
        KeywordIndustryCreate(
            name=DEFAULT_INDUSTRY_NAME,
            description="贷款、征信、经营贷相关热点视频",
            status="active",
        )
    )
    return created.id
