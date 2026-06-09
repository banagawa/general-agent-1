# Audit and Capability Token Storage Boundary

Status: historical finding superseded by runtime-state root

## Historical behavior

Audit logs and capability token state were previously cwd-relative:

- `.audit/audit.jsonl`
- `.audit/capability_tokens.json`
- `.audit/capability_revocations.json`

That behavior was characterized so migration work could be designed deliberately.

## Failed migration finding

A previous hardening attempt moved audit and token state under `workspace_root/.audit`.

That caused broad failures because runtime state written under `workspace_root` changed the workspace fingerprint between plan approval and execution. It also broke tests that intentionally isolate audit output by changing cwd.

## Current decision

Runtime bookkeeping now belongs under the explicit runtime-state root:

```text
workspace/agent_runtime/<workspace_name>/
```

This keeps runtime state outside the target worktree and avoids treating audit/token writes as source workspace drift.

Current runtime-state ownership is documented in:

- `docs/runtime_state_ownership.md`
- `docs/plan_artifact_ownership.md`
- `docs/anchors/current-state-ledger-v6.md`

## Guardrail

Future changes to audit, token, revocation, pending-patch, plan, summary, or failure-envelope storage must preserve:

- append-only audit behavior.
- workspace drift correctness.
- separation of app root, workspace root, execution root, runtime import root, and runtime-state root.
- no cleanup, deletion, compaction, retention, or migration tooling without explicit design.
