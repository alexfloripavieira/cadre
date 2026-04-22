# Cadre v0.1 — Discovery Blueprint

- Date: 2026-04-22
- Owner: Alexsander Vieira
- Status: Pre-implementation
- Depends on ADRs: 0001 (monorepo), 0002 (multi-provider), 0003 (rebrand + pivot), 0004 (agentic orchestration)

---

## 1. Product Definition (v0.1 scope)

Cadre v0.1 is an **agentic delivery plugin for Claude Code** that ships as a
single installable plugin, provides a curated set of delivery agents, and
implements the Level 2 (planned) agentic orchestration model from ADR 0004.

Explicit non-goals for v0.1:
- Level 3 (fully emergent) orchestration — deferred to v0.2.
- Managed cloud control plane — deferred to Beta.
- Web dashboard, hosted SEP log viewer — deferred.
- Multi-tenant / SSO / enterprise features — deferred.
- Premium connectors (Jira, Linear, Slack, Datadog) — deferred.

## 2. What ships in v0.1 (in / out)

### In

**Plugin package (distributable via Claude Code plugin marketplace):**
- 1 runtime backbone (`services/runtime/cadre/`) — Python, implements the reliability wrapper, policy loader, SEP log writer, checkpoint store.
- 3 skills (Level 2, planned agentic):
  - `/implement` — land a reviewable code change against acceptance criteria.
  - `/bug-fix` — root-cause + fix + test + PR-ready diff.
  - `/review` — produce a structured review of a PR branch or diff.
- 1 skill (Level 1, scripted — kept as safety fallback):
  - `/release` — version bump, changelog, tag. No agentic ceremony.
- ~8 agents with the ADR 0004 spec-card frontmatter:
  - `orchestrator`, `product-manager`, `tech-lead`, `backend-developer`, `frontend-developer`, `test-planner`, `code-reviewer`, `security-reviewer`.
- 1 policy profile: `standard-delivery` (retry budget, fallback matrix, doom-loop patterns, cost ceiling $5/run, max review cycles = 2).
- Cross-run memory at `.cadre/memory.md` (auto-created per repo, gitignored by default).
- SEP log written to `ai-docs/.cadre-log/` with YAML frontmatter extended per ADR 0004 (plan, decide, delegate, review phases).

**CLI (optional, for dogfooding and debugging):**
- `cadre log <run-id> --format pretty` — reads SEP log, prints timeline.
- `cadre log <run-id> --format tree` — renders delegation tree.
- `cadre policy validate` — verifies policy file parses and schema is valid.

**Docs:**
- README (shipped, done).
- ADRs 0001–0005 (0005 pending, added in v0.1 for plugin manifest).
- `docs/SKILL-CONTRACT.md`, `docs/AGENT-CONTRACT.md` (inherited from claude-tech-squad, updated for Level 2 agentic).
- `docs/GETTING-STARTED.md` updated for Cadre install + first run.

### Out

- Levels 3 (emergent) orchestration.
- More than 4 skills.
- More than ~8 agents.
- Premium connectors.
- Managed cloud / web dashboard.
- Any feature requiring enterprise auth.

## 3. Release Gates (v0.1 = tagged v0.1.0 when all pass)

1. `/implement` runs end-to-end against a synthetic fixture repo, produces a PR-ready diff, all claimed acceptance criteria verified by generated tests.
2. `/bug-fix` reproduces bug via test, applies fix, generated test passes, regression suite green.
3. `/review` produces a structured review on a known-bad PR fixture and flags ≥80% of the planted issues.
4. `/release` (scripted fallback) cuts a tag and updates changelog deterministically.
5. Retry budget enforced: injected provider error is retried per policy, then surfaced.
6. Fallback matrix: primary provider forced to fail → secondary takes the call → SEP log records the fallback.
7. Doom-loop detection: synthetic oscillating-fix scenario halts within the configured pattern window.
8. Cost ceiling: runaway test scenario halts within 10% of declared `max_budget_usd`.
9. Checkpoint/resume: SIGKILL mid-run, `cadre resume <run-id>` completes from last checkpoint.
10. SEP log: every release-gate run produces a parseable log with all required phases.
11. Plugin installs cleanly in a fresh Claude Code workspace with `/plugin install alexfloripavieira/cadre`.
12. CI green on Python 3.11 and 3.12.
13. First-run docs: a new user installs the plugin and completes `/implement` on the reference fixture repo in under 15 minutes.

## 4. Technical architecture (recap of ADRs)

Not expanded here — see ADRs 0001–0004. One-line summary per decision:

