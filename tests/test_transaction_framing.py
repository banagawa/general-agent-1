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
    # Import inside function so env vars are applied before mounts/policy read them.
    from tools.gateway import ToolGateway  # noqa: WPS433

    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # Ensure .audit lands in tmp_path, not your real repo.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _read_audit_events(repo_root: Path) -> list[dict]:
    audit_file = repo_root / ".audit" / "audit.jsonl"
    assert audit_file.exists(), "Expected audit log to be written"
    rows: list[dict] = []
    for line in audit_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _find_events(rows: list[dict], event_name: str) -> list[dict]:
    return [r for r in rows if r.get("event") == event_name]


def test_cmd_run_denied_emits_tx_start_and_rollback(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["bash"], cap_token_id=tok.id)

    assert res.get("ok") is False
    assert res.get("denied") is True

    rows = _read_audit_events(isolated_repo)
    starts = _find_events(rows, "TRANSACTION_START")
    rollbacks = _find_events(rows, "TRANSACTION_ROLLBACK")

    assert starts, "Expected TRANSACTION_START"
    assert rollbacks, "Expected TRANSACTION_ROLLBACK"

    # Assert last start/rollback correlate via tx_id
    s_meta = starts[-1].get("meta", {})
    r_meta = rollbacks[-1].get("meta", {})

    assert s_meta.get("tool") == "CMD_RUN"
    assert r_meta.get("tool") == "CMD_RUN"
    assert s_meta.get("tx_id")
    assert r_meta.get("tx_id") == s_meta.get("tx_id")
    assert r_meta.get("rollback_reason") == "POLICY_DENIAL"


def test_cmd_run_allowed_emits_tx_start_and_commit(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "--version"], cap_token_id=tok.id)

    assert res.get("denied") is not True

    rows = _read_audit_events(isolated_repo)
    starts = _find_events(rows, "TRANSACTION_START")
    commits = _find_events(rows, "TRANSACTION_COMMIT")

    assert starts, "Expected TRANSACTION_START"
    assert commits, "Expected TRANSACTION_COMMIT"

    s_meta = starts[-1].get("meta", {})
    c_meta = commits[-1].get("meta", {})

    assert s_meta.get("tool") == "CMD_RUN"
    assert c_meta.get("tool") == "CMD_RUN"
    assert s_meta.get("tx_id")
    assert c_meta.get("tx_id") == s_meta.get("tx_id")
    assert isinstance(c_meta.get("duration_ms"), int)


def test_cmd_run_timeout_emits_tx_rollback_timeout(isolated_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _set_workspace(monkeypatch, tmp_path)
    gw = _make_gateway()

    tok = issue_token(actions=["CMD_RUN"], ttl_seconds=120)
    res = gw.cmd_run(["python", "-c", "import time; time.sleep(2)"], timeout_seconds=1, cap_token_id=tok.id)

    assert res.get("denied") is not True
    assert res.get("timed_out") is True

    rows = _read_audit_events(isolated_repo)
    starts = _find_events(rows, "TRANSACTION_START")
    rollbacks = _find_events(rows, "TRANSACTION_ROLLBACK")

    assert starts, "Expected TRANSACTION_START"
    assert rollbacks, "Expected TRANSACTION_ROLLBACK"

    s_meta = starts[-1].get("meta", {})
    r_meta = rollbacks[-1].get("meta", {})

    assert s_meta.get("tool") == "CMD_RUN"
    assert r_meta.get("tool") == "CMD_RUN"
    assert s_meta.get("tx_id")
    assert r_meta.get("tx_id") == s_meta.get("tx_id")
    assert r_meta.get("rollback_reason") == "TIMEOUT"
