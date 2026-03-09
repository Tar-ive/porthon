"""In-memory idempotency middleware with TTL."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

# TTL in seconds (24 hours)
_TTL = 86400

# In-memory store: key → (response_body, status_code, timestamp)
_store: dict[str, tuple[Any, int, float]] = {}


def _prune() -> None:
    """Remove expired entries."""
    now = time.time()
    expired = [k for k, (_, _, ts) in _store.items() if now - ts > _TTL]
    for k in expired:
        del _store[k]


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in {"POST", "PUT", "DELETE"}:
            return await call_next(request)

        idem_key = request.headers.get("idempotency-key")
        if not idem_key:
            return await call_next(request)

        # Scope key to method + path + idempotency key
        cache_key = hashlib.sha256(f"{request.method}:{request.url.path}:{idem_key}".encode()).hexdigest()

        _prune()

        if cache_key in _store:
            body, status, _ = _store[cache_key]
            resp = JSONResponse(content=body, status_code=status)
            resp.headers["idempotent-replayed"] = "true"
            return resp

        response = await call_next(request)

        # Only cache JSON responses
        if "application/json" in response.headers.get("content-type", ""):
            body_bytes = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                if isinstance(chunk, str):
                    body_bytes += chunk.encode()
                else:
                    body_bytes += chunk
            try:
                body = json.loads(body_bytes)
                _store[cache_key] = (body, response.status_code, time.time())
                return JSONResponse(content=body, status_code=response.status_code, headers=dict(response.headers))
            except (json.JSONDecodeError, Exception):
                pass

        return response
