"""配置 SQLite 连接、ORM 基类和 UTC 时间的存取方式。"""

from collections.abc import Iterator
from datetime import UTC, datetime
from sqlite3 import Connection as SQLiteConnection

from fastapi import Request
from sqlalchemy import URL, DateTime, Engine, create_engine, event
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.types import TypeDecorator

from app.config import Settings


class Base(DeclarativeBase):
    """业务表共享的映射基类，表结构通过 Alembic 创建。"""


class UTCDateTime(TypeDecorator[datetime]):
    """SQLite 保存 UTC 时间值，读取时补回 UTC 时区，拒绝含义不明的无时区输入。"""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("操作时间必须带有时区。")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


def create_database_engine(settings: Settings) -> Engine:
    """创建连接池，每条连接启用外键、WAL 和明确的事务控制。"""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database_url = URL.create("sqlite+pysqlite", database=str(settings.database_path))
    engine = create_engine(
        database_url,
        hide_parameters=True,
        connect_args={
            "check_same_thread": False,
            "autocommit": False,
            "timeout": settings.sqlite_busy_timeout_ms / 1000,
        },
    )

    @event.listens_for(engine, "connect")
    def configure_connection(
        connection: SQLiteConnection, _connection_record: ConnectionPoolEntry
    ) -> None:
        # PRAGMA 必须在事务外设置，随后恢复 Python 3.13 的显式事务模式。
        connection.autocommit = True
        cursor = connection.cursor()
        try:
            cursor.execute(f"PRAGMA busy_timeout = {settings.sqlite_busy_timeout_ms}")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
        finally:
            cursor.close()
            connection.autocommit = False

    return engine


def get_session(request: Request) -> Iterator[Session]:
    """每个请求独立使用会话，服务层管理事务，结束请求时自动释放连接。"""
    engine: Engine = request.app.state.database_engine
    with Session(engine, expire_on_commit=False) as session:
        yield session
