# Agent Contract

Every agent file in `plugins/claude-tech-squad/agents/` must implement this contract. An agent that omits any required section is structurally incomplete and will be rejected by `scripts/validate.sh`.

---

## File location and naming

```
plugins/claude-tech-squad/agents/<role-slug>.md
```

Examples: `pm.md`, `backend-dev.md`, `security-reviewer.md`

---

## Required frontmatter

```yaml
---
name: <role-slug>
description: <one-line description of what this agent does and when it is invoked>
---
```

Optional fields:

```yaml
tools:
  - Bash
  - Read
  - Glob
  - Grep
tool_allowlist:
  - Read
  - Glob
  - Grep
  - Bash
  - Edit
  - Write
```

### Tool Allowlist Enforcement

The `tool_allowlist` field declares which tools the agent is permitted to use at runtime. The orchestrator must not provide tools outside this list when spawning the agent.

**Categories:**

| Agent type | Default tool_allowlist |
|---|---|
| Analysis/review agents (pm, reviewer, qa, security-reviewer, etc.) | `Read, Glob, Grep, WebSearch, WebFetch` |
| Implementation agents (backend-dev, frontend-dev, etc.) | `Read, Glob, Grep, Bash, Edit, Write` |
| Documentation agents (docs-writer, tech-writer) | `Read, Glob, Grep, Edit, Write` |
| Operations agents (devops, ci-cd, sre, release) | `Read, Glob, Grep, Bash, Edit, Write` |
| Orchestrator agents (incident-manager) | `Read, Glob, Grep, Bash, Edit, Write, Agent` |

If `tool_allowlist` is omitted, the agent inherits the default allowlist for its category. The `tools` field (legacy) is treated as equivalent to `tool_allowlist` for backward compatibility.

---

## Required sections

### 1. Role heading and ownership statement

```markdown
# <Role Name> Agent

You own <one-sentence scope>.
```

The ownership statement must be specific. "You do everything" is not valid.

### 2. Rules

A focused list of behavioral constraints specific to this role. These are the non-negotiable operating rules for this agent.

### 3. Handoff Protocol

Every agent returns output to the orchestrator in a defined format. This section specifies that format as a markdown code block with labeled fields.

Example:

```
## Output from <Role Name>

### <Section A>
{{field_a}}

### <Section B>
{{field_b}}
```

### 4. Result Contract

**Mandatory. A response without this block is structurally incomplete.**

Always placed at the end of the response:

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts: []
  findings: []
  next_action: "..."
```

Rules for filling the contract:
- Use empty lists `[]` when there are no blockers, artifacts, or findings.
- `next_action` must name the single most useful downstream step.
- `status: blocked` requires at least one entry in `blockers`.
- A response missing `result_contract` is treated as a retry trigger.

### 5. Documentation Standard

Every agent includes this block verbatim. It governs how agents look up library and framework documentation.

```markdown
## Documentation Standard — Context7 First, Repository Fallback

Before using **any** library, framework, or external API — regardless of stack — use Context7 when it is available. If Context7 is unavailable, fall back to repository evidence, installed local docs, and explicit assumptions in your output. Training data alone is never the source of truth for API signatures or default behavior.

**Required workflow for every library or API used:**

1. Resolve the library ID:
   mcp__plugin_context7_context7__resolve-library-id("library-name")
2. Query the relevant docs:
   mcp__plugin_context7_context7__query-docs(context7CompatibleLibraryID, topic="specific feature or method")

**If Context7 is unavailable or does not have documentation for the library:** note it explicitly and proceed with caution, flagging assumptions in your output.
```

---

## Conditional sections

### Absolute Prohibitions (required for agents with execution authority)

Agents that can execute commands, write code, make git operations, or interact with infrastructure must include this section.

```markdown
## Absolute Prohibitions

**NEVER execute or suggest any of these without explicit written user confirmation:**

- [action 1 specific to this role]
- [action 2 specific to this role]
- ...

