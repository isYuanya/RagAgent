from app.core.config import settings
from app.schemas.copy import CopyAssetSummary, CopyImportRowError
from app.schemas.task import TaskProgress, TaskResponse
from app.services.copy_analysis import analyze_copy, extract_text_import_payload
from app.services.copy_assets import (
    MAX_SYNC_IMPORT_ROWS,
    create_copy_asset,
    parse_copy_import_row,
    read_copy_import_csv,
)
from app.services.copy_postprocess import sync_imported_asset_to_knowledge
from app.workers.tasks import (
    create_task,
    set_task_failed,
    set_task_progress,
    set_task_result,
    set_task_running,
)


def run_copy_import_task(
    csv_text: str, task_id: str | None = None, collection_ids: list[str] | None = None
) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            current_message="等待处理 CSV。",
        )
    )
    if task_id is not None:
        task = task.model_copy(update={"task_id": task_id})
        from app.workers import tasks

        tasks._TASKS[task_id] = task

    errors: list[CopyImportRowError] = []
    assets: list[CopyAssetSummary] = []

    try:
        fieldnames, rows = read_copy_import_csv(csv_text)
        if not fieldnames or "source_text" not in fieldnames:
            message = "CSV 必须包含 source_text 表头。"
            progress = TaskProgress(
                phase="failed",
                model=settings.openai_model,
                percent=100,
                failed_count=1,
                current_message=message,
                errors=[{"row_number": 1, "message": message}],
            )
            return _publish(set_task_failed(task.task_id, message, progress))

        total_rows = len(rows)
        if total_rows > MAX_SYNC_IMPORT_ROWS:
            message = f"同步导入最多支持 {MAX_SYNC_IMPORT_ROWS} 行，请拆分 CSV。"
            progress = TaskProgress(
                phase="failed",
                model=settings.openai_model,
                total_rows=total_rows,
                percent=100,
                failed_count=total_rows,
                current_message=message,
                errors=[{"row_number": 1, "message": message}],
            )
            return _publish(set_task_failed(task.task_id, message, progress))

        progress = TaskProgress(
            phase="parsing_csv",
            model=settings.openai_model,
            total_rows=total_rows,
            current_message=f"已读取 {total_rows} 条 CSV 数据。",
        )
        _publish(set_task_running(task.task_id, progress))

        for offset, row in enumerate(rows, start=1):
            row_number = offset + 1
            progress = progress.model_copy(
                update={
                    "phase": "calling_llm",
                    "current_row": row_number,
                    "processed_count": offset - 1,
                    "percent": _percent(offset - 1, total_rows),
                    "current_message": f"正在调用 LLM 拆解第 {offset}/{total_rows} 条。",
                }
            )
            _publish(set_task_progress(task.task_id, progress))

            parsed = parse_copy_import_row(row, row_number)
            if isinstance(parsed, CopyImportRowError):
                errors.append(parsed)
                progress = _row_done(progress, total_rows, offset, len(assets), len(errors), errors)
                _publish(set_task_progress(task.task_id, progress))
                continue

            try:
                analysis = analyze_copy(parsed)
            except RuntimeError as exc:
                errors.append(CopyImportRowError(row_number=row_number, message=str(exc)))
                progress = _row_done(progress, total_rows, offset, len(assets), len(errors), errors)
                _publish(set_task_progress(task.task_id, progress))
                if "OPENAI_API_KEY" in str(exc):
                    failed_progress = progress.model_copy(
                        update={"phase": "failed", "current_message": str(exc)}
                    )
                    return _publish(set_task_failed(task.task_id, str(exc), failed_progress))
                continue

            progress = progress.model_copy(
                update={"phase": "saving_asset", "current_message": f"正在保存第 {offset}/{total_rows} 条。"}
            )
            _publish(set_task_progress(task.task_id, progress))
            asset = create_copy_asset(parsed, analysis, collection_ids=collection_ids or [])
            sync_imported_asset_to_knowledge(asset)
            assets.append(asset)
            progress = _row_done(progress, total_rows, offset, len(assets), len(errors), errors)
            _publish(set_task_progress(task.task_id, progress))

        result = {
            "imported_count": len(assets),
            "failed_count": len(errors),
            "asset_ids": [asset.id for asset in assets],
            "storage_backends": sorted({asset.storage_backend for asset in assets}),
        }
        finished_progress = progress.model_copy(
            update={
                "phase": "finished",
                "percent": 100,
                "current_message": "导入完成。",
                "success_count": len(assets),
                "failed_count": len(errors),
                "errors": [error.model_dump() for error in errors],
            }
        )
        _publish(set_task_progress(task.task_id, finished_progress))
        return _publish(set_task_result(task.task_id, result))
    except Exception as exc:
        return _publish(
            set_task_failed(
                task.task_id,
                str(exc),
                TaskProgress(
                    phase="failed",
                    model=settings.openai_model,
                    percent=100,
                    current_message=str(exc),
                    errors=[{"row_number": 0, "message": str(exc)}],
                ),
            )
        )


