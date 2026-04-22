# ADR 0003 — Rebrand to Cadre and Pivot to Agentic Orchestration

- Status: Accepted
- Date: 2026-04-21
- Deciders: Alexsander Vieira
- Supersedes aspects of: ADR 0001, ADR 0002 (positioning only; technical decisions stand)

## Context

This repository started under the name **Keel**, positioned as a "reliability backbone
for AI engineering agents" — a Python runtime exposing retry budgets, fallback matrix,
doom-loop detection, cost guardrails, checkpoint/resume, and a structured audit log
(SEP) to teams running agent pipelines in production.

After validating positioning against the real market (notably **Compozy**, a local-first
CLI orchestrator with 500+ GitHub stars, MIT, Go binary) and against the author's
real-world constraints (solo, technical, no network, averse to longform writing, no
plan to raise capital), two decisions fell out:

1. **The reliability-runtime-as-standalone-product positioning is too narrow for this
   author's distribution profile.** Reliability runtimes grow via technical writing
   (blog posts, conference talks, design-partner hunting) — channels the author has
   explicitly opted out of.

2. **The underlying assets (agent specs, skill orchestration, SEP log, retry/fallback
   policy, templates) are more valuable packaged as a Claude Code plugin than as a
   standalone runtime.** Claude Code's plugin marketplace solves distribution for a
   solo technical founder. Users discover plugins via `/plugin install`, not via
   conferences or blogs.

The brand name "Keel" was also flagged as too infrastructural — it anchors the
product to a narrow identity ("bottom of the ship, structural member") that does not
communicate the agentic, team-of-specialists value the product actually delivers.

## Decision

### 1. Rename the project from **Keel** to **Cadre**.

**Cadre** means "a small group of highly trained specialists forming the nucleus of a
larger organization." This captures the product's actual shape: a curated, coordinated
set of agent specialists (PM, tech lead, architect, backend dev, reviewer, QA, SRE,
etc.) operating as a single delivery team inside Claude Code.

Rationale for the name:
- Two syllables; pronounceable internationally; no trademark baggage unlike military
  references (Navy SEAL, Delta Force, etc.).
- Literal semantic match to what the product is, not a metaphor requiring explanation.
- Short enough to brand (`cadre.dev`, `@cadre/*` npm scope, `cadre-labs` GitHub org
  all available as of 2026-04-21).
- Works in both consumer ("a cadre of agents") and enterprise ("the Cadre platform")
  contexts.

### 2. Reposition as an **agentic delivery plugin for Claude Code**, not a standalone
   reliability runtime.

The Python runtime, SEP log, retry/fallback primitives, and contract schemas remain —
but they are now the **internal foundation** of a Claude Code plugin, not the
user-facing product surface. The user-facing surface is the plugin itself: skills,
agents, commands invoked from within Claude Code.

### 3. Shift orchestration model from **fixed pipeline** to **agentic**.

The current skill design (inherited from `claude-tech-squad`) expresses workflows as
pre-wired sequences in YAML: `pm → ba → po → planner → architect → techlead → ...`.
This is deterministic and easy to reason about, but it does not exploit what modern
coding assistants (Claude Code included) can do: reason about what to do next based
on context.

The new model allows:

- **Dynamic agent selection.** An orchestrator examines the task and decides which
  agents to invoke, in what order, and how many times. It may skip PM if the briefing
  is already technical; it may invoke architect twice if the first output is weak.
- **Agent-to-agent delegation.** Each agent can expose a `spawn_agent(role, task)`
  tool and call peer agents directly, rather than returning to a central dispatcher.
- **Self-correction loops.** A critic-reviewer agent automatically re-reads output
  from a producer agent and requests revisions until a quality threshold is met.
- **Adaptive retry.** Retry logic examines the failure mode and chooses an action
  appropriate to the cause (wait + retry, fall back to another provider, re-plan,
  escalate to a different agent, or halt with a clear blocker report).
- **Cross-run memory.** Decisions made in prior Cadre runs on the same repository
  persist in a lightweight markdown memory file, so the agent team does not
  re-litigate architectural choices each session.

Reliability primitives (retry budget, fallback matrix, doom-loop detection, cost
ceilings, SEP log) continue to apply — they wrap every model call, regardless of who
orchestrates it.

## Consequences

Positive:

- Distribution is unblocked. Claude Code's plugin ecosystem delivers users directly;
  the author does not need to build an audience through writing or outbound sales.
- The brand `Cadre` communicates the product's shape in one word, which reduces
  marketing copy burden for someone who self-identifies as weak at benefit-oriented
  writing.
- Reliability primitives already built (retry, fallback, SEP log, policy schema) are
  not discarded — they become the substrate of a more valuable product.
- Cross-run memory is a defensible moat: knowledge of *this* repository accumulates
  over time, which the big horizontal players (Devin, Cognition, Copilot Workspace)
  cannot replicate without operating inside each customer's codebase for months.

Negative:

- The rebrand cost itself is small but non-zero: docs, code, and policy files all
  referenced `Keel` and must be swept. Done in a single pass; see the commit that
  introduces this ADR.
- The narrower identity ("Claude Code plugin") binds the product to one ecosystem
  (Claude Code / Anthropic). If Claude Code's market share declines, Cadre's
  distribution narrows with it. Mitigated by keeping the runtime portable enough to
  surface behind another client later — the plugin manifest is the thin top layer.
- The "agentic" commitment is a technical bar the project must now meet. Fixed
  pipelines were simpler; agentic loops require disciplined prompt design, tool
  interfaces, and observability to not degenerate into doom loops. Mitigated by the
  existing reliability primitives, which were built for exactly this failure mode.

## Alternatives considered

- **Keep the Keel name and the reliability-runtime-as-product positioning.**
  Rejected after competitive analysis against Compozy and honest assessment of the
  author's distribution capability. The brand and positioning sit on a channel the
  author cannot staff (technical writing, public speaking, design-partner outreach).

- **Pivot to a vertical AI product (travel, media, legacy refactor).**
  Rejected: the author reports zero professional network in the target verticals and
  is not suited to the sales motion those products require.

- **Keep this work as a personal side-project without commercial intent.**
  Considered and rejected. The effort already invested is substantial; shaping it
  into a plugin with a plausible commercial tier preserves optionality at low
  incremental cost.

- **Fold this work back into `claude-tech-squad` and keep MIT.**
  Rejected: `claude-tech-squad` remains strategically valuable as a free, broad plugin
  that seeds awareness. Cadre is the reliability-first, agentic successor with its
  own commercial arc. Keeping them separate allows each to evolve on its own license
  and cadence.

## Follow-ups

- ADR 0004 — the concrete design of agentic orchestration: tool interfaces, spawn
  semantics, memory format, critic loops.
- ADR 0005 — the plugin manifest shape for Claude Code, and the mapping between
  `packages/skills/*` and plugin-exposed commands.
- README rewrite around the Cadre name and agentic positioning (done alongside this
  ADR).
- Legacy Keel references: all production docs, code, and config swept in the same
  commit. Historical artifacts (prior discovery docs, plan-v2, HANDOFF) preserved
  under `ai-docs/archive/keel-era/` for traceability.