- Monorepo with `services/` (code) + `packages/` (contracts). Python runtime MVP.
- LiteLLM as the single provider-agnostic client.
- Rebranded from Keel; positioned as Claude Code plugin, not standalone runtime.
- Three authority levels (scripted, planned, emergent); v0.1 ships Levels 1 and 2.

## 5. Implementation sequence (the 30-day plan)

### Week 1 — Contracts and spec cards

1. Extend `packages/agents/*.md` frontmatter with the spec-card schema from ADR 0004. Retrofit the 4 existing agents (`prd-author`, `inception-author`, `tasks-planner`, `work-item-mapper`).
2. Author 4 new agents: `orchestrator`, `backend-developer`, `frontend-developer`, `security-reviewer`. Copy shape from existing agents in claude-tech-squad where appropriate, add spec cards.
3. Extend skill frontmatter schema with `authority_level`, `intent`, `candidate_agents`, `required_agents`, `max_budget_usd`, `max_duration_seconds`.
4. Write `packages/skills/implement/SKILL.md` at Level 2. Declare candidates: pm, tech-lead, backend-dev, frontend-dev, test-planner, code-reviewer.
5. ADR 0005 — plugin manifest shape (Claude Code plugin contract).

### Week 2 — Runtime core

6. Implement `cadre.runtime.call()` with retry budget + SEP log write. One provider only (Anthropic).
7. Implement policy loader — reads `runtime-policy.yaml`, resolves skill × agent × default.
8. Implement checkpoint store (SQLite).
9. Implement SEP log writer with all 4 new phase types (plan, decide, delegate, review).
10. First integration test: synthetic call through `runtime.call()` writes SEP log + checkpoint.

### Week 3 — Orchestrator and agentic loop

11. Implement orchestrator agent prompt + tool interface (`propose_plan`, `request_agent`).
12. Wire plan-validity checker (runs after each step, decides re-plan vs advance).
13. Wire `request_agent` delegation tool with depth cap.
14. Wire critic/review loop with `max_review_cycles` enforcement.
15. First end-to-end run: `/implement` on the reference fixture repo, Anthropic-only, no fallback yet.

### Week 4 — Reliability primitives, polish, release candidate

16. Fallback matrix implementation; test with forced provider failure.
17. Doom-loop detection — 3 patterns wired.
18. Cost ceiling enforcement.
19. Cross-run memory read/write with auto-compaction.
20. Second skill (`/bug-fix`) wired, gate 2 passes.
21. Third skill (`/review`) wired, gate 3 passes.
22. `/release` scripted skill, gate 4 passes.
23. Plugin manifest finalized per ADR 0005; `plugin.json` (or equivalent) committed.
24. Tag `v0.1.0-rc1`.

### Week 5-6 (buffer) — Fixes, hardening, docs

25. Fix whatever broke during gate testing.
26. README + GETTING-STARTED polished.
27. Record one 60-second demo GIF of `/implement` end-to-end.
28. Tag `v0.1.0`.

This timeline is aggressive for a solo effort. Mitigation: Levels 3 deferred to v0.2 saves roughly 30% of complexity, and the claude-tech-squad heritage (agents, templates, policy schema) means Week 1 is retrofit work, not greenfield design.

## 6. Test Strategy (novel content — agentic is hard to test)

Agentic skills are non-deterministic by design. Testing needs to separate what's deterministic from what's stochastic.

### Deterministic layer tests (unit / integration)

- Policy loader: given YAML input, produces expected resolved policy.
- `runtime.call()` dry-run: given a canned LLM response, writes the correct SEP log entry.
- Retry budget: given X injected failures, call() retries exactly per policy.
- Fallback matrix: given primary failure, call() hits secondary per config.
- Checkpoint: write → read → same state.
- Doom-loop detection: given handcrafted sequence of responses, halts on pattern match.
- Cost ceiling: given priced responses, halts at declared threshold.
- SEP log writer: schema valid, frontmatter parseable, phase tree reconstructable.

These live in `services/runtime/tests/` and run on every CI.

### Orchestration layer tests (replay)

- Record golden runs: run `/implement` on the reference fixture with deterministic seed / fixed prompts, save SEP log + all LLM interactions (prompts + responses).
- Replay: re-run with the same inputs, compare SEP log structure (not exact text — structural match: same phases, same agent sequence, same outputs produced).
- Regression: if the replay diverges structurally, CI fails and operator decides if it's an improvement or a regression.

This replay suite is the primary regression net for agentic skills. Costs tokens on first record, near-zero on subsequent replays (cached LLM interactions).

### End-to-end smoke tests

