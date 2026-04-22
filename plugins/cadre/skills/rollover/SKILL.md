---
name: rollover
description: Consolidate an in-flight run into a handoff brief plus structured state. Operator-invokable or triggered by the Claude Code PreCompact hook. Reference ADR 0006.

authority_level: 2
intent: >
  Produce a markdown brief and JSON state artifact for a run, sufficient for
  /resume to reconstruct working memory after /clear. Summarization, not
  reasoning.
preconditions:
  - "run_id is provided or inferable from the most recent SEP log"
  - "SEP log for the run exists and is readable"
success_criteria:
  - "ai-docs/rollover-<run_id>.md exists and is non-empty"
  - "ai-docs/rollover-<run_id>.json validates against schema v1.0"
  - "next_action in the JSON names a concrete continuation"
candidate_agents:
  - context-summarizer
required_agents:
  - context-summarizer
policy_profile: standard-delivery
max_budget_usd: 0.50
max_duration_seconds: 120
max_review_cycles: 0
---

# /rollover — Context Rollover

Consolidate a run's state before `/clear`. The operator invokes this
proactively, or the PreCompact hook invokes it automatically when Claude Code
is about to compact the window. Reference: `docs/architecture/0006-context-rollover.md`.

## Global Safety Contract

**Violating the following requires explicit written user confirmation.**

No step may:
- Mutate or delete the SEP log. The log is audit trail.
- Overwrite a checkpoint record from the run being consolidated.
- Execute `/clear`. `/clear` is a CLI command and only the operator can run it.
- Invoke any agent not listed in `candidate_agents`.
- Skip the artifact-validation step.

If any step needs one of these, halt and surface the decision.

## When to Use

- Proactively, before a break in a long run.
- Automatically, when the runtime emits `context_rollover_suggested`.
- Automatically, when the Claude Code PreCompact hook fires.
- Never while a producer or executor agent is mid-call for the same run.

## Execution

### Step 1 — Resolve the run

Accept `run_id` from the invocation arguments. If absent, read the most recent
SEP log under `.cadre-log/` (or the configured `sep_log_dir`) and use its
`run_id`. If no active run is detectable, halt with a clear error.

### Step 2 — Collect sources

For the resolved `run_id`, collect:

- All SEP log entries (chronological).
- The current `CheckpointStore` latest record for the run, if any.
- Paths of any artifacts produced under `ai-docs/` whose filenames reference
  the `run_id`.
- The token counter for the run from `Runtime.tokens_used(run_id)`.

### Step 3 — Invoke `context-summarizer`

Call `context-summarizer` via `cadre.runtime.call()` with the collected
sources, the rollover reason, and the success criteria above. The agent runs
on a chat-class model per `policy_profile: standard-delivery`.

### Step 4 — Validate artifacts

After the summarizer returns:

- Confirm `ai-docs/rollover-<run_id>.md` exists and is non-empty.
- Confirm `ai-docs/rollover-<run_id>.json` exists, parses as JSON, and has
  `schema_version: "1.0"` plus all required keys (`run_id`, `skill`,
  `completed_steps`, `open_decisions`, `invariants`, `next_action`,
  `checkpoint_ref`, `brief_path`).

If validation fails, retry the summarizer once with a compacted input. If it
fails again, surface the failure and halt. Do not fabricate artifacts.

### Step 5 — Write the rollover checkpoint

Save a checkpoint with `label="rollover_pending"` so `/resume` can find the
canonical state boundary:

```python
runtime.checkpoint_store.save(
    run_id=run_id,
    step_id=<next>,
    label="rollover_pending",
    data={"brief_path": ..., "state_path": ..., "summarizer_model": ...},
)
```

### Step 6 — Print the operator handoff

Emit exactly:

```
==============================================
Rollover prepared for run <run_id>.

Artifacts:
- Brief: ai-docs/rollover-<run_id>.md
- State: ai-docs/rollover-<run_id>.json

To resume cleanly in a new session:
  1. Run  /clear
  2. Run  /resume <run_id>

You can safely close this session. All work is persisted.
==============================================
```

Stop. Do not invoke another agent. Do not execute `/clear`.

## Result Contract

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts:
    - ai-docs/rollover-<run_id>.md
    - ai-docs/rollover-<run_id>.json
  findings: []
  next_action: "/resume <run_id>"
```

## Cost

Expected per invocation: ~$0.01 at Haiku-tier pricing for a 100k-input → 2k-output
summarization. Budget cap 0.50 USD provides headroom. If cost exceeds
$0.10, the summarizer was routed to a reasoning-class model — investigate
`summarizer_model_class` in the policy.

## Observability

The skill itself writes no SEP entries beyond those emitted by
`context-summarizer` through `cadre.runtime.call()`. The checkpoint
`rollover_pending` is the canonical resume anchor.

## Relationship to Other Skills

- Upstream trigger: any long-running skill + the PreCompact hook + manual
  invocation.
- Downstream consumer: `/resume`, which reads the JSON artifact and reloads
  the checkpoint.
