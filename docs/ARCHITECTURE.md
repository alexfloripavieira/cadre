# Cadre Architecture

This is the system-level view. For formal decisions, see
`docs/architecture/0001-*.md` through `0005-*.md` (the ADR series). For
runtime API reference, see `docs/API.md`. For operational manual, see
`docs/MANUAL.md`.

## High-level system

```
User
 │
 ├── Claude Code CLI
 │     │
 │     └── /plugin install alexfloripavieira/cadre
 │           │
 │           ▼
 │     plugins/cadre/  ◄─── loaded by Claude Code
 │       .claude-plugin/plugin.json
 │       agents/*.md                  (8 agents with ADR 0004 spec cards)
 │       skills/*/SKILL.md            (4 skills, Level 1 and 2)
 │       templates/*.md               (PRD, TechSpec, Tasks)
 │       runtime-policy.yaml          (retry, fallback, budgets, profiles)
 │
 ├── Python embedding (optional)
 │     │
 │     └── import cadre
 │           │
 │           ▼
 │     services/runtime/cadre/  ◄─── reliability runtime
 │       Runtime.call()                (retry, fallback, cost, doom-loop)
 │       SkillRunner                   (plan → execute → outcome)
 │       PolicyLoader                  (YAML profile → Policy)
 │       AgentRegistry                 (load spec cards from disk)
 │       CheckpointStore               (SQLite, resume semantics)
 │       SEPLogger                     (YAML audit log, one entry per call)
 │
 └── LLM providers (via LiteLLM)
       Anthropic, OpenAI, Groq, OpenRouter, Gemini, HF, Ollama, ...
```

## Anatomy of a Level 2 run

A Level 2 skill run follows this lifecycle:

```
1. Skill spec loaded      (SkillRunner.run)
     │
     ▼
2. Roster loaded           (AgentRegistry.load_many on candidate_agents + required_agents)
     │
     ▼
3. Policy resolved         (PolicyLoader.resolve(skill.policy_profile))
     │
     ▼
4. Plan produced           (planner: default required_order_planner or custom)
     │
     ▼
5. For each planned step:
     │
     ├─ Build messages      (message_builder)
     │
     ├─ Select model        (model_for_role)
     │
     ├─ Runtime.call        ─────────────┐
     │    ├─ budget precheck              │
     │    ├─ for each model in chain:     │
     │    │    ├─ for each retry:         │
     │    │    │    ├─ provider call      │ ◄─── LiteLLM
     │    │    │    ├─ on success:        │
     │    │    │    │    ├─ cost compute  │
     │    │    │    │    ├─ sep_log.write │
     │    │    │    │    ├─ checkpoint    │
     │    │    │    │    └─ return        │
     │    │    │    └─ on error:          │
     │    │    │         ├─ sep_log.write │
     │    │    │         ├─ doom-loop chk │
     │    │    │         └─ backoff sleep │
     │    │    └─ fallback_triggered      │
     │    └─ RetryBudgetExceeded          │
     │       or DoomLoopDetected          │
     │       or CostCeilingExceeded       │
     │                                    │
     └─ StepOutcome recorded ◄────────────┘
     │
     ▼
6. SkillRunResult returned (status: completed | halted, total_cost_usd,
                            per-step outcomes, per-call SEP log entries)
```

## The three concerns, separated

Cadre deliberately keeps three concerns in distinct modules:

1. **What to do** — the skill intent and the plan. Owned by skills,
   agents, and the planner callable. Decoupled from retry logic.
2. **How to survive** — retry budget, fallback, doom-loop detection, cost
   ceiling. Owned by `Runtime.call()`. Uniform regardless of skill.
3. **What happened** — SEP log entries, checkpoints. Owned by `SEPLogger`
   and `CheckpointStore`. Append-only, machine-readable, parseable without
   rerunning.

The benefit: changing one concern does not force changes to the others.
A new skill does not need its own retry logic; a better retry strategy
does not need skill updates; observability can be upgraded without
touching orchestration.

## Agentic vs scripted orchestration (ADR 0004)

The product runs skills at one of three authority levels:

- **Level 1 — Scripted.** Fixed sequence. Same as claude-tech-squad's
  skills. Used when the workflow is deterministic and simple.
- **Level 2 — Planned.** Orchestrator produces an execution plan before
  executing. Plan is recorded in SEP log. Re-plan allowed when a step
  surprises the plan. Bounded by `max_review_cycles` and budget.
- **Level 3 — Emergent.** Orchestrator decides each step in isolation,
  no upfront plan. Deferred to v0.2.

