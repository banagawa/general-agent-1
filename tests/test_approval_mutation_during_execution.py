from __future__ import annotations

from pathlib import Path
import json
import threading
import time
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


def test_approved_plan_mutation_after_execution_starts_does_not_change_outcome(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_schema import Plan, ToolStep
    from agent_core.plan_executor import submit_plan, approve_plan, execute_plan
    from agent_core.plan_store import approved_plan_path

    gw = _make_gateway()

    plan = Plan(
        plan_id="approval-mutation-test-1",
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

    path = approved_plan_path(plan_hash)

    result_holder = {}
    error_holder = {}

    def run_execute():
        try:
            result_holder["value"] = execute_plan(gw, plan_hash)
        except Exception as e:
            error_holder["value"] = e

    t = threading.Thread(target=run_execute)
    t.start()

    # give execute_plan a moment to start and pass preflight
    time.sleep(0.1)

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    payload["plan_id"] = "tampered-after-start"

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)

    t.join(timeout=5)

    assert "value" in result_holder, error_holder
    assert result_holder["value"]["plan_hash"] == plan_hash
