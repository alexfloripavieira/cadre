# ADR 0004 — Agentic Orchestration Design

- Status: Accepted
- Date: 2026-04-21
- Deciders: Alexsander Vieira
- Builds on: ADR 0003 (rebrand + agentic pivot)

## Context

ADR 0003 committed Cadre to an "agentic" orchestration model: instead of running
agents through pre-wired YAML pipelines (`pm → ba → po → planner → architect → ...`),
the system reasons about each task and decides, at runtime, which agents to invoke,
in what order, and when to re-plan.

This ADR answers the concrete design questions that commitment leaves open:

1. What exactly is an "agentic" skill, and how does it differ from a scripted skill?
2. How does the orchestrator decide what to run next?
3. What tools do agents expose to each other?
4. How does cross-run memory work?
5. When and how does the critic/review loop engage?
6. How do reliability primitives (retry, fallback, doom-loop, cost, SEP log) wrap
   the whole thing without re-implementing them at each layer?
7. What is the fallback when the agentic path fails or goes into a doom loop?

Getting this design wrong produces two failure modes both already observed in the
wild:

- **Fully emergent "just let the model figure it out"** — token-hungry, non-reproducible,
  prone to doom loops, and impossible to audit.
- **Fully scripted with a few if/else branches** — not actually agentic, just a YAML
  flowchart, defeats the positioning.

Cadre commits to a middle path: **planner-led emergent execution, reliability-wrapped,
audit-first.**

## Decision

### 1. Three levels of orchestration authority

Every Cadre skill runs at one of three authority levels, declared in its spec:

- **Level 1 — Scripted.** Fixed sequence, no dynamic choices. Used for simple,
  well-understood workflows (e.g. `/release`, `/dependency-check`). Identical to
  claude-tech-squad today.
- **Level 2 — Planned.** An orchestrator agent produces an execution plan before
  running. The plan is recorded (SEP log); execution follows the plan, but the plan
  may be re-issued if conditions change (failure, quality miss, budget breach). This
  is the default for most skills (`/implement`, `/bug-fix`, `/refactor`).
- **Level 3 — Emergent.** No upfront plan. An orchestrator agent decides each next
  step based on current state. Used sparingly, only for open-ended or exploratory
  tasks (`/discovery`, `/explore`). Budget caps and doom-loop detection carry most
  of the risk management at this level.

Declared as `authority_level: 1 | 2 | 3` in each skill's frontmatter.

### 2. Agent metadata schema (the "spec card")

Every agent under `packages/agents/*.md` must declare frontmatter that makes the
agent **selectable by a planner**:

```yaml
---
role: backend-architect
authority: advisor                 # advisor | producer | reviewer | executor
inputs_required:
  - product_scope
  - architecture_style
inputs_optional:
  - specialist_digests
outputs_produced:
  - backend_design_notes
invoke_when:
  - "task touches server-side behavior"
  - "api contracts change"
  - "database schema change"
avoid_when:
  - "pure frontend change"
  - "docs-only change"
cost_profile: medium               # low | medium | high
typical_duration_seconds: 120
requires_model_class: reasoning    # chat | reasoning | coding
policy_profile: default
---
```

The planner reads `invoke_when` / `avoid_when` / `inputs_required` to decide whether
this agent is a candidate for the current task. `authority` distinguishes agents
that *propose* (advisor/reviewer) from agents that *produce artifacts*
(producer/executor).

Agents without this frontmatter are still usable at Level 1, but the planner at
Level 2/3 will not route to them automatically.

### 3. Skill as intent declaration (Level 2/3)

A Level 2/3 skill no longer prescribes a linear sequence. Instead it declares:

```yaml
---
name: implement
authority_level: 2
intent: >
  Land a reviewable code change that satisfies the stated acceptance criteria,
  with tests and a passing CI pipeline.
preconditions:
  - "repository tests are currently green"
  - "acceptance criteria are stated"
success_criteria:
  - "all declared acceptance criteria verified by test"
  - "no regression in existing test suite"
  - "code review has no blocking findings"
candidate_agents:
  - product-manager
  - tech-lead
  - backend-architect
  - backend-developer
  - frontend-developer
  - test-planner
  - code-reviewer
required_agents:
  - code-reviewer
policy_profile: standard-delivery
max_budget_usd: 5.00
max_duration_seconds: 1800
---
```

`candidate_agents` is the pool. `required_agents` are non-negotiable (code-reviewer
is always in the loop for any `implement`). `policy_profile` selects the reliability
policy to apply (retry, fallback, doom-loop thresholds). `max_budget_usd` and
`max_duration_seconds` cap the entire run — the runtime enforces both.

### 4. Orchestrator protocol

The orchestrator is itself an agent, invoked first in Level 2/3 skills.

**Level 2 (Planned):**
1. Orchestrator reads the skill intent, candidate agents' spec cards, and the task
   briefing (commit, diff, user prompt, etc.).
2. Produces an **execution plan** as a structured artifact: ordered list of agent
   invocations, inputs to each, expected outputs, checkpoints.
