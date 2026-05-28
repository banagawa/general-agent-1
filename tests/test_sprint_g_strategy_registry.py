from __future__ import annotations

from pathlib import Path

from agent_core.strategy_registry import StrategyRegistry


def test_registry_appends_and_loads_records(tmp_path: Path) -> None:
    path = tmp_path / "registry.jsonl"
    registry = StrategyRegistry(path)

    registry.append({"strategy_id": "s1"})
    registry.append({"strategy_id": "s2"})

    records = list(registry.load())

    assert len(records) == 2
    assert records[0]["strategy_id"] == "s1"
    assert records[1]["strategy_id"] == "s2"
