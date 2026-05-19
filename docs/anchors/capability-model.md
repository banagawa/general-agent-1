# Capability Token Model

Status: Active Architecture Anchor

This document defines the scoped token model used at execution time.

---

## Motivation

Move from:

global mutation or command permission

To:

scoped, expiring, token-based capabilities checked per tool invocation.

---

## Token Schema

```text
{
  id,
  actions,
  scope,
  constraints,
  expiry,
  issued_at
}
```

---

## Enforcement Rules

- every tool call checks token validity
- expired tokens deny automatically
- revocation is keyed by token ID
- missing token denies
- mismatched scope denies
- unexpected token state fails closed

---

## Token Types

- `FS_WRITE_PATCH`
- `FS_EDIT_PATCH`
- `CMD_RUN`
- `GIT_RUN`

Future:
- `CONNECTOR_*`

---

## Scope Model

Current scoped use:

- `PATCH_APPLY` → exact-path scope
- `PATCH_EDIT` → exact-path scope
- `TEST_RUN` → action-scoped
- `GIT_RUN` → action-scoped

Exact-path scoped means the token is valid only for the resolved workspace path for the approved step.

---

## Expiry Model

- every token expires
- expiry is enforced per invocation
- execution must deny if a token is expired

---

## Revocation Model

- stored on disk
- revocation invalidates token immediately
- fail closed if token is revoked, missing, or malformed

---

## Bridge to UX

This model enables later UX such as:

- permission request cards
- scoped grants
- time-based approval
- one-click revoke
- active grants list

without changing the core execution boundary.
