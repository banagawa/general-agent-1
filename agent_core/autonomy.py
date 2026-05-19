from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import time
from typing import Any, Callable, Dict, Optional

from audit.log import log_event
from agent_core.task_spec import TaskSpec


class AutonomyMode(str, Enum):
    MANUAL = "MANUAL"
    ASSISTED = "ASSISTED"
    BOUNDED_AUTONOMOUS = "BOUNDED_AUTONOMOUS"


class AutonomyStopReason(str, Enum):
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    SUCCESS_CRITERIA_MET = "SUCCESS_CRITERIA_MET"
    DENIED = "DENIED"
    VIOLATION = "VIOLATION"
    ERROR = "ERROR"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class AutonomyBudget:
    max_cycles: int = 1
    max_runtime_seconds: int = 120
    max_mutation_steps: int = 1
    cycles_used: int = 0
    runtime_seconds_used: int = 0
    mutation_steps_used: int = 0


@dataclass(frozen=True)
class AutonomyCycleResult:
    mode: str
    task_goal: str
    cycle_index: int
    plan_hash: Optional[str]
    status: str
    stop_reason: str
    budget_remaining: Dict[str, int]


def budget_remaining(budget: AutonomyBudget) -> Dict[str, int]:
    return {
        "cycles": budget.max_cycles - budget.cycles_used,
        "runtime_seconds": budget.max_runtime_seconds - budget.runtime_seconds_used,
        "mutation_steps": budget.max_mutation_steps - budget.mutation_steps_used,
    }


def budget_is_valid(budget: AutonomyBudget) -> bool:
    values = (
        budget.max_cycles,
        budget.max_runtime_seconds,
        budget.max_mutation_steps,
        budget.cycles_used,
        budget.runtime_seconds_used,
        budget.mutation_steps_used,
    )
    if not all(isinstance(value, int) for value in values):
        return False
    if budget.max_cycles <= 0 or budget.max_runtime_seconds <= 0 or budget.max_mutation_steps <= 0:
        return False
    if budget.cycles_used < 0 or budget.runtime_seconds_used < 0 or budget.mutation_steps_used < 0:
        return False
    return True


def budget_exhausted(budget: AutonomyBudget) -> bool:
    if not budget_is_valid(budget):
        return True
    remaining = budget_remaining(budget)
    return any(value <= 0 for value in remaining.values())


_MUTATING_TOOLS = {"PATCH_APPLY", "PATCH_EDIT", "FILE_CREATE"}


def _count_mutation_steps(plan: Any) -> int:
    steps = getattr(plan, "steps", ())
    count = 0

    for step in steps:
        if getattr(step, "tool", None) in _MUTATING_TOOLS:
            count += 1

    return count


def run_autonomy_cycle(
    *,
    task_spec: TaskSpec,
    mode: AutonomyMode,
    budget: AutonomyBudget,
    generate_plan: Callable[[TaskSpec], Dict[str, Any]],
    submit_plan: Callable[[Any], Dict[str, Any]],
    parse_plan: Callable[[Dict[str, Any]], Any],
    bounded_autonomous_enabled: bool = False,
) -> AutonomyCycleResult:
    started_monotonic = time.monotonic()

    if not isinstance(task_spec, TaskSpec):
        raise ValueError("task_spec must be TaskSpec")

    if not budget_is_valid(budget) or budget_exhausted(budget):
        log_event(
            "AUTONOMY_BUDGET_EXHAUSTED",
            {
                "mode": mode.value,
                "task_goal": task_spec.goal,
                "cycles_used": budget.cycles_used,
                "runtime_seconds_used": budget.runtime_seconds_used,
                "mutation_steps_used": budget.mutation_steps_used,
            },
        )

        return AutonomyCycleResult(
            mode=mode.value,
            task_goal=task_spec.goal,
            cycle_index=budget.cycles_used,
            plan_hash=None,
            status="DENIED",
            stop_reason=AutonomyStopReason.BUDGET_EXHAUSTED.value,
            budget_remaining=budget_remaining(budget),
        )

    if mode == AutonomyMode.BOUNDED_AUTONOMOUS and not bounded_autonomous_enabled:
        return AutonomyCycleResult(
            mode=mode.value,
            task_goal=task_spec.goal,
            cycle_index=budget.cycles_used,
            plan_hash=None,
            status="DENIED",
            stop_reason=AutonomyStopReason.DISABLED.value,
            budget_remaining=budget_remaining(budget),
        )

    if mode not in {AutonomyMode.MANUAL, AutonomyMode.ASSISTED, AutonomyMode.BOUNDED_AUTONOMOUS}:
        return AutonomyCycleResult(
            mode=str(mode),
            task_goal=task_spec.goal,
            cycle_index=budget.cycles_used,
            plan_hash=None,
            status="DENIED",
            stop_reason=AutonomyStopReason.DENIED.value,
            budget_remaining=budget_remaining(budget),
        )

    plan_dict = generate_plan(task_spec)
    plan = parse_plan(plan_dict)

    elapsed_seconds = int(time.monotonic() - started_monotonic)
    projected_runtime_seconds = budget.runtime_seconds_used + elapsed_seconds
    if projected_runtime_seconds >= budget.max_runtime_seconds:
        return AutonomyCycleResult(
            mode=mode.value,
            task_goal=task_spec.goal,
            cycle_index=budget.cycles_used,
            plan_hash=None,
            status="DENIED",
            stop_reason=AutonomyStopReason.BUDGET_EXHAUSTED.value,
            budget_remaining=budget_remaining(
                AutonomyBudget(
                    max_cycles=budget.max_cycles,
                    max_runtime_seconds=budget.max_runtime_seconds,
                    max_mutation_steps=budget.max_mutation_steps,
                    cycles_used=budget.cycles_used,
                    runtime_seconds_used=projected_runtime_seconds,
                    mutation_steps_used=budget.mutation_steps_used,
                )
            ),
        )

    projected_mutation_steps = budget.mutation_steps_used + _count_mutation_steps(plan)
    if projected_mutation_steps > budget.max_mutation_steps:
        return AutonomyCycleResult(
            mode=mode.value,
            task_goal=task_spec.goal,
            cycle_index=budget.cycles_used,
            plan_hash=None,
            status="DENIED",
            stop_reason=AutonomyStopReason.BUDGET_EXHAUSTED.value,
            budget_remaining=budget_remaining(budget),
        )

    submitted = submit_plan(plan)

    log_event(
        "AUTONOMY_PLAN_PENDING_APPROVAL",
        {
            "mode": mode.value,
            "task_goal": task_spec.goal,
            "plan_hash": submitted.get("plan_hash"),
            "cycles_used": budget.cycles_used + 1,
            "projected_runtime_seconds": projected_runtime_seconds,
            "projected_mutation_steps": projected_mutation_steps,
        },
    )

    return AutonomyCycleResult(
        mode=mode.value,
        task_goal=task_spec.goal,
        cycle_index=budget.cycles_used + 1,
        plan_hash=submitted.get("plan_hash"),
        status=submitted.get("status", "PENDING_APPROVAL"),
        stop_reason=AutonomyStopReason.AWAITING_APPROVAL.value,
        budget_remaining=budget_remaining(
            AutonomyBudget(
                max_cycles=budget.max_cycles,
                max_runtime_seconds=budget.max_runtime_seconds,
                max_mutation_steps=budget.max_mutation_steps,
                cycles_used=budget.cycles_used + 1,
                runtime_seconds_used=projected_runtime_seconds,
                mutation_steps_used=projected_mutation_steps,
            )
        ),
    )
