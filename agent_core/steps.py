from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Step:
    tool: str
    args: Dict[str, Any]
    cap_token_id: Optional[str]
