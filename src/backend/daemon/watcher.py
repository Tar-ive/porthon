"""DataWatcher — polls Theo's JSONL data files for changes and triggers re-analysis."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

# Map filename → domain label used in SSE events and AnalysisCache
_DOMAIN_MAP: dict[str, str] = {
    "transactions.jsonl": "finance",
    "calendar.jsonl": "calendar",
    "lifelog.jsonl": "lifelog",
    "social_posts.jsonl": "social",
    "conversations.jsonl": "conversations",
    "emails.jsonl": "emails",
    "files_index.jsonl": "files",
}


@dataclass
class RunContext:
    """Execution context for a single watcher-triggered analysis run.

    Separates *reasoning mode* (demo vs live LLM/KG) from *integration mode*
    (Notion writes, webhook visibility) so each can be controlled independently.

    Attributes
    ----------
    demo_mode:
        When True, analysis uses demo scenarios/actions instead of live LLM/KG.
        Does NOT disable Notion writes or webhook visibility.
    source:
        What triggered this run (for logging / provenance tagging).
    notion_write:
        Whether outbound Notion writes are permitted for this run.
    """

    demo_mode: bool = False
    source: str = "file_poll"  # demo_push | live_webhook | file_poll | manual
    notion_write: bool = True


def _evt_id() -> str:
    return f"evt_{uuid4().hex[:12]}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class DataWatcher:
    """Polls persona JSONL files and publishes SSE events when data changes.

    On a detected change it:
    1. Publishes a ``data_changed`` event immediately so the frontend can show a banner.
    2. Invalidates the in-memory scenario cache so the next /api/scenarios call
       reflects fresh data.
    3. Fires a background re-analysis task that runs extract → scenario_gen,
       publishing ``analysis_running`` and ``scenarios_updated`` events as it goes.
       If ``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` are absent the task skips LLM
       and emits a lightweight demo-mode refresh instead.
    """

    def __init__(
        self,
        master,  # AlwaysOnMaster — typed loosely to avoid circular import
        data_dir: Path,
        persona_id: str = "p05",
        poll_interval: float = 3.0,
    ) -> None:
        self._master = master
        self._data_dir = data_dir
        self._persona_id = persona_id
        self._poll_interval = poll_interval
        self._mtimes: dict[Path, float] = {}
        self._task: asyncio.Task | None = None
        self._reanalysis_task: asyncio.Task | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        # Snapshot current mtimes so we don't fire on startup
        self._snapshot()
        self._task = asyncio.create_task(self._poll_loop(), name="data-watcher-poll")
        logger.info("DataWatcher started — watching %s (%.1fs interval)", self._data_dir, self._poll_interval)

    async def force_check(self, demo_mode: bool = False) -> None:
        """Trigger an immediate file check without waiting for the next poll tick.

        Parameters
        ----------
        demo_mode:
            When True, re-analysis uses demo reasoning (no live LLM/KG queries).
            Notion writes and webhook visibility are unaffected.
        """
        ctx = RunContext(demo_mode=demo_mode, source="demo_push" if demo_mode else "manual")
        try:
            await self._check_files(ctx)
        except Exception:
            logger.exception("DataWatcher force_check error")

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._reanalysis_task):
            if t and not t.done():
                t.cancel()
                try:
                    await t
                except asyncio.CancelledError:
                    pass
        logger.info("DataWatcher stopped")

    # ------------------------------------------------------------------
    # Poll loop
    # ------------------------------------------------------------------

    def _snapshot(self) -> None:
        """Record current mtimes without firing events."""
        for path in self._data_dir.glob("*.jsonl"):
            try:
                self._mtimes[path] = path.stat().st_mtime
            except OSError:
                pass

    async def _poll_loop(self) -> None:
        ctx = RunContext(source="file_poll")
        while self._running:
            await asyncio.sleep(self._poll_interval)
            try:
                await self._check_files(ctx)
            except Exception:
                logger.exception("DataWatcher poll error")

    async def _check_files(self, ctx: RunContext | None = None) -> None:
        if ctx is None:
            ctx = RunContext(source="file_poll")
        for path in self._data_dir.glob("*.jsonl"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue

            previous = self._mtimes.get(path)
            if previous is None:
                # New file appeared — just record it
                self._mtimes[path] = mtime
                continue

            if mtime != previous:
                self._mtimes[path] = mtime
                domain = _DOMAIN_MAP.get(path.name, "unknown")
                logger.info(
                    "DataWatcher: change detected in %s (domain=%s, source=%s, demo=%s)",
                    path.name, domain, ctx.source, ctx.demo_mode,
                )
                await self._on_file_changed(path, domain, ctx)

    # ------------------------------------------------------------------
    # React to a change
    # ------------------------------------------------------------------

    async def _on_file_changed(self, path: Path, domain: str, ctx: RunContext) -> None:
        # 1. Invalidate scenario cache immediately
        self._invalidate_legacy_cache()

        # 2. Publish data_changed so frontend can show a banner right away
        await self._master.stream.publish({
            "event_id": _evt_id(),
            "type": "data_changed",
            "payload": {
                "domain": domain,
                "file": path.name,
                "persona_id": self._persona_id,
                "analysis_running": True,
                "source": ctx.source,
            },
            "created_at": _now_iso(),
        })

        # 3. Kick off background re-analysis (cancel any in-flight one first)
        if self._reanalysis_task and not self._reanalysis_task.done():
            self._reanalysis_task.cancel()
        self._reanalysis_task = asyncio.create_task(
            self._reanalyze(domain, ctx), name="data-watcher-reanalysis"
        )

        # 4. Best-effort: ingest new record into LightRAG.
        # Skipped for demo pushes — we don't want demo data mutating live KG infra.
        if not ctx.demo_mode:
            asyncio.create_task(
                self._ingest_new_record(path, domain), name="data-watcher-kg-ingest"
            )

    def _invalidate_legacy_cache(self) -> None:
        """Also bust the route-level cache so HTTP /api/scenarios reflects fresh data."""
        try:
            from app.api.v1.scenarios import _cached_scenarios
            _cached_scenarios.clear()
        except Exception:
            pass

    async def _ingest_new_record(self, path: Path, domain: str) -> None:
        """Best-effort: ingest the last record from a changed JSONL file into LightRAG."""
        import json as _json
        try:
            import os
            if not os.environ.get("NEO4J_URI"):
                return  # LightRAG not configured — skip silently
            from deepagent.workers.kg_worker import _create_rag_instance
            rag = _create_rag_instance()
            if rag is None:
                return
            # Read the last non-empty line (newest record)
            last_line = ""
            with path.open("rb") as f:
                f.seek(0, 2)
                pos = f.tell()
                while pos > 0:
                    pos -= 1
                    f.seek(pos)
                    ch = f.read(1)
                    if ch == b"\n" and last_line.strip():
                        break
                    last_line = ch.decode("utf-8", errors="ignore") + last_line
            record = _json.loads(last_line.strip())
            text = record.get("text") or _json.dumps(record)
            await asyncio.wait_for(rag.ainsert(text), timeout=20.0)
            logger.info("DataWatcher: ingested new %s record into LightRAG", domain)
        except Exception as exc:
            logger.debug("DataWatcher: LightRAG ingest skipped for %s: %s", domain, exc)

    async def _reanalyze_active_actions(self, cache, has_llm: bool, ctx: RunContext | None = None) -> None:
        """Re-generate actions for the currently active scenario and emit actions_updated."""
        try:
            state = self._master.store.load()
            active = state.active_scenario
            if active is None:
                return
            scenario = {
                "id": active.scenario_id,
                "title": active.title,
                "horizon": active.horizon,
                "likelihood": active.likelihood,
                "summary": active.summary,
            }
            await self._master.stream.publish({
                "event_id": _evt_id(),
                "type": "analysis_running",
                "payload": {"stage": "actions", "message": "Updating quest recommendations…"},
                "created_at": _now_iso(),
            })
            actions, _ = await asyncio.wait_for(
                cache.get_actions(scenario, changed_domains=None, has_llm=has_llm),
                timeout=35.0,
            )
            await self._master.stream.publish({
                "event_id": _evt_id(),
                "type": "actions_updated",
                "payload": {
                    "scenario_id": active.scenario_id,
                    "count": len(actions),
                },
                "created_at": _now_iso(),
            })
            logger.info("DataWatcher: actions updated (%d) for scenario=%s", len(actions), active.scenario_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("DataWatcher: actions refresh failed: %s", exc)

    async def _reanalyze(self, domain: str, ctx: RunContext | None = None) -> None:
        """Re-analyze via AnalysisCache — only re-extracts the changed domain
        and only calls the LLM if the prompt inputs actually changed.

        ``has_llm`` is computed from two factors:
        - env_has_llm: whether live LLM keys are configured
        - ctx.demo_mode: if True, force demo reasoning regardless of env keys

        This means demo pushes always use demo scenarios/actions, while
        live file changes (webhooks, operator edits) use real LLM if configured.
        Notion writes and webhook visibility are NOT affected by demo_mode.
        """
        from daemon.analysis_cache import get_analysis_cache

        if ctx is None:
            ctx = RunContext(source="file_poll")

        cache = get_analysis_cache()
        if cache is None:
            logger.warning("DataWatcher: AnalysisCache not initialized, skipping re-analysis")
            return

        env_has_llm = bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("LLM_BINDING_API_KEY")
        )
        # demo_mode forces demo reasoning even when live keys are present
        has_llm = env_has_llm and not ctx.demo_mode

        await self._master.stream.publish({
            "event_id": _evt_id(),
            "type": "analysis_running",
            "payload": {
                "stage": "scenarios",
                "domain": domain,
                "message": f"New {domain} data detected — checking trajectories…",
            },
            "created_at": _now_iso(),
        })

        try:
            scenarios, regenerated = await asyncio.wait_for(
                cache.get_scenarios(changed_domains={domain}, has_llm=has_llm),
                timeout=35.0,
            )

            # Also bust the route-level TTL cache so next HTTP call is fresh
            self._invalidate_legacy_cache()

            if regenerated:
                await self._master.stream.publish({
                    "event_id": _evt_id(),
                    "type": "scenarios_updated",
                    "payload": {
                        "count": len(scenarios),
                        "persona_id": self._persona_id,
                        "triggered_by": domain,
                    },
                    "created_at": _now_iso(),
                })
                logger.info("DataWatcher: trajectories updated (%d) after %s change", len(scenarios), domain)
                # Re-generate actions for the active scenario so quests auto-refresh
                asyncio.create_task(
                    self._reanalyze_active_actions(cache, has_llm, ctx),
                    name="data-watcher-actions-refresh",
                )
            else:
                # In demo mode, always refresh actions even if scenario hash unchanged.
                # Demo actions are context-aware (detect pushed records), so they change
                # even when the scenario trajectory itself doesn't.
                if ctx.demo_mode:
                    asyncio.create_task(
                        self._reanalyze_active_actions(cache, has_llm, ctx),
                        name="data-watcher-actions-refresh",
                    )
                # Let frontend know analysis is stable
                await self._master.stream.publish({
                    "event_id": _evt_id(),
                    "type": "analysis_stable",
                    "payload": {
                        "domain": domain,
                        "message": f"{domain} data updated — trajectories unchanged",
                    },
                    "created_at": _now_iso(),
                })
                logger.info("DataWatcher: %s changed but trajectory inputs unchanged, LLM skipped", domain)

        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            logger.warning("DataWatcher: re-analysis timed out for domain=%s", domain)
            await self._master.stream.publish({
                "event_id": _evt_id(),
                "type": "analysis_error",
                "payload": {"message": "Re-analysis timed out — using cached trajectories"},
                "created_at": _now_iso(),
            })
        except Exception as exc:
            logger.warning("DataWatcher: re-analysis failed for domain=%s: %s", domain, exc)
            await self._master.stream.publish({
                "event_id": _evt_id(),
                "type": "analysis_error",
                "payload": {"message": "Re-analysis failed — using cached trajectories"},
                "created_at": _now_iso(),
            })
