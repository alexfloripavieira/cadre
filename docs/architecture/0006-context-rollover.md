# ADR 0006 — Context Window Management and Orchestrator Model Class

- Status: Accepted
- Date: 2026-04-22
- Deciders: Alexsander Vieira
- Builds on: ADR 0002 (multi-provider), ADR 0004 (agentic orchestration)
- Amends: ADR 0004 — downgrades the `orchestrator` agent's declared model class
  for summarization-shaped duties

## Context

Long runs orchestrated by Cadre's `Runtime.call` accumulate messages across many
agent turns. Past roughly 100k cumulative input tokens, Claude Code (and every
other frontier model Cadre supports via LiteLLM) exhibits measurable quality
degradation on recall-heavy tasks. Past 140k, degradation becomes severe and
native compaction fires unpredictably.

Three concrete failure modes follow from doing nothing:

1. **Silent quality decay** — agents produce lower-fidelity output near the
   limit without the operator or SEP log showing the cause.
2. **Unstructured compaction** — Claude Code's native compaction drops content
   opaquely, and the SEP log loses provenance of what was summarised.
3. **Work loss on resume** — without a structured handoff, a `/clear`,
   session crash, or context window refresh makes checkpoint state hard to
   re-enter with fidelity.

Cadre already has the pieces to solve this cleanly:

- `Runtime.call` emits a per-attempt SEP log and owns retry budget, cost
  ceiling, and doom-loop detection.
- `CheckpointStore` persists arbitrary JSON state per `run_id` and survives
  process restarts.
- `PolicyLoader` resolves named profiles from `runtime-policy.yaml`.

Missing: a token-accounting axis, a summarizer agent, and a skill that closes
the loop by resuming from a handoff artifact.

Separately, ADR 0004 declared the `orchestrator` agent with
`model_class: reasoning` (aspirational, for v0.1.5 tool-use routing). For the
narrow case of context consolidation the orchestrator is asked to perform
summarization, not reasoning. Using a reasoning-class model here is waste.

## Decision

Introduce context rollover as a first-class runtime concern, composed of four
layers that follow Cadre's invisible-by-default posture while remaining
overridable by operators.

### 1. Token-accounting axis in `Runtime.call`

Extend the per-run ledger (today holds cost) to also hold approximate token
usage, summed across attempts of the same `run_id`. On every `call`:

- Read `usage.prompt_tokens` and `usage.completion_tokens` from the provider
  response when available; fall back to `tiktoken`-style estimation from the
  input messages plus response text.
- After updating the ledger, compare cumulative tokens against the active
  policy's `context_window.advisory_threshold_tokens` and
  `context_window.hard_threshold_tokens`.
- Emit corresponding SEP log events: `context_advisory` at soft, and
  `context_rollover_suggested` at hard. Never block; `Runtime.call` stays
  non-interactive.

### 2. `context-summarizer` agent (chat-class)

A new agent defined under `plugins/cadre/agents/context-summarizer.md`, with:

- `authority: advisor`
- `cost: low`
- `model_class: chat`
- Role: produce a two-artifact handoff from the run's SEP log and checkpoint:
  - `ai-docs/rollover-<run_id>.md` — narrative brief for humans (≤ 2000
    tokens).
  - `ai-docs/rollover-<run_id>.json` — structured handoff (schema v1.0) for
    the resume skill.

The summarizer is invoked by the `/rollover` skill and by the PreCompact
hook. It does not make routing decisions; it consolidates.

### 3. `/rollover` and `/resume` skills

- `/rollover` — operator-invokable or hook-triggered. Runs the summarizer,
  validates artifacts, writes a `rollover-pending` checkpoint cursor, exits
  with instructions.
- `/resume` — reads the JSON handoff plus the checkpoint, reconstructs the
  working memory, emits the locked invariants, confirms the next action with
  the operator, and hands control back to the originating skill.

### 4. Claude Code PreCompact hook

Ship a `plugins/cadre/hooks/pre-compact.sh` that Claude Code invokes before
native compaction. The hook calls `/rollover` on the active `run_id`, and
Claude Code uses the produced summary as the compacted context. This path
is invisible to the operator when it succeeds.

Fallback when PreCompact is unavailable or the hook fails: `/rollover`
remains operator-invokable and writes `NEXT_ACTION.md` in the run directory
with the resume command. Operator runs `/clear` + `/resume <run_id>` manually.

### Orchestrator model class downgrade

ADR 0004 ships `orchestrator` as `model_class: reasoning`. Amend that
declaration for summarization-shaped duties (route planning and critic loop
remain `reasoning`).

Concretely: the `orchestrator` spec card gains a `sub_tasks` block declaring
`context_consolidation: chat`. `Runtime.call` uses the sub-task binding when
the skill requests a consolidation phase, and falls back to the top-level
`model_class` otherwise.

Preferred models for the summarizer and any consolidation sub-task:

1. `anthropic/claude-haiku-4-5`
2. `groq/llama-3.3-70b-versatile` (preferred on free-tier profile)
3. `openai/gpt-4o-mini` (fallback)

## Thresholds

