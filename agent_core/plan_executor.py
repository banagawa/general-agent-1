from dataclasses import replace

from audit.log import log_event
from policy.capabilities import issue_token

from .execute_step import execute_step
from .plan_hash import compute_plan_hash
from .plan_store import (
    load_approved_plan,
    mark_plan_approved,
    plan_is_approved,
    store_pending_plan,
)
from .plan_validator import validate_plan


TOKEN_ACTION_BY_TOOL = {
    "TEST_RUN": "CMD_RUN",
    "GIT_RUN": "GIT_RUN",
    "PATCH_APPLY": "FS_WRITE_PATCH",
}


def submit_plan(plan):
    validate_plan(plan)
    plan_hash = compute_plan_hash(plan)
    store_pending_plan(plan_hash, plan)

    log_event(
        "PLAN_CREATED",
        {
            "plan_hash": plan_hash,
            "steps": len(plan.steps),
            "status": "PENDING_APPROVAL",
        },
    )

    return {
        "plan_hash": plan_hash,
        "steps": len(plan.steps),
        "status": "PENDING_APPROVAL",
    }


def approve_plan(plan_hash: str):
    mark_plan_approved(plan_hash)

    log_event(
        "PLAN_APPROVED",
        {
            "plan_hash": plan_hash,
        },
    )

    return {
        "plan_hash": plan_hash,
        "status": "APPROVED",
    }


def _issue_step_token(step):
    action = TOKEN_ACTION_BY_TOOL.get(step.tool)
    if not action:
        raise ValueError(f"no token action mapping for tool: {step.tool}")

    scope = {}
    if step.tool == "PATCH_APPLY":
        scope = {"path": step.args["path"]}

    token = issue_token(
        actions=[action],
        scope=scope,
        constraints={
            "plan_step_id": step.step_id,
            "plan_tool": step.tool,
        },
        ttl_seconds=300,
    )
    return token.id


def _step_with_token(step, cap_token_id: str):
    args = dict(step.args)
    args["cap_token_id"] = cap_token_id
    return replace(step, args=args)


def execute_plan(gateway, plan_hash: str):
    if not plan_is_approved(plan_hash):
        log_event(
            "PLAN_EXECUTION_DENIED",
            {
                "plan_hash": plan_hash,
                "reason": "plan not approved",
            },
        )
        raise RuntimeError("plan not approved")

    plan = load_approved_plan(plan_hash)

    log_event(
        "PLAN_EXECUTION_STARTED",
        {
            "plan_hash": plan_hash,
            "steps": len(plan.steps),
        },
    )

    results = []

    try:
        for step in plan.steps:
            cap_token_id = _issue_step_token(step)
            step_with_token = _step_with_token(step, cap_token_id)

            result = execute_step(gateway, step_with_token)
            results.append(
                {
                    "step_id": step.step_id,
                    "tool": step.tool,
                    "result": result,
                }
            )

        payload = {
            "plan_hash": plan_hash,
            "results": results,
        }

        log_event(
            "PLAN_EXECUTION_FINISHED",
            {
                "plan_hash": plan_hash,
                "steps": len(plan.steps),
            },
        )
        return payload

    except Exception as e:
        log_event(
            "PLAN_EXECUTION_FAILED",
            {
                "plan_hash": plan_hash,
                "error": str(e),
            },
        )
        raise
