"""Common API response envelope and error types (02 §6)."""

from __future__ import annotations

from typing import Any


def ok(data: Any, meta: dict | None = None) -> dict:
    """Standard success envelope."""
    return {"data": data, "meta": meta or {}}


class APIError(Exception):
    """Application-level error rendered as {"error": {"code", "message"}}."""

    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def not_found(message: str) -> APIError:
    return APIError(code="NOT_FOUND", message=message, http_status=404)


def validation_error(message: str) -> APIError:
    return APIError(code="VALIDATION_ERROR", message=message, http_status=400)


def not_implemented(message: str = "This feature is not implemented yet.") -> APIError:
    return APIError(code="NOT_IMPLEMENTED", message=message, http_status=501)
