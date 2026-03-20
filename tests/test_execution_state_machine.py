from __future__ import annotations

from pathlib import Path
import pytest


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_invalid_state_transition_executed_to_failed_is_denied(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_store import (
        acquire_execution_lock,
        transition_to_executed,
        transition_to_failed,
        STATE_IN_FLIGHT,
        STATE_EXECUTED,
        STATE_FAILED,
    )

    plan_hash = "a" * 64

    acquire_execution_lock(
        plan_hash,
        {
            "plan_hash": plan_hash,
            "tx_id": "tx-1",
            "state": STATE_IN_FLIGHT,
            "execution_started_at": "2026-03-20T00:00:00Z",
        },
    )

    transition_to_executed(
        plan_hash,
        {
            "plan_hash": plan_hash,
            "tx_id": "tx-1",
            "state": STATE_EXECUTED,
            "execution_started_at": "2026-03-20T00:00:00Z",
            "execution_finished_at": "2026-03-20T00:01:00Z",
            "result_status": "SUCCESS",
        },
    )

    with pytest.raises(RuntimeError, match="invalid execution state transition"):
        transition_to_failed(
            plan_hash,
            {
                "plan_hash": plan_hash,
                "tx_id": "tx-1",
                "state": STATE_FAILED,
                "execution_started_at": "2026-03-20T00:00:00Z",
                "execution_finished_at": "2026-03-20T00:02:00Z",
                "result_status": "FAILED",
            },
        )
