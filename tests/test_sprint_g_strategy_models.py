from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from agent_core.strategy import Strategy, StrategyProposal


def test_strategy_is_frozen() -> None:
    strategy = Strategy(strategy_id="s1", outcome="TEST_FAILURE", patch_hints=("retry",))

    with pytest.raises(FrozenInstanceError):
        strategy.enabled = True


def test_strategy_proposal_converts_to_disabled_strategy() -> None:
    proposal = StrategyProposal(proposal_id="p1", outcome="TEST_FAILURE", patch_hints=("retry",))

    strategy = proposal.to_strategy()

    assert strategy.strategy_id == "p1"
    assert strategy.enabled is False


def test_models_expose_no_executable_fields() -> None:
    strategy = Strategy(strategy_id="s1", outcome="FAILED", patch_hints=())

    assert not hasattr(strategy, "tool")
    assert not hasattr(strategy, "argv")
    assert not hasattr(strategy, "command")
