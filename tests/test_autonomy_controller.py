from __future__ import annotations

from agent_core.autonomy import (
    AutonomyBudget,
    AutonomyMode,
    AutonomyStopReason,
    budget_exhausted,
    budget_is_valid,
    budget_remaining,
    run_autonomy_cycle,
)
from agent_core.plan_schema import Plan, ToolStep
from agent_core.task_spec import TaskSpec


def _task_spec() -> TaskSpec:
    return TaskSpec(
        raw_task="add sprint f autonomy controller",
        goal="add sprint f autonomy controller",
        success_criteria=["execution completes without error"],
    )


def _plan_dict(task_spec: TaskSpec) -> dict:
    return {
        "plan_id": "autonomy-test-plan",
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
        "metadata": {
            "intent": {
                "goal": task_spec.goal,
                "success_criteria": task_spec.success_criteria,
            }
        },
    }


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


class SubmitRecorder:
    def __init__(self) -> None:
        self.calls = 0
        self.plans = []

    def __call__(self, plan: Plan) -> dict:
        self.calls += 1
        self.plans.append(plan)
        return {
            "plan_hash": "a" * 64,
            "steps": len(plan.steps),
            "status": "PENDING_APPROVAL",
        }


def test_budget_helpers_accept_valid_budget() -> None:
    budget = AutonomyBudget(max_cycles=2, cycles_used=1)

    assert budget_is_valid(budget) is True
    assert budget_exhausted(budget) is False
    assert budget_remaining(budget)["cycles"] == 1


def test_exhausted_cycle_budget_is_fail_closed() -> None:
    recorder = SubmitRecorder()
    budget = AutonomyBudget(max_cycles=1, cycles_used=1)

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=budget,
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert result.plan_hash is None
    assert recorder.calls == 0


def test_manual_mode_creates_one_pending_plan_and_stops_for_approval() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert recorder.calls == 1
    assert result.plan_hash == "a" * 64
    assert result.status == "PENDING_APPROVAL"
    assert result.stop_reason == AutonomyStopReason.AWAITING_APPROVAL.value
    assert result.budget_remaining["cycles"] == 0


def test_assisted_mode_creates_one_pending_plan_and_stops_for_approval() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.ASSISTED,
        budget=AutonomyBudget(max_cycles=1),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert recorder.calls == 1
    assert result.status == "PENDING_APPROVAL"
    assert result.stop_reason == AutonomyStopReason.AWAITING_APPROVAL.value


def test_bounded_autonomous_is_disabled_by_default() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.BOUNDED_AUTONOMOUS,
        budget=AutonomyBudget(max_cycles=1),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.DISABLED.value
    assert result.plan_hash is None
    assert recorder.calls == 0


def test_controller_does_not_execute_plan_directly() -> None:
    recorder = SubmitRecorder()
    executed = {"called": False}

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert executed["called"] is False
    assert recorder.calls == 1
    assert result.stop_reason == AutonomyStopReason.AWAITING_APPROVAL.value


def test_mutation_budget_exhaustion_denies_before_submit() -> None:
    recorder = SubmitRecorder()

    def mutating_plan_dict(task_spec: TaskSpec) -> dict:
        return {
            "plan_id": "autonomy-mutating-test-plan",
            "steps": [
                {
                    "step_id": 1,
                    "tool": "FILE_CREATE",
                    "capability": "file.create",
                    "args": {
                        "path": "created.txt",
                        "content": "created\\n",
                    },
                }
            ],
        }

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1, max_mutation_steps=0),
        generate_plan=mutating_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert result.plan_hash is None
    assert recorder.calls == 0


def test_runtime_budget_exhaustion_denies_before_submit(monkeypatch) -> None:
    recorder = SubmitRecorder()
    ticks = iter([0.0, 2.0])

    monkeypatch.setattr("agent_core.autonomy.time.monotonic", lambda: next(ticks))

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=1, max_runtime_seconds=1),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert result.plan_hash is None
    assert result.budget_remaining["runtime_seconds"] <= 0
    assert recorder.calls == 0


def test_success_result_budget_remaining_accounts_for_runtime(monkeypatch) -> None:
    recorder = SubmitRecorder()
    ticks = iter([10.0, 13.0])

    monkeypatch.setattr("agent_core.autonomy.time.monotonic", lambda: next(ticks))

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=2, max_runtime_seconds=10),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "PENDING_APPROVAL"
    assert result.budget_remaining["cycles"] == 1
    assert result.budget_remaining["runtime_seconds"] == 7
    assert recorder.calls == 1


def test_success_result_budget_remaining_accounts_for_mutations() -> None:
    recorder = SubmitRecorder()

    def mutating_plan_dict(task_spec: TaskSpec) -> dict:
        return {
            "plan_id": "autonomy-mutating-budget-accounting-test-plan",
            "steps": [
                {
                    "step_id": 1,
                    "tool": "FILE_CREATE",
                    "capability": "file.create",
                    "args": {
                        "path": "created.txt",
                        "content": "created\\n",
                    },
                }
            ],
        }

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=2, max_mutation_steps=2),
        generate_plan=mutating_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "PENDING_APPROVAL"
    assert result.budget_remaining["mutation_steps"] == 1
    assert recorder.calls == 1


def test_budget_exhaustion_returns_denied_status() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(
            max_cycles=1,
            cycles_used=1,
        ),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "DENIED"
    assert result.stop_reason == AutonomyStopReason.BUDGET_EXHAUSTED.value
    assert recorder.calls == 0


def test_pending_approval_contains_plan_hash() -> None:
    recorder = SubmitRecorder()

    result = run_autonomy_cycle(
        task_spec=_task_spec(),
        mode=AutonomyMode.MANUAL,
        budget=AutonomyBudget(max_cycles=2),
        generate_plan=_plan_dict,
        submit_plan=recorder,
        parse_plan=_parse_plan,
    )

    assert result.status == "PENDING_APPROVAL"
    assert result.plan_hash == "a" * 64