- Install plugin in a fresh Claude Code workspace (ephemeral Docker).
- Run `/implement` on the reference fixture.
- Assert: PR-ready diff exists, tests pass, SEP log written, cost under budget.

These run nightly, not per-commit. Token cost is the reason.

### Chaos tests

- Inject provider 500 errors at random points; assert retry + fallback behave.
- Inject timeouts; assert retry budget + escalation.
- Inject SIGKILL mid-run; assert `cadre resume` completes.

Budget: these run weekly in CI with a small chaos token budget.

## 7. Risks specific to v0.1

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Orchestrator prompt regresses when Claude model updates | High | High | Versioned orchestrator prompts; replay suite catches regressions; pin model version in release policy |
| Agentic skills exceed budget on real repos (not fixtures) | Medium | High | Hard cost ceiling ($5/run default, tunable); cost analytics in SEP log to calibrate |
| Token cost of building + testing Cadre exceeds author's budget | Medium | High | Local models (Ollama) for dev runs; real providers only for gate tests |
| Plugin manifest contract (Claude Code side) changes mid-build | Low | High | Track Claude Code plugin API docs; ADR 0005 pins the contract we target; fallback to static definition file |
| Users expect Level 3 (emergent) on day 1 and are disappointed by Level 2 | Medium | Medium | Clear docs that v0.1 ships Level 2 only; roadmap published for v0.2 Level 3 |
| Memory file (`.cadre/memory.md`) leaks sensitive info in multi-dev repos | Medium | High | Gitignored by default; clear docs on opt-in git-tracking; security-reviewer agent runs against memory writes |
| Replay test suite grows unmaintainably | Medium | Medium | Cap at 10 golden runs in v0.1; prune aggressively |
| `/implement` misunderstands non-trivial user intent in 50%+ of cases | High | High | Accept that v0.1 is for "structured tasks with clear acceptance criteria"; explicitly out-of-scope: vague or open-ended intents |
| Solo-maintainer bus factor | High | High | Public repo from day 1; extensive docs (ADRs, contracts); SEP log semantics fully documented so someone else can pick up the project |

## 8. Open questions to resolve before starting

### Tier 1 — block implementation

1. **Plugin manifest shape for Claude Code.** Is it JSON, YAML, or markdown with frontmatter? Where does it live? What fields are required? → Research before Week 1 ends; output is ADR 0005.
2. **Orchestrator model choice.** Does the orchestrator need the same reasoning tier as producer agents, or a smaller/faster model? → Default to `claude-sonnet` for orchestrator; `claude-opus` for producers; validate during Week 3.
3. **Memory privacy posture.** Default gitignored vs default tracked? → Gitignored. Document opt-in for teams that want shared memory.

### Tier 2 — non-blocking, can defer

4. **Fixture repo for gate tests.** Which stack? Node? Python? Simple library with tests? → Python single-package library. Keep it boring.
5. **Release cadence.** Weekly? Biweekly? → Biweekly for v0.1 series.
6. **Licensing for community-contributed agents.** Inherited BSL 1.1, or carve out MIT for agent specs? → BSL 1.1, same as rest.

### Tier 3 — philosophy, revisit at Beta

7. **Telemetry.** Opt-in anonymous usage telemetry or never? → Defer to Beta.
8. **Managed cloud boundary.** What exactly moves to cloud vs stays local? → Defer until v0.2 data exists.

## 9. Immediate next actions (this week)

In order, smallest first:

1. **Extend spec-card frontmatter** on the 4 existing agents (`packages/agents/*.md`). ~30 min.
2. **Add `authority_level` + intent declaration fields** to the existing `packages/skills/inception/SKILL.md`. Classify as Level 2. ~30 min.
3. **Author `orchestrator` agent** with tool interface stubs. ~1 h.
4. **Research + write ADR 0005 (plugin manifest)**. ~2 h research + drafting.
5. **First code: `cadre.runtime.call()` skeleton** with retry budget only, SEP log write. ~3 h.
6. **First test passes:** `test_call_writes_sep_log.py` green.

That's roughly one week of focused work. After that, Week 2–4 sequence from Section 5.

## 10. Success criteria for the author (not the product)

This blueprint is worth writing only if it produces these outcomes:

- Decisions locked — no more weekly pivots on positioning or scope.
- Execution unblocked — next action is always knowable from the current state + this doc + ADRs.
- Honest risk sheet — no surprises that were foreseeable at plan time.
- Exit on failure — by day 45, if `/implement` is not running end-to-end on the fixture, reassess scope before continuing. Don't grind.

If any of these break, stop and reopen the blueprint before writing more code.
