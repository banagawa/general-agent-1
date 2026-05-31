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
    Return the runtime-state root for the active workspace.

    Runtime state is stored outside the live app root and outside the target
    worktree. For a workspace at:

        <app_root>/workspace/<workspace_name>

    runtime state lives at:

        <app_root>/workspace/agent_runtime/<workspace_name>

    Existing stores are not migrated by this helper alone.
    """
    workspace_root = get_workspace_root()
    workspace_container = workspace_root.parent
    return workspace_container / "agent_runtime" / workspace_root.name


def _assert_not_live_app_repo(root: Path) -> None:
    app_root = get_app_root()

    if root.resolve() == app_root.resolve():
        raise RuntimeError(
            "refusing to use live app repo as workspace; "
            "use a git worktree under workspace/"
        )
