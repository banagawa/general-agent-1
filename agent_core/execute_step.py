from __future__ import annotations

from sandbox.mounts import get_workspace_root

from .capability_guard import check_capability

from agent_core.security_invariants import assert_security_invariants

def execute_step(gateway, step):
    assert_security_invariants(direct_tool_bypass=False)
    check_capability(step)

    if step.tool == "GIT_RUN":
        return gateway.git_run(
            argv=step.args["argv"],
            timeout_seconds=step.args.get("timeout_seconds", 10),
            cap_token_id=step.args.get("cap_token_id"),
        )

    if step.tool == "PATCH_APPLY":
        workspace_root = get_workspace_root()
        path = (workspace_root / step.args["path"]).resolve()
        return gateway.patch_apply(
            path=path,
            new_content=step.args["new_content"],
            cap_token_id=step.args.get("cap_token_id"),
        )

    if step.tool == "TEST_RUN":
        return gateway.test_run(
            argv=step.args["argv"],
            timeout_seconds=step.args.get("timeout_seconds", 30),
            cap_token_id=step.args.get("cap_token_id"),
        )

    raise ValueError(f"unknown tool: {step.tool}")
