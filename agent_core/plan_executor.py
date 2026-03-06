from .execute_step import execute_step
from .plan_hash import compute_plan_hash
from .plan_store import (
    load_approved_plan,
    load_pending_plan,
    mark_plan_approved,
    plan_is_approved,
    store_pending_plan,
)
from .plan_validator import validate_plan


def submit_plan(plan):
    validate_plan(plan)

    plan_hash = compute_plan_hash(plan)
    store_pending_plan(plan_hash, plan)

    print(f"AUDIT PLAN_CREATED hash={plan_hash}")

    return {
        "plan_hash": plan_hash,
        "steps": len(plan.steps),
        "status": "PENDING_APPROVAL",
    }


def approve_plan(plan_hash: str):
    mark_plan_approved(plan_hash)

    print(f"AUDIT PLAN_APPROVED hash={plan_hash}")

    return {
        "plan_hash": plan_hash,
        "status": "APPROVED",
    }


def execute_plan(gateway, plan_hash: str):
    if not plan_is_approved(plan_hash):
        print(f"AUDIT PLAN_EXECUTION_DENIED hash={plan_hash} reason=not_approved")
        raise RuntimeError("plan not approved")

    plan = load_approved_plan(plan_hash)

    print(f"AUDIT PLAN_EXECUTION_STARTED hash={plan_hash}")

    results = []

    for step in plan.steps:
        result = execute_step(gateway, step)
        results.append(
            {
                "step_id": step.step_id,
                "tool": step.tool,
                "result": result,
            }
        )

    print(f"AUDIT PLAN_EXECUTION_FINISHED hash={plan_hash}")

    return {
        "plan_hash": plan_hash,
        "results": results,
    }


def get_pending_plan(plan_hash: str):
    return load_pending_plan(plan_hash)
