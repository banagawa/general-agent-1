from __future__ import annotations

import json

from audit.log import log_event
from policy.capabilities import issue_token, revoke_token


def test_audit_log_remains_cwd_relative_when_workspace_root_is_set(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    log_event("AUDIT_LOCATION_CONTRACT", {"ok": True})

    audit_file = cwd / ".audit" / "audit.jsonl"
    assert audit_file.is_file()
    assert not (workspace / ".audit" / "audit.jsonl").exists()

    event = json.loads(audit_file.read_text(encoding="utf-8").splitlines()[-1])
    assert event["action"] == "AUDIT_LOCATION_CONTRACT"
    assert event["detail"] == {"ok": True}


def test_capability_token_store_remains_cwd_relative_when_workspace_root_is_set(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    token = issue_token(actions={"FS_WRITE_PATCH"}, scope={})
    revoke_token(token.id)

    assert (cwd / ".audit" / "capability_tokens.json").is_file()
    assert (cwd / ".audit" / "capability_revocations.json").is_file()
    assert not (workspace / ".audit" / "capability_tokens.json").exists()
    assert not (workspace / ".audit" / "capability_revocations.json").exists()


def test_audit_and_token_state_are_not_currently_workspace_fingerprint_neutral(tmp_path, monkeypatch):
    """
    Characterization test.

    Audit/token state is currently cwd-relative. Moving it under workspace_root
    would make plan approval/execution create workspace files unless the
    fingerprint model excludes runtime state first.
    """
    workspace = tmp_path / "workspace"
    cwd = tmp_path / "cwd"
    workspace.mkdir()
    cwd.mkdir()

    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.chdir(cwd)

    log_event("FINGERPRINT_CONTRACT_CHECK", {})
    issue_token(actions={"FS_WRITE_PATCH"}, scope={})

    assert (cwd / ".audit").is_dir()
    assert not (workspace / ".audit").exists()
