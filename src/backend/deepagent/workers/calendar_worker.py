"""Calendar Scheduler Worker — ADHD-aware time blocking.

Absorbs agents/calendar_coach.py:
  - Google Calendar free/busy queries via Composio
  - ADHD-aware focus block creation
  - Event creation with body-doubling windows

Composio actions:
  GOOGLECALENDAR_FREE_BUSY_QUERY  — find open slots
  GOOGLECALENDAR_CREATE_EVENT     — create focus blocks
"""

from __future__ import annotations

import logging
import os
from hashlib import sha256
from datetime import datetime, timedelta, timezone

from deepagent.workers.base import BaseWorker, WorkerExecution
from deepagent.workers.llm_schemas import CalendarPlanLLM
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class CalendarWorker(BaseWorker):
    worker_id = "calendar_worker"
    label = "Calendar Scheduler"

    ACTIONS = {
        "sync_schedule": "_sync_schedule",
        "create_block": "_create_block",
        "move_block": "_create_block",
    }

    async def execute(self, action: str, payload: dict) -> WorkerExecution:
        handler_name = self.ACTIONS.get(action)
        if not handler_name:
            return WorkerExecution(ok=False, message=f"Unknown action: {action}")
        handler = getattr(self, handler_name)
        return await handler(payload)

    async def _fetch_free_slots(self) -> list[dict]:
        """Query Google Calendar for free slots next week."""
        now = datetime.now(timezone.utc)
        days_until_monday = (7 - now.weekday()) % 7 or 7
        start = (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + timedelta(days=7)

        result = await execute_action(
            "GOOGLECALENDAR_FREE_BUSY_QUERY",
            params={
                "timeMin": start.isoformat(),
                "timeMax": end.isoformat(),
                "items": [{"id": "primary"}],
                "timeZone": "America/Chicago",
            },
            app_name="googlecalendar",
        )

        if result.get("dry_run"):
            return []

        busy = (
            result.get("result", {})
            .get("data", {})
            .get("calendars", {})
            .get("primary", {})
            .get("busy", [])
        )

        free = []
        for day_offset in range(7):
            day = start + timedelta(days=day_offset)
            day_name = day.strftime("%A")

            day_busy = [
                b for b in busy
                if b["start"][:10] == day.strftime("%Y-%m-%d")
            ]

            if not day_busy:
                free.append({
                    "day": day_name,
                    "start": "9:00 AM",
                    "end": "9:00 PM",
                    "hours_free": 12,
                })
            else:
                free.append({
                    "day": day_name,
                    "busy_blocks": len(day_busy),
                    "start": "9:00 AM",
                    "end": "9:00 PM",
                    "hours_free": max(0, 12 - len(day_busy) * 2),
                })

        return free

    def _build_scheduling_prompt(
        self, free_slots: list[dict], kg_context: dict, payload: dict,
    ) -> str:
        """Build an ADHD-aware scheduling prompt using KG context."""
        kg_snippets = kg_context.get("snippets", [])
        kg_text = "\n".join(f"  - {s}" for s in kg_snippets[:5]) if kg_snippets else "  (no KG context available)"

        slots_str = ""
        if free_slots:
            slots_str = "\nCalendar availability next week:\n"
            slots_str += "\n".join(
                f"  {s['day']}: {s.get('hours_free', '?')}h free ({s['start']}–{s['end']})"
                for s in free_slots
            )

        actions_str = payload.get("actions_text", "No specific actions provided")

        return f"""Persona context from knowledge graph:
{kg_text}

Chosen scenario: "{payload.get('scenario_title', '')}"

Actions to schedule:
{actions_str}
{slots_str}

Scheduling rules (ADHD-aware):
- Create 3h morning hyperfocus blocks for creative/deep work
- Use 25min pomodoros for admin tasks
- Add 10min transition buffers between context switches
- Front-load revenue-generating tasks Monday–Wednesday
- Use eventType "focusTime" for deep work blocks
- Schedule body-doubling windows at locations that work (e.g., UT library)
- Keep individual tasks ≤15 minutes for admin

Generate a weekly calendar plan. Return JSON:
{{
  "events": [
    {{
      "title": "event title",
      "description": "what to do and why",
      "start_time": "2026-03-09T09:00:00",
      "end_time": "2026-03-09T12:00:00",
      "event_type": "focus_block|admin|body_doubling|learning|break|review",
      "adhd_note": "optional ADHD accommodation note"
    }}
  ],
  "weekly_rhythm_summary": "overview of the weekly structure",
  "adhd_accommodations": ["list of ADHD-specific accommodations used"],
  "quest_connection": "how this calendar supports the chosen scenario"
}}"""

    async def _sync_schedule(self, payload: dict) -> WorkerExecution:
        """Fetch free slots and create ADHD-aware schedule blocks."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            plan = {
                "events": [
                    {
                        "title": "Deep Work: Portfolio Sprint (UT Library)",
                        "description": "3h focused portfolio build block.",
                        "start_time": "2026-03-09T09:00:00",
                        "end_time": "2026-03-09T12:00:00",
                        "event_type": "focus_block",
                        "adhd_note": "Body-doubling friendly location.",
                    },
                    {
                        "title": "Deep Work: Client Deliverable Block (UT Library)",
                        "description": "Client conversion deliverable sprint.",
                        "start_time": "2026-03-11T09:00:00",
                        "end_time": "2026-03-11T12:00:00",
                        "event_type": "focus_block",
                        "adhd_note": "Low-distraction environment.",
                    },
                    {
                        "title": "Admin Sprint: Invoice Follow-up",
                        "description": "Short admin loop for receivables.",
                        "start_time": "2026-03-10T16:00:00",
                        "end_time": "2026-03-10T16:45:00",
                        "event_type": "admin",
                        "adhd_note": "25-minute chunks + short break.",
                    },
                    {
                        "title": "Debt-Paydown Review",
                        "description": "Weekly debt stress reduction check-in.",
                        "start_time": "2026-03-12T17:00:00",
                        "end_time": "2026-03-12T17:30:00",
                        "event_type": "review",
                        "adhd_note": "One clear decision before stopping.",
                    },
                ],
                "weekly_rhythm_summary": "Two deep-work blocks, one admin block, one review block.",
                "adhd_accommodations": [
                    "Body-doubling location",
                    "Short admin sprint",
                    "Protected focus windows",
                ],
                "quest_connection": "Calendar schedule supports conversion-first execution.",
            }
            return WorkerExecution(
                ok=True,
                message="Scheduled 4 deterministic demo events",
                data=plan,
            )

        kg_context = payload.get("kg_context", {})

        # 1. Get free slots from Google Calendar
        free_slots = await self._fetch_free_slots()
        logger.info("Calendar: found %d free slot windows", len(free_slots))

        # 2. Generate ADHD-aware schedule via LLM
        prompt = self._build_scheduling_prompt(free_slots, kg_context, payload)
        plan_model = await self._llm_typed(
            system=(
                "You are an ADHD-aware calendar coach. You create weekly schedules "
                "optimized for neurodivergent users. Use ISO datetime strings. "
                "Return ONLY valid JSON."
            ),
            user=prompt,
            schema=CalendarPlanLLM,
        )
        plan = plan_model.model_dump(mode="json")

        # 3. Create events via Composio
        events = plan_model.events
        created = 0
        for event in events:
            params = {
                "summary": event.title,
                "description": event.description,
                "start_datetime": event.start_time,
                "end_datetime": event.end_time,
                "timezone": "America/Chicago",
                "calendar_id": "primary",
            }
            if event.event_type == "focus_block":
                params["eventType"] = "focusTime"

            result = await execute_action(
                "GOOGLECALENDAR_CREATE_EVENT",
                params=params,
                app_name="googlecalendar",
            )
            if not result.get("dry_run"):
                created += 1

        logger.info("Calendar: created %d/%d events", created, len(events))

        return WorkerExecution(
            ok=True,
            message=f"Scheduled {created} events ({len(events)} planned)",
            data=plan,
        )

    async def _create_block(self, payload: dict) -> WorkerExecution:
        """Create a single calendar event. Requires approval for moves."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            title = payload.get("title", "Focus Block")
            return WorkerExecution(
                ok=True,
                message=f"Created demo event: {title}",
                data={
                    "demo_mode": True,
                    "event_id": f"demo_cal_{sha256(title.encode()).hexdigest()[:10]}",
                    "title": title,
                    "start_time": payload.get("start_time", ""),
                    "end_time": payload.get("end_time", ""),
                },
            )

        title = payload.get("title", "Focus Block")
        start = payload.get("start_time", "")
        end = payload.get("end_time", "")

        if not start or not end:
            return WorkerExecution(ok=False, message="start_time and end_time required")

        result = await execute_action(
            "GOOGLECALENDAR_CREATE_EVENT",
            params={
                "summary": title,
                "description": payload.get("description", ""),
                "start_datetime": start,
                "end_datetime": end,
                "timezone": "America/Chicago",
                "calendar_id": "primary",
            },
            app_name="googlecalendar",
        )

        is_move = payload.get("moves_existing", False)
        return WorkerExecution(
            ok=True,
            message=f"Created event: {title}",
            data=result,
            approval_required=is_move,
            approval_reason="Moving an existing calendar event requires approval" if is_move else "",
        )
