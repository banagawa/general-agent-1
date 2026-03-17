from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from agent_core.llm_planner import (
    LLMPlannerClient,
    LLMPlannerConfig,
    PlannerDenied,
    generate_plan_with_llm,
)
from agent_core.task_spec import TaskSpec


def task_to_spec(raw_task: str) -> TaskSpec:
    if not isinstance(raw_task, str):
        raise ValueError("task must be a string")

    raw_task = raw_task.strip()
    if not raw_task:
        raise ValueError("empty task")

    goal = raw_task
    success_criteria = _derive_success_criteria(goal)

    return TaskSpec(
        raw_task=raw_task,
        goal=goal,
        success_criteria=success_criteria,
    )


def _derive_success_criteria(goal: str) -> List[str]:
    goal_lower = goal.lower()
    criteria: List[str] = []

    if "test" in goal_lower:
        criteria.append("tests pass")

    if "run" in goal_lower or "verify" in goal_lower:
        criteria.append("command executes successfully")

    if not criteria:
        criteria.append("execution completes without error")

    return criteria


def generate_plan(task_spec: TaskSpec) -> Dict[str, Any]:
    if not isinstance(task_spec, TaskSpec):
        raise ValueError("task_spec must be TaskSpec")

    return {
        "plan_id": "planner-v1",
        "goal": task_spec.goal,
        "success_criteria": task_spec.success_criteria,
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


def planner_llm_enabled() -> bool:
    value = os.environ.get("AGENT_LLM_PLANNER_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def generate_plan_fail_closed(
    task_spec: TaskSpec,
    llm_enabled: Optional[bool] = None,
    llm_client: Optional[LLMPlannerClient] = None,
) -> Dict[str, Any]:
    """
    Fail-closed behavior:
    - if LLM disabled -> deterministic local plan
    - if LLM enabled but missing client -> create default client
    - if LLM returns malformed output -> deny
    - only validated caller-owned plan execution path may continue
    """
    if llm_enabled is None:
        llm_enabled = planner_llm_enabled()

    if not llm_enabled:
        return generate_plan(task_spec)

    config = LLMPlannerConfig(enabled=True)

    client = llm_client or LLMPlannerClient(config)
    return generate_plan_with_llm(task_spec, client, config)
