"""Normalization helpers for Figma webhook payloads."""

from __future__ import annotations

import hashlib
from typing import Any


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def render_comment_fragments(fragments: list[Any]) -> str:
    parts: list[str] = []
    for fragment in fragments:
        item = _as_dict(fragment)
        raw_text = item.get("text")
        text = raw_text if isinstance(raw_text, str) else ""
        mention = _as_text(item.get("mention"))
        if text:
            parts.append(text)
        elif mention:
            parts.append(f"@{mention}")
    return "".join(parts).strip()


def normalize_figma_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    root = _as_dict(payload)
    event = _as_dict(root.get("event"))
    data = _as_dict(root.get("data"))
    resource = _as_dict(root.get("resource"))
    comment_obj = _as_dict(data.get("comment"))

    fragments = _as_list(root.get("comment"))
    if not fragments:
        fragments = _as_list(data.get("comment"))
    fragment_message = render_comment_fragments(fragments)

    message = (
        _as_text(root.get("message"))
        or _as_text(data.get("message"))
        or _as_text(event.get("message"))
        or _as_text(comment_obj.get("message"))
        or fragment_message
    )

    comment_id = (
        _as_text(root.get("comment_id"))
        or _as_text(data.get("comment_id"))
        or _as_text(event.get("comment_id"))
        or _as_text(comment_obj.get("id"))
    )
    file_key = (
        _as_text(root.get("file_key"))
        or _as_text(data.get("file_key"))
        or _as_text(event.get("file_key"))
        or _as_text(resource.get("file_key"))
        or _as_text(comment_obj.get("file_key"))
    )
    created_at = (
        _as_text(root.get("created_at"))
        or _as_text(data.get("created_at"))
        or _as_text(event.get("created_at"))
        or _as_text(comment_obj.get("created_at"))
        or _as_text(root.get("timestamp"))
    )
    event_type = (
        _as_text(root.get("event_type"))
        or _as_text(event.get("event_type"))
        or _as_text(root.get("type"))
    )
    raw_event_id = (
        _as_text(root.get("event_id"))
        or _as_text(root.get("id"))
        or _as_text(event.get("id"))
        or _as_text(root.get("webhook_id"))
    )

    actor = (
        _as_dict(root.get("triggered_by"))
        or _as_dict(root.get("from"))
        or _as_dict(event.get("from"))
        or _as_dict(data.get("from"))
        or _as_dict(comment_obj.get("from"))
        or _as_dict(comment_obj.get("user"))
    )

    dedupe_raw = "|".join([raw_event_id, comment_id, file_key, message, created_at, event_type])
    dedupe_hash = hashlib.sha256(dedupe_raw.encode("utf-8")).hexdigest()[:20]
    event_id = raw_event_id or f"figma_evt_{dedupe_hash}"

    return {
        "event_id": event_id,
        "event_type": event_type,
        "comment_id": comment_id,
        "file_key": file_key,
        "message": message,
        "from": actor,
        "triggered_by": actor,
        "created_at": created_at,
        "timestamp": _as_text(root.get("timestamp")),
        "passcode": _as_text(root.get("passcode")),
        "webhook_id": _as_text(root.get("webhook_id")),
        "dedupe_key": event_id or dedupe_hash,
        "raw": root,
    }


def passcode_matches(normalized_payload: dict[str, Any], expected_passcode: str | None) -> bool:
    expected = _as_text(expected_passcode)
    if not expected:
        return True
    return _as_text(normalized_payload.get("passcode")) == expected
