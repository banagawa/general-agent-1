from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
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


def test_only_one_concurrent_execution_of_same_plan_succeeds(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _set_workspace(monkeypatch, tmp_path)

    from agent_core.plan_schema import Plan, ToolStep
    from agent_core.plan_executor import submit_plan, approve_plan, execute_plan

    gw = _make_gateway()

    plan = Plan(
        plan_id="concurrent-replay-test-1",
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

    def run_once():
        try:
            result = execute_plan(gw, plan_hash)
            return ("success", result["plan_hash"])
        except RuntimeError as e:
            return ("error", str(e))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_once) for _ in range(2)]
        outcomes = [f.result() for f in futures]

    successes = [x for x in outcomes if x[0] == "success"]
    errors = [x for x in outcomes if x[0] == "error"]

    assert len(successes) == 1, outcomes
    assert len(errors) == 1, outcomes
    assert errors[0][1] == "approved plan already executed"
