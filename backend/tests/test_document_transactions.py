"""通过并行 HTTP 请求和数据库失败验证创建幂等性、版本竞争与事务回滚。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from app.documents import repository
from app.documents.models import Document, DocumentRevision


def test_simultaneous_open_creates_one_report_and_one_snapshot(
    client: TestClient, engine: Engine
) -> None:
    barrier = Barrier(2)

    def open_at_same_time() -> Response:
        barrier.wait(timeout=5)
        return client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: open_at_same_time(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 1
        assert session.scalar(select(func.count()).select_from(DocumentRevision)) == 1


def test_simultaneous_save_accepts_one_version(client: TestClient, engine: Engine) -> None:
    created = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"}).json()
    document_id = created["id"]
    barrier = Barrier(2)

    def save_at_same_time(body: str) -> Response:
        barrier.wait(timeout=5)
        return client.patch(
            f"/api/v1/documents/{document_id}", json={"expected_version": 1, "content_md": body}
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(save_at_same_time, ("页面 A", "页面 B")))
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(response.json() for response in responses if response.status_code == 200)
    assert client.get(f"/api/v1/documents/{document_id}").json() == winner
    with Session(engine) as session:
        assert session.scalars(select(DocumentRevision.version)).all() == [1, 2]


def duplicate_snapshot(session: Session, document: Document) -> None:
    """故意重复同一快照，触发真实唯一性错误，验证整个写入回滚。"""
    for _ in range(2):
        session.add(
            DocumentRevision(
                document_id=document.id,
                version=document.version,
                title=document.title,
                content_md=document.content_md,
                change_source="manual",
            )
        )
        session.flush()


def test_snapshot_failure_rolls_back_saved_body_and_version(
    client: TestClient,
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"}).json()
    monkeypatch.setattr(repository, "add_revision", duplicate_snapshot)
    url = f"/api/v1/documents/{original['id']}"
    response = client.patch(
        url, json={"expected_version": 1, "content_md": "private-body-sentinel"}
    )
    assert response.status_code == 500
    assert client.get(url).json() == original
    assert "private-body-sentinel" not in caplog.text
    with Session(engine) as session:
        assert session.scalars(select(DocumentRevision.version)).all() == [1]


def test_snapshot_failure_rolls_back_new_document(
    client: TestClient, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repository, "add_revision", duplicate_snapshot)
    response = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})
    assert response.status_code == 500
    with Session(engine) as session:
        assert (
            session.scalar(select(Document).where(Document.period_start == date(2026, 11, 12)))
            is None
        )
        assert session.scalar(select(func.count()).select_from(DocumentRevision)) == 0


def test_busy_database_returns_retryable_response(client: TestClient, engine: Engine) -> None:
    document = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"}).json()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(
                update(Document).where(Document.id == document["id"]).values(title="持有写锁")
            )
            response = client.patch(
                f"/api/v1/documents/{document['id']}",
                json={"expected_version": 1, "content_md": ""},
            )
            assert response.status_code == 503
            assert response.headers["retry-after"] == "1"
        finally:
            transaction.rollback()
    assert client.get(f"/api/v1/documents/{document['id']}").json() == document
