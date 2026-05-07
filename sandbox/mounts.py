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
    
def _assert_repo_write_allowed(root: Path) -> None:
    # detect repo root by presence of .git or pyproject or similar
    is_repo_root = (root / ".git").exists() or (root / "README.md").exists()

    if is_repo_root:
        if os.environ.get("AGENT_ALLOW_REPO_WRITE") != "1":
            raise RuntimeError(
                "refusing to operate on repo root without AGENT_ALLOW_REPO_WRITE=1"
            )
