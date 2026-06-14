from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_copy_analyze_endpoint() -> None:
    response = client.post("/api/copy/analyze", json={"source_text": "先别急着换产品。"})
    assert response.status_code == 200
    assert response.json()["topic"]