3. Plan is written to SEP log *before execution* (`phase: plan`).
4. Runtime executes the plan step by step, calling each agent via the **reliability
   wrapper** (see section 7).
5. After each step, a lightweight "plan-is-still-valid" check runs. If the step
   produced a surprise (new blocker, unexpected artifact, quality miss), the
   orchestrator is re-invoked with the new state and produces a revised plan.
   Re-planning is budgeted — a hard cap on re-plans per run prevents oscillation.

**Level 3 (Emergent):**
1. Orchestrator runs in a loop: observe current state, pick next agent, invoke,
   observe, repeat.
2. No upfront plan. Each decision is logged as `phase: decide` in the SEP log.
3. Loop exits when: success criteria satisfied, budget exhausted, doom-loop
   detected, or orchestrator declares "no further productive action available."

Both levels produce identical SEP log structure; only the `phase` tags differ.

### 5. Agent-to-agent delegation (spawn interface)

Agents can request peer help without routing back to the orchestrator. Two surfaces:

**Explicit delegation tool.** Each agent's prompt exposes a `request_agent(role, task, context)`
tool. When called, the runtime:
1. Verifies `role` is in the current skill's `candidate_agents`.
2. Verifies the request does not blow the run budget.
3. Invokes the target agent, captures its output, returns it to the caller as tool
   output.
4. Logs the delegation in SEP log (`phase: delegate`).

**Implicit handoff.** An agent can declare in its output that its work is "complete,
next step is X" — the orchestrator picks this up on the next plan-validity check
and routes appropriately. This is softer than a direct spawn; it preserves planner
authority.

`request_agent` depth is capped (default 2 levels) to prevent fractal spawning.

### 6. Critic/review loop

High-stakes artifacts (code diffs, API contracts, migrations, security-sensitive
changes) automatically enter a critic loop before being accepted.

**Trigger:** artifact's producer agent declares `review_required: true` in its
output metadata, or the skill's policy profile requires review for this artifact
class.

**Loop:**
1. Reviewer agent (`code-reviewer`, `security-reviewer`, etc.) reads the artifact
   + the original intent.
2. Reviewer returns `status: approved` | `status: revision_requested` | `status: blocked`.
3. On `revision_requested`: producer is re-invoked with the reviewer's findings as
   input. Loop continues up to `max_review_cycles` (default 2).
4. On `blocked`: escalate to user with reviewer's explanation. Run halts.
5. On `approved`: proceed.

Review cycles count against the run budget. Doom-loop detection catches the case
where reviewer and producer oscillate without converging.

### 7. Reliability wrapper around every model call

Every call to a model — whether from the orchestrator, a candidate agent, a
reviewer, or a delegated spawn — flows through `cadre.runtime.call()`:

```python
response = cadre.runtime.call(
    run_id=run_id,
    agent_role=agent_role,
    phase=phase,                 # plan | execute | delegate | review | decide
    model=selected_model,
    messages=messages,
    policy=active_policy,        # resolved from skill + agent + default
)
```

This single entry point enforces:
- Retry budget (bounded retries per agent + per run).
- Fallback matrix (model swap on primary failure, per policy).
- Cost tracking against `max_budget_usd`.
- Doom-loop detection across consecutive attempts with matching failure signatures.
- Checkpoint write after every successful call.
- SEP log entry with tokens, latency, cost, provider chosen, fallback invoked.

Nothing in Cadre calls a provider SDK directly. This is the discipline that keeps
the agentic surface auditable — regardless of which agent or orchestrator level
triggers a call.

### 8. Cross-run memory

Cadre writes a lightweight markdown memory file per repository at
`.cadre/memory.md` (git-tracked or gitignored, user's choice — defaulted to
gitignored for privacy).

Format:

```markdown
# Cadre memory for <repo-name>

## Architecture decisions
- 2026-03-12 — Chose Redis over RabbitMQ for task queue. Reason: ...
- 2026-04-05 — Standardized on pytest over unittest. ...

## Known pitfalls
- Migration 0042 is not reversible — rollback requires data restore.
- Celery workers OOM above concurrency=8; do not increase.

## Recurrent skill outcomes
- /implement on auth module: historically requires 3 review cycles. Budget accordingly.
```

**Write triggers:**
- Successful plan-approval gates add entries under `Architecture decisions`.
- Failure postmortems (from `/incident-postmortem`) add entries under `Known pitfalls`.
- Skill completion writes an entry under `Recurrent skill outcomes` (skill name,
  duration, cost, cycles).

**Read triggers:**
- Every orchestrator invocation includes the relevant sections of memory as
  context (budget-aware; memory truncation is summarization, not naive cut).

**Size budget:** 16 KB / 200 lines default; auto-compaction when exceeded
(agent rewrites to denser form).

Memory is the *moat*: the longer Cadre operates on a repository, the more
repository-specific knowledge it accumulates, and the harder it becomes for a
generic horizontal player to match the quality without operating on that same
codebase.

