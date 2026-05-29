from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Sequence


# Keep generic CMD_RUN behavior stable for existing workflows.
# TEST_RUN has a narrower allow-list because it is an execution path that can
# otherwise become a mutation bypass.
CMD_ALLOWLIST: dict[str, dict] = {
    "python": {
        # Existing generic CMD_RUN behavior remains unchanged.
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

PYTHON_LAUNCHERS = {"python", "python3", "py"}
PYTEST_LAUNCHERS = {"pytest"}
ALLOWED_INLINE_PYTHON = {
    "import sys; sys.exit(1)",
}

# Things we never want in argv (defense-in-depth even though shell=False later)
DISALLOWED_TOKENS = {
    "&&", "||", "|", ">", ">>", "<", "<<",
    "`", "$(", "${",
}

DISALLOWED_FOR_NON_PYTHON = {";"}

# Options that can redirect pytest's operating roots or temp roots.
# Keep this narrow so ordinary pytest usage stays usable.
DISALLOWED_PYTEST_OPTIONS = {
    "--rootdir",
    "--basetemp",
    "--confcutdir",
    "--pyargs",
}


@dataclass(frozen=True)
class CmdDecision:
    allowed: bool
    reason: str


def _has_disallowed_tokens(argv: Sequence[str]) -> bool:
    cmd = argv[0].strip().lower() if argv else ""
    for a in argv:
        if any(tok in a for tok in DISALLOWED_TOKENS):
            return True
        if cmd != "python" and any(tok in a for tok in DISALLOWED_FOR_NON_PYTHON):
            return True
    return False


def _has_parent_segment(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts


def _has_absolute_or_drive_path(value: str) -> bool:
    candidate = value.split("=", 1)[1] if "=" in value else value
    posix_path = PurePosixPath(candidate)
    windows_path = PureWindowsPath(candidate)
    return posix_path.is_absolute() or windows_path.is_absolute() or bool(windows_path.drive)


def _is_safe_pytest_arg(value: str) -> bool:
    if not value:
        return False
    if "\x00" in value:
        return False
    if any(tok in value for tok in DISALLOWED_TOKENS):
        return False
    if "\\" in value:
        return False
    if _has_parent_segment(value):
        return False
    if _has_absolute_or_drive_path(value):
        return False

    option_name = value.split("=", 1)[0]
    if option_name in DISALLOWED_PYTEST_OPTIONS:
        return False

    return True


def validate_test_run_argv(argv: Sequence[str]) -> CmdDecision:
    """
    TEST_RUN remains a deterministic execution probe, but it is allow-listed.

    Allowed command forms:
      python --version
      python -c "import sys; sys.exit(1)"
      python -m pytest [...]
      python3 -m pytest [...]
      py -m pytest [...]
      pytest [...]

    Denied examples:
      python -c "open('owned.txt','w').write('x')"
      python script.py
      python -m pip ...
      pytest --rootdir=/outside
      pytest ../tests
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

    if cmd in PYTHON_LAUNCHERS:
        if len(argv) == 2 and argv[1] == "--version":
            return CmdDecision(True, "allowed")

        if len(argv) == 3 and argv[1] == "-c":
            inline = argv[2].strip()
            if inline in ALLOWED_INLINE_PYTHON:
                return CmdDecision(True, "allowed")
            return CmdDecision(False, "test_run_inline_python_not_allowlisted")

        if len(argv) >= 3 and argv[1] == "-m" and argv[2] == "pytest":
            pytest_args = argv[3:]
        else:
            return CmdDecision(False, "test_run_python_shape_not_allowlisted")
    elif cmd in PYTEST_LAUNCHERS:
        pytest_args = argv[1:]
    else:
        return CmdDecision(False, "test_run_command_not_allowlisted")

    for arg in pytest_args:
        if not _is_safe_pytest_arg(arg):
            return CmdDecision(False, "unsafe_pytest_arg")

    return CmdDecision(True, "allowed")


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
