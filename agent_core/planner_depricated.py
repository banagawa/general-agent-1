from __future__ import annotations

from typing import List

from agent_core.task_spec import TaskSpec


def task_to_spec(raw_task: str) -> TaskSpec:
    if not isinstance(raw_task, str):
        raise ValueError("task must be a string")

    raw_task = raw_task.strip()
    if not raw_task:
        raise ValueError("empty task")

    # minimal deterministic parsing
    goal = raw_task

    success_criteria = _derive_success_criteria(goal)

    return TaskSpec(
        raw_task=raw_task,
        goal=goal,
        success_criteria=success_criteria,
    )


def _derive_success_criteria(goal: str) -> List[str]:
    goal = goal.lower()

    criteria = []

    if "test" in goal:
        criteria.append("tests pass")

    if "run" in goal or "verify" in goal:
        criteria.append("command executes successfully")

    if not criteria:
        criteria.append("execution completes without error")

    return criteria


def generate_plan(task_spec: TaskSpec) -> dict:
    if not isinstance(task_spec, TaskSpec):
        raise ValueError("task_spec must be TaskSpec")

    steps = []

    # deterministic mapping (no guessing)
    steps.append(
        {
            "step_id": 1,
            "tool": "TEST_RUN",
            "capability": "test.run",
            "args": {
                "argv": ["python", "--version"],
                "timeout_seconds": 10,
            },
        }
    )

    return {
        "plan_id": "planner-v1",
        "goal": task_spec.goal,
        "success_criteria": task_spec.success_criteria,
        "steps": steps,
    }
