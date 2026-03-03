from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Any

# Sprint C allowlist
ALLOWED_SUBCOMMANDS = {"init", "status", "diff", "add", "commit", "log"}

# Explicit denies (Sprint C)
DENY_SUBCOMMANDS = {
    "push", "pull", "fetch", "clone", "remote",
    "checkout", "switch", "branch", "merge", "rebase", "tag",
    "submodule",
}

# Hard-deny config/worktree overrides
DENY_FLAGS = {
    "-c", "--git-dir", "--work-tree", "-C", "--config-env",
}

# Minimal strict flags per subcommand (no passthrough)
ALLOWED_FLAGS = {
    "init": {"--quiet", "-q"},
    "status": {"--porcelain", "--short", "-s", "--branch", "-b"},
    "diff": {"--staged", "--cached", "--stat", "--name-only"},
    "log": {"--oneline", "--decorate", "--graph", "--no-decorate", "-n", "--max-count"},
    "add": {"-A", "--all", "-p", "--patch", "-N", "--intent-to-add"},
    "commit": {"-m", "--message", "--allow-empty", "--no-gpg-sign"},
}

@dataclass(frozen=True)
class GitDecision:
    allowed: bool
    reason: str

def _is_flag(tok: str) -> bool:
    return tok.startswith("-") and tok != "-"

def _resolve_under_ws(ws_root: Path, raw: str) -> bool:
    # raw may be "path", "./path", "dir/file"
    try:
        p = (ws_root / raw).resolve()
        p.relative_to(ws_root.resolve())
        return True
    except Exception:
        return False

def validate_git_run(argv: Sequence[str], ws_root: Path) -> GitDecision:
    """
    argv must be: ["git", <subcommand>, ...]
    Strict parsing:
      - only allow ALLOWED_SUBCOMMANDS
      - deny remote/branch/submodule commands
      - deny override flags anywhere
      - only allow per-subcommand flags in ALLOWED_FLAGS
      - validate any path-like args are within workspace
    """
    if not isinstance(argv, (list, tuple)):
        return GitDecision(False, "argv_must_be_list_or_tuple")
    if len(argv) < 2:
        return GitDecision(False, "missing_subcommand")
    if not all(isinstance(x, str) and x.strip() for x in argv):
        return GitDecision(False, "argv_must_be_nonempty_strings")

    if argv[0].strip().lower() != "git":
        return GitDecision(False, "cmd_must_be_git")

    sub = argv[1].strip().lower()

    if sub in DENY_SUBCOMMANDS:
        return GitDecision(False, "subcommand_denied")
    if sub not in ALLOWED_SUBCOMMANDS:
        return GitDecision(False, "subcommand_not_allowlisted")

    allowed_flags = ALLOWED_FLAGS.get(sub, set())

    # parse rest
    i = 2
    while i < len(argv):
        tok = argv[i]

        # hard-deny override flags anywhere
        for deny in DENY_FLAGS:
            if tok == deny or tok.startswith(f"{deny}="):
                return GitDecision(False, "forbidden_flag")

        if tok == "--":
            # treat remaining args as paths (only valid for add/diff)
            if sub not in {"add", "diff"}:
                return GitDecision(False, "unexpected_arg")
            i += 1
            while i < len(argv):
                if not _resolve_under_ws(ws_root, argv[i]):
                    return GitDecision(False, "path_outside_workspace")
                i += 1
            break
        if _is_flag(tok):
            if tok not in allowed_flags:
                return GitDecision(False, "flag_not_allowlisted")

            # flags that take a value
            if tok in {"-n", "--max-count", "-m", "--message"}:
                if i + 1 >= len(argv):
                    return GitDecision(False, "flag_missing_value")
                val = argv[i + 1]
                if _is_flag(val):
                    return GitDecision(False, "flag_value_invalid")
                i += 2
                continue

            i += 1
            continue

        # non-flag token: treat as path for add/diff; for others, disallow extra args
        if sub in {"add", "diff"}:
            # allow bare "--" separator is a flag but handled above; if user passes it as tok it startswith '-' anyway
            if not _resolve_under_ws(ws_root, tok):
                return GitDecision(False, "path_outside_workspace")
            i += 1
            continue

        # allow no extra args for init/status/log/commit (beyond their strict flags)
        return GitDecision(False, "unexpected_arg")

    return GitDecision(True, "allowed")
