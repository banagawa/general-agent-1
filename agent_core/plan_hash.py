import hashlib
import json
from .plan_schema import Plan

def compute_plan_hash(plan: Plan):

    serialized = json.dumps(
        plan,
        default=lambda o: o.__dict__,
        sort_keys=True
    )

    return hashlib.sha256(serialized.encode()).hexdigest()
