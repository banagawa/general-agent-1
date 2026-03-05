from tools.gateway import ToolGateway
from sandbox.mounts import WORKSPACE_ROOT
from agent_core.patches import new_patch, PatchProposal
from audit.log import log_event
from agent_core.pending_store import load_pending, save_pending
from policy.capabilities import issue_token, revoke_token, revoke_all_tokens
import ast

from agent_core.steps import Step
from agent_core.execute_step import execute_step


class AgentLoop:
    def __init__(self, gateway):
        self.gateway = gateway
        self.pending: dict[str, PatchProposal] = {}
        self.pending = load_pending()

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

        if task.lower().startswith("update file:"):
            parts = task.split(":", 2)
            if len(parts) < 3:
                return "Usage: update file: <relative_path>: <new content>"

            rel_path = parts[1].strip()
            new_content = parts[2].strip()
            full_path = (WORKSPACE_ROOT / rel_path).resolve()

            tok = issue_token(
                actions=["FS_WRITE_PATCH"],
                scope={"path": str(full_path)},
                ttl_seconds=300,
            )

            step = Step(
                tool="FS_WRITE_PATCH",
                args={"path": full_path, "new_content": new_content},
                cap_token_id=tok.id,
            )

            try:
                diff = execute_step(self.gateway, step)
                return f"Patch applied:\n{diff}"
            except Exception as e:
                return str(e)

        if task.lower().startswith("propose patch:"):
            parts = task.split(":", 2)

            if len(parts) < 3:
                return "Usage: propose patch: <relative_path>: <new content>"

            rel_path = parts[1].strip()
            new_content = parts[2]

            full_path = (WORKSPACE_ROOT / rel_path).resolve()

            # policy check (write intent), but DO NOT write
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

            tok = issue_token(
                actions=["FS_WRITE_PATCH"],
                scope={"path": str(full_path)},
                ttl_seconds=300,
            )

            step = Step(
                tool="FS_WRITE_PATCH",
                args={"path": full_path, "new_content": proposal.new_content},
                cap_token_id=tok.id,
            )

            try:
                diff = execute_step(self.gateway, step)
                log_event(
                    "APPROVE_PATCH",
                    {"patch_id": patch_id, "path": proposal.rel_path, "token_id": tok.id},
                )
                del self.pending[patch_id]
                save_pending(self.pending)
                return f"Patch applied.\n\n{diff}"
            except Exception as e:
                log_event("DENY_APPROVE", {"patch_id": patch_id, "error": str(e), "token_id": tok.id})
                return str(e)

        # Replacement for global "revoke writes" (no global flag allowed in A5).
        if task.lower().strip() == "revoke writes":
            revoke_all_tokens()
            log_event("REVOKE_TOKENS", {"mode": "all"})
            return "All capability tokens revoked (cleared)."

        if task.lower().startswith("revoke token:"):
            token_id = task.split(":", 1)[1].strip()
            revoke_token(token_id)
            log_event("REVOKE_TOKENS", {"mode": "single", "token_id": token_id})
            return f"Token revoked: {token_id}"

        if task.lower().startswith("cmd.run:"):
            raw = task.split(":", 1)[1].strip()

            try:
                argv = ast.literal_eval(raw)
            except Exception:
                return "Usage: cmd.run: ['python','--version']"

            tok = issue_token(actions=["CMD_RUN"], scope={}, ttl_seconds=120)

            step = Step(
                tool="CMD_RUN",
                args={"argv": argv, "timeout_seconds": 30},
                cap_token_id=tok.id,
            )

            try:
                result = execute_step(self.gateway, step)
                return str(result)
            except Exception as e:
                return str(e)

        if task.lower().startswith("cmd.run"):
            # Expect: cmd.run ["python","--version"]
            try:
                start = task.index("[")
                end = task.rindex("]") + 1
                argv_literal = task[start:end]
                argv = ast.literal_eval(argv_literal)
            except Exception:
                return "Usage: cmd.run [\"python\",\"--version\"]"

            tok = issue_token(actions=["CMD_RUN"], scope={}, ttl_seconds=120)

            step = Step(
                tool="CMD_RUN",
                args={"argv": argv, "timeout_seconds": 30},
                cap_token_id=tok.id,
            )

            try:
                result = execute_step(self.gateway, step)
                return str(result)
            except Exception as e:
                return str(e)

        return f"[STUB] Agent received task: {task}"
