from __future__ import annotations

from pathlib import Path
import json
import pytest


def _set_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("AGENT_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))
    return workspace


def _make_gateway():
    from tools.gateway import ToolGateway
    return ToolGateway()


@pytest.fixture()
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _read_audit_events(repo_root: Path) -> list[dict]:
    audit_dir = repo_root / ".audit"
    events: list[dict] = []

    if not audit_dir.exists():
        return events

    for path in sorted(audit_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))

    return events


def test_replay_denial_emits_reason_code(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_schema import Plan, ToolStep
    from agent_core.plan_executor import submit_plan, approve_plan, execute_plan

    gw = _make_gateway()

    plan = Plan(
        plan_id="audit-replay-test-1",
        steps=(
            ToolStep(
                step_id=1,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "--version"],
                    "timeout_seconds": 10,
                },
            ),
        ),
        metadata={},
    )

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]

    approve_result = approve_plan(plan_hash)
    assert approve_result["status"] == "APPROVED"

    first = execute_plan(gw, plan_hash)
    assert first["plan_hash"] == plan_hash

    with pytest.raises(RuntimeError, match="approved plan already executed"):
        execute_plan(gw, plan_hash)

    events = _read_audit_events(isolated_repo)

    deny_events = [
        e for e in events
        if e.get("action") == "DENY"
        and e.get("detail", {}).get("reason_code") == "PLAN_REPLAY_DENIED"
    ]

    assert deny_events, events

    payload = deny_events[-1]["detail"]

    assert payload["reason_code"] == "PLAN_REPLAY_DENIED"
    assert payload["reason"] == "approved plan already executed"
    assert payload["plan_hash"] == plan_hash
    assert "timestamp" in payload

def test_workspace_drift_denial_emits_reason_code(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    workspace = _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_schema import Plan, ToolStep
    from agent_core.plan_executor import submit_plan, approve_plan, execute_plan

    gw = _make_gateway()

    plan = Plan(
        plan_id="audit-drift-test-1",
        steps=(
            ToolStep(
                step_id=1,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "--version"],
                    "timeout_seconds": 10,
                },
            ),
        ),
        metadata={},
    )

    submit_result = submit_plan(plan)
    plan_hash = submit_result["plan_hash"]

    approve_plan(plan_hash)

    # mutate workspace to force drift
    drift_file = workspace / "drift.txt"
    drift_file.write_text("drift", encoding="utf-8")

    with pytest.raises(RuntimeError, match="workspace drift detected"):
        execute_plan(gw, plan_hash)

    events = _read_audit_events(isolated_repo)

    deny_events = [
        e for e in events
        if e.get("action") == "DENY"
        and e.get("detail", {}).get("reason_code") == "PLAN_EXECUTION_DRIFT_DENIED"
    ]

    assert deny_events, events
