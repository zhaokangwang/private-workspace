"""通过 HTTP 入口验证日报创建、读取、列表、保存与请求校验。"""

from datetime import UTC, datetime, tzinfo
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentRevision
from app.documents.schemas import DocumentDetail


@pytest.fixture
def report(client: TestClient) -> DocumentDetail:
    response = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})
    assert response.status_code == 201
    return DocumentDetail.model_validate(response.json())


def test_open_initializes_template_and_existing_open_preserves_content(
    client: TestClient, report: DocumentDetail, engine: Engine
) -> None:
    assert report.title == "2026-11-12 日报"
    assert report.version == 1
    assert "## 今日完成" in report.content_md
    assert report.metadata == {}
    response = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})
    assert response.status_code == 200
    assert response.json()["id"] == report.id
    with Session(engine) as session:
        assert session.scalars(select(DocumentRevision.version)).all() == [1]


def test_today_uses_beijing_date(client: TestClient) -> None:
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            assert tz == ZoneInfo("Asia/Shanghai")
            return datetime(2026, 11, 11, 16, 30, tzinfo=UTC).astimezone(tz)

    with patch("app.documents.schemas.datetime", FixedDateTime):
        response = client.post("/api/v1/daily-reports/open", json={})
    assert response.status_code == 201
    assert response.json()["period_start"] == "2026-11-12"
    assert response.json()["created_at"].endswith("Z")


def test_read_and_save_round_trip(
    client: TestClient, report: DocumentDetail, engine: Engine
) -> None:
    saved = client.patch(
        f"/api/v1/documents/{report.id}",
        json={
            "expected_version": 1,
            "title": "  新标题  ",
            "content_md": "# 中文\n\n```python\nprint(1)\n```\n",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert saved.json()["title"] == "新标题"
    loaded = client.get(f"/api/v1/documents/{report.id}")
    assert loaded.status_code == 200
    assert loaded.json() == saved.json()
    with Session(engine) as session:
        snapshots = session.scalars(
            select(DocumentRevision).order_by(DocumentRevision.version)
        ).all()
        assert [snapshot.version for snapshot in snapshots] == [1, 2]
        assert snapshots[0].content_md == report.content_md
        assert snapshots[1].content_md == saved.json()["content_md"]


def test_partial_save_keeps_omitted_fields_and_allows_empty_body(
    client: TestClient, report: DocumentDetail
) -> None:
    response = client.patch(
        f"/api/v1/documents/{report.id}", json={"expected_version": 1, "title": "仅修改标题"}
    )
    assert response.status_code == 200
    assert response.json()["content_md"] == report.content_md
    response = client.patch(
        f"/api/v1/documents/{report.id}", json={"expected_version": 2, "content_md": ""}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "仅修改标题"
    assert response.json()["content_md"] == ""
    assert response.json()["version"] == 3


def test_stale_save_is_rejected_without_new_snapshot(
    client: TestClient, report: DocumentDetail, engine: Engine
) -> None:
    url = f"/api/v1/documents/{report.id}"
    assert (
        client.patch(url, json={"expected_version": 1, "content_md": "已保存"}).status_code == 200
    )
    response = client.patch(url, json={"expected_version": 1, "content_md": "过期内容"})
    assert response.status_code == 409
    assert client.get(url).json()["content_md"] == "已保存"
    reopened = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})
    assert reopened.status_code == 200
    assert reopened.json()["content_md"] == "已保存"
    with Session(engine) as session:
        assert session.scalars(select(DocumentRevision.version)).all() == [1, 2]


def test_list_pagination_dates_and_summary(client: TestClient) -> None:
    for report_date in ("2026-11-10", "2026-11-11", "2026-11-12"):
        assert (
            client.post("/api/v1/daily-reports/open", json={"report_date": report_date}).status_code
            == 201
        )
    response = client.get("/api/v1/documents", params={"page": 2, "page_size": 1})
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert page["page"] == 2
    assert page["page_size"] == 1
    assert page["items"][0]["period_start"] == "2026-11-11"
    assert "content_md" not in page["items"][0]
    response = client.get(
        "/api/v1/documents", params={"start_date": "2026-11-11", "end_date": "2026-11-12"}
    )
    assert response.json()["total"] == 2
    assert [item["period_start"] for item in response.json()["items"]] == [
        "2026-11-12",
        "2026-11-11",
    ]
    assert client.get("/api/v1/documents", params={"page": 99}).json()["items"] == []
    assert client.get("/api/v1/documents", params={"document_type": "weekly"}).json()["total"] == 0


def test_deleted_document_is_hidden_and_new_open_gets_new_id(
    client: TestClient, report: DocumentDetail, engine: Engine
) -> None:
    with Session(engine) as session, session.begin():
        session.execute(
            update(Document).where(Document.id == report.id).values(deleted_at=datetime.now(UTC))
        )
    url = f"/api/v1/documents/{report.id}"
    assert client.get(url).status_code == 404
    assert client.patch(url, json={"expected_version": 1, "content_md": "修改"}).status_code == 404
    assert client.get("/api/v1/documents").json()["total"] == 0
    reopened = client.post("/api/v1/daily-reports/open", json={"report_date": "2026-11-12"})
    assert reopened.status_code == 201
    assert reopened.json()["id"] != report.id


def test_unknown_document_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/documents/999").status_code == 404
    assert (
        client.patch(
            "/api/v1/documents/999", json={"expected_version": 1, "content_md": ""}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_version": 1},
        {"expected_version": 1, "title": "   "},
        {"expected_version": 1, "title": "长" * 201},
        {"expected_version": 1, "title": None},
        {"expected_version": 1, "content_md": None},
        {"expected_version": 0, "content_md": ""},
        {"expected_version": True, "content_md": ""},
        {"content_md": ""},
        {"expected_version": 1, "content_md": "", "period_start": "2026-11-13"},
    ],
)
def test_invalid_save_is_rejected(client: TestClient, payload: dict[str, object]) -> None:
    assert client.patch("/api/v1/documents/1", json=payload).status_code == 422


@pytest.mark.parametrize(
    "parameters",
    [
        {"page": 0},
        {"page_size": 101},
        {"document_type": "unknown"},
        {"start_date": "2026-11-13", "end_date": "2026-11-12"},
        {"start_date": "invalid"},
        {"unknown": "value"},
    ],
)
def test_invalid_list_query_is_rejected(
    client: TestClient, parameters: dict[str, str | int]
) -> None:
    assert client.get("/api/v1/documents", params=parameters).status_code == 422


@pytest.mark.parametrize("document_id", ["0", "-1", "invalid"])
def test_invalid_id_is_rejected(client: TestClient, document_id: str) -> None:
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 422


@pytest.mark.parametrize(
    "payload", [{"report_date": "2026-02-30"}, {"report_date": None}, {"extra": 1}]
)
def test_invalid_open_is_rejected(client: TestClient, payload: dict[str, object]) -> None:
    assert client.post("/api/v1/daily-reports/open", json=payload).status_code == 422


def test_openapi_lists_the_four_operations(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "post" in schema["paths"]["/api/v1/daily-reports/open"]
    assert "get" in schema["paths"]["/api/v1/documents"]
    assert set(schema["paths"]["/api/v1/documents/{document_id}"]) >= {"get", "patch"}
