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

## Revoke

- Persistent revocation store.
- Blocks propose and approve.
- Survives CLI restarts.

Audit: WRITE_REVOKED

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
