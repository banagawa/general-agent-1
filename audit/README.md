# Audit Notes

Status: current through Sprint H Slice 7

Audit logging remains append-only. Allow, deny, failure, summary, and mutation paths must remain auditable.

## Runtime location

Runtime bookkeeping is stored outside the target worktree under:

```text
workspace/agent_runtime/<workspace_name>/
```

This runtime-state root owns:

- audit logs.
- capability token state.
- revocation state.
- pending patch state.
- plan lifecycle artifacts.
- execution summaries.
- failure envelopes.

## Core audit expectations

Audit coverage includes:

- plan creation.
- plan approval.
- execution start and finish.
- failure-envelope recording.
- summary recording.
- denial events.
- mutation allow/deny/execute events.
- rollback events.
- autonomy decisions.
- strategy registry appends.
- workspace graph rebuilds when requested.

## Deny observability

Representative denial paths must emit audit events, including:

- TEST_RUN denial.
- PATCH_APPLY token denial.
- PATCH_EDIT token denial.
- replay denial.
- workspace drift denial.
- malformed plan/hash denial.

## Runtime history health

Runtime history health reporting is read-only and report-only.

It may appear in summaries and failure envelopes, but it must not affect:

- execution success.
- failure classification.
- rollback behavior.
- approval behavior.
- replay behavior.
- drift decisions.

## Workspace intelligence

Workspace intelligence may emit advisory metadata such as graph rebuild records. Graph output must not become authority. ToolGateway and PolicyEngine remain the authority boundary.
