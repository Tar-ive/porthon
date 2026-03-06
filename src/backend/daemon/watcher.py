"""DataWatcher — polls Theo's JSONL data files for changes and triggers re-analysis."""

from __future__ import annotations

import asyncio
import logging
import os
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
        while self._running:
            await asyncio.sleep(self._poll_interval)
            try:
                await self._check_files()
            except Exception:
                logger.exception("DataWatcher poll error")

    async def _check_files(self) -> None:
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
                logger.info("DataWatcher: change detected in %s (domain=%s)", path.name, domain)
                await self._on_file_changed(path, domain)

    # ------------------------------------------------------------------
    # React to a change
    # ------------------------------------------------------------------

    async def _on_file_changed(self, path: Path, domain: str) -> None:
        # 1. Invalidate scenario cache immediately
        self._invalidate_scenario_cache()

        # 2. Publish data_changed so frontend can show a banner right away
        await self._master.stream.publish({
            "event_id": _evt_id(),
            "type": "data_changed",
            "payload": {
                "domain": domain,
                "file": path.name,
                "persona_id": self._persona_id,
                "analysis_running": True,
            },
            "created_at": _now_iso(),
        })

        # 3. Kick off background re-analysis (cancel any in-flight one first)
        if self._reanalysis_task and not self._reanalysis_task.done():
            self._reanalysis_task.cancel()
        self._reanalysis_task = asyncio.create_task(
            self._reanalyze(domain), name="data-watcher-reanalysis"
        )

    def _invalidate_legacy_cache(self) -> None:
        """Also bust the route-level cache so HTTP /api/scenarios reflects fresh data."""
        try:
            from app.api.v1.scenarios import _cached_scenarios
            _cached_scenarios.clear()
        except Exception:
            pass

    async def _reanalyze(self, domain: str) -> None:
        """Re-analyze via AnalysisCache — only re-extracts the changed domain
        and only calls the LLM if the prompt inputs actually changed."""
        from daemon.analysis_cache import get_analysis_cache

        cache = get_analysis_cache()
        if cache is None:
            logger.warning("DataWatcher: AnalysisCache not initialized, skipping re-analysis")
            return

        has_llm = bool(
            os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("LLM_BINDING_API_KEY")
        )

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
            else:
                # Inputs unchanged — no LLM call needed, just let frontend know it's stable
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
