# Sprint E Closeout

Deterministic Execute--Test--Diff--Summarize Loop

## Goal

Implement a deterministic plan execution loop that:

• executes approved plans only\
• records execution results\
• captures repository diff state\
• produces a deterministic execution summary\
• prevents replay\
• records failure envelopes for failed runs

------------------------------------------------------------------------

# Architecture Invariants (Preserved)

ToolGateway choke point\
PolicyEngine deny-by-default\
Workspace boundary enforcement\
Patch-only file writes\
Append-only audit log

Execution path:

Orchestrator\
→ AgentLoop\
→ execute_plan\
→ execute_step\
→ ToolGateway\
→ PolicyEngine\
→ Tool Implementation

------------------------------------------------------------------------

# Plan Lifecycle

## submit

    plan.submit
    → plans/pending/<plan_hash>.json

## approve

    plan.approve
    → plans/approved/<plan_hash>.json

## execute

    plan.execute
    → deterministic step loop

Artifacts created:

    plans/executed/<plan_hash>.json
    plans/summaries/<plan_hash>-<tx_id>.json
    plans/failures/<plan_hash>-<tx_id>.json

------------------------------------------------------------------------

# Execution Loop Behavior

For each step:

1.  enforce transaction time budget
2.  issue capability token
3.  execute step through ToolGateway
4.  record step result
5.  track mutation count
6.  capture changed paths

After loop:

    collect_test_summary()
    collect_repo_diff()
    derive_result_status()

------------------------------------------------------------------------

# Success Path

If all steps succeed:

Artifacts written:

    plans/executed/<plan_hash>.json
    plans/summaries/<plan_hash>-<tx_id>.json

Audit events:

    EXECUTION_STARTED
    EXECUTION_FINISHED

Replay prevention enforced.

------------------------------------------------------------------------

# Failure Path

If any step fails:

Artifacts written:

    plans/failures/<plan_hash>-<tx_id>.json
    plans/summaries/<plan_hash>-<tx_id>.json

Failure envelope includes:

    plan_hash
    tx_id
    failure_class
    failing_step_id
    tool
    changed_paths
    test_summary
    diff_summary
    requires_new_approval

Executed marker is NOT written.

Audit event:

    EXECUTION_FAILED

------------------------------------------------------------------------

# Replay Protection

Second execution attempt:

    plan already executed

No new artifacts created.

------------------------------------------------------------------------

# Limits Enforced

    MAX_PLAN_STEPS
    MAX_TX_SECONDS
    MAX_MUTATIONS

Violation → execution failure.

------------------------------------------------------------------------

# Verification Tests Performed

## Success path

submit → approve → execute

Artifacts observed:

    plans/executed/<hash>.json
    plans/summaries/<hash>-<tx>.json

## Replay denial

Second execution attempt rejected.

## Failure path

TEST_RUN returning exit code 1 produced:

    plans/failures/<hash>-<tx>.json
    plans/summaries/<hash>-<tx>.json

Executed marker not written.

------------------------------------------------------------------------

# Sprint E Result

Deterministic plan execution loop implemented.

System now supports:

• approved plan execution\
• deterministic execution summaries\
• replay protection\
• failure envelopes\
• execution diff capture\
• bounded execution limits

Sprint E complete.

Next sprint: Sprint F -- Controlled Autonomy Mode
