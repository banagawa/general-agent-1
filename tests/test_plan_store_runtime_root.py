from __future__ import annotations

from agent_core.plan_schema import Plan
from agent_core.plan_store import (
    approved_plan_path,
    executed_plan_path,
    failure_envelope_path,
    pending_plan_path,
    store_pending_plan,
    summary_path,
)
from sandbox.mounts import get_runtime_state_root


def test_plan_paths_use_runtime_state_root(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    plan_hash = "a" * 64
    root = get_runtime_state_root() / "plans"

    assert pending_plan_path(plan_hash) == root / "pending" / f"{plan_hash}.json"
    assert approved_plan_path(plan_hash) == root / "approved" / f"{plan_hash}.json"
    assert executed_plan_path(plan_hash) == root / "executed" / f"{plan_hash}.json"
    assert failure_envelope_path(plan_hash, "tx-1") == root / "failures" / f"{plan_hash}-tx-1.json"
    assert summary_path(plan_hash, "tx-1") == root / "summaries" / f"{plan_hash}-tx-1.json"


def test_plan_store_writes_outside_target_worktree(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    plan_hash = "b" * 64
    plan = Plan(plan_id="runtime-plan-store-test", steps=(), metadata={})

    store_pending_plan(plan_hash, plan)

    expected = workspace_container / "agent_runtime" / "project-a" / "plans" / "pending" / f"{plan_hash}.json"

    assert expected.is_file()
    assert not (workspace / "plans").exists()
