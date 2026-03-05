from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

STATE_FILE = BACKEND_ROOT / "state" / "runtime_state.json"
os.environ.setdefault("NEO4J_URI", "")


def _reset_runtime_state() -> None:
    from state.store import JsonStateStore

    store = JsonStateStore(STATE_FILE)
    state = store._default_state()
    store.save(state)


@pytest.fixture(autouse=True)
def reset_runtime_state_each_test():
    _reset_runtime_state()


@pytest.fixture(scope="session")
def client():
    from main import app

    with TestClient(app) as c:
        yield c
