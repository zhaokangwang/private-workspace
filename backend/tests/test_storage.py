"""覆盖迁移后的真实表约束、事务、连接设置和跨连接持久化。"""

from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, delete, inspect, select, text, update
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import create_database_engine
from app.documents.models import Document, DocumentRevision


def make_document(
    document_type: str = "daily",
    start: date = date(2026, 11, 11),
    end: date | None = None,
) -> Document:
    return Document(
        document_type=document_type,
        title="测试日报",
        period_start=start,
        period_end=end or start,
        content_md="# 工作记录\n\n- 完成存储验证\n",
    )


def test_initial_migration_is_repeatable_and_matches_models(
    engine: Engine, migration_config: Config
) -> None:
    command.upgrade(migration_config, "head")
    assert set(inspect(engine).get_table_names()) >= {
        "document",
        "document_revision",
        "alembic_version",
    }
    command.check(migration_config)


def test_connection_settings_apply_to_every_connection(engine: Engine) -> None:
    with engine.connect() as first, engine.connect() as second:
        for connection in (first, second):
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 250


def test_repeated_upgrade_preserves_existing_content(
    engine: Engine, migration_config: Config
) -> None:
    with Session(engine) as session, session.begin():
        session.add(make_document())
    command.upgrade(migration_config, "head")
    with Session(engine) as session:
        document = session.scalar(select(Document))
        assert document is not None
        assert document.content_md == "# 工作记录\n\n- 完成存储验证\n"


def test_migration_can_be_reverted_and_reapplied(engine: Engine, migration_config: Config) -> None:
    # 仅在测试夹具生成的临时空库执行，验证降级顺序满足外键依赖。
    command.downgrade(migration_config, "base")
    assert "document" not in inspect(engine).get_table_names()
    command.upgrade(migration_config, "head")
    command.check(migration_config)


def test_content_survives_engine_restart(engine: Engine, database_settings: Settings) -> None:
    with Session(engine) as session, session.begin():
        document = make_document()
        session.add(document)
        session.flush()
        document_id = document.id
        assert document.created_at.tzinfo == UTC
    engine.dispose()

    reopened_engine = create_database_engine(database_settings)
    try:
        with Session(reopened_engine) as session:
            loaded_document = session.get(Document, document_id)
            assert loaded_document is not None
            assert loaded_document.content_md == "# 工作记录\n\n- 完成存储验证\n"
            assert loaded_document.period_start == date(2026, 11, 11)
            assert loaded_document.version == 1
            assert loaded_document.document_metadata == {}
            assert loaded_document.created_at.tzinfo == UTC
    finally:
        reopened_engine.dispose()


def test_same_day_duplicate_is_rejected(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        session.add(make_document())
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.add(make_document())


def test_soft_delete_allows_new_document_but_restore_conflicts(engine: Engine) -> None:
    with Session(engine) as session, session.begin():
        original = make_document()
        original.deleted_at = datetime.now(UTC)
        session.add(original)
        session.flush()
        original_id = original.id
    with Session(engine) as session, session.begin():
        session.add(make_document())
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.execute(update(Document).where(Document.id == original_id).values(deleted_at=None))


@pytest.mark.parametrize(
    ("document_type", "start", "end"),
    [
        ("weekly", date(2026, 11, 9), date(2026, 11, 15)),
        ("monthly", date(2026, 11, 1), date(2026, 11, 30)),
        ("monthly", date(2028, 2, 1), date(2028, 2, 29)),
    ],
)
def test_valid_report_periods(engine: Engine, document_type: str, start: date, end: date) -> None:
    with Session(engine) as session, session.begin():
        session.add(make_document(document_type, start, end))


@pytest.mark.parametrize(
    ("document_type", "start", "end"),
    [
        ("unknown", date(2026, 11, 11), date(2026, 11, 11)),
        ("daily", date(2026, 11, 11), date(2026, 11, 12)),
        ("weekly", date(2026, 11, 10), date(2026, 11, 16)),
        ("weekly", date(2026, 11, 9), date(2026, 11, 14)),
        ("monthly", date(2026, 11, 2), date(2026, 11, 30)),
        ("monthly", date(2027, 2, 1), date(2027, 2, 28) + timedelta(days=1)),
    ],
)
def test_invalid_report_periods_are_rejected(
    engine: Engine, document_type: str, start: date, end: date
) -> None:
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.add(make_document(document_type, start, end))


@pytest.mark.parametrize("title", ["", "   ", "长" * 201])
def test_invalid_title_is_rejected(engine: Engine, title: str) -> None:
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        document = make_document()
        document.title = title
        session.add(document)


def test_invalid_version_and_metadata_are_rejected(engine: Engine) -> None:
    for column, value in (("version", "0"), ("metadata", "'[]'")):
        # 列名和 SQL 片段来自固定测试用例，用于验证绕过 ORM 时数据库仍会拒绝非法数据。
        statement = text(
            f"INSERT INTO document (title, period_start, period_end, {column}) "
            f"VALUES ('测试', '2026-11-11', '2026-11-11', {value})"
        )
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(statement)


def test_revision_constraints_and_foreign_key(engine: Engine) -> None:
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.add(
            DocumentRevision(
                document_id=999, version=1, title="测试", content_md="", change_source="manual"
            )
        )
    with Session(engine) as session, session.begin():
        document = make_document()
        session.add(document)
        session.flush()
        document_id = document.id
        session.add(
            DocumentRevision(
                document_id=document_id,
                version=1,
                title="测试",
                content_md="",
                change_source="manual",
            )
        )
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.add(
            DocumentRevision(
                document_id=document_id,
                version=1,
                title="重复版本",
                content_md="",
                change_source="manual",
            )
        )
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        session.execute(delete(Document).where(Document.id == document_id))


def test_document_and_snapshot_roll_back_together(engine: Engine) -> None:
    with pytest.raises(IntegrityError), Session(engine) as session, session.begin():
        document = make_document()
        session.add(document)
        session.flush()
        session.add(
            DocumentRevision(
                document_id=document.id,
                version=1,
                title="测试",
                content_md="",
                change_source="invalid",
            )
        )
    with Session(engine) as session:
        assert session.scalar(select(Document.id)) is None


def test_utc_conversion_and_naive_time_rejection(engine: Engine) -> None:
    local_time = datetime(2026, 11, 11, 18, tzinfo=timezone(timedelta(hours=8)))
    with Session(engine) as session, session.begin():
        document = make_document()
        document.created_at = local_time
        session.add(document)
    with Session(engine) as session:
        loaded = session.scalar(select(Document))
        assert loaded is not None
        assert loaded.created_at == datetime(2026, 11, 11, 10, tzinfo=UTC)
    with pytest.raises(StatementError), Session(engine) as session, session.begin():
        document = make_document(start=date(2026, 11, 12))
        document.created_at = datetime(2026, 11, 12, 10)
        session.add(document)
