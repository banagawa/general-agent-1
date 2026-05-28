from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Strategy:
    strategy_id: str
    outcome: str
    patch_hints: Tuple[str, ...]
    enabled: bool = False


@dataclass(frozen=True)
class StrategyProposal:
    proposal_id: str
    outcome: str
    patch_hints: Tuple[str, ...]

    def to_strategy(self) -> Strategy:
        return Strategy(
            strategy_id=self.proposal_id,
            outcome=self.outcome,
            patch_hints=self.patch_hints,
            enabled=False,
        )
