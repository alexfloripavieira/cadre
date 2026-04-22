---
name: implement
description: Agentic delivery skill that lands a reviewable code change satisfying the stated acceptance criteria. Orchestrates PRD refinement (when needed), technical planning, implementation breakdown, a test plan, and a code review gate.

authority_level: 2
intent: >
  Land a reviewable code change on a working branch that satisfies the stated
  acceptance criteria, has a matching test plan, and passes a code review gate.
preconditions:
  - "repository tests are currently green on the base branch"
  - "acceptance criteria are stated or derivable from the task input"
  - "working tree is clean or isolated from the base branch"
success_criteria:
  - "acceptance criteria are each mapped to at least one test case"
  - "task breakdown sequences the work into atomic commits"
  - "code-reviewer returns approved or non-blocking findings"
  - "SEP log contains full trace of plan, execute, and review phases"
candidate_agents:
  - prd-author
  - inception-author
  - tasks-planner
  - test-planner
  - code-reviewer
required_agents:
  - tasks-planner
  - test-planner
  - code-reviewer
policy_profile: standard-delivery
max_budget_usd: 5.00
max_duration_seconds: 1800
max_review_cycles: 2
---

# /implement — Agentic Feature Delivery

Run the implement skill when you have a stated intent and want Cadre to produce
a reviewable change that lands it. The orchestrator decides the path based on
task complexity and existing artifacts.

## Required Inputs

- `intent` or `task_input` — the feature in one or two sentences.
- `acceptance_criteria` — list of testable statements.
- Either a reference branch or an explicit working path.

## Typical Path (orchestrator discretion)

1. **tasks-planner** — decomposes the intent + acceptance criteria into an
   ordered, atomic task list. Emits `tasks.md`.
2. **test-planner** — maps each acceptance criterion to at least one test case.
   Emits `test_plan_document`.
3. **code-reviewer** — reviews the produced artifacts (plan + tests + any diff
   staged during the run). Emits `review_findings` and a `review_status`.

The orchestrator may additionally invoke `prd-author` when the intent is too
vague for tasks-planner to consume directly, or `inception-author` when the
architectural scope is unclear. Invocations are logged as `phase: delegate`
in the SEP log.

## Output

- `tasks.md` written under `ai-docs/<slug>/tasks.md`.
- `test_plan.md` written under `ai-docs/<slug>/test_plan.md`.
- `review_findings` emitted inline and appended to the run's SEP log.
- A working-tree change staged for user review (optional in v0.1; explicit
  commit-before-review deferred to v0.2).

## Budget and Halt Behavior

- `max_budget_usd: 5.00` hard cap; run halts with `CostCeilingExceeded` if
  reached.
- `max_review_cycles: 2` — revision loops bounded. Exceeding halts and
  escalates.
- Doom-loop detection (per policy_profile `standard-delivery`) halts a
  specific producer-reviewer oscillation early.

## Non-goals in v0.1

- Not a fully autonomous end-to-end developer. Cadre plans, breaks down, tests,
  and reviews; it does not yet commit or push. That ships in v0.2.
- Not a PR creator. Use git + the user's normal PR tool at the end of the run.
