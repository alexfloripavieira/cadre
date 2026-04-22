# Cadre Manual

The full reference. See `docs/GETTING-STARTED.md` for install and first run.
See `docs/ARCHITECTURE.md` for the system-level view. See `docs/API.md` for
Python embedding.

## Table of contents

1. [Concepts](#concepts)
2. [Skills](#skills)
3. [Agents](#agents)
4. [Policy profiles](#policy-profiles)
5. [SEP log](#sep-log)
6. [Checkpoints and resume](#checkpoints-and-resume)
7. [Cost tracking](#cost-tracking)
8. [Doom-loop detection](#doom-loop-detection)
9. [Customizing Cadre](#customizing-cadre)
10. [Troubleshooting](#troubleshooting)

---

## Concepts

**Cadre** is an agentic delivery plugin for Claude Code. The product ships
two artifacts:

- **Plugin surface** (`plugins/cadre/`): agents, skills, templates, and
  runtime policy, loaded by Claude Code when the plugin is installed.
- **Python runtime** (`services/runtime/cadre/`): the reliability layer —
  retry, fallback, doom-loop detection, cost ceiling, SEP log, checkpoints.
  Used by the plugin under the hood, and by any caller that embeds Cadre.

A **run** is one execution of one skill against one task. Every run has:

- a `run_id` (auto-generated or supplied)
- one or more agent invocations, each a `Runtime.call()`
- a SEP log file with one entry per attempt
- optional checkpoints in a SQLite store
- a per-run cost budget

**Authority levels** (ADR 0004):

- **Level 1 (Scripted)**: fixed sequence, no planner. Used for simple,
  well-understood workflows.
- **Level 2 (Planned)**: an orchestrator agent produces an execution plan
  before running. Can re-plan when reality disagrees. Default for most
  skills in v0.1.
- **Level 3 (Emergent)**: no upfront plan; orchestrator decides each step.
  Deferred to v0.2.

---

## Skills

Skills live under `plugins/cadre/skills/<name>/SKILL.md`.

### Skill frontmatter schema

```yaml
---
name: <identifier>
description: <one-paragraph description>

authority_level: 1 | 2 | 3
intent: >
  <one or two sentences stating the goal>
preconditions:
  - "<condition that must hold before starting>"
success_criteria:
  - "<observable outcome that defines completion>"
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

### Skills shipped in v0.1

| Slash command | Authority | Required agents | Budget | Purpose |
|---|---|---|---|---|
| `/inception` | Level 2 | inception-author | $3.00 | PRD → TechSpec |
| `/implement` | Level 2 | tasks-planner, test-planner, code-reviewer | $5.00 | Land a reviewable code change |
| `/bug-fix` | Level 2 | test-planner, code-reviewer | $3.00 | Reproduce + fix + review a bug |
| `/review` | Level 2 | code-reviewer | $2.00 | Structured review of a diff or PR |

### Running a skill from Python

```python
from cadre import (
    AgentRegistry, PolicyLoader, Runtime, SkillRunner, load_skill_spec
)

runtime = Runtime(sep_log_dir="ai-docs/.cadre-log")
runner = SkillRunner(
    runtime=runtime,
    agent_registry=AgentRegistry("plugins/cadre/agents"),
    policy_loader=PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml"),
)

skill = load_skill_spec("plugins/cadre/skills/implement/SKILL.md")
result = runner.run(skill=skill, task_input={"intent": "add /ping endpoint"})

print(result.status, result.total_cost_usd)
```

### Running a skill inside Claude Code

After `/plugin install alexfloripavieira/cadre`:

```
/implement <intent in one sentence>
/bug-fix <bug report>
/review <diff path or PR URL>
/inception <path to prd.md>
```

---

## Agents

Agents live under `plugins/cadre/agents/<name>.md`. Each agent is
markdown with a YAML frontmatter "spec card" that makes the agent
selectable by the orchestrator.

### Agent spec card schema (ADR 0004)

```yaml
---
name: <identifier>
description: <one-line summary for Claude Code discovery>
tool_allowlist: [Read, Write, Edit, Glob, Grep, Bash, ...]

role: <same as name or a namespaced role>
authority: advisor | producer | reviewer | executor
inputs_required:
  - <named input expected from prior step or task>
inputs_optional:
  - <input accepted if present>
outputs_produced:
  - <named output this agent emits>
invoke_when:
  - "<natural-language trigger>"
avoid_when:
  - "<natural-language condition under which this agent should not run>"
cost_profile: low | medium | high
typical_duration_seconds: <int>
requires_model_class: chat | reasoning | coding
policy_profile: <name from runtime-policy.yaml>
---

# <Agent Name>

<body: the agent's system prompt, rules, output contract>
```

### Agents shipped in v0.1

| Role | Authority | Cost | Purpose |
|---|---|---|---|
| prd-author | producer | medium | Feature request → PRD |
| inception-author | producer | high | PRD → TechSpec |
| tasks-planner | producer | medium | PRD + TechSpec → task list |
| work-item-mapper | producer | low | Artifacts → work-items.md |
| test-planner | advisor | medium | Acceptance criteria → test plan |
| code-reviewer | reviewer | medium | Diff → structured findings |
| security-reviewer | reviewer | medium | Diff → security findings |
| orchestrator | executor | medium | Meta-agent: plans or decides next step |

### Adding a new agent

Create `plugins/cadre/agents/<role>.md` with the full frontmatter above
plus a markdown body. CI validates the frontmatter; all spec-card fields
are required.

---

## Policy profiles

Runtime policies live in `plugins/cadre/runtime-policy.yaml` under the
`policies:` section.

### Profile fields

```yaml
<profile-name>:
  max_retries: <int, default 3>
  retry_delay_seconds: <float, default 1.0>
  retry_backoff_multiplier: <float, default 2.0>
  fallback_models:
    - <model-string in LiteLLM format>
    - ...
  max_budget_usd: <float or null>
  max_duration_seconds: <float or null>
  doom_loop_same_error_threshold: <int, 0 to disable, >=2 to enable>
```

### Profiles shipped in v0.1

| Profile | max_retries | Fallback chain | Budget |
|---|---|---|---|
| `default` | 3 | none | unlimited |
| `orchestrator` | 2 | none | $1.00 |
| `standard-delivery` | 3 | openai/gpt-4.1 → groq/llama-3.3-70b | $5.00 |
| `low-cost` | 2 | groq/llama-3.3-70b → ollama/llama3 | $0.50 |
| `free-tier` | 2 | openrouter free chain → gemini 2.0 flash | unlimited |

### Resolving a policy

```python
from cadre import PolicyLoader

loader = PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml")
policy = loader.resolve("standard-delivery")
```

---

## SEP log

Every `Runtime.call()` writes one or more entries to the SEP log. Default
location: `.cadre-log/` under the working directory; override via
`sep_log_dir` on the Runtime constructor.

### Entry format

Each entry is one YAML document (preceded by `---`):

```yaml
---
timestamp: 2026-04-22T03:55:00.123456+00:00
run_id: smoke-001
phase: execute       # plan | execute | delegate | review | decide
agent_role: inception-author
model: groq/llama-3.3-70b-versatile
is_primary: true
retry_index: 1
attempt_overall: 1
outcome: success     # success | error | fallback_triggered | doom_loop_triggered
cost_usd: 0.0
run_budget_used_usd: 0.0
duration_seconds: 1.234
```

Error entries add `error_class`, `error_message`. Fallback entries add
`reason`, `next_model`. Doom-loop entries add `error_signature`,
`occurrences`, `threshold`.

### Reading a log programmatically

```python
from cadre import SEPLogger
logger = SEPLogger("ai-docs/.cadre-log")
entries = logger.read("smoke-001")
for e in entries:
    print(e["phase"], e["outcome"], e.get("cost_usd"))
```

---

## Checkpoints and resume

Cadre writes a checkpoint to SQLite after every successful `Runtime.call()`
when a `CheckpointStore` is attached.

```python
from cadre import CheckpointStore, Runtime

store = CheckpointStore("ai-docs/.cadre-checkpoints.db")
runtime = Runtime(checkpoint_store=store)

# ... run ...

# query checkpoints for a run
for cp in store.all("smoke-001"):
    print(cp["step_id"], cp["label"], cp["data"])

# remove all checkpoints for a run
store.clear("smoke-001")
```

Resume semantics (re-executing from the last checkpoint) are deferred
to v0.2; the store is written and readable today.

---

## Cost tracking

Cost is opt-in. Pass a `cost_estimator` to the Runtime:

```python
from cadre import Runtime, litellm_cost_estimator

runtime = Runtime(cost_estimator=litellm_cost_estimator)
```

`litellm_cost_estimator` delegates to `litellm.completion_cost()`, which
knows pricing for major providers.

For fully deterministic cost (useful in CI):

```python
from cadre import ModelPricing, PricedCostEstimator, Runtime

pricing = {
    "anthropic/claude-sonnet-4-6": ModelPricing(
        input_per_1k_tokens_usd=0.003,
        output_per_1k_tokens_usd=0.015,
    ),
}
runtime = Runtime(cost_estimator=PricedCostEstimator(pricing))
```

Per-run budget is enforced by the policy's `max_budget_usd`. When the
accumulated cost for a run_id meets or exceeds the budget, the next call
raises `CostCeilingExceeded`. Reset with `runtime.reset_run(run_id)`.

---

## Doom-loop detection

Per ADR 0004, `Runtime.call()` tracks consecutive error signatures
(error class + first 50 chars of the error message) within each model's
retry loop. When the count of identical-signature failures reaches
`policy.doom_loop_same_error_threshold`:

- The run aborts retries on the current model.
- A `doom_loop_triggered` entry is written to the SEP log.
- Execution advances to the next fallback model, if any.
- If no fallback remains, `DoomLoopDetected` is raised.

Enable:

```python
from cadre import Policy
policy = Policy(max_retries=5, doom_loop_same_error_threshold=3)
```

A threshold of 1 is rejected as meaningless; use 0 to disable or >= 2.

---

## Customizing Cadre

### Override the default planner

`SkillRunner` uses `required_order_planner` by default (executes
`required_agents` in declaration order). Inject your own planner:

```python
def my_planner(skill, agents, state):
    # return a Plan(steps=..., rationale=...)
    ...

runner = SkillRunner(..., planner=my_planner)
```

### Override the model-per-role mapping

```python
def my_model_for_role(agent_spec):
    if agent_spec.requires_model_class == "reasoning":
        return "openrouter/deepseek/deepseek-r1:free"
    return "groq/llama-3.3-70b-versatile"

runner = SkillRunner(..., model_for_role=my_model_for_role)
```

### Override the message builder

```python
def my_message_builder(skill, step, task):
    return [
        {"role": "system", "content": "You are a careful assistant."},
        {"role": "user", "content": f"Skill: {skill.name}\n\nTask: {task}"},
    ]

runner = SkillRunner(..., message_builder=my_message_builder)
```

---

## Troubleshooting

**`RetryBudgetExceeded`** — all attempts across primary + fallback chain
failed. Increase `max_retries`, add more fallback_models, or investigate
the underlying error via the SEP log.

**`CostCeilingExceeded`** — the run's accumulated cost met
`max_budget_usd`. Raise the cap in the policy, switch to a cheaper model,
or reset the run.

**`DoomLoopDetected`** — same error N times in a row. The orchestrator's
inputs or the model's behavior are stuck. Inspect the SEP log error
signature and either change the prompt or advance to a better model.

**`PolicyError: unknown policy fields`** — you added a field to a profile
in `runtime-policy.yaml` that `Policy` does not recognize. Either remove
the field or add it to `cadre.policy.Policy`.

**`SpecError: agent spec <name> missing fields`** — you added an agent
without a full ADR 0004 spec card. CI catches this; fix the frontmatter.

**SEP log is empty** — check that the Runtime was constructed with
`sep_log_dir` pointing to a writable directory.

**A skill runs but produces no diff** — v0.1 agents plan and review; they
do not yet stage diffs. Diff staging ships in v0.2.

For anything not covered here, open a GitHub issue with the SEP log
attached.
