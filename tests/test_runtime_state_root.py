from __future__ import annotations

from sandbox.mounts import get_app_root, get_runtime_state_root, get_workspace_root


def test_runtime_state_root_is_workspace_scoped(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace = tmp_path / "workspace"
    app_root.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    runtime_root = get_runtime_state_root()

    assert runtime_root == workspace / ".runtime_state"
    assert runtime_root != get_app_root()
    assert runtime_root != get_workspace_root()
    runtime_root.relative_to(workspace)


def test_runtime_state_root_does_not_create_directory_until_used(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    runtime_root = get_runtime_state_root()

    assert runtime_root == workspace / ".runtime_state"
    assert not runtime_root.exists()
