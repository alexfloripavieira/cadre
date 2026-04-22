# Cadre

> A cadre of AI agents for serious software delivery.

**Status:** alpha — not for production use. APIs and contracts will change.

## What Cadre is

Cadre is an **agentic delivery plugin for Claude Code**. It gives your Claude Code workspace a coordinated team of specialist agents (PM, tech lead, architect, backend dev, frontend dev, reviewer, QA, SRE, and more) that plan, execute, and verify software delivery tasks end to end — with retry budgets, multi-provider fallback, doom-loop detection, cost guardrails, checkpoint/resume, and a structured audit log underneath.

You bring the task ("ship feature X", "hot-fix this incident", "refactor this module"). Cadre decides which agents to run, in what order, re-plans when reality disagrees with the plan, and lands a reviewable result.

## What makes Cadre different

- **Agentic, not a fixed pipeline.** Agents decide what to do next based on the task and their own output — not a pre-wired YAML sequence.
- **Multi-provider by default.** Anthropic, OpenAI, Google, Groq, or local models via LiteLLM. Fallback happens automatically; the agent loop doesn't care which model served the call.
- **Reliability primitives built in.** Retry budget, fallback matrix, doom-loop detection, cost ceilings, checkpoint/resume — all enforced by the runtime, not bolted on by the user.
- **Structured audit log (SEP).** Every run writes a YAML-frontmatter log that answers "what ran, why, at what cost, with what outcome" — forensic-grade, no JSON grep.
- **Cross-run memory.** Cadre remembers the decisions made on this repository last time, so you don't re-explain your architecture every session.
- **Claude Code native.** Ships as a plugin. Install, invoke, done — no separate process, no external cloud, no account.

## What Cadre is not

- Not an LLM — Cadre is the harness around the model.
- Not a code generator in the naive sense — Cadre orchestrates specialist agents that produce artifacts (PRDs, tech specs, tasks, diffs, reviews), each with its own role.
- Not a replacement for engineers — Cadre automates delivery mechanics so engineers focus on judgment calls.
- Not a generic agent framework — it is tuned specifically for software delivery inside Claude Code.

## Architecture

```
.claude-plugin/
  marketplace.json       Claude Code marketplace manifest

plugins/
  cadre/                 Claude Code plugin surface (user-facing)
    .claude-plugin/plugin.json
    agents/              Agent specifications (markdown + ADR 0004 spec cards)
    skills/              Skill specifications
    templates/           PRD, TechSpec, Tasks templates
    runtime-policy.yaml  Retry, fallback, gates, observability

services/
  runtime/               Python reliability runtime powering the agent loop
  gateway/               Go — webhook receiver and queue worker (later)
  web/                   TypeScript — dashboard (later)

docs/                    Architecture decision records, contracts, guides
infra/                   Docker, Terraform, deployment artifacts
ai-docs/                 Run-local artifacts, archive, SEP logs
scripts/                 Repo-level tooling
```

See [`docs/architecture/0001-monorepo-layout.md`](docs/architecture/0001-monorepo-layout.md) for the layout rationale (amended by ADR 0005), [`docs/architecture/0002-multi-provider-llm.md`](docs/architecture/0002-multi-provider-llm.md) for provider strategy, [`docs/architecture/0003-rebrand-and-agentic-pivot.md`](docs/architecture/0003-rebrand-and-agentic-pivot.md) for positioning, [`docs/architecture/0004-agentic-orchestration.md`](docs/architecture/0004-agentic-orchestration.md) for orchestration design, and [`docs/architecture/0005-plugin-manifest.md`](docs/architecture/0005-plugin-manifest.md) for the plugin layout.

## Commercial model

Open-core + managed cloud. See [`docs/commercial.md`](docs/commercial.md) for the full plan.

## License

[BSL 1.1](LICENSE). Converts to Apache 2.0 on 2030-04-21. You can read, modify, and self-host Cadre freely. You cannot offer Cadre as a commercial service that competes with the Licensor during the BSL period.

## Genealogy

Cadre inherits the agent contracts, skill patterns, templates, and policy schema from [`claude-tech-squad`](https://github.com/alexfloripavieira/claude-tech-squad) — a free, open-source Claude Code plugin. `claude-tech-squad` stays MIT and independent. Cadre is the provider-neutral, reliability-first, agentic successor.

## Status pre-1.0

Cadre is pre-release. Expect breaking changes weekly. Do not run on production workloads. Follow the issue tracker for the roadmap to 1.0.
