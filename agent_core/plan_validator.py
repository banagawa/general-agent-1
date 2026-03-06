from .plan_schema import Plan, ToolStep


ALLOWED_TOOLS = {
    "GIT_RUN",
    "PATCH_APPLY",
    "TEST_RUN",
}


def validate_plan(plan: Plan) -> None:
    if not isinstance(plan, Plan):
        raise ValueError("plan must be Plan")

    if not isinstance(plan.plan_id, str) or not plan.plan_id.strip():
        raise ValueError("plan_id must be non-empty string")

    if not isinstance(plan.steps, tuple):
        raise ValueError("steps must be tuple")

    if len(plan.steps) == 0:
        raise ValueError("steps must be non-empty")

    expected = 1
    seen_ids = set()

    for step in plan.steps:
        if not isinstance(step, ToolStep):
            raise ValueError("all steps must be ToolStep")

        if step.step_id in seen_ids:
            raise ValueError("duplicate step id")

        seen_ids.add(step.step_id)

        if step.step_id != expected:
            raise ValueError("step ids must be sequential")

        if not isinstance(step.tool, str) or not step.tool.strip():
            raise ValueError("tool must be non-empty string")

        if step.tool not in ALLOWED_TOOLS:
            raise ValueError(f"tool not allowed: {step.tool}")

        if not isinstance(step.args, dict):
            raise ValueError("args must be dict")

        if not isinstance(step.capability, str) or not step.capability.strip():
            raise ValueError("missing capability")

        expected += 1
