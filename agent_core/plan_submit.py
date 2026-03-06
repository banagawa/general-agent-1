import json

from agent.plans.plan_schema import validate_plan
from agent.plans.plan_hash import compute_plan_hash
from agent.plans.plan_store import store_pending_plan


def plan_submit(plan_json: str):

    try:
        plan = json.loads(plan_json)
    except Exception:
        raise ValueError("invalid json")

    validate_plan(plan)

    plan_hash = compute_plan_hash(plan)

    store_pending_plan(plan_hash, plan)

    steps = len(plan["steps"])

    print(f"AUDIT PLAN_CREATED hash={plan_hash}")

    return {
        "plan_hash": plan_hash,
        "steps": steps,
        "status": "PENDING_APPROVAL"
    }
