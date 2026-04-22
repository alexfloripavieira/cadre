---
name: resume
description: Resume a run from its rollover handoff artifact after /clear. Reads the JSON state, reloads the checkpoint, re-emits locked invariants, and hands control back to the originating skill at the named next action. Reference ADR 0006.

authority_level: 2
intent: >
  Reconstruct a run's working memory from ai-docs/rollover-<run_id>.json plus
  the CheckpointStore, confirm the next action with the operator, and delegate
  back to the originating skill.
preconditions:
  - "ai-docs/rollover-<run_id>.json exists and validates against schema v1.0"
  - "run_id is supplied as an argument"
success_criteria:
  - "invariants from the handoff JSON are re-emitted before any new agent call"
  - "open decisions surface to the operator before resume proceeds"
  - "control is handed to the originating skill at the recorded next action"
candidate_agents: []
required_agents: []
policy_profile: standard-delivery
max_budget_usd: 0.25
max_duration_seconds: 60
max_review_cycles: 0
---

# /resume — Resume From Rollover Handoff

Pair skill of `/rollover`. Reads the rollover artifacts and hands control back
to the originating skill. Reference: `docs/architecture/0006-context-rollover.md`.

## Global Safety Contract

**Violating the following requires explicit written user confirmation.**

No step may:
- Modify the rollover artifacts being read. They remain audit trail.
- Silently skip an invariant declared in the handoff JSON.
- Resume past the recorded `next_action` without operator confirmation.
- Proceed when repository state contradicts a locked invariant.
- Overwrite a checkpoint record.

If any step needs one of these, halt and surface the decision.

## When to Use

- Immediately after `/clear` in a fresh session, passing the same `run_id`.
- After a session crash, if `ai-docs/rollover-<run_id>.json` exists.
- Never without a valid handoff artifact. For partial recovery without a
  rollover JSON, use the `CheckpointStore` directly.

## Execution

### Step 1 — Accept run_id

`run_id` is required. If missing, list the most recent rollover artifacts and
halt asking the operator to specify.

### Step 2 — Load and validate the handoff JSON

Read `ai-docs/rollover-<run_id>.json`. Confirm:

- File exists and parses.
- `schema_version == "1.0"`.
- Required keys present: `run_id`, `skill`, `completed_steps`, `open_decisions`,
  `invariants`, `next_action`, `checkpoint_ref`, `brief_path`.
- `run_id` inside the JSON matches the argument.

On failure, halt with a structured error. Do not attempt to repair the
artifact.

### Step 3 — Load the checkpoint

If `checkpoint_ref` is non-null, resolve it via `CheckpointStore.latest(run_id)`
(or by `step_id` if the ref encodes one). Restore that record's `data` as the
starting state for the resumed skill.

If `checkpoint_ref` is null, note it and proceed from the preflight state
encoded in `invariants`.

### Step 4 — Re-emit invariants

Print the invariants block verbatim from the JSON, so downstream agents see
the same locked values (profile, architecture style, test strategy, etc.)
that preflight established in the original session.

Print the brief inline (from `brief_path`) so the operator sees the state
before any agent call.

### Step 5 — Resolve open decisions

For each entry in `open_decisions`, halt and ask the operator:
- Accept current state as recorded.
- Override with a new value (record the override).
- Abort the resume.

Do not proceed past this step while decisions remain open.

### Step 6 — Confirm next action

Ask the operator to confirm the recorded `next_action`:
- `y` — proceed as recorded.
- `modify` — accept a replacement next action from the operator.
- `n` — abort cleanly; leave artifacts intact for inspection.

Do not proceed on silence.

### Step 7 — Hand control back

For `next_action.type`:
- `call_agent` — invoke the named agent via `cadre.runtime.call()` with the
  inputs reconstructed from the checkpoint.
- `open_gate` — open the named gate and wait for operator resolution.
- `run_command` — execute the named command under the active safety contract.

From this point the originating skill owns the run again. This skill exits.

## Result Contract

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts: []
  findings: []
  next_action: "handed back to <skill> at <next_action.target>"
```

## Failure Modes

- **Handoff JSON missing** — no prior `/rollover` for this run. Instruct to
  use `CheckpointStore` for partial recovery and halt.
- **Invariants conflict with repo state** — the repository drifted between
  rollover and resume. Halt with a structured conflict report. Do not force.
- **Checkpoint missing but JSON intact** — acceptable with reduced fidelity.
  Warn, confirm with operator, then proceed.

## Observability

Writes a single SEP entry with `phase: decide`, `agent_role: resume`,
`outcome: resume_accepted | resume_declined | resume_blocked` including the
resolved `run_id`, `brief_path`, `state_path`, and chosen `next_action`.
