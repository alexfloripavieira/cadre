# Dogfooding

Use this guide to validate `claude-tech-squad` against controlled scenarios before publishing or after any structural change to agents, skills, retries, or orchestration.

## Local Dogfood Pack

This repository now ships a versioned local dogfood pack:

- [layered-monolith](/home/alex/claude-tech-squad/fixtures/dogfooding/layered-monolith)
- [hexagonal-billing](/home/alex/claude-tech-squad/fixtures/dogfooding/hexagonal-billing)
- [hotfix-checkout](/home/alex/claude-tech-squad/fixtures/dogfooding/hotfix-checkout)
- [scenarios.json](/home/alex/claude-tech-squad/fixtures/dogfooding/scenarios.json)

Static validation:

```bash
bash scripts/dogfood.sh
bash scripts/dogfood-report.sh --schema-only
```

Prompt pack:

```bash
bash scripts/dogfood.sh --print-prompts
```

## Goal

Confirm three things:

- the workflow emits explicit preflight and execution lines
- the selected architecture style is respected instead of forced
- every specialist returns a role body plus `result_contract`

## Scenario 1 — Layered Repository

Fixture: [layered-monolith](/home/alex/claude-tech-squad/fixtures/dogfooding/layered-monolith)

Use when the target repo already follows a normal layered/module pattern and should **not** be pushed into Hexagonal Architecture.

Prompt:

```text
/claude-tech-squad:discovery
Design a delivery slice for audit-log filters in an existing layered monolith. Preserve the current repository structure, propose only the specialists that are actually needed, and show explicit preflight and execution lines.
```

Expect:

- `[Preflight Passed] discovery`
- `architecture_style=existing-repo-pattern` or `architecture_style=layered`
- `backend-architect` may be selected
- `hexagonal-architect` should only appear if the design explicitly chooses it

## Scenario 2 — Explicit Hexagonal Adoption

Fixture: [hexagonal-billing](/home/alex/claude-tech-squad/fixtures/dogfooding/hexagonal-billing)

Use when the task intentionally adopts Ports & Adapters for a new integration-heavy feature.

Prompt:

```text
/claude-tech-squad:discovery
Design a new billing integration using Hexagonal Architecture with explicit port contracts, outbound adapters, TDD-first delivery, and visible execution lines.
```

Then:

```text
/claude-tech-squad:implement
Use the approved blueprint and keep the feature in explicit Hexagonal Architecture. Show preflight lines and require structured result contracts from all specialists.
```

Expect:

- `architecture_style=hexagonal`
- `hexagonal-architect` selected in discovery
- reviewer and techlead auditing against the chosen style, not generic assumptions

## Scenario 3 — Hotfix

Fixture: [hotfix-checkout](/home/alex/claude-tech-squad/fixtures/dogfooding/hotfix-checkout)

Use when a minimal production fix is needed and the workflow must stay short but disciplined.

Prompt:

```text
/claude-tech-squad:hotfix
Investigate a production 500 error in checkout after the latest deploy. Show the diagnosis gate, minimal patch path, and explicit execution lines.
```

Expect:

- root cause analysis delegated through a valid plugin subagent
- no reference to `code-debugger`
- security and validation loops still present

## Manual Verification Checklist

- Preflight lines are visible before team creation
- `architecture_style` is explicit in the run
- `docs_lookup_mode=context7` or `docs_lookup_mode=repo-fallback` is explicit
- retries happen only with clear reasons and bounded budgets
- every specialist output ends with a `result_contract` block

## Static Smoke Test

Run:

```bash
bash scripts/smoke-test.sh
bash scripts/dogfood.sh
```

This validates the repository contracts statically:

- plugin structure and versions
- result contract presence in all agents
- preflight/result-contract sections in the main orchestrators
- Agent tool restricted to `incident-manager`
- local dogfooding fixtures and prompt pack
