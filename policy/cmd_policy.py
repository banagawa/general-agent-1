from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# Keep this intentionally small at first.
# We can expand later once tests + audit are solid.
CMD_ALLOWLIST: dict[str, dict] = {
    "python": {
        # allow python -c "...", python -m pytest, python -m ruff, etc.
        "allow_any_args": True,
    },
    "git": {
        # read-only-ish commands only
        "allow_any_args": False,
        "allowed_subcommands": {
            "status",
            "diff",
            "log",
            "show",
        },
    },
}

# Things we never want in argv (defense-in-depth even though shell=False later)
DISALLOWED_TOKENS = {
    ";", "&&", "||", "|", ">", ">>", "<", "<<",
    "`", "$(", "${", ")",  # keep conservative; we only accept argv anyway
}


@dataclass(frozen=True)
class CmdDecision:
    allowed: bool
    reason: str


def _has_disallowed_tokens(argv: Sequence[str]) -> bool:
    for a in argv:
        if any(tok in a for tok in DISALLOWED_TOKENS):
            return True
    return False


def validate_cmd_run(argv: Sequence[str]) -> CmdDecision:
    """
    Validate a proposed cmd.run invocation.
    Rules:
      - argv must be a non-empty sequence of strings (no single-string passthrough)
      - argv[0] must be in allowlist
      - if command has subcommand rules, enforce them
      - reject obvious shell metacharacters in any arg (defense in depth)
    """
    if not isinstance(argv, (list, tuple)):
        return CmdDecision(False, "argv_must_be_list_or_tuple")

    if len(argv) == 0:
        return CmdDecision(False, "argv_empty")

    if not all(isinstance(x, str) and x.strip() != "" for x in argv):
        return CmdDecision(False, "argv_must_be_nonempty_strings")

    if _has_disallowed_tokens(argv):
        return CmdDecision(False, "disallowed_token_in_argv")

    cmd = argv[0].strip().lower()
    if cmd not in CMD_ALLOWLIST:
        return CmdDecision(False, "cmd_not_allowlisted")

    rule = CMD_ALLOWLIST[cmd]
    if rule.get("allow_any_args", False):
        return CmdDecision(True, "allowed")

    # subcommand-based rules (e.g., git status/diff/log/show)
    if len(argv) < 2:
        return CmdDecision(False, "missing_required_subcommand")

    sub = argv[1].strip().lower()
    allowed_subs = rule.get("allowed_subcommands", set())
    if sub not in allowed_subs:
        return CmdDecision(False, "subcommand_not_allowlisted")

    return CmdDecision(True, "allowed")
