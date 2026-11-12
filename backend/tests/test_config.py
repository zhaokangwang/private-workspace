"""验证从 IDE、命令行和自定义目录启动时，配置的含义一致。"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Settings


def test_relative_data_path_is_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORKSPACE_DATA_DIR", "data")
    monkeypatch.chdir(tmp_path)
    assert Settings().database_path == PROJECT_ROOT / "data/workspace.db"


def test_custom_data_path_from_environment(database_settings: Settings) -> None:
    assert database_settings.database_path.name == "workspace.db"
    assert database_settings.database_path.is_absolute()
    assert database_settings.sqlite_busy_timeout_ms == 250


@pytest.mark.parametrize("timeout", [-1, 60001])
def test_invalid_lock_timeout_is_rejected(timeout: int, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        Settings(data_dir=tmp_path, sqlite_busy_timeout_ms=timeout)
