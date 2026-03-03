from __future__ import annotations

import json
from pathlib import Path

import pytest

from policy.capabilities import issue_token


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


def _make_gateway():
    from tools.gateway import ToolGateway  # noqa: WPS433
    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # keep .audit out of the real repo
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _read_audit_events(cwd: Path) -> list[dict]:
    audit_file = cwd / ".audit" / "audit.jsonl"
    assert audit_file.exists(), "audit file missing"
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    assert lines, "audit file empty"
    return [json.loads(line) for line in lines]


def _last_event(cwd: Path, event_name: str) -> dict:
    events = _read_audit_events(cwd)
    for e in reversed(events):
        if e.get("event") == event_name:
            return e
    raise AssertionError(f"missing audit event: {event_name}")


def test_git_run_denied_is_audited(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    res = gw.git_run(["git", "push"])
    assert res["ok"] is False
    assert res.get("denied") is True

    e = _last_event(isolated_repo, "GIT_RUN_DENIED")
    meta = e.get("meta") or {}
    assert meta.get("decision") == "deny"
    assert meta.get("argv") == ["git", "push"]


def test_git_run_executed_is_audited(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    tok = issue_token(actions=["GIT_RUN"], ttl_seconds=120)

    init = gw.git_run(["git", "init"], cap_token_id=tok.id)
    assert init["ok"] is True

    e = _last_event(isolated_repo, "GIT_RUN_EXECUTED")
    meta = e.get("meta") or {}
    assert meta.get("decision") == "allow"
    assert meta.get("argv") == ["git", "init"]
    assert meta.get("exit_code") in (0, None)
