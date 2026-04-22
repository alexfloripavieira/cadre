# Keel

> Reliability backbone for AI engineering agents.

**Status:** alpha — not for production use. APIs and contracts will change.

## What Keel is

Keel is a runtime that orchestrates AI engineering agents through reliable, contract-driven pipelines. It turns loosely-coupled agents (PRD author, tech lead, backend dev, reviewer, QA, SRE, and dozens more) into a predictable delivery system with retry budgets, fallback policies, checkpoint/resume, doom-loop detection, cost guardrails, and observability.

Keel is multi-provider from day one — Anthropic, OpenAI, Google, Groq, local models via a single provider-agnostic runtime. Agent specifications, skills, templates, and policies are vendor-neutral and configurable per team.

## What Keel is not

- Not an LLM — Keel is the harness around the model, not the model itself.
- Not a code generator — Keel orchestrates agents that produce artifacts (PRDs, tech specs, tasks, code, reviews), it does not generate code directly.
- Not a replacement for engineers — Keel automates delivery mechanics so engineers focus on judgment calls.

## Architecture

```
services/
  runtime/   Python — agent runtime, provider adapters, orchestrator (MVP)
  gateway/   Go — webhook receiver, queue worker, container orchestrator (later)
  web/       TypeScript — dashboard and admin UI (later)

packages/
  agents/    Vendor-neutral agent specifications (markdown)
  skills/    Pipeline orchestration specs
  templates/ PRD, TechSpec, Tasks output templates
  policy/    Runtime policy (retry, fallback, gates, observability)

infra/       Docker, Terraform, deployment artifacts
```

See [docs/architecture/0001-monorepo-layout.md](docs/architecture/0001-monorepo-layout.md) for the layout rationale and [docs/architecture/0002-multi-provider-llm.md](docs/architecture/0002-multi-provider-llm.md) for provider strategy.

## Commercial model

Open-core + managed cloud. See [docs/commercial.md](docs/commercial.md) for the plan.

## License

[BSL 1.1](LICENSE). Converts to Apache 2.0 on 2030-04-21. You can read, modify, and self-host Keel freely. You cannot offer Keel as a commercial service that competes with the Licensor during the BSL period.

## Genealogy

Keel is the commercial evolution of [`claude-tech-squad`](https://github.com/alexfloripavieira/claude-tech-squad), a Claude Code plugin the author built over 6 months. The agent contracts, skill orchestration patterns, templates, and policy schema were proven there and are reused here as the foundation.

`claude-tech-squad` remains a free, open-source Claude Code plugin. Keel is the provider-neutral, enterprise-ready runtime built on top of the same ideas.

## Status pre-1.0

Keel is pre-release. Expect breaking changes weekly. Do not run Keel on production workloads. Follow the issue tracker for the roadmap to 1.0.