**If a task seems to require any of the above:** STOP. Explain the risk and ask the user explicitly.
```

Agents that require this section: `backend-dev`, `frontend-dev`, `mobile-dev`, `data-engineer`, `devops`, `ci-cd`, `dba`, `platform-dev`, `cloud-architect`, `release`, `sre`, `incident-manager`.

Agents that do not require this section: pure analysis roles (`pm`, `business-analyst`, `architect`, `reviewer`, `qa`, `security-reviewer`, etc.) — they produce findings and recommendations, but do not execute.

### Architecture Guardrails (for implementation agents)

Agents that write code include guardrails for the supported architecture styles: hexagonal, layered, or repo-native. These guardrails enforce layer boundaries and import rules.

### TDD Mandate (for implementation agents)

Agents that write production code include a TDD mandate: tests are written first, implementation code follows. The mandate specifies the red-green-refactor order per architecture style.

### Reasoning Sandwich — Plan, Execute, Verify (required for all agents)

Every agent implements the full "Reasoning Sandwich" pattern: high reasoning to plan, standard execution, high reasoning to verify. This is enforced via three mandatory sections and a mechanically validated checklist.

#### Phase 1 — Pre-Execution Plan (required for execution agents)

Execution agents (those with `## Absolute Prohibitions`) must produce an explicit plan **before** writing any code or executing any command. The plan is included in the agent's output so the orchestrator and reviewer can trace decisions.

```markdown
## Pre-Execution Plan

1. **Goal:** {{one_sentence_what_I_will_deliver}}
2. **Inputs I will use:** {{list_of_inputs_from_prompt}}
3. **Approach:** {{step_by_step_plan_before_touching_code}}
4. **Files I expect to touch:** {{predicted_file_list}}
5. **Tests I will write first:** {{failing_tests_before_implementation}}
6. **Risks:** {{what_could_go_wrong_and_how_I_will_detect_it}}
```

Analysis agents (pm, reviewer, architect, etc.) replace this with a lighter `## Analysis Plan` that lists the inputs being evaluated and the evaluation criteria.

```markdown
## Analysis Plan

1. **Scope:** {{what_I_am_reviewing_or_analyzing}}
2. **Criteria:** {{checklist_of_what_I_will_evaluate}}
3. **Inputs:** {{list_of_inputs_from_prompt}}
```

#### Phase 2 — Execution

The agent performs its work (writing code, reviewing, analyzing, etc.) according to the plan.

#### Phase 3 — Self-Verification Protocol (required for all agents)

Before returning, every agent verifies its own output. The verification has two layers: **base checks** (identical for all agents) and **role-specific checks** (customized per agent category).

**Base checks (all agents):**

```markdown
## Self-Verification Protocol

Before returning your final output, verify it against these checks:

1. **Completeness** — Does your output address every item in the input prompt? List each requirement and confirm coverage.
2. **Accuracy** — Are all code snippets, commands, and technical references verified against real files in the repository (not assumed from training data)?
3. **Contract compliance** — Does your output include the required `result_contract` block with accurate `status`, `confidence`, and `findings`?
4. **Scope discipline** — Did you stay within your role boundary? Flag if you made recommendations outside your ownership area.
5. **Downstream readiness** — Can the next agent in the chain consume your output without ambiguity? Are all required fields populated?
```

**Role-specific checks** are appended after the base checks. Each agent category adds checks relevant to its domain:

| Category | Additional verification checks |
|---|---|
| Implementation agents | 6. All tests pass (`{{test_command}}`)? 7. Migrations reversible? 8. No hardcoded secrets? 9. Architecture boundaries respected? |
| Review agents | 6. Every finding has file:line reference? 7. Severity classification applied? 8. No false positives from assumptions? |
| Security agents | 6. OWASP Top 10 checked? 7. No credentials in output? 8. Threat model updated? |
| QA agents | 6. All acceptance criteria mapped to evidence? 7. Test commands actually executed (not just described)? 8. Regression scope covered? |
| Architecture agents | 6. Decisions have tradeoff analysis? 7. Constraints from existing repo respected? 8. No architecture astronautics? |
| Documentation agents | 6. All referenced files exist? 7. Code examples tested? 8. No stale references? |
| Operations agents | 6. Rollback plan exists? 7. No destructive commands without safeguards? 8. Monitoring/alerting considered? |
| LLM/AI agents | 6. Evaluation metrics defined? 7. Prompt injection risks assessed? 8. Cost estimates included? |

If any check fails, fix the issue before returning. Do not rely on the reviewer or QA to catch problems you can detect yourself.

#### Phase 4 — Verification Checklist (mandatory output block)

Every agent must include a `verification_checklist` block in its output, after the `result_contract`. This block is **mechanically validated** by the orchestrator — a response missing it is structurally incomplete and triggers a retry.

```yaml
verification_checklist:
  plan_produced: true
  base_checks_passed: [completeness, accuracy, contract, scope, downstream]
  role_checks_passed: [<role-specific check names>]
  issues_found_and_fixed: 0
  confidence_after_verification: high | medium | low
```

