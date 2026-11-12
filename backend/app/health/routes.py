"""提供轻量的健康检查接口，供前端和部署检查调用。"""

from fastapi import APIRouter

from app import __version__
from app.health.schemas import HealthResponse

router = APIRouter(tags=["系统状态"])


@router.get("/health", summary="检查后端服务", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """返回当前后端进程的服务名称和版本。"""
    return HealthResponse(service="私人工作站", version=__version__)
