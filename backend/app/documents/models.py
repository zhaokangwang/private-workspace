"""文档当前内容和历史快照的 ORM 映射，事务与业务规则由 service.py 处理。"""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, UTCDateTime


class Document(Base):
    """保存文档当前内容，未删除的同类报告在同一周期内唯一。"""

    __tablename__ = "document"
    __table_args__ = (
        CheckConstraint("document_type IN ('daily', 'weekly', 'monthly')", name="ck_document_type"),
        CheckConstraint(
            "length(trim(title)) > 0 AND length(title) <= 200", name="ck_document_title"
        ),
        CheckConstraint("typeof(version) = 'integer' AND version >= 1", name="ck_document_version"),
        CheckConstraint(
            "json_valid(metadata) AND json_type(metadata) = 'object'", name="ck_document_metadata"
        ),
        CheckConstraint(
            "date(period_start) IS NOT NULL AND date(period_end) IS NOT NULL "
            "AND period_start = date(period_start) AND period_end = date(period_end) AND ("
            "(document_type = 'daily' AND period_end = period_start) OR "
            "(document_type = 'weekly' AND strftime('%w', period_start) = '1' "
            "AND period_end = date(period_start, '+6 days')) OR "
            "(document_type = 'monthly' AND strftime('%d', period_start) = '01' "
            "AND period_end = date(period_start, 'start of month', '+1 month', '-1 day'))) ",
            name="ck_document_period",
        ),
        Index(
            "uk_document_active_period",
            "document_type",
            "period_start",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
        ),
        Index(
            "idx_document_active_date",
            "period_start",
            "id",
            sqlite_where=text("deleted_at IS NULL"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(16), default="daily", server_default="daily")
    title: Mapped[str] = mapped_column(String(200))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    content_md: Mapped[str] = mapped_column(Text, default="", server_default="")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    # metadata 是 SQLAlchemy 的保留属性，因此 Python 属性使用 document_metadata。
    # 修改扩展信息时赋予新的字典，以便 ORM 可靠地检测变更。
    document_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), default=None)


class DocumentRevision(Base):
    """保存特定版本的标题和 Markdown，文档软删除后继续保留快照。"""

    __tablename__ = "document_revision"
    __table_args__ = (
        CheckConstraint("typeof(version) = 'integer' AND version >= 1", name="ck_revision_version"),
        CheckConstraint(
            "length(trim(title)) > 0 AND length(title) <= 200", name="ck_revision_title"
        ),
        CheckConstraint(
            "change_source IN ('manual', 'periodic', 'import', 'agent', 'restore')",
            name="ck_revision_source",
        ),
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("document.id", name="fk_revision_document", ondelete="RESTRICT"),
        primary_key=True,
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content_md: Mapped[str] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.current_timestamp()
    )
