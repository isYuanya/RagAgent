from fastapi.testclient import TestClient

from app.main import app
from app.schemas.system import DependencyStatus, SystemStatusResponse
from app.services import system_status


client = TestClient(app)


def test_system_status_endpoint_returns_dependency_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.system.get_system_status",
        lambda: SystemStatusResponse(
            status="ok",
            services=[
                DependencyStatus(
                    name="postgres",
                    required=True,
                    status="ok",
                    latency_ms=1,
                    endpoint="postgresql+psycopg://rag:***@localhost:5432/rag",
                    message="PostgreSQL is reachable.",
                )
            ],
        ),
    )

    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"][0]["name"] == "postgres"
    assert "***" in payload["services"][0]["endpoint"]


def test_overall_status_is_down_when_required_service_fails() -> None:
    response = SystemStatusResponse(
        status=system_status._overall_status(
            [
                DependencyStatus(
                    name="postgres",
                    required=True,
                    status="down",
                    message="not reachable",
                ),
                DependencyStatus(
                    name="milvus",
                    required=False,
                    status="ok",
                    message="reachable",
                ),
            ]
        ),
        services=[],
    )

    assert response.status == "down"


def test_overall_status_is_degraded_when_only_optional_service_fails() -> None:
    status = system_status._overall_status(
        [
            DependencyStatus(name="postgres", required=True, status="ok", message="reachable"),
            DependencyStatus(name="redis", required=True, status="ok", message="reachable"),
            DependencyStatus(name="milvus", required=False, status="degraded", message="not reachable"),
        ]
    )

    assert status == "degraded"


def test_safe_url_redacts_password_and_query() -> None:
    redacted = system_status._safe_url(
        "postgresql+psycopg://rag:secret@localhost:5432/rag?sslmode=require"
    )

    assert redacted == "postgresql+psycopg://rag:***@localhost:5432/rag"
    assert "secret" not in redacted
    assert "sslmode" not in redacted


def test_copy_import_worker_down_when_no_worker_registered(monkeypatch) -> None:
    class FakeWorker:
        @staticmethod
        def all(connection):
            return []

    monkeypatch.setattr(system_status, "Worker", FakeWorker)
    monkeypatch.setattr(system_status, "_redis", lambda: object())

    result = system_status.check_copy_import_worker()

    assert result.status == "down"
    assert result.required is True
    assert "No worker" in result.message


def test_copy_import_worker_ok_when_worker_listens_to_queue(monkeypatch) -> None:
    class FakeWorkerInstance:
        name = "worker-1"

        def queue_names(self):
            return ["copy_import"]

    class FakeWorker:
        @staticmethod
        def all(connection):
            return [FakeWorkerInstance()]

    monkeypatch.setattr(system_status, "Worker", FakeWorker)
    monkeypatch.setattr(system_status, "_redis", lambda: object())

    result = system_status.check_copy_import_worker()

    assert result.status == "ok"
    assert "1 worker" in result.message
