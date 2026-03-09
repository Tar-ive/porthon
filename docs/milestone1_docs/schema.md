# Agent Output Schema

Universal deterministic envelope that every agent (Composio, KG, LLM, deterministic) returns to the orchestrator.

Source of truth: `src/backend/agents/schema.py`

## Models

### `DataSource`
Provenance — what data informed the result.

| Field | Type | Description |
|-------|------|-------------|
| `ref_id` | `str` | Record identifier, e.g. `"cal_042"`, `"kg:entity:theo_nakamura"` |
| `source_type` | `Literal` | One of `data_ref`, `kg_entity`, `kg_relation`, `api_response`, `user_input` |
| `description` | `str` | Human-readable description of what this source contributed |

### `ExecutionStep`
Trace of one phase in the agent lifecycle.

| Field | Type | Description |
|-------|------|-------------|
| `phase` | `Literal` | One of `plan`, `execute`, `verify`, `retrieve`, `classify` |
| `status` | `Literal` | One of `success`, `skipped`, `error` |
| `detail` | `str` | What happened in this phase |
| `duration_ms` | `float \| None` | Wall-clock time (optional) |

### `AgentResult`
The envelope the orchestrator consumes.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_name` | `str` | — | e.g. `"calendar_coach"`, `"kg_retriever"` |
| `agent_type` | `Literal` | — | `composio`, `kg`, `llm`, or `deterministic` |
| `status` | `Literal` | — | `success`, `partial`, `error`, or `dry_run` |
| `data` | `dict` | — | Agent-specific payload (CalendarPlan, KG context, etc.) |
| `sources` | `list[DataSource]` | `[]` | Provenance chain |
| `confidence` | `float` | `1.0` | 0–1 confidence score |
| `quest_connection` | `str` | `""` | How this ties to the chosen scenario |
| `execution_log` | `list[ExecutionStep]` | `[]` | Ordered trace of phases |
| `timestamp` | `str` | — | ISO 8601 |
| `error` | `str \| None` | `None` | Error message if status is `error` |

## Agent Type Mapping

| Agent | `agent_type` | Typical `data` payload |
|-------|-------------|----------------------|
| Calendar Coach | `composio` | `CalendarPlan` dict |
| Content Creator | `composio` | `ContentCalendar` dict |
| Learning Planner | `llm` | `LearningPlan` dict |
| Notion Workspace | `composio` | `NotionWorkspace` dict |
| KG Retriever | `kg` | Context dict with entities/relations |
| Pattern Analyzer | `deterministic` | `PatternReport` dict |

## Example

```json
{
  "agent_name": "calendar_coach",
  "agent_type": "composio",
  "status": "success",
  "data": {
    "events": [
      {"title": "Morning run", "time": "07:00", "duration_min": 30}
    ]
  },
  "sources": [
    {"ref_id": "cal_042", "source_type": "data_ref", "description": "Existing calendar pattern"}
  ],
  "confidence": 0.85,
  "quest_connection": "Supports health scenario goal of daily exercise",
  "execution_log": [
    {"phase": "retrieve", "status": "success", "detail": "Fetched 7 days of calendar data", "duration_ms": 120},
    {"phase": "plan", "status": "success", "detail": "Generated 3 calendar suggestions", "duration_ms": 450}
  ],
  "timestamp": "2026-03-02T10:30:00Z",
  "error": null
}
```

## Orchestrator Consumption

The future orchestrator will:

1. Collect `AgentResult` envelopes from all agents
2. Filter by `status != "error"`
3. Rank by `confidence`
4. Merge `sources` for full provenance
5. Combine `execution_log` entries for end-to-end tracing
