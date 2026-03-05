"""Calendar Scheduler Worker — ADHD-aware time blocking.

Absorbs agents/calendar_coach.py:
  - Google Calendar free/busy queries via Composio
  - ADHD-aware focus block creation
  - Event creation with body-doubling windows

Composio actions:
  GOOGLECALENDAR_FREE_BUSY_QUERY  — find open slots
  GOOGLECALENDAR_CREATE_EVENT     — create focus blocks
  GOOGLECALENDAR_FIND_EVENT       — verify/avoid duplicates
"""

from __future__ import annotations

import logging
import os
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from typing import Any

from deepagent.workers.base import BaseWorker, WorkerExecution
from deepagent.workers.llm_schemas import CalendarPlanLLM
from integrations.composio_client import execute_action

logger = logging.getLogger(__name__)


class CalendarWorker(BaseWorker):
    worker_id = "calendar_worker"
    label = "Calendar Scheduler"
    TIME_ZONE = "America/Chicago"
    CALENDAR_ID = "primary"
    FOCUS_TIME_PROPERTIES = {
        "autoDeclineMode": "declineOnlyNewConflictingInvitations",
        "chatStatus": "doNotDisturb",
    }

    ACTIONS = {
        "sync_schedule": "_sync_schedule",
        "create_block": "_create_block",
        "move_block": "_create_block",
        "check_conflict": "_check_conflict",
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
                "items": [{"id": self.CALENDAR_ID}],
                "timeZone": self.TIME_ZONE,
            },
            app_name="googlecalendar",
        )

        if result.get("dry_run"):
            return []

        busy = (
            result.get("result", {})
            .get("data", {})
            .get("calendars", {})
            .get(self.CALENDAR_ID, {})
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

    @staticmethod
    def _parse_iso_datetime(value: str) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _duration_parts(self, start: str, end: str) -> tuple[int, int, int]:
        start_dt = self._parse_iso_datetime(start)
        end_dt = self._parse_iso_datetime(end)
        if start_dt is None or end_dt is None:
            return 0, 0, 0
        total_minutes = int((end_dt - start_dt).total_seconds() // 60)
        if total_minutes <= 0:
            return 0, 0, 0
        hours, minutes = divmod(total_minutes, 60)
        return hours, minutes, total_minutes

    @staticmethod
    def _is_focus_block(event_type: str | None, title: str) -> bool:
        if event_type == "focus_block":
            return True
        lowered = title.strip().lower()
        return "focus" in lowered or "deep work" in lowered or "hyperfocus" in lowered

    async def _query_busy_windows(self, start: str, end: str) -> list[dict[str, Any]]:
        result = await execute_action(
            "GOOGLECALENDAR_FREE_BUSY_QUERY",
            params={
                "timeMin": start,
                "timeMax": end,
                "items": [{"id": self.CALENDAR_ID}],
                "timeZone": self.TIME_ZONE,
            },
            app_name="googlecalendar",
        )
        if result.get("dry_run"):
            return []
        busy = (
            result.get("result", {})
            .get("data", {})
            .get("calendars", {})
            .get(self.CALENDAR_ID, {})
            .get("busy", [])
        )
        if not isinstance(busy, list):
            return []
        return [b for b in busy if isinstance(b, dict)]

    async def _check_conflict(self, payload: dict) -> WorkerExecution:
        start = payload.get("start_time", "")
        end = payload.get("end_time", "")
        if not start or not end:
            return WorkerExecution(ok=False, message="start_time and end_time required")
        busy = await self._query_busy_windows(start=start, end=end)
        has_conflict = len(busy) > 0
        return WorkerExecution(
            ok=True,
            message="Conflict found" if has_conflict else "No conflict",
            data={"has_conflict": has_conflict, "busy_windows": busy},
        )

    def _build_create_event_params(
        self,
        *,
        title: str,
        description: str,
        start: str,
        end: str,
        is_focus: bool,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        hours, minutes, total_minutes = self._duration_parts(start, end)
        primary_params: dict[str, Any] = {
            "summary": title,
            "description": description,
            "start_datetime": start,
            "event_duration_hour": hours,
            "event_duration_minutes": minutes,
            "time_zone": self.TIME_ZONE,
            "calendar_id": self.CALENDAR_ID,
        }
        legacy_params: dict[str, Any] = {
            "summary": title,
            "description": description,
            "start_datetime": start,
            "end_datetime": end,
            "timezone": self.TIME_ZONE,
            "calendar_id": self.CALENDAR_ID,
        }
        if is_focus:
            primary_params["eventType"] = "focusTime"
            primary_params["focusTimeProperties"] = dict(self.FOCUS_TIME_PROPERTIES)
            legacy_params["eventType"] = "focusTime"
            legacy_params["focusTimeProperties"] = dict(self.FOCUS_TIME_PROPERTIES)
        return primary_params, legacy_params, total_minutes

    @staticmethod
    def _extract_calendar_link(result: dict[str, Any]) -> str:
        link = (
            result.get("result", {}).get("htmlLink")
            or result.get("result", {}).get("data", {}).get("htmlLink")
            or ""
        )
        return link if isinstance(link, str) else ""

    async def _create_event_with_fallback(
        self,
        *,
        primary_params: dict[str, Any],
        legacy_params: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        primary = await execute_action(
            "GOOGLECALENDAR_CREATE_EVENT",
            params=primary_params,
            app_name="googlecalendar",
        )
        if not primary.get("dry_run"):
            return primary, "primary"
        if primary.get("error"):
            logger.warning("Calendar create: primary payload failed, retrying legacy payload")
            fallback = await execute_action(
                "GOOGLECALENDAR_CREATE_EVENT",
                params=legacy_params,
                app_name="googlecalendar",
            )
            return fallback, "legacy"
        return primary, "primary"

    @staticmethod
    def _extract_find_event_items(result: dict[str, Any]) -> list[dict[str, Any]]:
        payload = result.get("result", {})
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        data = payload.get("data", payload)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if not isinstance(data, dict):
            return []
        for key in ("items", "results", "events"):
            entries = data.get(key, [])
            if isinstance(entries, list):
                return [x for x in entries if isinstance(x, dict)]
        return []

    async def _is_duplicate_event(self, title: str, start: str) -> bool:
        result = await execute_action(
            "GOOGLECALENDAR_FIND_EVENT",
            params={"search_term": title},
            app_name="googlecalendar",
        )
        if result.get("dry_run"):
            return False
        candidates = self._extract_find_event_items(result)
        target_title = title.strip().lower()
        target_start_prefix = start[:16]
        for item in candidates:
            summary = str(item.get("summary") or item.get("title") or "").strip().lower()
            if summary != target_title:
                continue
            start_obj = item.get("start")
            start_dt = ""
            if isinstance(start_obj, dict):
                start_dt = str(start_obj.get("dateTime") or "")
            if not start_dt:
                start_dt = str(item.get("start_datetime") or item.get("start_time") or "")
            if start_dt[:16] == target_start_prefix:
                return True
        return False

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
        deduped: list = []
        seen = set()
        for event in plan_model.events:
            key = (event.title.strip().lower(), event.start_time, event.end_time)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        events = deduped[:4]
        created = 0
        external_links: list[str] = []
        for event in events:
            if await self._is_duplicate_event(event.title, event.start_time):
                continue
            busy = await self._query_busy_windows(start=event.start_time, end=event.end_time)
            if busy:
                continue
            primary_params, legacy_params, total_minutes = self._build_create_event_params(
                title=event.title,
                description=event.description,
                start=event.start_time,
                end=event.end_time,
                is_focus=self._is_focus_block(event.event_type, event.title),
            )
            if total_minutes <= 0:
                continue
            result, _variant = await self._create_event_with_fallback(
                primary_params=primary_params,
                legacy_params=legacy_params,
            )
            if not result.get("dry_run"):
                created += 1
                link = self._extract_calendar_link(result)
                if isinstance(link, str) and link:
                    external_links.append(link)

        logger.info("Calendar: created %d/%d events", created, len(events))

        return WorkerExecution(
            ok=True,
            message=f"Scheduled {created} events ({len(events)} planned)",
            data={
                **plan,
                "external_links": {"calendar_events": external_links},
            },
        )

    async def _create_block(self, payload: dict) -> WorkerExecution:
        """Create a single calendar event. Requires approval for moves."""
        if payload.get("demo_mode") or os.environ.get("PORTTHON_OFFLINE_MODE") == "1":
            title = payload.get("title", "Focus Block")
            event_id = f"demo_cal_{sha256(title.encode()).hexdigest()[:10]}"
            return WorkerExecution(
                ok=True,
                message=f"Created demo event: {title}",
                data={
                    "demo_mode": True,
                    "event_id": event_id,
                    "title": title,
                    "start_time": payload.get("start_time", ""),
                    "end_time": payload.get("end_time", ""),
                    "external_links": {
                        "calendar_event": f"https://calendar.google.com/event?eid={event_id}"
                    },
                },
            )

        title = payload.get("title", "Focus Block")
        start = payload.get("start_time", "")
        end = payload.get("end_time", "")

        if not start or not end:
            return WorkerExecution(ok=False, message="start_time and end_time required")

        primary_params, legacy_params, total_minutes = self._build_create_event_params(
            title=title,
            description=payload.get("description", ""),
            start=start,
            end=end,
            is_focus=self._is_focus_block(payload.get("event_type"), title),
        )
        if total_minutes <= 0:
            return WorkerExecution(ok=False, message="end_time must be after start_time")

        busy = await self._query_busy_windows(start=start, end=end)
        if busy and not payload.get("allow_conflict"):
            return WorkerExecution(
                ok=False,
                message="Requested window conflicts with existing events",
                data={"busy_windows": busy},
            )

        if await self._is_duplicate_event(title, start):
            return WorkerExecution(
                ok=True,
                message=f"Skipped duplicate event: {title}",
                data={"duplicate": True},
            )

        result, payload_variant = await self._create_event_with_fallback(
            primary_params=primary_params,
            legacy_params=legacy_params,
        )

        is_move = payload.get("moves_existing", False)
        verify = await execute_action(
            "GOOGLECALENDAR_FIND_EVENT",
            params={"search_term": title},
            app_name="googlecalendar",
        )
        if result.get("error"):
            return WorkerExecution(
                ok=False,
                message=f"Failed to create event: {title}",
                data={
                    **result,
                    "payload_variant": payload_variant,
                    "verification_result": verify,
                },
                approval_required=is_move,
                approval_reason="Moving an existing calendar event requires approval" if is_move else "",
            )

        return WorkerExecution(
            ok=True,
            message=f"Created event: {title}",
            data={
                **result,
                "payload_variant": payload_variant,
                "verification_result": verify,
                "external_links": {
                    "calendar_event": self._extract_calendar_link(result),
                },
            },
            approval_required=is_move,
            approval_reason="Moving an existing calendar event requires approval" if is_move else "",
        )
