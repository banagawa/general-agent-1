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


def test_audit_log_is_currently_cwd_relative_runtime_bookkeeping(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    log_event("RUNTIME_STATE_OWNERSHIP_CHECK", {"kind": "audit"})

    audit_file = cwd / ".audit" / "audit.jsonl"
    assert audit_file.is_file()
    assert not (workspace / ".audit" / "audit.jsonl").exists()

    event = json.loads(audit_file.read_text(encoding="utf-8").splitlines()[-1])
    assert event["action"] == "RUNTIME_STATE_OWNERSHIP_CHECK"
    assert event["detail"] == {"kind": "audit"}


def test_capability_tokens_are_currently_cwd_relative_runtime_bookkeeping(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    token = issue_token(actions={"FS_WRITE_PATCH"}, scope={})

    token_file = cwd / ".audit" / "capability_tokens.json"
    assert token_file.is_file()
    assert not (workspace / ".audit" / "capability_tokens.json").exists()

    data = json.loads(token_file.read_text(encoding="utf-8"))
    assert token.id in data


def test_pending_patch_store_is_currently_cwd_relative_runtime_bookkeeping(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    # Import after chdir because pending_store defines cwd-relative module constants.
    import importlib
    import agent_core.pending_store as pending_store

    pending_store = importlib.reload(pending_store)

    assert pending_store.PENDING_FILE == Path(".audit") / "pending_patches.json"
    assert not (workspace / ".audit" / "pending_patches.json").exists()


def test_runtime_state_ownership_contract_has_no_production_behavior_change():
    assert capabilities.AUDIT_DIR == Path(".audit")

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