In v0.1 the default planner (`required_order_planner`) is deterministic
and does not call the LLM to produce the plan — the plan is always
"invoke required_agents in declaration order." This is Level 2 in
structure but not in runtime complexity. Full LLM-driven planning is a
follow-up once the underlying LiteLLM tool-use integration lands.

## Reliability primitives — what each enforces

| Primitive | Enforced by | Trigger | Policy fields |
|---|---|---|---|
| Retry budget | `Runtime.call` inner loop | provider exception | `max_retries`, `retry_delay_seconds`, `retry_backoff_multiplier` |
| Fallback matrix | `Runtime.call` outer loop | model retry exhausted | `fallback_models` |
| Doom-loop | `Runtime.call` error tracker | N identical error signatures | `doom_loop_same_error_threshold` |
| Cost ceiling | `Runtime._enforce_budget_precheck` | accumulated > max | `max_budget_usd` |
| Checkpoint | `Runtime._maybe_checkpoint` | successful call | (requires `checkpoint_store` passed) |
| SEP log | `Runtime.call` every attempt | always on | `sep_log_dir` |

## Data at rest

Cadre does not hold a database of its own in v0.1. All persistence is
filesystem-based:

- **SEP log files** — `<sep_log_dir>/<run_id>.log.yaml`. One YAML document
  per attempt. Append-only. Human-readable.
- **Checkpoint SQLite** — `<checkpoint_db_path>`. Standard SQLite file.
  Readable with `sqlite3` CLI or any SQLite client.
- **Cross-run memory** (deferred to v0.2) — `.cadre/memory.md` per repo.

No external database. No cloud service. Runs entirely on the user's
machine. This is intentional for alpha — a managed cloud with server-side
state is a separate commercial path (see `docs/commercial.md`).

## What Cadre does not own

Things that look adjacent but are explicitly someone else's job:

- **Provider integration** — delegated to LiteLLM (ADR 0002).
- **Prompt content for each agent** — lives in the agent markdown body.
  The runtime does not generate prompts; it forwards them.
- **Tool use for Claude Code** — the Claude Code host owns Read/Edit/Bash
  etc. Cadre's agents declare a `tool_allowlist` but the host enforces.
- **Git operations** — agents may request them via tool calls, but Cadre
  itself does not stage, commit, or push.
- **Secret management** — API keys live in env vars; Cadre never reads
  credential files.

## How upgrades happen

Claude Code model updates, LiteLLM updates, Anthropic API changes — these
are all expected and handled by keeping three disciplines:

1. Pin a known-good LiteLLM version in `pyproject.toml`.
2. Keep the orchestrator prompt versioned (ADR 0006, planned).
3. Run the replay suite in CI on every upgrade to catch regressions.

The replay suite records a golden run and asserts structural equivalence
on replay. Token content may drift (LLM non-determinism); the agentic
structure (which agents ran, in what order, with what outputs) must not.

## File map

```
cadre/
├── .claude-plugin/marketplace.json    ◄─── Claude Code marketplace manifest
├── plugins/
│   └── cadre/
│       ├── .claude-plugin/plugin.json ◄─── plugin manifest
│       ├── agents/                    ◄─── agent spec cards
│       ├── skills/                    ◄─── skill definitions
│       ├── templates/                 ◄─── output templates
│       └── runtime-policy.yaml        ◄─── policy profiles
├── services/
│   ├── runtime/                       ◄─── Python reliability runtime
│   │   ├── cadre/                     ◄─── the package
│   │   ├── tests/                     ◄─── 77 tests
│   │   └── pyproject.toml
│   ├── gateway/                       ◄─── reserved for Go gateway (v0.3+)
│   └── web/                           ◄─── reserved for dashboard (v0.3+)
├── docs/                              ◄─── user docs + ADRs
├── infra/                             ◄─── Docker, Terraform
├── scripts/                           ◄─── smoke-run.py, CI helpers
├── ai-docs/                           ◄─── run-local artifacts, archive
└── README.md
```

## Further reading

- `docs/architecture/0001-monorepo-layout.md` — polyglot monorepo rationale
- `docs/architecture/0002-multi-provider-llm.md` — LiteLLM choice
- `docs/architecture/0003-rebrand-and-agentic-pivot.md` — positioning
- `docs/architecture/0004-agentic-orchestration.md` — authority levels,
  spec cards, orchestrator protocol, critic loop, memory
- `docs/architecture/0005-plugin-manifest.md` — plugin layout and manifest
