# Changelog

All notable changes to Cadre are recorded here. Format follows Keep a
Changelog. Version numbers follow semver-ish (pre-1.0 may introduce
breaking changes in minor versions; see `CONTRIBUTING.md`).

## [Unreleased]

### Added
- Docs pass: `README.md` (root) polish, `docs/GETTING-STARTED.md`,
  `docs/MANUAL.md`, `docs/ARCHITECTURE.md`, `docs/API.md`,
  `docs/AGENT-CONTRACT.md`, `docs/SKILL-CONTRACT.md`.
- `CONTRIBUTING.md` at the repo root.
- This `CHANGELOG.md`.

### Changed
- Legacy docs from claude-tech-squad era moved to
  `docs/archive/legacy-claude-tech-squad/` to reduce noise for new
  contributors.

## [0.1.0-alpha] — 2026-04-22 (internal)

First buildable alpha. Not publicly tagged yet; tracked here for
internal reference. All work lands on `main` during the pre-1.0 period.

### Added

**Plugin surface (`plugins/cadre/`):**
- `.claude-plugin/marketplace.json` and `plugins/cadre/.claude-plugin/plugin.json`
  per Claude Code plugin layout (ADR 0005).
- 8 agents with full ADR 0004 spec cards: prd-author, inception-author,
  tasks-planner, work-item-mapper, orchestrator, code-reviewer,
  test-planner, security-reviewer.
- 4 skills: `/inception` (Level 2), `/implement` (Level 2), `/bug-fix`
  (Level 2), `/review` (Level 2).
- `runtime-policy.yaml` with 5 profiles: default, orchestrator,
  standard-delivery, low-cost, free-tier.
- Templates: prd-template, techspec-template, tasks-template,
  task-template.

**Python runtime (`services/runtime/cadre/`):**
- `Runtime.call()` with retry budget, exponential backoff, provider
  injection, clock and sleep injection, per-run budget ledger, auto
  step counter.
- Multi-provider **fallback matrix**: primary + fallback chain from
  policy; transition entries in SEP log.
- **Doom-loop detection** via `policy.doom_loop_same_error_threshold`;
  tracks consecutive error signatures within each model; halts and
  advances to fallback, or raises `DoomLoopDetected` if exhausted.
- **Cost ceiling** via `policy.max_budget_usd`; `CostCeilingExceeded`
  pre-check before each attempt; `runtime.budget_used(run_id)` and
  `reset_run(run_id)`.
- **SEP log writer** with YAML frontmatter, one document per attempt,
  extended phases (plan, execute, delegate, review, decide).
- **Checkpoint store** backed by SQLite; auto-write after every
  successful call when attached.
- `PolicyLoader` that reads `policies:` section from YAML and resolves
  profiles to `Policy` dataclasses.
- `SkillRunner` that loads a skill, builds an agent roster, calls a
  planner, executes steps through `Runtime.call`, aggregates cost, and
  returns a `SkillRunResult`.
- `AgentRegistry`, `load_agent_spec`, `load_skill_spec` for contract
  parsing.
- Cost estimators: `litellm_cost_estimator` (delegates to
  `litellm.completion_cost`), `PricedCostEstimator` (deterministic).
- Complete error hierarchy under `cadre.errors`.

**Infrastructure:**
- `.github/workflows/ci.yml` — Python 3.11 and 3.12 matrix, ruff check
  + format, pytest, plugin manifest validation, agent + skill
  frontmatter validation, shellcheck.
- Docker Compose local dev stack (postgres, redis, runtime) —
  scaffolded for future use; not required by v0.1.
- `scripts/smoke-run.py` — end-to-end run of the inception skill
  against any LiteLLM-supported provider.

**Tests:**
- 77 tests pass across policy, policy_loader, sep_log, checkpoint,
  runtime (including retry, fallback, doom-loop, cost ceiling,
  checkpoint integration), cost_estimators, specs, skill_runner.

**ADR series:**
- ADR 0001 — Monorepo layout (amended by ADR 0005).
- ADR 0002 — Multi-provider LLM via LiteLLM.
- ADR 0003 — Rebrand from Keel to Cadre and agentic pivot.
- ADR 0004 — Agentic orchestration design (authority levels, spec
  cards, orchestrator protocol, critic loop, memory).
- ADR 0005 — Plugin manifest and repository layout for Claude Code.

### Non-goals in this alpha

- Level 3 (emergent) orchestration — deferred to v0.2.
- Managed cloud control plane — deferred to Beta.
- Web dashboard / hosted SEP log viewer — deferred.
- Premium connectors (Jira, Linear, Slack, Datadog) — deferred.
- Multi-tenant auth / SSO / enterprise — deferred.
- Git staging / auto-commit — skills plan and review; they do not yet
  stage diffs (v0.2).
- Resume-from-checkpoint semantics in Runtime — store is written and
  readable; automatic resume ships in v0.2.

### Known limitations

- Default planner is deterministic (`required_order_planner` executes
  `required_agents` in declaration order). Full LLM-driven planning via
  orchestrator tool use ships in v0.1.5.
- `max_duration_seconds` is declared but not enforced in v0.1.
- Cost estimation for providers without LiteLLM pricing support returns
  0.0 silently; check `SEP log` entries to verify cost tracking matches
  expectations.
- Secret management assumes env-var credentials; no keyring or vault
  integration.

## [pre-history]

Repository started under the name **Keel**, positioned as a standalone
reliability runtime. After competitive analysis against Compozy and an
honest assessment of distribution constraints for a solo founder, the
project was rebranded to **Cadre** and repositioned as a Claude Code
plugin (ADR 0003). Artifacts from the Keel era are preserved under
`ai-docs/archive/keel-era/` for traceability.

Cadre inherits its agent contracts, skill patterns, templates, and
policy schema from `claude-tech-squad`, which remains a free, open-
source Claude Code plugin at https://github.com/alexfloripavieira/claude-tech-squad.
