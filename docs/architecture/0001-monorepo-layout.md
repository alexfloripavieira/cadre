# ADR 0001 — Monorepo Layout

- Status: Accepted (amended by ADR 0005)
- Date: 2026-04-21
- Deciders: Alexsander Vieira

> **Amendment note (2026-04-22):** ADR 0005 introduces a `plugins/cadre/` tree
> alongside `services/` to match the Claude Code plugin distribution contract.
> The contracts previously described here as living under `packages/` now live
> under `plugins/cadre/`. The `packages/` directory is retired. All other
> decisions in this ADR (polyglot services, contracts separated from code,
> path-scoped CI, future extractability) remain in force. See ADR 0005 for the
> amended layout.

## Context

Cadre is a reliability backbone for AI engineering agents. The system spans multiple
concerns that will, over time, be implemented in different languages and deployed as
separate services:

- **Runtime** — the core agent/skill execution engine, provider adapters, policy
  enforcement, and observability. Built in Python (MVP) to leverage the existing
  Python AI/LLM ecosystem (LiteLLM, FastAPI, Pydantic).
- **Gateway** — webhook receiver, queue worker, and container orchestrator. Planned
  to be built in Go for deployment footprint and concurrency ergonomics.
- **Web** — dashboard and admin UI. Planned TypeScript/React.

In parallel, Cadre ships **vendor-neutral assets** that are independent of any service:
agent specs, skill specs, templates, and runtime policy. These assets must be
consumable by any of the services and also by third parties.

We need a layout that:

1. Keeps shared contracts (agents, skills, templates, policy) in one versioned place.
2. Allows each service to evolve with its own language toolchain and build.
3. Enables a single CI pipeline to run language-scoped jobs without cross-contamination.
4. Supports future extraction of any service into its own repository if needed.

## Decision

Adopt a **polyglot monorepo** with two top-level trees:

```
services/
  runtime/   Python   agent runtime, providers, orchestrator
  gateway/   Go       webhook receiver, queue, orchestrator (later)
  web/       TS       dashboard and admin UI (later)

packages/
  agents/    vendor-neutral agent specs (markdown)
  skills/    pipeline orchestration specs
  templates/ PRD, TechSpec, Tasks templates
  policy/    runtime policy (retry, fallback, gates, observability)

infra/       Docker, Terraform, deployment artifacts
docs/        architecture ADRs, contracts, operational docs
scripts/     cross-repo tooling (rendering, linting helpers)
```

Rules:

- `packages/` contains **no executable code** — only specs, templates, and policy that
  are loaded by services at runtime or consumed by tooling.
- Each `services/<name>/` is a self-contained project with its own build, lockfile,
  and test runner. Services do not import each other's source; they communicate via
  contracts in `packages/`.
- CI runs one job per service, scoped by path filter, plus shared jobs for policy
  validation and script linting.
- `infra/docker/compose.yaml` wires services for local dev; production deployment is
  handled per-service via `infra/terraform/` (later).

## Consequences

Positive:

- One place to version and review shared contracts alongside their consumers.
- Any service can be extracted to its own repo later with `git filter-repo` because
  dependencies on `packages/` are path-scoped, not coupled via tooling.
- Contributors working on a single service only need that service's toolchain installed.
- CI cost scales with what changed, not with the full repo.

Negative:

- Slightly higher initial setup cost vs. a single-language layout.
- Contributors must understand which tree owns what (`services/` vs `packages/`).
- Language-specific idioms (e.g. workspace files) are not available across languages;
  each service manages its own dependencies.

## Alternatives considered

- **Separate repositories per service.** Rejected for the MVP: the contracts in
  `packages/` evolve together with the runtime, and splitting would force a release
  dance on every contract change.
- **Single-language repo (Python-only) with planned rewrites later.** Rejected: the
  gateway's characteristics (long-lived connections, many concurrent jobs) favor Go
  from day one, and committing to Python would either force a rewrite or lock in a
  suboptimal choice.
- **Nx / Turborepo style workspace.** Rejected for MVP: adds tooling before there
  are enough services to justify it. Revisit if/when the number of services or the
  CI graph becomes unmanageable.
