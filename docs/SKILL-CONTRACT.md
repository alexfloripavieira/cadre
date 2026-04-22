# Skill Contract

The contract every skill in `plugins/cadre/skills/<name>/SKILL.md` must
satisfy. Normative for v0.1. See
`docs/architecture/0004-agentic-orchestration.md` for the formal
decision.

## File shape

Each skill lives in its own directory:

```
plugins/cadre/skills/
├── inception/
│   └── SKILL.md
├── implement/
│   └── SKILL.md
├── bug-fix/
│   └── SKILL.md
└── review/
    └── SKILL.md
```

Additional files (helper scripts, fixtures) may live alongside
`SKILL.md` in the same directory.

## Required frontmatter

```yaml
---
name: <string>                        # slash command identifier
description: <string>                 # one-paragraph Claude Code discovery

authority_level: 1 | 2 | 3
intent: >
  <one or two sentences stating the goal>

preconditions:
  - "<condition>"
success_criteria:
  - "<observable outcome>"

candidate_agents:
  - <role>
  - ...
required_agents:
  - <role>
  - ...

policy_profile: <name from runtime-policy.yaml>
max_budget_usd: <number or null>
max_duration_seconds: <number or null>
max_review_cycles: <integer>
---
```

CI validates `authority_level in {1, 2, 3}` and that every file parses.
The runtime (`cadre.load_skill_spec`) validates that `name` and
`authority_level` are present.

## Authority levels

- **Level 1 — Scripted.** A fixed sequence. `required_agents` are
  executed in declaration order; no planner involvement. Used when the
  workflow is deterministic.
- **Level 2 — Planned.** An orchestrator produces an execution plan
  before execution. Plan is recorded in SEP log. Re-plan allowed when a
  step surprises the plan, bounded by `max_review_cycles` and budget.
- **Level 3 — Emergent.** No upfront plan; orchestrator decides each
  step in isolation. Deferred to v0.2.

In v0.1, the shipped default planner (`required_order_planner`) is
Level 2 in structure but deterministic in implementation: every Level 2
skill runs its `required_agents` in declaration order. Full planner
sophistication requires tool-use integration coming in v0.1.5.

## `intent` vs `success_criteria`

- `intent` answers "what are we trying to do?". One or two sentences.
  The orchestrator uses this in prompts.
- `success_criteria` answers "how do we know we are done?". A list of
  observable, verifiable outcomes. The reviewer uses these to decide
  approve vs revision_requested.

Both are required for Level 2 and 3 skills.

## `candidate_agents` vs `required_agents`

- **`candidate_agents`** — the roster the planner is allowed to pick
  from. The orchestrator never invokes an agent outside this list.
- **`required_agents`** — non-negotiable. These must appear in every
  plan; `required_order_planner` treats them as the plan itself.

A role appearing in `required_agents` must also be loadable by the
`AgentRegistry` (the file must exist). A role in `candidate_agents` but
not shipped is an error at runtime when the registry tries to load it.

## Budget and time caps

- **`max_budget_usd`** — hard ceiling in USD for the entire run. When
  accumulated cost meets or exceeds this, the next `Runtime.call` raises
  `CostCeilingExceeded`. Use `null` for no cap (rare).
- **`max_duration_seconds`** — advisory for now; not enforced by
  `Runtime.call` in v0.1. A follow-up wall-clock cap ships in v0.2.
- **`max_review_cycles`** — maximum producer/reviewer oscillations.
  When exceeded, the run halts and escalates to the user.

## The markdown body

The body of `SKILL.md` is human documentation for developers. It is
also loaded as `SkillSpec.body` and available to the orchestrator if
extra context is needed. Keep it:

- **Role and purpose** in one paragraph.
- **Required inputs** — what the task input must contain.
- **Typical path** — the happy path the skill expects to take.
- **Output** — what the user sees when the skill completes.
- **Budget and halt behavior** — user-facing summary of policy.
- **Non-goals** — explicit scope cuts.

Avoid: long prose explanations of orchestrator logic (that lives in the
agent spec cards and the orchestrator agent body). Avoid: claims that
do not yet ship (track these in `CHANGELOG.md` roadmap).

## Validation

- **CI** — validates frontmatter fields and authority_level.
- **Runtime** — `cadre.load_skill_spec` raises `SpecError` for missing
  `name` or `authority_level`, or invalid level value.
- **Runner** — `SkillRunner.run` raises `SkillRunError` if the skill
  level is not in {1, 2} (3 is deferred).
- **Runner** — rejects skills with empty `required_agents` and empty
  `candidate_agents`.

## Adding a new skill

1. Create `plugins/cadre/skills/<name>/SKILL.md` with the full
   frontmatter.
2. Make sure every role in `candidate_agents` + `required_agents` has a
   file in `plugins/cadre/agents/`.
3. Pick a policy profile from `plugins/cadre/runtime-policy.yaml` (or
   add a new profile first).
4. Test end-to-end from Python:

```python
from cadre import AgentRegistry, PolicyLoader, Runtime, SkillRunner, load_skill_spec

runner = SkillRunner(
    runtime=Runtime(sep_log_dir="/tmp/sep"),
    agent_registry=AgentRegistry("plugins/cadre/agents"),
    policy_loader=PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml"),
)
skill = load_skill_spec("plugins/cadre/skills/my-skill/SKILL.md")
result = runner.run(skill=skill, task_input={})
assert result.status == "completed"
```

5. Add the skill to the table in `docs/MANUAL.md`.
6. Capture a golden run once agents work correctly end-to-end.

## Evolution

- Frontmatter fields are contractual. Removing a field is a breaking
  change; ADR and migration plan required.
- Authority level changes (Level 1 → Level 2) are non-breaking for
  users but require the orchestrator to support the new level.
- Budget or policy-profile changes across releases are expected and
  non-breaking; document in `CHANGELOG.md`.