| Threshold | Action |
|-----------|--------|
| 100k cumulative input tokens | emit `context_advisory` event; run continues |
| 140k cumulative input tokens | emit `context_rollover_suggested`; PreCompact hook (if registered) runs `/rollover` automatically |

Thresholds configurable per profile under `runtime-policy.yaml`:

```yaml
<profile>:
  context_window:
    advisory_threshold_tokens: 100000
    hard_threshold_tokens: 140000
    summarizer_model: claude-haiku-4-5
    summarizer_model_class: chat
    rollover_skill: rollover
    resume_skill: resume
```

Defaults live in the `standard-delivery` profile. `free-tier` substitutes
Groq Llama 3.3 70B as the summarizer.

## Handoff artifact schema

`ai-docs/rollover-<run_id>.json`:

```json
{
  "schema_version": "1.0",
  "run_id": "string",
  "skill": "string",
  "rollover_reason": "operator_requested | hard_threshold | precompact_hook",
  "timestamp_utc": "ISO-8601",
  "tokens_used_approx": 0,
  "phase_at_rollover": "string",
  "completed_steps": [
    {"name": "string", "outcome": "string", "artifacts": ["path"]}
  ],
  "open_decisions": [
    {"id": "string", "description": "string", "owner": "operator|agent"}
  ],
  "pending_steps": [
    {"name": "string", "blocked_by": ["decision-id"]}
  ],
  "invariants": {
    "profile": "string",
    "architecture_style": "string",
    "test_strategy": "string"
  },
  "next_action": {
    "type": "call_agent | open_gate | run_command",
    "target": "string"
  },
  "checkpoint_ref": "string or null",
  "brief_path": "ai-docs/rollover-<run_id>.md"
}
```

Schema version is explicit so the resume skill can reject unknown majors.

## Consequences

### Positive
- Token saturation moves from invisible event to structured SEP log entry.
- Existing `CheckpointStore` gains a primary use case (resume, not just save).
- Rollover cost is bounded (~$0.01 at Haiku pricing for a 100k-token input
  compressed to a 2k-token brief). Declared as
  `cost_budget_usd_per_rollover: 0.10` in policy; anything above is a
  misconfiguration signal.
- Invisible happy path via PreCompact — operator sees no ritual when the hook
  works. Degraded path (`/rollover` + `/clear` + `/resume`) is explicit and
  auditable.
- Orchestrator cost drops substantially for summarization sub-tasks.

### Negative
- Token accounting is approximate. LiteLLM `usage` fields are authoritative
  when present but not every provider fills them consistently; estimation
  fallback introduces drift. Documented, not solved.
- The PreCompact hook depends on Claude Code runtime behavior that may evolve.
  The fallback path protects us from version skew but complicates docs.
- Introduces a new agent class (advisor, chat-tier) that requires test
  coverage in `services/runtime/tests/`.

### Neutral
- No change to the provider interface. Summarizer uses the same
  `ProviderCallable` protocol as every other agent.
- No change to `CheckpointStore` schema. Handoff JSON is a separate artifact,
  referenced by `checkpoint_ref`.

## Alternatives considered

**A. Mechanical token counter with hard cutoff only, no summarizer.**
Rejected: produces a stop event but no resume path. Operator loses state.

**B. Full automatic rollover in `Runtime.call` without hooks or skills.**
Rejected: `Runtime.call` is non-interactive by design. Triggering a
multi-step consolidation from inside a single call conflates concerns and
breaks retry semantics.

**C. Per-agent token budgets, no global ledger.**
Rejected as sole mechanism: the problem is cumulative, not per-call.
Per-agent budgets remain complementary and already exist via
`Policy.max_budget_usd`.

**D. Reasoning-class summarizer.**
Rejected: summarization is structured extraction, not reasoning. No measurable
quality lift from Opus over Haiku on this workload, at 20x cost.

**E. Aggressive thresholds (60k / 90k).**
Rejected: forces rollover during single-skill runs that legitimately need
~80k to complete. Reduces operator trust in the threshold.

## References

- ADR 0002 — multi-provider LLM strategy
- ADR 0004 — agentic orchestration (amended for orchestrator sub-task model
  class)
- `services/runtime/cadre/runtime.py` — `Runtime.call` and the ledger
- `services/runtime/cadre/checkpoint.py` — `CheckpointStore`
- `plugins/cadre/runtime-policy.yaml` — profile definitions
- sibling project `claude-tech-squad`, ADR 0001 — gate-based rollover model,
  reference for the human-in-the-loop variant

## Follow-ups

- Implementation sequence (tracked as separate commits):
  1. This ADR.
  2. `context-summarizer` spec card.
  3. Token ledger and threshold events in `Runtime.call`.
  4. `/rollover` skill (baseline, operator-invokable).
  5. PreCompact hook template under `plugins/cadre/hooks/`.
  6. `/resume` skill reading handoff JSON plus checkpoint.
  7. Runtime tests with fake provider covering soft-event, hard-event, and
     resume round-trip.
- Thresholds will be revisited after the first 20 real rollovers logged under
  `ai-docs/` in golden runs.
- A future ADR 0007 will document the orchestrator sub-task binding when it
  grows beyond the single `context_consolidation` entry.
