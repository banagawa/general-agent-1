from __future__ import annotations

import json

from audit.log import log_event
from policy.capabilities import revoke_all_tokens, revoke_token
from sandbox.mounts import WORKSPACE_ROOT

from agent_core.plan_executor import approve_plan, execute_plan, submit_plan
from agent_core.plan_schema import Plan, ToolStep


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
                relative = p.relative_to(WORKSPACE_ROOT)
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
            except Exception as e:
                return str(e)

        if cmd.startswith("plan.approve:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = approve_plan(plan_hash)
                return f"PLAN_APPROVED {result['plan_hash']}"
            except Exception as e:
                return str(e)

        if cmd.startswith("plan.execute:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = execute_plan(self.gateway, plan_hash)
                return json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
            except Exception as e:
                return str(e)

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
