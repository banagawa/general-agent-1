# Security Invariants

Status: Anchor

This file defines the execution and mutation invariants that must remain true.

If implementation or other docs conflict with this file, this file wins.

---

## 1. ToolGateway choke point

All tool execution must pass through `ToolGateway`.

Required execution spine:

Human
→ `task.plan` or `plan.submit`
→ `plan.approve`
→ `plan.execute`
→ Orchestrator
→ AgentLoop
→ PlanExecutor
→ `execute_step`
→ `ToolGateway`
→ `PolicyEngine`
→ tool implementation

No direct loop-to-tool execution is allowed.

---

## 2. Deny-by-default policy

Every action is denied unless explicitly allowed.

Required properties:
- `PolicyEngine.is_allowed()` remains authoritative
- unexpected states fail closed
- unrecognized actions deny
- out-of-policy paths deny

---

## 3. Workspace boundary isolation

All filesystem mutation must remain inside `WORKSPACE_ROOT`.

Required properties:
- paths are canonicalized with `resolve()`
- resolved paths are checked against workspace boundary
- escape attempts deny
- mutation outside workspace is forbidden

---

## 4. Typed mutation separation

Two mutation tools exist and must remain distinct:

### `PATCH_APPLY`
- whole-file replacement only
- existing file required
- exact-path scoped token
- audited

### `PATCH_EDIT`
- anchored exact-text replacement only
- existing file required
- requires literal `old_text` and `new_text`
- optional `occurrence`
- optional `expected_file_sha256_before`
- exact-path scoped token
- audited

`PATCH_EDIT` must not become:
- regex editing
- fuzzy matching
- AST patching
- line-number-only editing
- fallback whole-file rewrite

This separation is a hard invariant.

Ambiguity behavior:
- 0 matches denies
- 1 exact match applies
- repeated exact matches without `occurrence` denies
- out-of-range `occurrence` denies

---

## 5. Capability-scoped execution

Each executable step requires a short-lived capability token.

Current mappings:
- `TEST_RUN` → `CMD_RUN`
- `GIT_RUN` → `GIT_RUN`
- `PATCH_APPLY` → `FS_WRITE_PATCH`
- `PATCH_EDIT` → `FS_EDIT_PATCH`

Mutation tokens must remain exact-path scoped.

---

## 6. Approval-bound execution

Mutation-capable execution requires:
- validated plan
- explicit approval
- preflight success
- execution through the approved plan path only

Raw execution commands remain blocked.

Planner-generated plans are proposals only and do not bypass approval.

---

## 7. Drift binding

Approval binds to workspace state.

Required properties:
- approval records workspace fingerprint
- execution recomputes workspace fingerprint before run
- mismatch denies execution
- rerun requires new approval

---

## 8. Atomic and fail-closed mutation

`PATCH_EDIT` multi-edit behavior must remain atomic:
- edits apply in order to in-memory content
- any failed edit denies whole step
- nothing is written on failure

All mutation paths must fail closed.

---

## 9. Append-only audit

Allow and deny paths must both be logged.

Required audit coverage includes:
- plan lifecycle events
- deny events
- mutation allow/deny/execute events

Typed mutation audit events include:
- `PATCH_EDIT_ALLOWED`
- `PATCH_EDIT_DENIED`
- `PATCH_EDIT_EXECUTED`

Audit logs remain append-only.
