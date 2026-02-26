# Write Lifecycle Architecture

Defines the mutation control model.

---

## Flow Overview

1. Propose Patch
2. Store Pending Patch
3. Review Diff
4. Approve Patch
5. Apply Mutation
6. Audit Event
7. Optionally Revoke

---

## Propose

- Accepts relative path + new content.
- Generates unified diff.
- Stores pending patch on disk.
- Returns patch ID + diff.
- Does NOT modify file.

Audit: PATCH_PROPOSED

---

## Approve

- Requires valid patch ID.
- Must not be revoked.
- Applies patch.
- Removes from pending store.

Audit: PATCH_APPROVED

---

## Revoke (Sprint A5+ — Token-Based)

Revocation is capability-token based. The system no longer uses a global
“writes disabled” flag.

`revoke writes`:

- Clears all active capability tokens (persisted on disk).
- Emits a `REVOKE_TOKENS` audit event.

After revocation:

- Previously issued tokens are invalid.
- Any protected operation with a revoked/missing/expired token
  will deny and audit.
- Token validation is fail-closed at ToolGateway before execution.

Important:

Revocation does **not** globally disable propose/approve.
It invalidates existing capabilities. New operations require newly issued,
valid tokens.

Core invariants preserved:

- Deny-by-default
- ToolGateway choke point
- Append-only audit
- Fail-closed execution

---

## Enforcement

- Revocation checked on every write-related action.
- Fail-closed if revoked.
- No partial write state.

---

## Guarantees

- No silent overwrites.
- Full diff visibility.
- Persistent lifecycle.
- Audit trace for every state change.
