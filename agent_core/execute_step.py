from agent_core.steps import Step

def execute_step(gateway, step: Step):

    if step.tool == "FS_WRITE_PATCH":
        return gateway.write_file(
            step.args["path"],
            step.args["new_content"],
            cap_token_id=step.cap_token_id,
        )

    if step.tool == "CMD_RUN":
        return gateway.cmd_run(
            step.args["argv"],
            timeout_seconds=step.args.get("timeout_seconds", 30),
            cap_token_id=step.cap_token_id,
        )

    raise ValueError(f"unknown tool: {step.tool}")
