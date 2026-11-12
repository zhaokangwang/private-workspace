"""读取环境配置，统一确定数据目录，避免工作目录影响数据库位置。"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    """环境变量优先于 backend/.env，显式传入的参数优先级最高。"""

    model_config = SettingsConfigDict(
        env_prefix="WORKSPACE_",
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    data_dir: Path = PROJECT_ROOT / "data"
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=0, le=60000)

    @field_validator("data_dir")
    @classmethod
    def resolve_data_dir(cls, value: Path) -> Path:
        """相对路径固定从项目根目录解析，支持用户目录和绝对路径。"""
        expanded_path = value.expanduser()
        if not expanded_path.is_absolute():
            expanded_path = PROJECT_ROOT / expanded_path
        return expanded_path.resolve()

    @property
    def database_path(self) -> Path:
        return self.data_dir / "workspace.db"
