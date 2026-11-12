"""执行文档查询与原子写入，事务的提交和回滚由业务服务决定。"""

from collections.abc import Sequence
from datetime import UTC, date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session, load_only

from app.documents.models import Document, DocumentRevision
from app.documents.schemas import DocumentListQuery, SaveDocumentRequest


def insert_daily_report(session: Session, report_date: date, content_md: str) -> Document | None:
    """先尝试写入，冲突时返回空，避免先读再写在并发创建时发生竞争。"""
    statement = (
        insert(Document)
        .values(
            document_type="daily",
            title=f"{report_date.isoformat()} 日报",
            period_start=report_date,
            period_end=report_date,
            content_md=content_md,
        )
        .on_conflict_do_nothing(
            index_elements=[Document.document_type, Document.period_start],
            index_where=Document.deleted_at.is_(None),
        )
        .returning(Document)
    )
    return session.scalars(statement).one_or_none()


def find_daily_report(session: Session, report_date: date) -> Document:
    statement = select(Document).where(
        Document.document_type == "daily",
        Document.period_start == report_date,
        Document.deleted_at.is_(None),
    )
    return session.scalars(statement).one()


def find_active_document(session: Session, document_id: int) -> Document | None:
    statement = select(Document).where(Document.id == document_id, Document.deleted_at.is_(None))
    return session.scalars(statement).one_or_none()


def list_documents(session: Session, query: DocumentListQuery) -> tuple[Sequence[Document], int]:
    statement = select(Document).where(
        Document.document_type == query.document_type, Document.deleted_at.is_(None)
    )
    if query.start_date is not None:
        statement = statement.where(Document.period_start >= query.start_date)
    if query.end_date is not None:
        statement = statement.where(Document.period_start <= query.end_date)

    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    statement = (
        statement.options(
            load_only(
                Document.id,
                Document.document_type,
                Document.title,
                Document.period_start,
                Document.period_end,
                Document.version,
                Document.created_at,
                Document.updated_at,
            )
        )
        .order_by(Document.period_start.desc(), Document.id.desc())
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )
    return session.scalars(statement).all(), total


def update_document(
    session: Session, document_id: int, request: SaveDocumentRequest
) -> Document | None:
    """将版本检查放进同一条 UPDATE，只有一位竞争者可以写入当前版本。"""
    changes: dict[str, object] = {
        "version": Document.version + 1,
        "updated_at": datetime.now(UTC),
    }
    if request.title is not None:
        changes["title"] = request.title
    if request.content_md is not None:
        changes["content_md"] = request.content_md
    statement = (
        update(Document)
        .where(
            Document.id == document_id,
            Document.version == request.expected_version,
            Document.deleted_at.is_(None),
        )
        .values(**changes)
        .returning(Document)
        .execution_options(populate_existing=True)
    )
    return session.scalars(statement).one_or_none()


def add_revision(session: Session, document: Document) -> None:
    """记录本次人工保存后的完整标题与正文，失败时交由服务层回滚整个事务。"""
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
