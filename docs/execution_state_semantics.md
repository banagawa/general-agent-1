# Execution state semantics

## State model

An approved plan execution uses this state flow:

- `APPROVED`
- `IN_FLIGHT`
- `EXECUTED` or `FAILED`

Allowed transitions:

- `APPROVED -> IN_FLIGHT`
- `IN_FLIGHT -> EXECUTED`
- `IN_FLIGHT -> FAILED`

All other transitions are denied.

## Replay policy

Execution is single-use per approval.

Once a plan enters `IN_FLIGHT`, that approval is consumed.
A rerun requires explicit new approval.
There is no silent reset to `APPROVED`.

## Crash behavior

If a worker crashes after a plan enters `IN_FLIGHT`, the plan remains consumed.

Current policy:
- do not auto-reset `IN_FLIGHT`
- do not auto-retry
- do not silently reopen execution

Operator action is required to re-approve and rerun.

## Rationale

This fail-closed behavior is safer than attempting automatic recovery because:
- execution may have already produced side effects
- tools may not be idempotent
- replay could violate approval-bound execution guarantees

## Audit expectations

Denials and execution outcomes should remain searchable through append-only audit records.

Important denial classes include:
- replay denied
- workspace drift denied
- hash mismatch denied
- invalid input denied

## Long-term note

A later storage refactor may move control-plane state outside the workspace root.
That does not change the execution-state policy above.

## Preflight relationship

The execution state model is entered only after preflight succeeds.

Preflight is responsible for denying execution before `IN_FLIGHT` when:
- execution request shape is invalid
- identifiers are malformed
- approval metadata is missing or malformed
- canonical plan hash does not match
- workspace drift is detected

Those denials should be represented through standardized deny audit records with reason codes.

## Operator note

The presence of `IN_FLIGHT` without a terminal transition should be treated as a consumed approval, not as implicit permission to retry.

Manual operator action is required to:
- inspect state
- determine whether side effects may have occurred
- explicitly re-approve before any rerun
