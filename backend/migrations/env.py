"""Alembic 入口，复用业务配置与连接设置，按版本执行数据库变更。"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import URL

from app.config import Settings
from app.database import create_database_engine
from app.documents.models import Document

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 导入文档模型时会将当前表及历史快照表注册到同一份 metadata。
target_metadata = Document.metadata


def run_migrations_offline() -> None:
    """生成可审阅的 SQL，使用与实际迁移相同的数据路径。"""
    settings = Settings()
    context.configure(
        url=URL.create("sqlite+pysqlite", database=str(settings.database_path)),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """连接目标库，在事务中执行升级，执行完毕后释放连接池。"""
    engine = create_database_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
