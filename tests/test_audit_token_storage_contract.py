from __future__ import annotations

import json

from audit.log import log_event
from policy.capabilities import issue_token, revoke_token


def test_audit_log_uses_runtime_state_root_not_cwd(tmp_path, monkeypatch):
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

    log_event("AUDIT_LOCATION_CONTRACT", {"ok": True})

    audit_file = workspace_container / "agent_runtime" / "project-a" / "audit" / "audit.jsonl"
    assert audit_file.is_file()
    assert not (cwd / ".audit").exists()
    assert not (workspace / ".audit").exists()
    assert not (workspace / ".runtime_state").exists()

    event = json.loads(audit_file.read_text(encoding="utf-8").splitlines()[-1])
    assert event["action"] == "AUDIT_LOCATION_CONTRACT"
    assert event["detail"] == {"ok": True}


def test_capability_token_store_uses_runtime_state_root_not_cwd(tmp_path, monkeypatch):
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
    revoke_token(token.id)

    capability_dir = workspace_container / "agent_runtime" / "project-a" / "capabilities"
    assert (capability_dir / "capability_tokens.json").is_file()
    assert (capability_dir / "capability_revocations.json").is_file()
    assert not (cwd / ".audit").exists()
    assert not (workspace / ".audit").exists()
    assert not (workspace / ".runtime_state").exists()


def test_audit_and_token_state_are_kept_outside_target_worktree(tmp_path, monkeypatch):
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

    log_event("FINGERPRINT_CONTRACT_CHECK", {})
    issue_token(actions={"FS_WRITE_PATCH"}, scope={})

    assert (workspace_container / "agent_runtime" / "project-a").is_dir()
    assert not (cwd / ".audit").exists()
    assert not (workspace / ".audit").exists()
    assert not (workspace / ".runtime_state").exists()
