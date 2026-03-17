from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict

from agent_core.task_spec import TaskSpec


class PlannerDenied(Exception):
    pass


@dataclass(frozen=True)
class LLMPlannerConfig:
    enabled: bool = False
    model_name: str = "gpt-5.4"
    timeout_seconds: int = 20
    max_output_chars: int = 12000
    api_key_env: str = "OPENAI_API_KEY"


class LLMPlannerClient:
    """
    Pure adapter boundary.

    Contract:
    - input: TaskSpec
    - output: JSON string representing a PLAN object
    - no file writes
    - no tool calls
    - no side effects beyond one API request
    """

    def __init__(self, config: LLMPlannerConfig):
        self._config = config

    def generate_plan_json(self, task_spec: TaskSpec) -> str:
        if not isinstance(task_spec, TaskSpec):
            raise PlannerDenied("task_spec must be TaskSpec")

        api_key = os.environ.get(self._config.api_key_env)
        if not api_key:
            raise PlannerDenied("missing OPENAI_API_KEY")

        prompt = build_llm_prompt(task_spec)

        body = {
            "model": self._config.model_name,
            "input": prompt,
        }

        request = urllib.request.Request(
            url="https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._config.timeout_seconds,
            ) as response:
                raw_response = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise PlannerDenied(f"planner http error: {e.code} {detail}") from e
        except urllib.error.URLError as e:
            raise PlannerDenied(f"planner network error: {e.reason}") from e
        except Exception as e:
            raise PlannerDenied(f"planner request failed: {e}") from e

        return extract_output_text(raw_response)


def build_llm_prompt(task_spec: TaskSpec) -> str:
    criteria = "\n".join(f"- {item}" for item in task_spec.success_criteria)

    return (
        "Return JSON only.\n"
        "Generate exactly one plan object.\n"
        "Do not include markdown.\n"
        "Do not include prose.\n"
        "Do not include commentary.\n"
        "Do not execute anything.\n"
        "Do not assume approval.\n"
        "Plan shape must be a JSON object with keys:\n"
        'plan_id, goal, success_criteria, steps\n'
        "Each step must contain:\n"
        'step_id, tool, capability, args\n'
        "Task goal:\n"
        f"{task_spec.goal}\n\n"
        "Success criteria:\n"
        f"{criteria}\n"
    )


def extract_output_text(raw_response: str) -> str:
    try:
        obj = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise PlannerDenied(f"planner response invalid json: {e.msg}") from e

    if not isinstance(obj, dict):
        raise PlannerDenied("planner response must be a json object")

    output = obj.get("output")
    if not isinstance(output, list):
        raise PlannerDenied("planner response missing output")

    text_parts = []

    for item in output:
        if not isinstance(item, dict):
            continue

        content = item.get("content")
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict):
                continue

            if block.get("type") == "output_text":
                text_value = block.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)

    combined = "".join(text_parts).strip()
    if not combined:
        raise PlannerDenied("planner response missing output_text")

    return combined


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
