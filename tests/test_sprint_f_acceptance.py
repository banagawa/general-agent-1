from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_core.autonomy import (
    AutonomyBudget,
    AutonomyMode,
    AutonomyStopReason,
    run_autonomy_cycle,
)
from agent_core.loop import AgentLoop
from agent_core.plan_schema import Plan, ToolStep
from agent_core.task_spec import TaskSpec


class DummyGateway:
    pass


class SubmitRecorder:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, plan: Plan) -> dict:
        self.calls += 1
        return {
            "plan_hash": "b" * 64,
            "steps": len(plan.steps),
            "status": "PENDING_APPROVAL",
        }


def _task_spec() -> TaskSpec:
    return TaskSpec(
        raw_task="sprint f acceptance",
        goal="sprint f acceptance",
        success_criteria=["execution completes without error"],
    )


def _parse_plan(plan_dict: dict) -> Plan:
    return Plan(
        plan_id=plan_dict["plan_id"],
        steps=tuple(
            ToolStep(
                step_id=step["step_id"],
                tool=step["tool"],
                capability=step["capability"],
                args=step["args"],
            )
            for step in plan_dict["steps"]
        ),
        metadata=plan_dict.get("metadata", {}),
    )


def _test_plan_dict(task_spec: TaskSpec) -> dict:
    return {
        "plan_id": "sprint-f-acceptance-test-plan",
        "steps": [
            {
                "step_id": 1,
                "tool": "TEST_RUN",
                "capability": "test.run",
                "args": {
                    "argv": ["python", "--version"],
                    "timeout_seconds": 10,
                },
            }
        ],
    }


def _mutating_plan_dict(task_spec: TaskSpec) -> dict:
    return {
        "plan_id": "sprint-f-acceptance-mutating-plan",
        "steps": [
            {
                "step_id": 1,
                "tool": "FILE_CREATE",
                "capability": "file.create",
                "args": {
                    "path": "acceptance-created.txt",
                    "content": "created\n",
                },
            }
        ],
    }


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


def test_manual_and_assisted_modes_stop_at_pending_approval() -> None:
    for mode in (AutonomyMode.MANUAL, AutonomyMode.ASSISTED):
        recorder = SubmitRecorder()

        result = run_autonomy_cycle(
            task_spec=_task_spec(),
            mode=mode,
            budget=AutonomyBudget(max_cycles=2),
            generate_plan=_test_plan_dict,
            submit_plan=recorder,
            parse_plan=_parse_plan,
        )

        assert recorder.calls == 1
        assert result.status == "PENDING_APPROVAL"
        assert result.stop_reason == AutonomyStopReason.AWAITING_APPROVAL.value
        assert result.plan_hash == "b" * 64


def test_bounded_autonomous_is_disabled_by_default_through_command() -> None:
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "sprint f bounded acceptance",
        "mode": "BOUNDED_AUTONOMOUS",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=BOUNDED_AUTONOMOUS" in result
    assert "STATUS=DENIED" in result
    assert "STOP_REASON=DISABLED" in result
    assert "PLAN_HASH=" not in result


def test_bounded_autonomous_feature_flag_still_requires_approval(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_BOUNDED_AUTONOMY_ENABLED", "1")
    loop = AgentLoop(DummyGateway())
    payload = {
        "task": "sprint f bounded enabled acceptance",
        "mode": "BOUNDED_AUTONOMOUS",
    }

    result = loop.run(f"task.autonomy:{json.dumps(payload)}")

    assert "MODE=BOUNDED_AUTONOMOUS" in result
    assert "STATUS=PENDING_APPROVAL" in result
    assert "STOP_REASON=AWAITING_APPROVAL" in result
    assert "PLAN_HASH=" in result


def test_budget_exhaustion_denies_before_pending_plan() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1, cycles_used=1),
        generate_plan=_test_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert recorder.calls == 0
    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert result.plan_hash is None


def test_mutation_budget_denies_before_pending_plan() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1, max_mutation_steps=0),
        generate_plan=_mutating_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert recorder.calls == 0
    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert result.plan_hash is None


def test_failed_execution_rolls_back_file_create(
    isolated_repo: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _set_workspace(monkeypatch, tmp_path)
    target = workspace / "created.txt"

    from agent_core.plan_executor import approve_plan, execute_plan, submit_plan

    plan = Plan(
        plan_id="sprint-f-acceptance-rollback-plan",
        steps=(
            ToolStep(
                step_id=1,
                tool="FILE_CREATE",
                capability="file.create",
                args={
                    "path": "created.txt",
                    "content": "created\n",
                },
            ),
            ToolStep(
                step_id=2,
                tool="TEST_RUN",
                capability="test.run",
                args={
                    "argv": ["python", "-c", "import sys; sys.exit(1)"],
                    "timeout_seconds": 10,
                },
            ),
        ),
    )

    plan_hash = submit_plan(plan)["plan_hash"]
    approve_plan(plan_hash)

    result = execute_plan(_make_gateway(), plan_hash)

    assert result["summary"]["execution_status"] == "TEST_FAILURE"
    assert not target.exists()
    assert result["summary"]["rollback"]["attempted"] is True
    assert result["summary"]["rollback"]["deleted_paths"] == ["created.txt"]
