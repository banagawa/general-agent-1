from __future__ import annotations

import json
from pathlib import Path
import pytest

from tools.gateway import ToolGateway
from policy.capabilities import issue_token


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Force audit logs into temp directory and create expected workspace root.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    return tmp_path


def read_events(root: Path):
    audit_file = root / ".audit" / "audit.jsonl"
    assert audit_file.exists()
    return [json.loads(line) for line in audit_file.read_text().splitlines()]


def find_events(events, name):
    return [e for e in events if e["event"] == name]


def test_cmd_run_success_emits_start_and_commit(isolated_repo):
    gw = ToolGateway()
    token = issue_token(actions=["CMD_RUN"], scope={}, ttl_seconds=60)

    result = gw.cmd_run(
        ["python", "-c", "print('hi')"],
        timeout_seconds=5,
        cap_token_id=token.id,
    )

    assert result["ok"] is True

    events = read_events(isolated_repo)

    starts = find_events(events, "TRANSACTION_START")
    commits = find_events(events, "TRANSACTION_COMMIT")
    rollbacks = find_events(events, "TRANSACTION_ROLLBACK")

    assert len(starts) == 1
    assert len(commits) == 1
    assert len(rollbacks) == 0

    assert starts[0]["meta"]["tx_id"] == commits[0]["meta"]["tx_id"]


def test_cmd_run_timeout_emits_rollback(isolated_repo):
    gw = ToolGateway()
    token = issue_token(actions=["CMD_RUN"], scope={}, ttl_seconds=60)

    result = gw.cmd_run(
        ["python", "-c", "import time; time.sleep(2)"],
        timeout_seconds=1,
        cap_token_id=token.id,
    )

    assert result["ok"] is True
    assert result["timed_out"] is True

    events = read_events(isolated_repo)

    starts = find_events(events, "TRANSACTION_START")
    commits = find_events(events, "TRANSACTION_COMMIT")
    rollbacks = find_events(events, "TRANSACTION_ROLLBACK")

    assert len(starts) == 1
    assert len(commits) == 0
    assert len(rollbacks) == 1
    assert rollbacks[0]["meta"]["reason"] == "TIMEOUT"


def test_cmd_run_missing_token_rolls_back(isolated_repo):
    gw = ToolGateway()

    result = gw.cmd_run(
        ["python", "-c", "print('hi')"],
        timeout_seconds=5,
        cap_token_id=None,
    )

    assert result["ok"] is False
    assert result["denied"] is True

    events = read_events(isolated_repo)

    starts = find_events(events, "TRANSACTION_START")
    commits = find_events(events, "TRANSACTION_COMMIT")
    rollbacks = find_events(events, "TRANSACTION_ROLLBACK")

    assert len(starts) == 1
    assert len(commits) == 0
    assert len(rollbacks) == 1
    assert rollbacks[0]["meta"]["reason"] == "POLICY_DENIAL"
