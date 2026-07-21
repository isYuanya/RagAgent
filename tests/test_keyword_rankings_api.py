import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.keyword_crawler_jobs import _apply_crawler_progress
from app.services.keyword_rankings import calculate_hot_score, reset_keyword_ranking_store
from app.workers.tasks import create_task, get_task


client = TestClient(app)


def setup_function() -> None:
    reset_keyword_ranking_store()


def test_keyword_crawler_progress_uses_visible_ratio_percent() -> None:
    task = create_task()

    _apply_crawler_progress(
        task.task_id,
        20,
        "CRAWLER_PROGRESS "
        + json.dumps(
            {
                "phase": "scrolling",
                "current_scroll": 8,
                "total_scroll": 20,
                "eligible_count": 22,
                "saved_count": 0,
                "target_count": 20,
                "message": "已滚动 8/20 次，满足点赞条件 22 条",
            }
        ),
    )
    scrolling = get_task(task.task_id)
    assert scrolling is not None
    assert scrolling.progress is not None
    assert scrolling.progress.percent == 40

    _apply_crawler_progress(
        task.task_id,
        20,
        "CRAWLER_PROGRESS "
        + json.dumps(
            {
                "phase": "processing_video",
                "saved_count": 8,
                "target_count": 20,
                "message": "已爬取视频 8/20 条",
            }
        ),
    )
    processing = get_task(task.task_id)
    assert processing is not None
    assert processing.progress is not None
    assert processing.progress.percent == 40


def test_keyword_industry_keyword_and_import_flow() -> None:
    industry_response = client.post(
        "/api/keyword-industries",
        json={"name": "loan", "description": "loan trend videos", "status": "active"},
    )
    assert industry_response.status_code == 200
    industry = industry_response.json()
    assert industry["keyword_count"] == 0
    assert industry["video_count"] == 0

    keyword_response = client.post(
        "/api/keywords",
        json={"industry_id": industry["id"], "keyword": "credit"},
    )
    assert keyword_response.status_code == 200
    keyword = keyword_response.json()
    assert keyword["keyword"] == "credit"

    csv_text = "\n".join(
        [
            "source_text,source_url,author_name,author_url,author_follower_count,platform,industry,audience,purpose,style,likes,comments,favorites,shares",
            "first video,https://example.com/1,A,https://example.com/a,1000,douyin,loan,owner,lead,plain,100,20,40,10",
            "second video,https://example.com/2,B,https://example.com/b,2000,douyin,loan,owner,lead,plain,300,10,20,5",
        ]
    )
    import_response = client.post(
        "/api/keyword-videos/import",
        json={"industry_id": industry["id"], "keyword": "credit", "csv_text": csv_text},
    )
    assert import_response.status_code == 200
    result = import_response.json()
    assert result["keyword_id"] == keyword["id"]
    assert result["created_count"] == 2
    assert result["updated_count"] == 0
    assert result["video_count"] == 2

    videos_response = client.get(f"/api/keywords/{keyword['id']}/videos")
    assert videos_response.status_code == 200
    videos = videos_response.json()["items"]
    assert [item["source_url"] for item in videos] == [
        "https://example.com/2",
        "https://example.com/1",
    ]
    assert videos[0]["rank"] == 1
    assert videos[0]["hot_score"] == calculate_hot_score(
        likes=300, comments=10, favorites=20, shares=5
    )

    update_csv = "\n".join(
        [
            "source_text,source_url,author_name,likes,comments,favorites,shares",
            "first video updated,https://example.com/1,A updated,500,50,100,20",
        ]
    )
    second_import = client.post(
        "/api/keyword-videos/import",
        json={"industry_id": industry["id"], "keyword": "credit", "csv_text": update_csv},
    )
    assert second_import.status_code == 200
    second_result = second_import.json()
    assert second_result["created_count"] == 0
    assert second_result["updated_count"] == 1
    assert second_result["video_count"] == 2

    videos_after = client.get(f"/api/keywords/{keyword['id']}/videos").json()["items"]
    assert len(videos_after) == 2
    assert videos_after[0]["source_url"] == "https://example.com/1"
    assert videos_after[0]["source_text"] == "first video updated"
    assert videos_after[0]["author_name"] == "A updated"


def test_import_creates_missing_keyword_and_reports_row_errors() -> None:
    industry_response = client.post("/api/keyword-industries", json={"name": "medical"})
    assert industry_response.status_code == 200
    industry_id = industry_response.json()["id"]

    csv_text = "\n".join(
        [
            "source_text,source_url,likes,comments,favorites,shares",
            ",https://example.com/empty,1,2,3,4",
            "valid video,https://example.com/ok,10,2,3,1",
        ]
    )
    response = client.post(
        "/api/keyword-videos/import",
        json={"industry_id": industry_id, "keyword": "clinic", "csv_text": csv_text},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["created_count"] == 1
    assert payload["failed_count"] == 1
    assert payload["errors"][0]["row_number"] == 2

    keywords_response = client.get(f"/api/keyword-industries/{industry_id}/keywords")
    assert keywords_response.status_code == 200
    keywords = keywords_response.json()["items"]
    assert len(keywords) == 1
    assert keywords[0]["keyword"] == "clinic"
    assert keywords[0]["video_count"] == 1


def test_delete_keyword_group_removes_videos() -> None:
    industry = client.post("/api/keyword-industries", json={"name": "education"}).json()
    keyword = client.post(
        "/api/keywords",
        json={"industry_id": industry["id"], "keyword": "school"},
    ).json()
    csv_text = "\n".join(
        [
            "source_text,source_url,likes,comments,favorites,shares",
            "school video,https://example.com/school,10,2,3,1",
        ]
    )
    response = client.post(
        "/api/keyword-videos/import",
        json={"industry_id": industry["id"], "keyword": "school", "csv_text": csv_text},
    )
    assert response.status_code == 200

    delete_response = client.delete(f"/api/keywords/{keyword['id']}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/keywords/{keyword['id']}/videos").status_code == 404
    keywords = client.get(f"/api/keyword-industries/{industry['id']}/keywords").json()["items"]
    assert keywords == []


def test_delete_industry_removes_keywords_and_videos() -> None:
    industry = client.post("/api/keyword-industries", json={"name": "auto"}).json()
    keyword = client.post(
        "/api/keywords",
        json={"industry_id": industry["id"], "keyword": "car loan"},
    ).json()
    csv_text = "\n".join(
        [
            "source_text,source_url,likes,comments,favorites,shares",
            "auto video,https://example.com/auto,10,2,3,1",
        ]
    )
    response = client.post(
        "/api/keyword-videos/import",
        json={"industry_id": industry["id"], "keyword": "car loan", "csv_text": csv_text},
    )
    assert response.status_code == 200

    delete_response = client.delete(f"/api/keyword-industries/{industry['id']}")
    assert delete_response.status_code == 204

    assert client.get(f"/api/keyword-industries/{industry['id']}").status_code == 404
    assert client.get(f"/api/keyword-industries/{industry['id']}/keywords").status_code == 404
    assert client.get(f"/api/keywords/{keyword['id']}/videos").status_code == 404
