from __future__ import annotations

from pathlib import Path

import pytest

from state.store import JsonStateStore


@pytest.mark.fast
def test_state_store_bootstraps_default_state(tmp_path: Path):
    store = JsonStateStore(tmp_path / "runtime_state.json")
    state = store.load()

    assert state.persona_id == "p05"
    assert len(state.workers) == 6
    assert len(state.budgets) == 6
    assert len(state.circuits) == 6
    assert state.active_scenario is None
