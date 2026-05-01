from __future__ import annotations

from dataclasses import dataclass

from src.models.account_raw import CollectionErrorCode


@dataclass(frozen=True)
class CrawlError(RuntimeError):
    """采集链路统一异常。

    Attributes:
        error_code: 归因码（用于入库与统计）。
        retryable: 是否建议自动重试。
    """

    error_code: str = CollectionErrorCode.UNKNOWN.value
    retryable: bool = True

    def __init__(self, message: str, error_code: str, retryable: bool = True):
        super().__init__(message)
        object.__setattr__(self, "error_code", error_code)
        object.__setattr__(self, "retryable", retryable)


class LoginRequiredError(CrawlError):
    """需要登录/被登录弹窗拦截。通常不建议自动重试，应先刷新登录态。"""

    def __init__(self, message: str = "login required"):
        super().__init__(message, error_code=CollectionErrorCode.LOGIN_REQUIRED.value, retryable=False)


class RateLimitedError(CrawlError):
    """触发限流（429 等），可重试。"""

    def __init__(self, message: str = "rate limited"):
        super().__init__(message, error_code=CollectionErrorCode.RATE_LIMITED.value, retryable=True)

