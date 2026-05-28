from __future__ import annotations

import hashlib

from agent_core.strategy import StrategyProposal


FAILURE_OUTCOMES = {"TEST_FAILURE", "PATCH_REJECTED", "FAILED"}


def propose_strategy_from_execution(payload: dict):
    outcome = payload.get("result_status") or payload.get("execution_status")

    if outcome == "SUCCESS":
        return None
    if outcome not in FAILURE_OUTCOMES:
        return None

    digest = hashlib.sha256(outcome.encode("utf-8")).hexdigest()[:12]
    return StrategyProposal(proposal_id=f"proposal-{digest}", outcome=outcome, patch_hints=("retry",))
