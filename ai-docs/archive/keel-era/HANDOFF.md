# Keel — Context Handoff

Use this document to resume work on the Keel project in a new Claude session.

---

## What Keel is

Keel is a new public repository being built as the commercial evolution of the `claude-tech-squad` Claude Code plugin.

- **Repo path:** `/home/alex/keel`
- **GitHub:** to be created at `alexfloripavieira/keel` (public)
- **License:** BSL 1.1 (Business Source License), converts to Apache 2.0 on 2030-04-21
- **Status:** alpha / pre-1.0
- **Positioning:** reliability backbone for AI engineering agents — a runtime harness, not an LLM

### One-line description
> Reliability backbone for AI engineering agents. Multi-provider, contract-driven pipelines with retry budgets, fallbacks, checkpoints, doom-loop detection, cost guardrails, and observability.

### What it is not
- Not an LLM
- Not a code generator
- Not a replacement for engineers

---

## Architecture

```
services/
  runtime/   Python (MVP)       agent runtime, provider adapters, orchestrator
  gateway/   Go (later)          webhook receiver, queue worker, container orchestrator
  web/       TypeScript (later)  dashboard and admin UI

packages/
  agents/    Vendor-neutral agent specs (markdown)
  skills/    Pipeline orchestration specs
  templates/ PRD, TechSpec, Tasks templates
  policy/    Runtime policy (retry, fallback, gates, observability)

infra/       Docker, Terraform, deployment artifacts
docs/        Architecture ADRs, commercial plan
```

### Key technology choices
- **Python MVP** for runtime (leveraging LiteLLM for multi-provider LLM access)
- **Polyglot-ready monorepo** — Go gateway and TS web planned but not built for MVP
- **Multi-provider from day 1** — Anthropic, OpenAI, Google, Groq, local models via a single provider-agnostic layer
- **Vendor-neutral** — no ties to any specific company or product

---

## Commercial model

**Open-core + managed cloud:**
- Free tier: self-host under BSL 1.1
- Paid tier: managed cloud with SLAs, support, and premium connectors
- BSL restriction: cannot offer a competing commercial service during the 4-year BSL period

---

## Genealogy

Keel reuses proven contracts from `claude-tech-squad`:
- Agent Contract (Result Contract, Self-Verification Protocol, verification_checklist, Analysis Plan, Documentation Standard)
- Skill Contract (Preflight Gate, Progressive Disclosure, ARC, Runtime Resilience, Checkpoint/Resume, Visual Reporting)
- Harness Engineering (retry budgets, fallback matrix, doom-loop detection, cost guardrails, auto-advance, entropy management)
- SEP log schema
- Vendor-neutral work item taxonomy (initiative/epic/story/task/subtask + defect/bug)

`claude-tech-squad` remains free and open source (MIT). Keel is the provider-neutral enterprise runtime.

---

## Current state of `/home/alex/keel`

### Done
- `git init` on `main`
- Directory structure scaffolded
- `README.md` written (project vision, architecture, commercial model, license, genealogy)
- Copied from claude-tech-squad:
  - `packages/agents/` — prd-author.md, inception-author.md, tasks-planner.md, work-item-mapper.md
  - `packages/templates/` — prd-template.md, techspec-template.md, tasks-template.md, task-template.md
  - `packages/skills/inception/SKILL.md`
  - `packages/policy/runtime-policy.yaml`
  - `scripts/render-teammate-card.sh`, `scripts/render-pipeline-board.sh`
- `packages/policy/runtime-policy.yaml` namespace adapted: `claude-tech-squad:` → `keel:` (139 replacements, 0 remaining refs)

### Pending (9 files + repo creation)
1. `LICENSE` — BSL 1.1 template adapted
   - Licensor: Alexsander Vieira
   - Change Date: 2030-04-21
   - Change License: Apache 2.0
   - Additional Use Grant: restricting competing commercial service
2. `CLAUDE.md` — project rules for Claude Code working in the repo (no emojis, no AI self-reference, technical commits)
3. `docs/architecture/0001-monorepo-layout.md` — ADR explaining monorepo decision
4. `docs/architecture/0002-multi-provider-llm.md` — ADR explaining multi-provider strategy via LiteLLM
5. `docs/commercial.md` — open-core + managed cloud plan detail
6. `services/runtime/pyproject.toml` — Python deps: litellm, fastapi, pydantic, pytest
7. `services/runtime/keel_runtime/__init__.py` + smoke test that passes
8. `.github/workflows/ci.yml` — basic CI (lint + test)
9. `infra/docker/compose.yaml` — local dev stack

Then:
10. First commit (structured)
11. `gh repo create alexfloripavieira/keel --public --source=. --push`

---

## How to resume

Open a new Claude session in `/home/alex/keel` and paste:

> Read `ai-docs/keel-handoff/keel-context.md` (symlink or copy from claude-tech-squad), then continue from the Pending list. Next file is LICENSE (BSL 1.1).

Or, from scratch:
```bash
cd /home/alex/keel
claude
# then: "Continue from the Pending list in the handoff doc. Next file is LICENSE."
```

---

## Fixes already applied (don't redo)

- `render-teammate-card.sh` and `render-pipeline-board.sh` need `export LC_ALL=C LC_NUMERIC=C` at top to avoid pt_BR locale breaking `printf` with decimals. Already applied in the copies under `/home/alex/keel/scripts/`.
- `runtime-policy.yaml` namespace already rewritten to `keel:` — do not replace again.

---

## User decisions already locked

- Public repo under `alexfloripavieira/keel`
- BSL 1.1 with 4-year change period
- Python-only MVP, polyglot structure ready
- Multi-provider from day 1 via LiteLLM
- Open-core + managed cloud business model
- Vendor-neutral — no company-specific content anywhere
- Copy (not symlink) the proven assets from claude-tech-squad so Keel can diverge freely