### 9. Failure protocol and escalation

Any of the following conditions halts the current agentic path and considers
fallback:

- Retry budget exhausted on a single agent.
- Doom loop detected (same error, oscillating fix, growing diff) across ≥3
  consecutive attempts on the same step.
- `max_review_cycles` exceeded without convergence.
- `max_budget_usd` or `max_duration_seconds` breached.
- Orchestrator returns `status: blocked` with no path forward.

**Fallback order:**
1. **Downgrade to Level 1 (scripted).** If a scripted fallback variant of the
   skill exists (`<skill>.scripted.md`), run it. This is the "known-safe" path.
2. **Escalate to user.** Emit SEP log entry `phase: escalate` with full context,
   expose it in Claude Code output, and halt. User decides next move.

Fallback never retries the agentic path automatically — repeated agentic failure
with the same inputs is not productive.

### 10. SEP log extensions for agentic runs

The existing SEP log schema is extended with four new `phase` values:

- `plan` — orchestrator emitted an execution plan (Level 2).
- `decide` — orchestrator chose a next step (Level 3).
- `delegate` — agent invoked a peer via `request_agent`.
- `review` — critic loop cycle.

Each entry carries `parent_phase_id` so the SEP log reconstructs the full agentic
tree, not just a linear sequence.

## Consequences

Positive:

- Skills become declarative ("what should be achieved") instead of imperative ("do
  these 12 steps"). Less brittle to small task variations.
- Agents become composable; authoring a new agent adds capability without editing
  every skill.
- Cross-run memory creates a defensible moat that is not easily copied by any
  horizontal player.
- Reliability primitives apply uniformly. No agentic path can sneak past the retry
  budget or cost ceiling.
- Three authority levels let the author choose complexity per skill — scripted
  stays simple, emergent is available when needed.

Negative:

- The orchestrator itself is now a dependency. A weak orchestrator degrades every
  Level 2/3 skill. Mitigated by: (a) allowing policy to force scripted fallback,
  (b) keeping orchestrator prompts and tool interfaces minimal and auditable,
  (c) versioning orchestrator prompts so regressions are tracked.
- Non-determinism increases. Two runs of the same skill on the same inputs may
  follow different paths. Mitigated by: (a) recording plan artifacts in SEP log
  for reproducibility investigations, (b) deterministic mode for test runs
  (pinned model temperature, fixed random seed where applicable).
- Costs rise vs scripted: orchestrator itself consumes tokens per run, and
  re-planning adds more. Mitigated by `max_budget_usd` cap and by keeping
  orchestrator prompts short.
- Debugging a failed run now requires reading the plan + decision log + delegation
  tree, not a linear trace. The SEP log schema extension addresses this, but
  tooling (pretty printer, timeline view) must exist from day one.

## Alternatives considered

- **Fully emergent, single-level, no planner.** Rejected: too non-deterministic,
  token-hungry, doom-loop prone. Would produce impressive demos and unreliable
  production behavior.
- **Single agentic framework (e.g. AutoGen, CrewAI).** Rejected: inherits their
  orchestration model, ties Cadre to their runtime, and gives up the reliability
  primitives Cadre already has. Not worth the coupling.
- **Keep everything scripted, simulate "agentic" via bigger YAML trees.**
  Rejected: at that point the positioning is honest marketing, not honest
  engineering. If a user compares a claude-tech-squad skill tree with a "Cadre
  agentic" skill tree and they differ only in ceremony, the rebrand is a lie.
- **Multi-orchestrator / hierarchical orchestrators (meta-orchestrator that picks
  sub-orchestrators).** Rejected for MVP as over-engineering. Two levels of
  authority (orchestrator + agent) are enough for the skills shipped in v0.1.
  Revisit only if a skill genuinely requires three or more levels.

## Implementation sequence

This ADR is a contract, not an implementation. Next steps, in order:

1. Extend the agent spec frontmatter schema in `packages/agents/` with the new
   metadata fields. Update the 4 existing agents.
2. Introduce `authority_level` to skill frontmatter. Classify existing skills.
3. Author the orchestrator agent (`packages/agents/orchestrator.md`) with its
   tool interface (`propose_plan`, `request_agent`, `emit_decision`).
4. Extend `cadre.runtime.call()` to accept `phase` and route SEP log accordingly.
5. Implement `request_agent` tool in the runtime.
6. Build the critic loop wrapper.
7. Ship first agentic skill conversion — probably `/implement` as the highest-value
   target with a clear success criterion (code merges, tests green).
8. Golden-run suite against the first agentic skill.
9. ADR 0005 — plugin manifest shape for Claude Code distribution.

Each step is ADR-gated where it introduces new contract surface (points 1, 3, 5, 9);
the rest are implementation.

## Follow-ups

- ADR 0005 — plugin manifest for Claude Code.
- ADR 0006 — orchestrator prompt versioning and regression strategy.
- ADR 0007 — memory privacy model (what never leaves the machine, what syncs to
  managed cloud once that exists).
