from __future__ import annotations

import json

from audit.log import log_event
from policy.capabilities import revoke_all_tokens, revoke_token
from sandbox.mounts import get_workspace_root

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

                plan = self._parse_plan_json(json.dumps(plan_dict))
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
