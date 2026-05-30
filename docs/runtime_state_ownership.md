# Runtime State Ownership Contract

Status: characterization guard

## Purpose

This document records the runtime-state ownership model currently implied by the codebase.

It does not migrate storage.
It does not change runtime behavior.
It exists so future migrations can be designed deliberately.

## Workspace state

Workspace state is the protected project content that participates in workspace fingerprinting.

Examples:

- source code
- tests
- documentation
- configuration

When these files change, workspace fingerprint drift should be visible.

## Execution history

Execution history is stored under `plans/`.

Examples:

- `plans/pending/`
- `plans/approved/`
- `plans/executed/`
- `plans/failures/`
- `plans/summaries/`

The current fingerprint implementation excludes `plans/` from workspace fingerprinting.

This means execution history is stored inside the workspace tree, but it is not treated as protected workspace content for drift detection.

## Runtime bookkeeping

Runtime bookkeeping is currently cwd-relative under `.audit/`.

Examples:

- `.audit/audit.jsonl`
- `.audit/capability_tokens.json`
- `.audit/capability_revocations.json`
- `.audit/pending_patches.json`

These files are runtime records, not source workspace content.

## Runtime-state fingerprint exclusion

The workspace fingerprint excludes `.runtime_state/`.

This creates a safe future landing zone for runtime bookkeeping without causing workspace drift. It does not move any current audit or token files.

## Current unresolved question

The unresolved question is whether `.audit/` should remain cwd-relative or move to an explicit runtime-state root.

A previous direct migration to `workspace_root/.audit` caused broad failures because runtime writes under the workspace affected approval, execution, and drift semantics.

## Future migration requirement

Before `.audit/` moves, the repo must explicitly define:

1. where runtime state lives
2. whether runtime state participates in fingerprints
3. how append-only audit history is preserved
4. how tests isolate runtime bookkeeping
5. how workspace drift detection ignores runtime-only writes without ignoring real source changes

## Non-goals

This contract does not:

- move audit logs
- move token stores
- change plan storage
- add a new subsystem
