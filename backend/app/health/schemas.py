"""健康检查接口的响应结构，与前端 HealthResponse 保持一致。"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """后端进程的运行状态，不代表数据库等外部资源已经就绪。"""

    status: Literal["ok"] = "ok"
    service: str
    version: str
