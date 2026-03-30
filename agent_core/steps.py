from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Step:

    tool: str                      # "GIT_RUN" | "PATCH_APPLY" | "FILE_CREATE" | "TEST_RUN"
    args: Dict[str, Any]           # parsed args only
    cap_token_id: Optional[str]    # token id to forward to ToolGateway

