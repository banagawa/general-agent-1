from __future__ import annotations

from sandbox.mounts import get_app_root, get_runtime_state_root, get_workspace_root


def test_runtime_state_root_is_visible_sibling_under_workspace_container(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    runtime_root = get_runtime_state_root()

    assert runtime_root == workspace_container / "agent_runtime" / "project-a"
    assert runtime_root != get_app_root()
    assert runtime_root != get_workspace_root()
    assert runtime_root.name == "project-a"
    assert runtime_root.parent.name == "agent_runtime"
    assert not runtime_root.parent.name.startswith(".")
    runtime_root.relative_to(workspace_container)


def test_runtime_state_root_is_outside_target_worktree(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    runtime_root = get_runtime_state_root()

    try:
        runtime_root.relative_to(workspace)
    except ValueError:
        pass
    else:
        raise AssertionError("runtime root must not be inside target worktree")


def test_runtime_state_root_does_not_create_directory_until_used(tmp_path, monkeypatch):
    workspace_container = tmp_path / "workspace"
    workspace = workspace_container / "project-a"
    workspace_container.mkdir()
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    runtime_root = get_runtime_state_root()

    assert runtime_root == workspace_container / "agent_runtime" / "project-a"
    assert not runtime_root.exists()
