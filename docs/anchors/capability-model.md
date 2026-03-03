# Capability Token Model (Implemented in Sprint A5)

This document defines the transition from global write revocation to tokenized capability enforcement.

---

## Motivation

Move from:

Global write flag

To:

Scoped, expiring, token-based capabilities.

---

## Token Schema

{
  id,
  actions,
  scope,
  constraints,
  expiry,
  issued_at
}

---

## Enforcement Rules

- Every tool call checks token validity.
- Expired tokens deny automatically.
- Revocation list keyed by token ID.
- No global write flag.

---

## Token Types (Planned)

FS_WRITE_PATCH  
CMD_RUN  
Future: CONNECTOR_*  

---

## Expiry Model

- Always set.
- Even long-lived tokens expire.
- Enforced per invocation.

---

## Revocation Model

- Stored on disk.
- Revocation invalidates token immediately.
- Fail-closed if token missing or invalid.

---

## Bridge to UX

Enables:

- Permission request cards
- Scoped grants
- Time-based approval
- One-click revoke
- Active grants list
