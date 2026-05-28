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

Controlled autonomy invariants:
- autonomy modes may only create pending plans
- only `plan.execute` may execute steps
- bounded autonomy is disabled unless explicitly feature-flag enabled
- runtime, cycle, and mutation budgets fail closed
- mutation failures trigger rollback

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

All filesystem mutation must remain inside `WORKSPACE_ROOT`. Runtime authority and mutation authority must remain separate.

Required properties:
- paths are canonicalized with `resolve()`
- resolved paths are checked against workspace boundary
- escape attempts deny
- mutation outside workspace is forbidden
- `app_root` is the authoritative runtime/security-code root
- `workspace_root` is the mutation boundary
- `execution_root` is command/test cwd only
- `runtime_import_root` must not be derived from mutable workspace cwd
- `workspace_root` must be app-root anchored or explicitly configured
- cwd-relative workspace defaults are forbidden
- `app_root` and `workspace_root` must never collapse
- `AGENT_APP_ROOT` may bind runtime root for worktree-safe execution

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

`TEST_RUN` may select only `cwd: "workspace"` or `cwd: "app"`; raw cwd paths are forbidden.

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

## 7. Strategy data boundary

Sprint G strategy behavior must remain inert unless explicitly approved by a later workflow.

Required properties:
- strategies are data only
- strategy proposals do not execute tools
- strategy proposals do not mutate policy
- strategy proposals do not modify plan schema
- strategy proposals do not expand autonomy
- strategy registry records are append-only
- automatic strategy installation is forbidden

---

## 8. Drift binding

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
