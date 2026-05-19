from __future__ import annotations

import json
import os

from audit.log import log_event
from policy.capabilities import revoke_all_tokens, revoke_token
from sandbox.mounts import get_workspace_root

from agent_core.autonomy import AutonomyBudget, AutonomyMode, run_autonomy_cycle
from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
from agent_core.plan_schema import Plan, ToolStep
from agent_core.planner import generate_plan_fail_closed, task_to_spec, planner_llm_enabled
from agent_core.plan_validator import validate_plan

class AgentLoop:
    def __init__(self, gateway):
        self.gateway = gateway

    def _parse_plan_json(self, raw: str) -> Plan:
        data = json.loads(raw)

        steps = tuple(
            ToolStep(
                step_id=step["step_id"],
                tool=step["tool"],
                capability=step["capability"],
                args=step["args"],
            )
            for step in data["steps"]
        )

        return Plan(
            plan_id=data["plan_id"],
            steps=steps,
            metadata=data.get("metadata", {}),
        )

    def _parse_plan_dict(self, data: dict) -> Plan:
        steps = tuple(
            ToolStep(
                step_id=step["step_id"],
                tool=step["tool"],
                capability=step["capability"],
                args=step["args"],
            )
            for step in data["steps"]
        )

        return Plan(
            plan_id=data["plan_id"],
            steps=steps,
            metadata=data.get("metadata", {}),
        )

    def _generate_task_plan_dict(self, task_spec):
        planner_source = "llm" if planner_llm_enabled() else "deterministic"

        plan_dict = generate_plan_fail_closed(
            task_spec=task_spec,
            llm_enabled=None,
            llm_client=None,
        )

        plan_dict["metadata"] = {
            "planner": {
                "source": planner_source,
            },
            "intent": {
                "goal": task_spec.goal,
                "success_criteria": task_spec.success_criteria,
            },
        }

        return plan_dict

    def _bounded_autonomous_enabled(self) -> bool:
        value = os.environ.get("AGENT_BOUNDED_AUTONOMY_ENABLED", "")
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _parse_autonomy_payload(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid payload JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError("expected object")

        raw_task = data.get("task")
        if not isinstance(raw_task, str) or not raw_task.strip():
            raise ValueError("task is required")

        raw_mode = data.get("mode")
        if not isinstance(raw_mode, str) or not raw_mode.strip():
            raise ValueError("mode is required")

        try:
            mode = AutonomyMode(raw_mode.strip().upper())
        except ValueError as e:
            raise ValueError("unsupported mode") from e

        raw_budget = data.get("budget", {})
        if raw_budget is None:
            raw_budget = {}
        if not isinstance(raw_budget, dict):
            raise ValueError("budget must be object")

        def require_positive_int(name: str, default: int) -> int:
            value = raw_budget.get(name, default)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be positive int")
            return value

        def require_nonnegative_int(name: str, default: int) -> int:
            value = raw_budget.get(name, default)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be nonnegative int")
            return value

        budget = AutonomyBudget(
            max_cycles=require_positive_int("max_cycles", 1),
            max_runtime_seconds=require_positive_int("max_runtime_seconds", 120),
            max_mutation_steps=require_positive_int("max_mutation_steps", 1),
            cycles_used=require_nonnegative_int("cycles_used", 0),
            runtime_seconds_used=require_nonnegative_int("runtime_seconds_used", 0),
            mutation_steps_used=require_nonnegative_int("mutation_steps_used", 0),
        )

        return raw_task.strip(), mode, budget

    def run(self, task: str) -> str:
        task = task.strip()
        cmd = task.lower()

        if cmd.startswith("find and summarize:"):
            query = task.split(":", 1)[1].strip()
            paths = self.gateway.search_files(query)

            if not paths:
                return f"No matches found for: {query}"

            out = [f"Top matches for '{query}':"]
            for p in paths[:3]:
                content = self.gateway.read_abs_path(p)
                snippet = content[:400].replace("\n", " ")
                relative = p.relative_to(get_workspace_root())
                out.append(f"- {relative}: {snippet}")

            return "\n".join(out)

        if cmd.startswith("search:"):
            query = task.split(":", 1)[1].strip()
            paths = self.gateway.search_files(query)
            return "\n".join(str(p) for p in paths[:20]) if paths else "No matches."

        if cmd == "revoke writes":
            revoke_all_tokens()
            log_event("REVOKE_TOKENS", {"mode": "all"})
            return "All capability tokens revoked (cleared)."

        if cmd.startswith("revoke token:"):
            token_id = task.split(":", 1)[1].strip()
            revoke_token(token_id)
            log_event("REVOKE_TOKENS", {"mode": "single", "token_id": token_id})
            return f"Token revoked: {token_id}"

        if cmd.startswith("task.plan:"):
            raw_task = task.split(":", 1)[1].strip()
            log_event("PLANNER_REQUESTED", {"task": raw_task})

            try:
                task_spec = task_to_spec(raw_task)

                planner_source = "llm" if planner_llm_enabled() else "deterministic"

                plan_dict = self._generate_task_plan_dict(task_spec)

                plan = self._parse_plan_dict(plan_dict)
                validate_plan(plan)

                result = submit_plan(plan)

                log_event(
                    "PLANNER_PLAN_CREATED",
                    {
                        "goal": task_spec.goal,
                        "planner_source": planner_source,
                        "plan_hash": result["plan_hash"],
                    },
                )

                return (
                    f"PLAN_HASH={result['plan_hash']}\n"
                    f"STEPS={result['steps']}\n"
                    f"STATUS={result['status']}"
                )

            except ValueError as e:
                log_event(
                    "PLANNER_DENIED",
                    {
                        "task": raw_task,
                        "reason": f"invalid task/plan: {e}",
                    },
                )
                return f"DENIED: invalid task/plan: {e}"
            except Exception as e:
                log_event(
                    "PLANNER_DENIED",
                    {
                        "task": raw_task,
                        "reason": str(e),
                    },
                )
                return f"DENIED: {e}"

        if cmd.startswith("task.autonomy:"):
            raw_payload = task.split(":", 1)[1].strip()

            try:
                raw_task, mode, budget = self._parse_autonomy_payload(raw_payload)
                task_spec = task_to_spec(raw_task)

                result = run_autonomy_cycle(
                    task_spec=task_spec,
                    mode=mode,
                    budget=budget,
                    generate_plan=self._generate_task_plan_dict,
                    submit_plan=submit_plan,
                    parse_plan=self._parse_plan_dict,
                    bounded_autonomous_enabled=self._bounded_autonomous_enabled(),
                )

                out = [
                    f"MODE={result.mode}",
                    f"STATUS={result.status}",
                    f"STOP_REASON={result.stop_reason}",
                    f"CYCLES_USED={result.cycle_index}",
                    f"BUDGET_REMAINING={json.dumps(result.budget_remaining, sort_keys=True)}",
                ]
                log_event(
                    "AUTONOMY_CYCLE_RECORDED",
                    {
                        "mode": result.mode,
                        "task_goal": result.task_goal,
                        "cycle_index": result.cycle_index,
                        "plan_hash": result.plan_hash,
                        "status": result.status,
                        "stop_reason": result.stop_reason,
                        "budget_remaining": result.budget_remaining,
                    },
                )

                if result.plan_hash:
                    out.insert(1, f"PLAN_HASH={result.plan_hash}")
                return "\n".join(out)

            except ValueError as e:
                log_event(
                    "AUTONOMY_DENIED",
                    {
                        "reason": f"invalid payload: {e}",
                    },
                )
                return f"DENIED: invalid payload: {e}"
            except Exception as e:
                log_event(
                    "AUTONOMY_DENIED",
                    {
                        "reason": str(e),
                    },
                )
                return f"DENIED: {e}"

        if cmd.startswith("plan.submit:"):
            raw = task.split(":", 1)[1].strip()

            try:
                plan = self._parse_plan_json(raw)
                result = submit_plan(plan)
                return (
                    f"PLAN_HASH={result['plan_hash']}\n"
                    f"STEPS={result['steps']}\n"
                    f"STATUS={result['status']}"
                )
            except ValueError as e:
                return f"DENIED: invalid plan: {e}"
            except Exception as e:
                return f"DENIED: {e}"

        if cmd.startswith("plan.approve:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = approve_plan(plan_hash)
                return f"PLAN_APPROVED {result['plan_hash']}"
            except ValueError as e:
                return f"DENIED: invalid approval: {e}"
            except Exception as e:
                return f"DENIED: {e}"

        if cmd.startswith("plan.execute:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = execute_plan(self.gateway, plan_hash)
                return json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
            except ValueError as e:
                return f"DENIED: invalid execution: {e}"
            except Exception as e:
                return f"DENIED: {e}"

        denied_prefixes = (
            "propose patch:",
            "approve patch:",
            "update file:",
            "cmd.run:",
            "cmd.run",
        )
        for prefix in denied_prefixes:
            if cmd.startswith(prefix):
                log_event("PLAN_REQUIRED", {"task_prefix": prefix})
                return "DENIED: use PLAN"

        return f"[STUB] Agent received task: {task}"
