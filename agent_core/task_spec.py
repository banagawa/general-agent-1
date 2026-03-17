from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class TaskSpec:
    raw_task: str
    goal: str
    success_criteria: List[str]
