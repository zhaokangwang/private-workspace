"""日报 HTTP 接口，负责参数接收和业务错误的状态码转换。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.documents import service
from app.documents.errors import DocumentNotFoundError, DocumentVersionConflictError
from app.documents.schemas import (
    DocumentDetail,
    DocumentListQuery,
    DocumentPage,
    ErrorResponse,
    OpenDailyReportRequest,
    SaveDocumentRequest,
)

router = APIRouter(
    tags=["日报文档"],
    responses={
        500: {"model": ErrorResponse, "description": "数据库操作失败"},
        503: {"model": ErrorResponse, "description": "数据库正忙，可稍后重试"},
    },
)
DatabaseSession = Annotated[Session, Depends(get_session)]
DocumentId = Annotated[int, Path(gt=0)]


@router.post(
    "/daily-reports/open",
    response_model=DocumentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="打开或创建日报",
    responses={200: {"model": DocumentDetail, "description": "返回已有日报"}},
)
def open_daily_report(
    request: OpenDailyReportRequest, response: Response, session: DatabaseSession
) -> DocumentDetail:
    """传入 {} 时使用北京时间的今天，首次创建返回 201，已存在返回 200。"""
    document, created = service.open_daily_report(session, request.report_date)
    if not created:
        response.status_code = status.HTTP_200_OK
    return document


@router.get("/documents", response_model=DocumentPage, summary="分页查询文档列表")
def list_documents(
    query: Annotated[DocumentListQuery, Query()], session: DatabaseSession
) -> DocumentPage:
    """按报告开始日期筛选，日期范围包含两端，结果按日期倒序返回。"""
    return service.list_documents(session, query)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetail,
    summary="读取文档详情",
    responses={404: {"model": ErrorResponse}},
)
def get_document(document_id: DocumentId, session: DatabaseSession) -> DocumentDetail:
    try:
        return service.get_document(session, document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentDetail,
    summary="按版本保存文档",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def save_document(
    document_id: DocumentId, request: SaveDocumentRequest, session: DatabaseSession
) -> DocumentDetail:
    """只更新传入的标题或正文，每次成功保存递增版本并记录一份人工保存快照。"""
    try:
        return service.save_document(session, document_id, request)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentVersionConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
