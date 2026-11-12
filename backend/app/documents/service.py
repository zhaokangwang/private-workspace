"""处理日报创建、读取和版本化保存，并明确事务边界。"""

from datetime import date

from sqlalchemy.orm import Session

from app.documents import repository
from app.documents.errors import DocumentNotFoundError, DocumentVersionConflictError
from app.documents.schemas import (
    DocumentDetail,
    DocumentListQuery,
    DocumentPage,
    DocumentSummary,
    SaveDocumentRequest,
)


def open_daily_report(session: Session, report_date: date) -> tuple[DocumentDetail, bool]:
    """首次创建时保存初始快照；重复或并发打开时返回已有内容。"""
    content_md = (
        f"# {report_date.isoformat()} 日报\n\n"
        "## 今日完成\n\n- \n\n## 遇到的问题\n\n- \n\n## 明日计划\n\n- \n"
    )
    with session.begin():
        document = repository.insert_daily_report(session, report_date, content_md)
        created = document is not None
        if document is None:
            document = repository.find_daily_report(session, report_date)
        else:
            repository.add_revision(session, document)
        result = DocumentDetail.model_validate(document)
    return result, created


def get_document(session: Session, document_id: int) -> DocumentDetail:
    with session.begin():
        document = repository.find_active_document(session, document_id)
        if document is None:
            raise DocumentNotFoundError("文档不存在或已移入回收站。")
        return DocumentDetail.model_validate(document)


def list_documents(session: Session, query: DocumentListQuery) -> DocumentPage:
    with session.begin():
        documents, total = repository.list_documents(session, query)
        return DocumentPage(
            items=[DocumentSummary.model_validate(document) for document in documents],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


def save_document(
    session: Session, document_id: int, request: SaveDocumentRequest
) -> DocumentDetail:
    """原子更新正文和版本，并在同一事务中保存快照，失败时一起回滚。"""
    with session.begin():
        document = repository.update_document(session, document_id, request)
        if document is None:
            if repository.find_active_document(session, document_id) is None:
                raise DocumentNotFoundError("文档不存在或已移入回收站。")
            raise DocumentVersionConflictError("文档已被修改，请保留当前输入并重新读取最新版本。")
        repository.add_revision(session, document)
        return DocumentDetail.model_validate(document)
