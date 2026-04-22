# Agent Contract

The contract every agent in `plugins/cadre/agents/` must satisfy. This is
normative for v0.1. The canonical decision record is
`docs/architecture/0004-agentic-orchestration.md`.

## File shape

Each agent is one markdown file at `plugins/cadre/agents/<role>.md`.

```
---
<yaml frontmatter: spec card>
---

# <Agent Name>

<body: role, rules, output contract, anti-patterns>
```

## Required frontmatter fields (spec card)

```yaml
name: <string>                        # Claude Code discovery
description: <string>                 # one-line summary

# classic Claude Code plugin fields
tool_allowlist: [Read, Write, Edit, Glob, Grep, Bash, ...]

# ADR 0004 spec card (required for Level 2 and 3 skills)
role: <string>                        # typically same as name
authority: advisor | producer | reviewer | executor
inputs_required: [<name>, ...]
inputs_optional: [<name>, ...]
outputs_produced: [<name>, ...]
invoke_when:
  - "<natural-language trigger>"
avoid_when:
  - "<natural-language contraindication>"
cost_profile: low | medium | high
typical_duration_seconds: <int>
requires_model_class: chat | reasoning | coding
policy_profile: <string>              # profile name in runtime-policy.yaml
```

CI validates all fields are present on every file under
`plugins/cadre/agents/*.md`. Missing any field fails the build.

## Authority classes

- **advisor** — produces analysis or recommendations, does not change
  artifacts. Example: `test-planner`.
- **producer** — emits a concrete artifact (PRD, TechSpec, tasks file,
  diff). Example: `prd-author`.
- **reviewer** — reviews a producer's artifact and returns a verdict.
  Does not modify. Example: `code-reviewer`, `security-reviewer`.
- **executor** — drives the run itself, does not produce user-facing
  content. Example: `orchestrator`.

An agent has exactly one authority. Multi-authority agents are rejected
by the contract; split into two agents.

## Input/output discipline

- **`inputs_required`**: the orchestrator will not invoke this agent
  unless all of these are present in the run state or task input.
- **`inputs_optional`**: the agent should use these when available but
  must not fail when absent.
- **`outputs_produced`**: the named outputs this agent places into the
  run state on success. The orchestrator uses this list to track
  dependency satisfaction.

All three are lists of strings; the strings are shared names across
agents (for example, `prd_document` is produced by `prd-author` and
required by `inception-author`).

## The body (the system prompt)

The markdown body after the frontmatter is used as the system prompt
when the agent is invoked. It should contain:

1. **Role statement** — one paragraph stating what the agent does and
   does not do.
2. **Output contract** — exact schema of what the agent must return.
3. **Rules** — hard constraints (things the agent must never do, things
   it must always do).
4. **Anti-patterns** — observed failure modes to avoid.

Pre-v0.1 agents inherited from claude-tech-squad include broader
sections; these are preserved where useful but are not contractually
required.

## Cost profile and model class

These two hints drive the default `model_for_role` in `SkillRunner`:

- `cost_profile: low` → cheap model (Haiku-class, Llama 3.3 70B)
- `cost_profile: medium` → mid-tier model (Sonnet-class, GPT-4o-mini)
- `cost_profile: high` → premium reasoning model (Opus-class, o1-class,
  DeepSeek R1)

- `requires_model_class: chat` → small/fast models OK
- `requires_model_class: reasoning` → prefer a reasoning-optimized model
- `requires_model_class: coding` → prefer a coding-optimized model

The runner has defaults; users can override via `model_for_role` when
embedding the runtime.

## Validation

Two places validate agent spec cards:

1. **CI** — `.github/workflows/ci.yml` runs a frontmatter check on
   every `plugins/cadre/agents/*.md` file on every push.
2. **Runtime** — `cadre.load_agent_spec` raises `SpecError` when
   required fields are missing or malformed.

Both use the same required set. Keep them in sync; when adding a new
required field, update both validators and the existing agents in the
same commit.

## Adding a new agent

1. Copy an existing agent (e.g. `code-reviewer.md`) to
   `plugins/cadre/agents/<your-role>.md`.
2. Update all spec-card fields for the new role.
3. Rewrite the body to state role, output contract, rules.
4. Run `pytest -q` in `services/runtime/` — the registry's `load_all`
   test will pick up the new file.
5. Reference the agent from at least one skill's `candidate_agents` (or
   leave orphan and ship later).

## Evolution

- Spec card fields are contractual. Removing a field is a breaking
  change; plan an ADR and a migration window.
- The markdown body is not contractual; prompt engineering may rewrite
  it freely between releases. Changes should be captured in golden-run
  replay tests so we catch unintended behavior shifts.
