"""文档业务失败原因，由接口层转换为 HTTP 状态码。"""


class DocumentNotFoundError(Exception):
    """文档不存在或已被移入回收站。"""


class DocumentVersionConflictError(Exception):
    """调用方提交的版本已经过期，需要重新读取文档。"""
