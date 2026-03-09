from __future__ import annotations

import pytest

from deepagent.lead_os import _resolve_project_root


@pytest.mark.fast
def test_resolve_project_root_handles_shallow_container_layout(monkeypatch):
    monkeypatch.delenv("PORTHON_PROJECT_ROOT", raising=False)
    root = _resolve_project_root("/app/deepagent/lead_os.py")
    assert str(root) == "/app"


@pytest.mark.fast
def test_resolve_project_root_prefers_env_override(monkeypatch, tmp_path):
    custom_root = tmp_path / "my_root"
    custom_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PORTHON_PROJECT_ROOT", str(custom_root))

    root = _resolve_project_root("/app/deepagent/lead_os.py")
    assert root == custom_root.resolve()
