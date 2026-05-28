# Historical Document Waivers

## sprint-e-closeout.md

Decision: WAIVED

Reason:
This file is retained as a historical sprint artifact and is not treated as a live architecture or runtime contract document.

Current source of truth lives in:
- `README.md`
- `docs/anchors/architecture-contract.md`
- `docs/anchors/security-invariants.md`
- `docs/anchors/system-state-v1.md`
- `docs/anchors/write-lifecycle.md`

## Sprint G Pause For Worktree Root Hardening

Decision: DOCUMENTED PAUSE

Reason:
Sprint G execution exposed cwd-relative workspace root ambiguity under git worktree execution. No safety bypass, guard weakening, policy relaxation, or ToolGateway bypass is approved. Sprint G remains paused until runtime root and workspace root semantics are stable.
