"""Figma REST API client aligned to docs/api/figma_api/openapi.yaml."""

from __future__ import annotations

import os
from typing import Any

import httpx


class FigmaApiError(RuntimeError):
    """Raised for Figma REST API failures."""

    def __init__(self, status_code: int, message: str, body: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _env_api_key() -> str | None:
    api_key = os.environ.get("FIGMA_API_KEY", "").strip()
    return api_key or None


class FigmaAPI:
    """Direct Figma REST API client (token auth via X-Figma-Token)."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = "https://api.figma.com",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.api_key = (api_key or _env_api_key() or "").strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise FigmaApiError(
                status_code=400,
                message="FIGMA_API_KEY is not configured.",
            )

        headers = {
            "X-Figma-Token": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
        ) as client:
            resp = await client.request(
                method=method.upper(),
                url=path,
                headers=headers,
                params=params,
                json=json_body,
            )

        if resp.status_code >= 400:
            payload: Any
            try:
                payload = resp.json()
            except ValueError:
                payload = resp.text
            message = f"Figma API request failed ({resp.status_code})"
            raise FigmaApiError(status_code=resp.status_code, message=message, body=payload)

        if resp.status_code == 204:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"raw": resp.text}

    async def get_me(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/me")

    async def get_comments(self, file_key: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/files/{file_key}/comments")

    async def post_comment(
        self,
        file_key: str,
        message: str,
        *,
        comment_id: str | None = None,
        client_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"message": message}
        if comment_id:
            payload["comment_id"] = comment_id
        if isinstance(client_meta, dict) and client_meta:
            payload["client_meta"] = client_meta
        return await self._request("POST", f"/v1/files/{file_key}/comments", json_body=payload)

    async def delete_comment(self, file_key: str, comment_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/v1/files/{file_key}/comments/{comment_id}")

    async def list_webhooks(
        self,
        *,
        context: str | None = None,
        context_id: str | None = None,
        plan_api_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if context:
            params["context"] = context
        if context_id:
            params["context_id"] = context_id
        if plan_api_id:
            params["plan_api_id"] = plan_api_id
        return await self._request("GET", "/v2/webhooks", params=params or None)

    async def create_webhook(
        self,
        *,
        event_type: str,
        endpoint: str,
        passcode: str,
        context: str,
        context_id: str,
        status: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_type": event_type,
            "endpoint": endpoint,
            "passcode": passcode,
            "context": context,
            "context_id": context_id,
        }
        if status:
            payload["status"] = status
        if description:
            payload["description"] = description
        return await self._request("POST", "/v2/webhooks", json_body=payload)

    async def get_webhook(self, webhook_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v2/webhooks/{webhook_id}")

    async def update_webhook(self, webhook_id: str, **updates: Any) -> dict[str, Any]:
        payload = {k: v for k, v in updates.items() if v is not None}
        if not payload:
            return await self.get_webhook(webhook_id)
        return await self._request("PUT", f"/v2/webhooks/{webhook_id}", json_body=payload)

    async def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/v2/webhooks/{webhook_id}")

    async def get_webhook_requests(self, webhook_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v2/webhooks/{webhook_id}/requests")


def get_figma_api() -> FigmaAPI:
    return FigmaAPI()
