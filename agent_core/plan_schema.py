from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ToolStep:
    step_id: int
    tool: str
    capability: str
    args: Dict[str, Any]

@dataclass
class Plan:
    plan_id: str
    steps: List[ToolStep]
