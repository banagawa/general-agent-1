from __future__ import annotations

import os
from pathlib import Path

# Default to ./workspace if not set
WORKSPACE_ROOT = Path(
    os.environ.get("AGENT_WORKSPACE_ROOT", "./workspace")
).resolve()

def get_workspace_root() -> Path:
    root = os.getenv("AGENT_WORKSPACE_ROOT") or os.getenv("AGENT_WORKSPACE") or "workspace"
    return Path(root).resolve()
    
