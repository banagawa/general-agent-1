from .plan_schema import Plan, ToolStep

MAX_STEPS_PER_PLAN = 25

ALLOWED_TOOLS = {
    "GIT_RUN",
    "PATCH_APPLY",
    "TEST_RUN",
    "FILE_CREATE",
}

EXPECTED_CAPABILITY_BY_TOOL = {
    "GIT_RUN": "git.run",
    "PATCH_APPLY": "patch.apply",
    "TEST_RUN": "test.run",
    "FILE_CREATE": "file.create",
}


def _require_non_empty_string(value, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty string")


def _require_argv(args: dict, tool_name: str) -> None:
    argv = args.get("argv")
    if not isinstance(argv, list) or len(argv) == 0:
        raise ValueError(f"{tool_name} args.argv must be non-empty list")
    for item in argv:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{tool_name} args.argv entries must be non-empty strings")


def _require_timeout_if_present(args: dict, tool_name: str) -> None:
    timeout_seconds = args.get("timeout_seconds")
    if timeout_seconds is not None:
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError(f"{tool_name} timeout_seconds must be positive int")


def _validate_git_run(step: ToolStep) -> None:
    _require_argv(step.args, "GIT_RUN")
    _require_timeout_if_present(step.args, "GIT_RUN")


def _validate_patch_apply(step: ToolStep) -> None:
    path = step.args.get("path")
    new_content = step.args.get("new_content")

    _require_non_empty_string(path, "PATCH_APPLY args.path")

    if not isinstance(new_content, str):
        raise ValueError("PATCH_APPLY args.new_content must be string")

    if "argv" in step.args:
        raise ValueError("PATCH_APPLY must not include args.argv")


def _validate_test_run(step: ToolStep) -> None:
    _require_argv(step.args, "TEST_RUN")
    _require_timeout_if_present(step.args, "TEST_RUN")

def _validate_file_create(step: ToolStep) -> None:
    path = step.args.get("path")
    content = step.args.get("content")

    _require_non_empty_string(path, "FILE_CREATE args.path")

    if not isinstance(content, str):
        raise ValueError("FILE_CREATE args.content must be string")

    if "argv" in step.args:
        raise ValueError("FILE_CREATE must not include args.argv")

def validate_plan(plan: Plan) -> None:
    if not isinstance(plan, Plan):
        raise ValueError("plan must be Plan")

    _require_non_empty_string(plan.plan_id, "plan_id")

    if not isinstance(plan.steps, tuple):
        raise ValueError("steps must be tuple")

    if len(plan.steps) == 0:
        raise ValueError("steps must be non-empty")

    if len(plan.steps) > MAX_STEPS_PER_PLAN:
        raise ValueError(f"steps exceed max of {MAX_STEPS_PER_PLAN}")

    seen_ids = set()

    for index, step in enumerate(plan.steps, start=1):
        if not isinstance(step, ToolStep):
            raise ValueError("all steps must be ToolStep")

        if not isinstance(step.step_id, int):
            raise ValueError("step_id must be int")

        if step.step_id in seen_ids:
            raise ValueError("duplicate step id")

        if step.step_id != index:
            raise ValueError("step ids must be sequential starting at 1")

        seen_ids.add(step.step_id)

        _require_non_empty_string(step.tool, "tool")

        if step.tool not in ALLOWED_TOOLS:
            raise ValueError(f"tool not allowed: {step.tool}")

        if not isinstance(step.args, dict):
            raise ValueError("args must be dict")

        _require_non_empty_string(step.capability, "capability")

        expected_capability = EXPECTED_CAPABILITY_BY_TOOL[step.tool]
        if step.capability != expected_capability:
            raise ValueError(
                f"capability mismatch for {step.tool}: expected {expected_capability}"
            )

        if step.tool == "GIT_RUN":
            _validate_git_run(step)
        elif step.tool == "PATCH_APPLY":
            _validate_patch_apply(step)
        elif step.tool == "FILE_CREATE":
            _validate_file_create(step)
        elif step.tool == "TEST_RUN":
            _validate_test_run(step)
        else:
            raise ValueError(f"tool not allowed: {step.tool}")
