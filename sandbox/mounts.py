import os
from pathlib import Path

# Default to ./workspace if not set
WORKSPACE_ROOT = Path(
    os.environ.get("AGENT_WORKSPACE_ROOT", "./workspace")
).resolve()

def get_workspace_root() -> Path:
    return WORKSPACE_ROOT
