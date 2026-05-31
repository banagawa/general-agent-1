from __future__ import annotations

import os
from pathlib import Path


def _module_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _looks_like_app_root(path: Path) -> bool:
    return (path / "main.py").is_file() and (path / "sandbox").is_dir()


def get_app_root() -> Path:
    env_root = os.environ.get("AGENT_APP_ROOT")
    if env_root:
        return Path(env_root).resolve()

    module_root = _module_repo_root().resolve()

    # When tests are run from a git worktree under:
    #   <app_root>/workspace/<worktree>
    # the imported module root is the worktree, not the outer app root.
    # Infer the outer app root so the live-app guard does not falsely trip.
    if module_root.parent.name == "workspace":
        candidate = module_root.parent.parent.resolve()
        if _looks_like_app_root(candidate):
            return candidate

    return module_root


def get_workspace_root() -> Path:
    root = Path(
        os.environ.get(
            "AGENT_WORKSPACE_ROOT",
            str(get_app_root() / "workspace"),
        )
    ).resolve()

    _assert_not_live_app_repo(root)
    return root


def get_runtime_state_root() -> Path:
    """
    Return the workspace-scoped runtime-state root.

    This is a future landing zone for runtime bookkeeping such as audit logs,
    capability token state, and pending patch state. Existing stores are not
    migrated by this helper alone.
    """
    return get_workspace_root() / ".runtime_state"


def _assert_not_live_app_repo(root: Path) -> None:
    app_root = get_app_root()

    if root.resolve() == app_root.resolve():
        raise RuntimeError(
            "refusing to use live app repo as workspace; "
            "use a git worktree under workspace/"
        )
