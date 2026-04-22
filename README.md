# Cadre

> A cadre of AI agents for serious software delivery.

**Status:** alpha — not for production use. APIs and contracts will change.
**License:** BSL 1.1, converts to Apache 2.0 on 2030-04-21.

---

## What Cadre is

Cadre is an **agentic delivery plugin for Claude Code**. It gives your
workspace a coordinated team of specialist agents (PM, tech lead,
architect, backend dev, reviewer, QA, security, and more) that plan,
execute, and verify software delivery tasks end to end — with retry
budgets, multi-provider fallback, doom-loop detection, cost guardrails,
checkpoint/resume, and a structured audit log underneath.

You bring the task ("ship feature X", "hot-fix this incident", "refactor
this module"). Cadre decides which agents to run, in what order, re-plans
when reality disagrees with the plan, and lands a reviewable result.

## Why Cadre

Teams running agentic pipelines in production hit the same five problems:

1. **Runaway retries** and doom loops that silently burn tokens.
2. **Provider outages** (Anthropic rate-limits, OpenAI 500s) that break
   the pipeline.
3. **Opaque cost** — no attribution by run, feature, or agent.
4. **Lost work** when a long run crashes mid-execution.
5. **Forensics pain** — reconstructing what happened from unstructured logs.

Cadre packages all five solutions into one runtime that any agent plugin
or orchestrator can ride on top of. The agentic layer decides what to do;
the reliability layer makes sure it survives.

## What makes Cadre different

- **Agentic, not a fixed pipeline.** Agents decide what to do next based
  on the task and their own output — not a pre-wired YAML sequence.
- **Multi-provider by default.** Anthropic, OpenAI, Google, Groq,
  OpenRouter, HuggingFace, Ollama, or any LiteLLM provider. Fallback
  happens automatically; the agent loop doesn't care which model served
  the call.
- **Reliability primitives built in.** Retry budget, fallback matrix,
  doom-loop detection, cost ceilings, checkpoint/resume — all enforced
  by the runtime, not bolted on by the user.
- **Structured audit log (SEP).** Every run writes a YAML-frontmatter
  log that answers "what ran, why, at what cost, with what outcome" —
  forensic-grade, parseable with any YAML tool.
- **Claude Code native.** Ships as a plugin. Install, invoke, done — no
  separate process, no external cloud, no account.

## What Cadre is not

- Not an LLM — Cadre is the harness around the model.
- Not a generic code generator — Cadre orchestrates specialist agents
  that produce artifacts (PRDs, tech specs, tasks, diffs, reviews).
- Not a replacement for engineers — Cadre automates delivery mechanics
  so engineers focus on judgment calls.
- Not an agent framework competing with LangChain / LlamaIndex / AutoGen.

## Quick start

```bash
# clone + install
git clone https://github.com/alexfloripavieira/cadre.git
cd cadre
python3 -m venv .venv && source .venv/bin/activate
pip install -e services/runtime[dev]

# run tests
cd services/runtime && pytest -q   # expected: 77 passed
cd ../..

# smoke test against a real provider (free tier)
export GROQ_API_KEY=gsk_...        # from https://console.groq.com
python scripts/smoke-run.py
```

Install as a Claude Code plugin:

```
/plugin install alexfloripavieira/cadre
/inception ai-docs/prd-<slug>/prd.md
```

See [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) for the full
path.

## Architecture at a glance

```
.claude-plugin/marketplace.json       Claude Code marketplace manifest

plugins/cadre/                        Plugin surface (user-facing)
  .claude-plugin/plugin.json
  agents/                             8 agents with ADR 0004 spec cards
  skills/                             /inception, /implement, /bug-fix, /review
  templates/                          PRD, TechSpec, Tasks templates
  runtime-policy.yaml                 5 policy profiles

services/runtime/cadre/               Python reliability runtime
  Runtime.call()                      retry, fallback, doom-loop, cost, SEP log
  SkillRunner                         plan → execute → outcome
  PolicyLoader                        YAML profile → Policy
  AgentRegistry                       load agent spec cards
  CheckpointStore                     SQLite, resume semantics
  SEPLogger                           YAML audit log

docs/                                 Architecture decision records + user docs
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture
and the [ADR series](docs/architecture/) for the formal decisions.

## Documentation

- [`docs/GETTING-STARTED.md`](docs/GETTING-STARTED.md) — install and first
  run, 15 minutes.
- [`docs/MANUAL.md`](docs/MANUAL.md) — full reference: skills, agents,
  policies, SEP log, customization.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system-level view.
- [`docs/API.md`](docs/API.md) — Python API reference for embedding.
- [`docs/PROVIDERS.md`](docs/PROVIDERS.md) — supported LLM providers and
  how to pick one.
- [`docs/AGENT-CONTRACT.md`](docs/AGENT-CONTRACT.md) — what every agent
  must satisfy.
- [`docs/SKILL-CONTRACT.md`](docs/SKILL-CONTRACT.md) — what every skill
  must satisfy.
- [`docs/commercial.md`](docs/commercial.md) — open-core + managed cloud
  plan.
- [ADRs](docs/architecture/) — numbered design decisions with rationale.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). TL;DR: Python 3.11+, venv,
`ruff check` + `ruff format --check` + `pytest -q` must all pass before
PR. No AI self-reference in commits. Conventional-commit style. New
agents and skills must satisfy the frontmatter contracts.

Open an issue before non-trivial work so we align on scope.

## Genealogy

Cadre inherits the agent contracts, skill patterns, templates, and
policy schema from [`claude-tech-squad`](https://github.com/alexfloripavieira/claude-tech-squad) — a free,
open-source Claude Code plugin. `claude-tech-squad` stays MIT and
independent. Cadre is the provider-neutral, reliability-first, agentic
successor.

## License

[BSL 1.1](LICENSE). Converts to Apache 2.0 on 2030-04-21. You can read,
modify, and self-host Cadre freely. You cannot offer Cadre as a
commercial service that competes with the Licensor during the BSL
period. See [`docs/commercial.md`](docs/commercial.md) for the full
model.

## Status pre-1.0

Cadre is pre-release. Expect breaking changes between 0.x minors. Do
not run on production workloads without thorough testing. Follow the
issue tracker and [`CHANGELOG.md`](CHANGELOG.md) for the roadmap to
1.0.
