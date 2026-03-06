from tools.gateway import ToolGateway
from sandbox.mounts import WORKSPACE_ROOT
from agent_core.patches import new_patch, PatchProposal
from audit.log import log_event
from agent_core.pending_store import load_pending, save_pending
from policy.capabilities import revoke_token, revoke_all_tokens
import ast
import json

from agent_core.plan_schema import Plan, ToolStep
from agent_core.plan_executor import submit_plan, approve_plan, execute_plan


class AgentLoop:
    def __init__(self, gateway):
        self.gateway = gateway
        self.pending: dict[str, PatchProposal] = {}
        self.pending = load_pending()

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

        if task.lower().startswith("find and summarize:"):
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

        if task.lower().startswith("search:"):
            query = task.split(":", 1)[1].strip()
            paths = self.gateway.search_files(query)
            return "\n".join(str(p) for p in paths[:20]) if paths else "No matches."

        if task.lower().startswith("propose patch:"):
            parts = task.split(":", 2)

            if len(parts) < 3:
                return "Usage: propose patch: <relative_path>: <new content>"

            rel_path = parts[1].strip()
            new_content = parts[2]

            full_path = (WORKSPACE_ROOT / rel_path).resolve()

            if not self.gateway.policy.is_allowed("FS_WRITE_PATCH", full_path):
                log_event("DENY_PROPOSE", {"path": rel_path, "reason": "policy"})
                return f"Denied: not allowed to write {rel_path}"

            original = self.gateway.fs.read(full_path)
            diff = self.gateway.fs.preview_diff(original, new_content)

            proposal = new_patch(rel_path, new_content)
            self.pending[proposal.patch_id] = proposal
            save_pending(self.pending)

            log_event("PROPOSE_PATCH", {"patch_id": proposal.patch_id, "path": rel_path})
            return f"PATCH_ID={proposal.patch_id}\n\n{diff}"

        if task.lower().startswith("approve patch:"):
            patch_id = task.split(":", 1)[1].strip()

            proposal = self.pending.get(patch_id)
            if not proposal:
                return f"Unknown PATCH_ID: {patch_id}"

            full_path = (WORKSPACE_ROOT / proposal.rel_path).resolve()

            try:
                diff = self.gateway.write_file(full_path, proposal.new_content)
                log_event("APPROVE_PATCH", {"patch_id": patch_id, "path": proposal.rel_path})
                del self.pending[patch_id]
                save_pending(self.pending)
                return f"Patch applied.\n\n{diff}"
            except Exception as e:
                log_event("DENY_APPROVE", {"patch_id": patch_id, "error": str(e)})
                return str(e)

        if task.lower().strip() == "revoke writes":
            revoke_all_tokens()
            log_event("REVOKE_TOKENS", {"mode": "all"})
            return "All capability tokens revoked (cleared)."

        if task.lower().startswith("revoke token:"):
            token_id = task.split(":", 1)[1].strip()
            revoke_token(token_id)
            log_event("REVOKE_TOKENS", {"mode": "single", "token_id": token_id})
            return f"Token revoked: {token_id}"

        if task.lower().startswith("plan.submit:"):
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

        if task.lower().startswith("plan.approve:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = approve_plan(plan_hash)
                return f"PLAN_APPROVED {result['plan_hash']}"
            except Exception as e:
                return str(e)

        if task.lower().startswith("plan.execute:"):
            plan_hash = task.split(":", 1)[1].strip()

            try:
                result = execute_plan(self.gateway, plan_hash)
                return str(result)
            except Exception as e:
                return str(e)

        if task.lower().startswith("update file:"):
            return "DENIED: use PLAN"

        if task.lower().startswith("cmd.run:"):
            return "DENIED: use PLAN"

        if task.lower().startswith("cmd.run"):
            return "DENIED: use PLAN"

        return f"[STUB] Agent received task: {task}"
