# Write Lifecycle Architecture

Status: Anchor

Defines the current mutation control model.

---

## Current Write Tools

Two mutation tools exist and remain distinct:

- `PATCH_APPLY`
- `PATCH_EDIT`

Both execute only through:

`plan.submit` or `task.plan`
→ `plan.approve`
→ `plan.execute`
→ `ToolGateway`
→ `PolicyEngine`
→ filesystem tool implementation

No standalone write lifecycle bypass exists.

---

## PATCH_APPLY Lifecycle

`PATCH_APPLY` is used for whole-file replacement.

Rules:

- target file must already exist
- request must provide workspace-relative `path`
- request must provide full replacement `new_content`
- execution requires approval
- execution requires exact-path scoped capability token
- execution is audited

Use when:
- the full replacement content is already known exactly

Do not use when:
- the change should target one exact anchored substring only

---

## PATCH_EDIT Lifecycle

`PATCH_EDIT` is used for anchored exact-text replacement.

Rules:

- target file must already exist
- request must provide workspace-relative `path`
- request must provide non-empty `edits`
- every edit item must include:
  - `old_text`
  - `new_text`
- edit item may include:
  - `occurrence`
- step may include:
  - `expected_file_sha256_before`
- execution requires approval
- execution requires exact-path scoped capability token
- execution is audited

Use when:
- the current file content is known enough to target exact anchored text

Do not use when:
- the change is semantic only
- the target is ambiguous and no exact anchor exists
- the edit requires regex or fuzzy matching

---

## PATCH_EDIT Matching Rules

- 0 exact matches denies
- 1 exact match applies
- repeated exact matches without `occurrence` denies
- out-of-range `occurrence` denies

Multi-edit behavior:

- edits apply in declared order
- each edit sees the progressively updated in-memory content
- if any edit fails, the whole step denies
- no partial write is committed

---

## Enforcement

For all mutation:

- ToolGateway is the choke point
- PolicyEngine remains deny-by-default
- workspace boundary is enforced on resolved path
- token scope must match exact path for mutation
- all allow/deny paths are audited
- unexpected state fails closed

---

## Guarantees

- no silent overwrites
- no out-of-workspace mutation
- full approval-bound execution path
- typed mutation semantics
- append-only audit trail
