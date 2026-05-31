from __future__ import annotations

from agent_core.runtime_history_health import (
    RUNTIME_HISTORY_FILE_COUNT_WARNING,
    RUNTIME_HISTORY_SIZE_WARNING,
    get_runtime_history_health,
)
from sandbox.mounts import get_runtime_state_root


def test_runtime_history_health_reports_missing_root_without_creating_it(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    expected_root = workspace_container / "agent_runtime" / "project-a"

    health = get_runtime_history_health()

    assert health.root == str(expected_root)
    assert health.exists is False
    assert health.total_bytes == 0
    assert health.file_count == 0
    assert health.warnings == ()
    assert not expected_root.exists()


def test_runtime_history_health_reports_total_bytes_and_file_count(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    root = get_runtime_state_root()
    (root / "audit").mkdir(parents=True)
    (root / "plans" / "approved").mkdir(parents=True)

    audit_file = root / "audit" / "audit.jsonl"
    plan_file = root / "plans" / "approved" / "a.json"

    audit_file.write_text("audit\n", encoding="utf-8")
    plan_file.write_text("plan-data\n", encoding="utf-8")

    health = get_runtime_history_health()

    assert health.exists is True
    assert health.file_count == 2
    assert health.total_bytes == audit_file.stat().st_size + plan_file.stat().st_size
    assert health.warnings == ()


def test_runtime_history_health_emits_warning_codes_only(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    root = get_runtime_state_root()
    root.mkdir(parents=True)
    (root / "one.txt").write_text("12345", encoding="utf-8")
    (root / "two.txt").write_text("67890", encoding="utf-8")

    health = get_runtime_history_health(size_warning_bytes=1, file_count_warning=1)

    assert RUNTIME_HISTORY_SIZE_WARNING in health.warnings
    assert RUNTIME_HISTORY_FILE_COUNT_WARNING in health.warnings


def test_runtime_history_health_does_not_touch_target_worktree(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    get_runtime_history_health()

    assert not (workspace / "agent_runtime").exists()
    assert not (workspace / ".runtime_state").exists()
    assert not (workspace / ".audit").exists()
