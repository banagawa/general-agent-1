from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from agent_core.task_spec import TaskSpec


class PlannerDenied(Exception):
    pass


@dataclass(frozen=True)
class LLMPlannerConfig:
    enabled: bool = False
    model_name: str = "stub"
    timeout_seconds: int = 20
    max_output_chars: int = 12000


class LLMPlannerClient:
    """
    Pure adapter boundary.

    Contract:
    - input: TaskSpec
    - output: JSON string representing a PLAN object
    - no tool calls
    - no file writes
    - no side effects
    """

    def __init__(self, config: LLMPlannerConfig):
        self._config = config

    def generate_plan_json(self, task_spec: TaskSpec) -> str:
        raise PlannerDenied("LLM planner not configured")


def build_llm_prompt(task_spec: TaskSpec) -> str:
    criteria = "\n".join(f"- {item}" for item in task_spec.success_criteria)

    return (
        "Return JSON only.\n"
        "Generate a deterministic plan object.\n"
        "Do not include markdown.\n"
        "Do not include commentary.\n"
        "Do not include prose.\n"
        "Do not execute anything.\n"
        "Do not assume approval.\n"
        "Task goal:\n"
        f"{task_spec.goal}\n\n"
        "Success criteria:\n"
        f"{criteria}\n"
    )


def parse_llm_plan_json(raw: str, max_output_chars: int) -> Dict[str, Any]:
    if not isinstance(raw, str):
        raise PlannerDenied("planner output must be a string")

    raw = raw.strip()
    if not raw:
        raise PlannerDenied("planner output empty")

    if len(raw) > max_output_chars:
        raise PlannerDenied("planner output too large")

    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise PlannerDenied(f"planner output invalid json: {e.msg}") from e

    if not isinstance(obj, dict):
        raise PlannerDenied("planner output must be a json object")

    return obj


def generate_plan_with_llm(
    task_spec: TaskSpec,
    client: LLMPlannerClient,
    config: LLMPlannerConfig,
) -> Dict[str, Any]:
    if not isinstance(task_spec, TaskSpec):
        raise PlannerDenied("task_spec must be TaskSpec")

    if not config.enabled:
        raise PlannerDenied("LLM planner disabled")

    raw = client.generate_plan_json(task_spec)
    return parse_llm_plan_json(raw, config.max_output_chars)
