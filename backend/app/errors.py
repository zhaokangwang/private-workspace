"""统一数据库失败响应，向调用方提供可重试状态并保护内部错误信息。"""

import logging
import sqlite3

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


async def handle_database_error(_request: Request, exception: Exception) -> JSONResponse:
    """锁等待超时返回 503，其余数据库异常记录后返回通用错误。"""
    if isinstance(exception, OperationalError):
        error_code = getattr(exception.orig, "sqlite_errorcode", None)
        # SQLite 扩展错误码的低 8 位是基础错误码，包含 BUSY_SNAPSHOT 等锁竞争情况。
        if isinstance(error_code, int) and error_code & 0xFF in (
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        ):
            return JSONResponse(
                status_code=503,
                content={"detail": "数据库正忙，本次操作未完成，请稍后重试。"},
                headers={"Retry-After": "1"},
            )
    logger.error("数据库操作失败，当前事务已回滚。", exc_info=exception)
    return JSONResponse(status_code=500, content={"detail": "数据保存或读取失败，请稍后重试。"})
