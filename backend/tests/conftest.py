"""所有存储测试使用独立临时库，并通过实际 Alembic 迁移创建表。"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.config import BACKEND_ROOT, Settings
from app.database import create_database_engine
from app.main import create_app


@pytest.fixture
def database_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("WORKSPACE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("WORKSPACE_SQLITE_BUSY_TIMEOUT_MS", "250")
    return Settings()


@pytest.fixture
def migration_config(database_settings: Settings) -> Config:
    assert database_settings.database_path.parent.is_absolute()
    return Config(str(BACKEND_ROOT / "alembic.ini"))


@pytest.fixture
def engine(migration_config: Config, database_settings: Settings) -> Iterator[Engine]:
    command.upgrade(migration_config, "head")
    database_engine = create_database_engine(database_settings)
    try:
        yield database_engine
    finally:
        database_engine.dispose()


@pytest.fixture
def client(engine: Engine, database_settings: Settings) -> Iterator[TestClient]:
    # engine 夹具先迁移临时库，应用随后按相同设置建立独立连接池。
    assert engine.url.database == str(database_settings.database_path)
    with TestClient(create_app(database_settings), raise_server_exceptions=False) as test_client:
        yield test_client
