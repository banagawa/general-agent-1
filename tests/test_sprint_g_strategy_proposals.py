from __future__ import annotations

from agent_core.strategy_proposals import propose_strategy_from_execution


def test_success_returns_no_proposal() -> None:
    assert propose_strategy_from_execution({"result_status": "SUCCESS"}) is None


def test_failure_returns_deterministic_proposal() -> None:
    a = propose_strategy_from_execution({"result_status": "FAILED"})
    b = propose_strategy_from_execution({"result_status": "FAILED"})

    assert a is not None
    assert a.proposal_id == b.proposal_id
