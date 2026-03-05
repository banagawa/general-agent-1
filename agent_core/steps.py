from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence

@dataclass(frozen=True)
class Step:
    tool: str                      # "CMD_RUN" | "FS_WRITE_PATCH"
    args: Dict[str, Any]           # parsed args only
    cap_token_id: Optional[str]    # token id to forward to ToolGateway
