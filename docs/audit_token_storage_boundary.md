# Audit and Capability Token Storage Boundary

Status: characterization guard

## Current behavior

Audit logs and capability token state are cwd-relative today:

- `.audit/audit.jsonl`
- `.audit/capability_tokens.json`
- `.audit/capability_revocations.json`

This is not ideal long term, but it is the behavior current tests and execution flows expect.

## Failed migration finding

A previous hardening attempt moved audit and token state under `workspace_root/.audit`.

That caused broad failures because runtime state written under `workspace_root` changed the workspace fingerprint between plan approval and execution. It also broke tests that intentionally isolate audit output by changing cwd.

## Current decision

Do not move audit/token storage yet.

Before changing storage location, the repo needs an explicit runtime-state model:

1. Decide whether audit/token files are part of workspace state.
2. If not, exclude runtime state from workspace fingerprinting.
3. Preserve append-only audit behavior.
4. Keep live app root free of mutable runtime state.
5. Add migration tests before changing storage.

## Guardrail

The accompanying tests intentionally document the current cwd-relative behavior so a future migration fails loudly unless it also updates fingerprint and audit-location semantics.
