    from .plan_validator import validate_plan
from .plan_hash import compute_plan_hash

def prepare_plan(plan):

    validate_plan(plan)

    plan_hash = compute_plan_hash(plan)

    return {
        "plan": plan,
        "plan_hash": plan_hash,
        "approved": False
    }

def execute_plan(plan_record):

    if not plan_record["approved"]:
        raise RuntimeError("plan not approved")

    for step in plan_record["plan"].steps:
        execute_step(step)
