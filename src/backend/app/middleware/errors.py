"""Structured error handler middleware."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiException(Exception):
    """Raise to return a structured Stripe-style error."""

    def __init__(
        self,
        status_code: int = 400,
        type: str = "invalid_request_error",
        code: str = "unknown",
        message: str = "",
        param: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.type = type
        self.code = code
        self.message = message
        self.param = param
        super().__init__(message)


async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.type,
                "code": exc.code,
                "message": exc.message,
                "param": exc.param,
                "doc_url": f"https://api.porthon.ai/docs/errors#{exc.code}",
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "api_error",
                "code": "internal_error",
                "message": "An internal error occurred.",
            }
        },
    )
