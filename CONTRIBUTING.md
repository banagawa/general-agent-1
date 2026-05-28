# CONTRIBUTING.md

Status: Governing Contributor Guide

Before contributing read:

- SECURITY.md
- docs/anchors/security-invariants.md
- docs/anchors/architecture-contract.md
- docs/anchors/system-state-v1.md

---

## Non Negotiable Development Rules

### No Tool Bypass

All execution must pass through:

AgentLoop → ToolGateway → PolicyEngine → Tool

### No shell=True

Commands must be argv lists and executed with shell=False.

### Typed File Mutation Rules

Repository mutation uses two distinct tools:

- `PATCH_APPLY` for whole-file replacement
- `PATCH_EDIT` for anchored exact-text replacement

Contributors must preserve that separation.

Do not:
- collapse both behaviors into one generic write path
- add regex or fuzzy edit behavior to `PATCH_EDIT`
- add fallback from `PATCH_EDIT` to `PATCH_APPLY`
- bypass ToolGateway or PolicyEngine for mutation

When updating docs, tests, or runtime behavior, keep capability mappings aligned:

- `PATCH_APPLY` → `FS_WRITE_PATCH`
- `PATCH_EDIT` → `FS_EDIT_PATCH`

### Deny By Default

PolicyEngine must enforce workspace boundaries and capability checks.

### Runtime And Workspace Roots

Contributors must keep root semantics explicit:

- `app_root` is the authoritative runtime/security-code root.
- `workspace_root` is the allowed mutation boundary.
- `execution_root` is command/test cwd only.
- `runtime_import_root` is where runtime modules are imported from.

Do not derive workspace authority from cwd. Do not allow `app_root` and `workspace_root` to collapse. Use `AGENT_APP_ROOT` only to bind the authoritative runtime root for worktree-safe execution.


### Audit Everything

Every tool invocation must log:

- allow
- deny
- metadata

---

## Commit Discipline

Before committing:

git status
git diff
git diff --staged

Rules:

- commits must be small and focused
- do not commit audit artifacts
- do not commit workspace temp files