def run_text_import_task(
    text: str, task_id: str | None = None, collection_ids: list[str] | None = None
) -> TaskResponse:
    task = create_task(
        progress=TaskProgress(
            phase="queued",
            model=settings.openai_model,
            total_rows=1,
            current_message="等待处理纯文本。",
        )
    )
    if task_id is not None:
        task = task.model_copy(update={"task_id": task_id})
        from app.workers import tasks

        tasks._TASKS[task_id] = task

    source_text = text.strip()
    if not source_text:
        message = "text 不能为空。"
        progress = TaskProgress(
            phase="failed",
            model=settings.openai_model,
            total_rows=1,
            percent=100,
            failed_count=1,
            current_message=message,
            errors=[{"row_number": 1, "message": message}],
        )
        return _publish(set_task_failed(task.task_id, message, progress))

    progress = TaskProgress(
        phase="calling_llm",
        model=settings.openai_model,
        current_row=1,
        total_rows=1,
        current_message="正在调用 LLM 拆解纯文本。",
    )
    _publish(set_task_running(task.task_id, progress))

    try:
        payload = extract_text_import_payload(source_text)
        analysis = analyze_copy(payload)
        progress = progress.model_copy(
            update={
                "phase": "saving_asset",
                "percent": 80,
                "current_message": "正在保存拆解后的文案资产。",
            }
        )
        _publish(set_task_progress(task.task_id, progress))
        asset = create_copy_asset(payload, analysis, collection_ids=collection_ids or [])
        sync_imported_asset_to_knowledge(asset)
    except RuntimeError as exc:
        failed_progress = progress.model_copy(
            update={
                "phase": "failed",
                "percent": 100,
                "failed_count": 1,
                "current_message": str(exc),
                "errors": [{"row_number": 1, "message": str(exc)}],
            }
        )
        return _publish(set_task_failed(task.task_id, str(exc), failed_progress))
    except Exception as exc:
        failed_progress = TaskProgress(
            phase="failed",
            model=settings.openai_model,
            total_rows=1,
            percent=100,
            failed_count=1,
            current_message=str(exc),
            errors=[{"row_number": 1, "message": str(exc)}],
        )
        return _publish(set_task_failed(task.task_id, str(exc), failed_progress))

    finished_progress = progress.model_copy(
        update={
            "phase": "finished",
            "current_row": 1,
            "processed_count": 1,
            "success_count": 1,
            "failed_count": 0,
            "percent": 100,
            "current_message": "纯文本导入完成。",
            "errors": [],
        }
    )
    _publish(set_task_progress(task.task_id, finished_progress))
    return _publish(
        set_task_result(
            task.task_id,
            {
                "imported_count": 1,
                "failed_count": 0,
                "asset_ids": [asset.id],
                "storage_backends": [asset.storage_backend],
            },
        )
    )


def _row_done(
    progress: TaskProgress,
    total_rows: int,
    offset: int,
    success_count: int,
    failed_count: int,
    errors: list[CopyImportRowError],
) -> TaskProgress:
    return progress.model_copy(
        update={
            "processed_count": offset,
            "success_count": success_count,
            "failed_count": failed_count,
            "percent": _percent(offset, total_rows),
            "errors": [error.model_dump() for error in errors],
            "current_message": f"已处理 {offset}/{total_rows} 条。",
        }
    )


def _percent(processed_count: int, total_rows: int) -> int:
    if total_rows <= 0:
        return 100
    return min(100, round((processed_count / total_rows) * 100))


def _publish(task: TaskResponse) -> TaskResponse:
    try:
        from rq import get_current_job

        job = get_current_job()
        if job is not None:
            job.meta["task"] = task.model_dump(mode="json")
            job.save_meta()
    except Exception:
        pass
    return task
