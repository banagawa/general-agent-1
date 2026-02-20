from tools.gateway import ToolGateway
from sandbox.mounts import WORKSPACE_ROOT, get_workspace_root
from agent_core.patches import new_patch, PatchProposal
from policy.revocations import writes_revoked
from audit.log import log_event
from agent_core.pending_store import load_pending, save_pending

class AgentLoop:
    def __init__(self,gateway):
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
                # p is a Path from fs_tools.search
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

            try:
                diff = self.gateway.write_file(full_path, new_content)
                return f"Patch applied:\n{diff}"
            except Exception as e:
                return str(e)

        if task.lower().startswith("propose patch:"):
            parts = task.split(":", 2)

            if len(parts) < 3:
                return "Usage: propose patch: <relative_path>: <new content>"

            rel_path = parts[1].strip()
            new_content = parts[2]

            # normalize to workspace path
            full_path = (WORKSPACE_ROOT / rel_path).resolve()

            # policy check (write intent), but DO NOT write
            if writes_revoked:
                log_event("DENY_PROPOSE", f"{rel_path} reason=revoked")
                return "Denied: writes are revoked"

            if not self.gateway.policy.is_allowed("FS_WRITE_PATCH", full_path):
                log_event("DENY_PROPOSE", f"{rel_path} reason=policy")
                return f"Denied: not allowed to write {rel_path}"

            # Generate diff preview without applying:
            original = self.gateway.fs.read(full_path)
            diff = self.gateway.fs.preview_diff(original, new_content)

            proposal = new_patch(rel_path, new_content)
            self.pending[proposal.patch_id] = proposal
            save_pending(self.pending)

            log_event("PROPOSE_PATCH", f"id={proposal.patch_id} path={rel_path}")
            return f"PATCH_ID={proposal.patch_id}\n\n{diff}"


        if task.lower().startswith("approve patch:"):
            if writes_revoked():
                log_event("DENY_APPROVE", f"id={patch_id} reason=revoked")
                return "Denied: writes are revoked"
            patch_id = task.split(":", 1)[1].strip()

            proposal = self.pending.get(patch_id)
            if not proposal:
                return f"Unknown PATCH_ID: {patch_id}"

            full_path = (WORKSPACE_ROOT / proposal.rel_path).resolve()

            try:
                diff = self.gateway.write_file(full_path, proposal.new_content)
                log_event("APPROVE_PATCH", f"id={patch_id} path={proposal.rel_path}")
                del self.pending[patch_id]
                save_pending(self.pending)
                return f"Patch applied.\n\n{diff}"
            except Exception as e:
                log_event("DENY_APPROVE", f"id={patch_id} err={e}")
                return str(e)

        if task.lower().strip() == "revoke writes":
            writes_revoked()
            log_event("REVOKE_WRITES", "writes_revoked=true")
            return "Writes revoked."


        return f"[STUB] Agent received task: {task}"


