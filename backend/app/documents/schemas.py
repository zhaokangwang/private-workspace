"""日报接口的请求、响应和分页约定，校验不符合业务范围的输入。"""

from datetime import date, datetime
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

DocumentType = Literal["daily", "weekly", "monthly"]
DocumentTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


def beijing_today() -> date:
    """通过明确的业务时区确定今天，避免服务器时区影响日报所属日期。"""
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


class OpenDailyReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_date: date = Field(default_factory=beijing_today)


class DocumentListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: DocumentType = "daily"
    start_date: date | None = None
    end_date: date | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date is not None and self.end_date is not None:
            if self.start_date > self.end_date:
                raise ValueError("开始日期不能晚于结束日期。")
        return self


class SaveDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1, strict=True)
    title: DocumentTitle | None = None
    content_md: str | None = None

    @field_validator("title", "content_md")
    @classmethod
    def reject_explicit_null(cls, value: str | None) -> str:
        # 未传入的字段保留默认值；显式传 null 会被拒绝，避免清空内容的含义不明确。
        if value is None:
            raise ValueError("修改字段不能为 null。清空正文请传入空字符串。")
        return value

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not self.model_fields_set.intersection({"title", "content_md"}):
            raise ValueError("至少需要提供标题或 Markdown 正文。")
        return self


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    document_type: DocumentType
    title: str
    period_start: date
    period_end: date
    version: int
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    content_md: str
    metadata: dict[str, object] = Field(validation_alias="document_metadata")


class DocumentPage(BaseModel):
    items: list[DocumentSummary]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    detail: str
