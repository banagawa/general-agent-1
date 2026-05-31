from __future__ import annotations

import json
from pathlib import Path

from agent_core.workspace_fingerprint import compute_workspace_fingerprint
from audit.log import log_event
from policy.capabilities import issue_token
from policy import capabilities


def test_plans_directory_is_execution_history_excluded_from_workspace_fingerprint(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    source_file = workspace / "tracked_source.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")

    before = compute_workspace_fingerprint()

    plan_dir = workspace / "plans" / "approved"
    plan_dir.mkdir(parents=True)
    (plan_dir / "example.json").write_text('{"state":"approved"}\n', encoding="utf-8")

    after = compute_workspace_fingerprint()

    assert after == before


def test_source_files_are_workspace_state_included_in_fingerprint(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    source_file = workspace / "tracked_source.py"
    source_file.write_text("VALUE = 1\n", encoding="utf-8")

    before = compute_workspace_fingerprint()

    source_file.write_text("VALUE = 2\n", encoding="utf-8")

    after = compute_workspace_fingerprint()

    assert after != before


def test_audit_log_uses_runtime_state_root(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    cwd = tmp_path / "cwd"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    log_event("RUNTIME_STATE_OWNERSHIP_CHECK", {"kind": "audit"})

    audit_file = workspace_container / "agent_runtime" / "project-a" / "audit" / "audit.jsonl"
    assert audit_file.is_file()
    assert not (cwd / ".audit").exists()
    assert not (workspace / ".audit").exists()

    event = json.loads(audit_file.read_text(encoding="utf-8").splitlines()[-1])
    assert event["action"] == "RUNTIME_STATE_OWNERSHIP_CHECK"
    assert event["detail"] == {"kind": "audit"}


def test_capability_tokens_use_runtime_state_root(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    cwd = tmp_path / "cwd"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    token = issue_token(actions={"FS_WRITE_PATCH"}, scope={})

    token_file = workspace_container / "agent_runtime" / "project-a" / "capabilities" / "capability_tokens.json"
    assert token_file.is_file()
    assert not (cwd / ".audit" / "capability_tokens.json").exists()
    assert not (workspace / ".audit" / "capability_tokens.json").exists()

    data = json.loads(token_file.read_text(encoding="utf-8"))
    assert token.id in data


def test_pending_patch_store_uses_runtime_state_root(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    workspace_container = app_root / "workspace"
    workspace = workspace_container / "project-a"
    cwd = tmp_path / "cwd"
    app_root.mkdir()
    workspace_container.mkdir()
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_APP_ROOT", str(app_root))
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    import agent_core.pending_store as pending_store

    pending_store.save_pending({})

    assert (workspace_container / "agent_runtime" / "project-a" / "pending" / "pending_patches.json").is_file()
    assert not (cwd / ".audit" / "pending_patches.json").exists()
    assert not (workspace / ".audit" / "pending_patches.json").exists()


def test_runtime_state_ownership_contract_has_migrated_runtime_bookkeeping():
    from sandbox.mounts import get_runtime_state_root

    assert capabilities._capability_dir() == get_runtime_state_root() / "capabilities"

def test_runtime_state_directory_is_excluded_from_workspace_fingerprint(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))

    source_file = workspace / "tracked_source.py"
    source_file.write_text("VALUE = 1\\n", encoding="utf-8")

    before = compute_workspace_fingerprint()

    runtime_dir = workspace / ".runtime_state" / "audit"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "audit.jsonl").write_text('{"event":"runtime"}\\n', encoding="utf-8")
    (runtime_dir / "capability_tokens.json").write_text("{}\\n", encoding="utf-8")

    after = compute_workspace_fingerprint()

    assert after == before
