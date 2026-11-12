"""创建文档当前内容、历史快照以及周期唯一性约束。"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_documents"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """创建首版存储结构，保留后续升级所需的独立迁移记录。"""
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_type", sa.String(16), nullable=False, server_default="daily"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "document_type IN ('daily', 'weekly', 'monthly')", name="ck_document_type"
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0 AND length(title) <= 200", name="ck_document_title"
        ),
        sa.CheckConstraint(
            "typeof(version) = 'integer' AND version >= 1", name="ck_document_version"
        ),
        sa.CheckConstraint(
            "json_valid(metadata) AND json_type(metadata) = 'object'", name="ck_document_metadata"
        ),
        sa.CheckConstraint(
            "date(period_start) IS NOT NULL AND date(period_end) IS NOT NULL "
            "AND period_start = date(period_start) AND period_end = date(period_end) AND ("
            "(document_type = 'daily' AND period_end = period_start) OR "
            "(document_type = 'weekly' AND strftime('%w', period_start) = '1' "
            "AND period_end = date(period_start, '+6 days')) OR "
            "(document_type = 'monthly' AND strftime('%d', period_start) = '01' "
            "AND period_end = date(period_start, 'start of month', '+1 month', '-1 day'))) ",
            name="ck_document_period",
        ),
        sqlite_autoincrement=True,
    )
    op.create_index(
        "uk_document_active_period",
        "document",
        ["document_type", "period_start"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_document_active_date",
        "document",
        ["period_start", "id"],
        sqlite_where=sa.text("deleted_at IS NULL"),
    )
    create_revision_table()


def create_revision_table() -> None:
    """历史快照引用文档，限制直接删除仍有关联快照的文档。"""
    op.create_table(
        "document_revision",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("change_source", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()
        ),
        sa.PrimaryKeyConstraint("document_id", "version"),
        sa.ForeignKeyConstraint(
            ["document_id"], ["document.id"], name="fk_revision_document", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "typeof(version) = 'integer' AND version >= 1", name="ck_revision_version"
        ),
        sa.CheckConstraint(
            "length(trim(title)) > 0 AND length(title) <= 200", name="ck_revision_title"
        ),
        sa.CheckConstraint(
            "change_source IN ('manual', 'periodic', 'import', 'agent', 'restore')",
            name="ck_revision_source",
        ),
    )


def downgrade() -> None:
    """移除两张业务表，此操作会删除其中的数据。"""
    op.drop_table("document_revision")
    op.drop_index("idx_document_active_date", table_name="document")
    op.drop_index("uk_document_active_period", table_name="document")
    op.drop_table("document")