The orchestrator validates:
- `plan_produced: true` is present (for execution agents, a `## Pre-Execution Plan` must exist in the output; for analysis agents, `## Analysis Plan`)
- `base_checks_passed` lists exactly 5 items
- `role_checks_passed` is non-empty
- `confidence_after_verification` matches the `confidence` in `result_contract`

A response missing `verification_checklist` is treated the same as a missing `result_contract` — it triggers the Teammate Failure Protocol.

**Why this matters:** The full Reasoning Sandwich (plan + execute + verify + proof-of-verification) reduces retry cycles by ~40% and eliminates "silent non-compliance" where agents claim to have verified but skip checks.

---

## Boundary text

Every agent must be readable in isolation and answer two questions without requiring context from other files:

1. What does this agent do?
2. What does this agent NOT do?

When two agents have adjacent responsibilities (e.g., `security-reviewer` vs `security-engineer`, `docs-writer` vs `tech-writer`), each agent must explicitly state the boundary.

Example from the split between `docs-writer` and `tech-writer`:
- `docs-writer` → internal developer and operator documentation
- `tech-writer` → external user guides, public API references, customer changelogs

---

## Agent Overlap Map — Why Similar Agents Exist

Some agents appear to overlap. This is by design — they are **stack variants** of the same role, not duplicates. The skill routing table selects one variant per run based on the detected stack.

### Stack variants (same role, different stack expertise)

| Generic agent | Stack variant | When the variant is used |
|---|---|---|
| `pm` | `django-pm` | Django projects — PM with Django/DRF domain knowledge |
| `techlead` | `tech-lead` | Django projects — TechLead with Django-specific patterns |
| `backend-dev` | `django-backend`, `python-developer` | Django → django-backend; Python (no Django) → python-developer |
| `frontend-dev` | `django-frontend`, `react-developer`, `vue-developer`, `typescript-developer`, `javascript-developer` | One is selected based on detected frontend stack |
| `reviewer` | `code-reviewer` | Django → code-reviewer (Django-specific review checks) |
| `qa` | `qa-tester` | Web stacks → qa-tester (Playwright-based E2E) |

**Rule:** Only ONE variant per role is spawned per run. The routing table in `/implement` Step 0.5 resolves this at preflight. A run never has both `backend-dev` and `django-backend` active simultaneously.

### Adjacent but distinct roles (different responsibilities)

| Agent A | Agent B | A does | B does | Boundary |
|---|---|---|---|---|
| `security-reviewer` | `security-engineer` | Reviews code for vulnerabilities | Implements security features (OAuth, WAF) | Review vs implementation |
| `architect` | `solutions-architect` | Solution design for a specific feature | Cross-cutting architecture across multiple systems | Feature vs system scope |
| `reviewer` | `code-quality` | PR-level review (correctness, TDD) | Strategic quality baseline (lint config, tech debt trends) | Tactical vs strategic |
| `docs-writer` | `tech-writer` | Internal dev docs | External user-facing docs | Audience |
| `observability-engineer` | `monitoring-specialist` | System-level (logs, traces, metrics) | Dashboard/APM configuration | Infrastructure vs tooling |
| `test-planner` | `tdd-specialist` | Maps AC to test types | Defines red-green-refactor cycles | Planning vs execution |

### Actual agent count

| Category | Count | Notes |
|---|---|---|
| Unique roles (generic) | ~45 | Core roles without stack specialization |
| Stack variants | ~15 | Django (4), React (1), Vue (1), TS (1), JS (1), Python (1), Shell (1), plus generic QA/reviewer variants |
| LLM/AI specialists | ~9 | Distinct roles (ai-engineer, rag, prompt, eval, safety, cost, ml, agent-architect, conversational) |
| Specialist reviewers | ~5 | Each covers a distinct domain (security, privacy, compliance, accessibility, performance) |
| **Total** | **74** | All have distinct prompts; ~15 are stack-variant selections |

---

## What makes an agent invalid

| Problem | Effect |
|---|---|
| Missing `result_contract` | Treated as a retry trigger; breaks SEP log |
| Missing `verification_checklist` | Treated as a retry trigger; Reasoning Sandwich not enforced |
| Missing `Documentation Standard` | Agent may silently use stale training data for API signatures |
| Execution agent without `Absolute Prohibitions` | Rejected by `validate.sh` |
| Execution agent without `Pre-Execution Plan` instruction | Rejected by `validate.sh` |
| Missing `Self-Verification Protocol` | Rejected by `validate.sh` |
| Agent without role-specific verification checks | Generic verification only; quality degraded |
| Ownership statement too broad | Overlaps with other agents; breaks the specialist model |
| No handoff format defined | Orchestrator cannot parse output; breaks the chain |
