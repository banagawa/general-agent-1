from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class ToolStep:
    step_id: int
    tool: str
    capability: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Plan:
    plan_id: str
    steps: Tuple[ToolStep, ...] = field(default_factory=tuple)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id must be non-empty string")

        normalized_steps = tuple(self.steps)

        for step in normalized_steps:
            if not isinstance(step, ToolStep):
                raise ValueError("all steps must be ToolStep")
            if not isinstance(self.metadata, dict):
                raise ValueError("metadata must be dict")

        object.__setattr__(self, "steps", normalized_steps)
