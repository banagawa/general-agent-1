from __future__ import annotations

import os
from pathlib import Path


def get_app_root() -> Path:
    raw = os.getenv("AGENT_APP_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()

    return Path(__file__).resolve().parents[1]


def get_workspace_root() -> Path:
    app_root = get_app_root()

    raw = os.getenv("AGENT_WORKSPACE_ROOT") or os.getenv("AGENT_WORKSPACE")

    if raw:
        root = Path(raw).expanduser().resolve()
    else:
        root = (app_root / "workspace").resolve()

    _assert_not_live_app_repo(root)

    root.mkdir(parents=True, exist_ok=True)
    return root


def _assert_not_live_app_repo(root: Path) -> None:
    app_root = get_app_root()

    if root.resolve() == app_root.resolve():
        raise RuntimeError(
            "refusing to use live app repo as workspace; "
            "use a git worktree under workspace/"
        )
