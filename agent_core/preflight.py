from dataclasses import dataclass
from typing import Any, Dict

from agent_core.deny import deny_hash_mismatch
from agent_core.validators import (
    validate_plan_hash,
    validate_approved_meta,
    validate_execution_request
    )

@dataclass(frozen=True)
class PreflightResult:
    plan_hash: str
    plan: Dict[str, Any]
    meta: Dict[str, Any]


def preflight_execute(
    plan_hash: str,
    load_approved_plan,
    load_approval_meta,
    recompute_plan_hash,
    check_workspace_drift,
):
    # 1. validate input hash
    plan_hash = validate_execution_request(plan_hash)

    # 2. load approved plan
    plan = load_approved_plan(plan_hash)
    if plan is None:
        raise RuntimeError("approved plan not found")

    # 3. load approval metadata
    meta = load_approval_meta(plan_hash)
    if meta is None:
        raise RuntimeError("approval metadata missing")

    # 4. validate metadata shape
    validate_approved_meta(meta)

    # 5. recompute canonical hash and compare
    computed_hash = recompute_plan_hash(plan)
    if computed_hash != plan_hash:
        deny_hash_mismatch(plan_hash)

    # 6. workspace drift check
    check_workspace_drift(plan_hash)

    # 7. replay protection check (non-atomic pre-check)
    
    return PreflightResult(
        plan_hash=plan_hash,
        plan=plan,
        meta=meta,
    )
