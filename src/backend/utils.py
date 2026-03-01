import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence

import ollama
import openai
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Shared message models
# ---------------------------------------------------------------------------


class ClientMessagePart(BaseModel):
    type: str
    text: Optional[str] = None

    model_config = {"extra": "allow"}


class ClientMessage(BaseModel):
    role: str
    content: Optional[str] = None
    parts: Optional[List[ClientMessagePart]] = None

    model_config = {"extra": "allow"}


def extract_text(msg: ClientMessage) -> str:
    if msg.parts:
        return "".join(p.text or "" for p in msg.parts if p.type == "text")
    return msg.content or ""


# ---------------------------------------------------------------------------
# Typed stream events
# ---------------------------------------------------------------------------


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolStart:
    tool_call_id: str
    tool_name: str


@dataclass
class ToolArgsDelta:
    tool_call_id: str
    delta: str


@dataclass
class ToolResult:
    tool_call_id: str
    output: Any


@dataclass
class ToolError:
    tool_call_id: str
    error: str


StreamEvent = TextDelta | ToolStart | ToolArgsDelta | ToolResult | ToolError


# ---------------------------------------------------------------------------
# Client iterators
# ---------------------------------------------------------------------------


def iter_openai_events(
    messages: List[ClientMessage],
    model: str = "gpt-4o-mini",
    tool_definitions: Sequence[Dict[str, Any]] = (),
    available_tools: Mapping[str, Callable[..., Any]] = {},
    system_prompt: str = "",
) -> Iterator[StreamEvent]:
    formatted = [{"role": m.role, "content": extract_text(m)} for m in messages]
    if system_prompt:
        formatted.insert(0, {"role": "system", "content": system_prompt})
    client = openai.OpenAI()

    stream = client.chat.completions.create(
        model=model,
        messages=formatted,  # type: ignore[arg-type]
        stream=True,
        tools=list(tool_definitions) or openai.NOT_GIVEN,  # type: ignore[arg-type]
    )

    tool_calls_state: Dict[int, Dict[str, Any]] = {}
    finish_reason = None

    for chunk in stream:
        for choice in chunk.choices:
            if choice.finish_reason:
                finish_reason = choice.finish_reason

            delta = choice.delta
            if delta is None:
                continue

            if delta.content:
                yield TextDelta(text=delta.content)

            for tc in delta.tool_calls or []:
                state = tool_calls_state.setdefault(
                    tc.index, {"id": None, "name": None, "arguments": "", "started": False}
                )
                if tc.id:
                    state["id"] = tc.id
                fn = getattr(tc, "function", None)
                if fn:
                    if fn.name:
                        state["name"] = fn.name
                    if fn.arguments:
                        state["arguments"] += fn.arguments

                if state["id"] and state["name"] and not state["started"]:
                    yield ToolStart(tool_call_id=state["id"], tool_name=state["name"])
                    state["started"] = True

                if fn and fn.arguments and state["id"]:
                    yield ToolArgsDelta(tool_call_id=state["id"], delta=fn.arguments)

    if finish_reason == "tool_calls":
        for state in tool_calls_state.values():
            tool_call_id = state.get("id")
            tool_name = state.get("name")
            if not tool_call_id or not tool_name:
                continue

            try:
                parsed = json.loads(state["arguments"]) if state["arguments"] else {}
            except Exception as e:
                yield ToolError(tool_call_id=tool_call_id, error=str(e))
                continue

            fn = available_tools.get(tool_name)
            if fn is None:
                yield ToolError(tool_call_id=tool_call_id, error=f"Tool '{tool_name}' not found.")
                continue

            try:
                yield ToolResult(tool_call_id=tool_call_id, output=fn(**parsed))
            except Exception as e:
                yield ToolError(tool_call_id=tool_call_id, error=str(e))


def iter_ollama_events(
    messages: List[ClientMessage],
    host: str,
    model: str,
    system_prompt: str = "",
) -> Iterator[StreamEvent]:
    formatted = [{"role": m.role, "content": extract_text(m)} for m in messages]
    if system_prompt:
        formatted.insert(0, {"role": "system", "content": system_prompt})
    client = ollama.Client(host=host)
    for chunk in client.chat(model=model, messages=formatted, stream=True):
        if chunk.message.content:
            yield TextDelta(text=chunk.message.content)


# ---------------------------------------------------------------------------
# SSE formatter
# ---------------------------------------------------------------------------


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"


def wrap_stream(events: Iterable[StreamEvent]) -> Iterator[str]:
    """Translate typed stream events into Vercel AI SDK SSE frames."""
    message_id = f"msg-{uuid.uuid4().hex}"
    text_stream_id = "text-1"
    text_started = False

    yield _sse({"type": "start", "messageId": message_id})

    for event in events:
        if isinstance(event, TextDelta):
            if not text_started:
                yield _sse({"type": "text-start", "id": text_stream_id})
                text_started = True
            yield _sse({"type": "text-delta", "id": text_stream_id, "delta": event.text})

        elif isinstance(event, ToolStart):
            yield _sse({"type": "tool-input-start", "toolCallId": event.tool_call_id, "toolName": event.tool_name})

        elif isinstance(event, ToolArgsDelta):
            yield _sse({"type": "tool-input-delta", "toolCallId": event.tool_call_id, "inputTextDelta": event.delta})

        elif isinstance(event, ToolResult):
            yield _sse({"type": "tool-output-available", "toolCallId": event.tool_call_id, "output": event.output})

        elif isinstance(event, ToolError):
            yield _sse({"type": "tool-output-error", "toolCallId": event.tool_call_id, "errorText": event.error})

    if text_started:
        yield _sse({"type": "text-end", "id": text_stream_id})

    yield _sse({"type": "finish"})
    yield "data: [DONE]\n\n"


def patch_response_with_headers(response: StreamingResponse) -> StreamingResponse:
    """Apply standard streaming headers expected by the Vercel AI SDK."""
    response.headers["x-vercel-ai-ui-message-stream"] = "v1"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Expose-Headers"] = "x-porthon-intent"
    return response
