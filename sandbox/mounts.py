from __future__ import annotations

import os
from pathlib import Path


def get_workspace_root() -> Path:
    raw = os.getenv("AGENT_WORKSPACE_ROOT") or os.getenv("AGENT_WORKSPACE") or "workspace"
    root = Path(raw).expanduser().resolve()

    _assert_not_live_app_repo(root)

    root.mkdir(parents=True, exist_ok=True)
    return root


def _assert_not_live_app_repo(root: Path) -> None:
    app_root = Path(__file__).resolve().parents[1]

    if root.resolve() == app_root.resolve():
        raise RuntimeError(
            "refusing to use live app repo as workspace; "
            "use a git worktree under workspace/"
        )
