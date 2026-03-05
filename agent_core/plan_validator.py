from .plan_schema import Plan, ToolStep

ALLOWED_TOOLS = {
    "GIT_RUN",
    "PATCH_APPLY",
    "TEST_RUN"
}

def validate_plan(plan: Plan):

    if not isinstance(plan.steps, list):
        raise ValueError("steps must be list")

    expected = 1

    for step in plan.steps:

        if step.step_id != expected:
            raise ValueError("step ids must be sequential")

        if step.tool not in ALLOWED_TOOLS:
            raise ValueError("tool not allowed")

        if not isinstance(step.args, dict):
            raise ValueError("args must be dict")

        if not step.capability:
            raise ValueError("missing capability")

        expected += 1
