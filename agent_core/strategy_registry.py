from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from audit.log import log_event


class StrategyRegistry:
    def __init__(self, path: Path):
        self.path = path

    def append(self, record: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

        log_event("STRATEGY_REGISTRY_APPEND", record)

    def load(self) -> Iterable[dict]:
        if not self.path.exists():
            return []

        records = []
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records
