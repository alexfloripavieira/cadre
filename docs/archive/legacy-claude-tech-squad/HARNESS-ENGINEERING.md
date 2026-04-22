# Harness Engineering — From Prompt Executor to Production Agent

A practical guide to the discipline that makes AI agents reliable.

---

## Why This Document Exists

Most developers use Claude Code as a **prompt executor**: type a request, get a response, manually verify, repeat. This works for small tasks but fails at scale because:

- The agent has no memory between tasks
- There are no guardrails against destructive actions
- There is no way to know if the output is good without reading every line
- Errors compound silently across multi-step workflows
- Cost is unpredictable

Harness Engineering solves this by wrapping the AI agent in **infrastructure that makes it reliable** — the same way a horse needs reins, saddle, and stirrups to be useful, not just raw power.

This document explains every concept and shows exactly how `claude-tech-squad` implements each one.

---

## The Metaphor

| Component | Horse | AI Agent |
|---|---|---|
| Raw power | Fast, strong, can run anywhere | Intelligent, can write any code |
| Without harness | Runs in random directions, dangerous | Hallucinates, breaks things, wastes tokens |
| With harness | Directed, controlled, productive | Guided, safe, reliable |
| Harness | Reins + saddle + stirrups + bridle | Rules + tools + guardrails + feedback loops |

**The model is not the product. The harness is.**

---

## The 5 Pillars

### Pillar 1 — Tool Orchestration

**What:** Define which tools each agent can access, with which permissions.

**Why:** An agent with access to everything is an agent that can break everything. A `docs-writer` does not need `Bash`. A `security-reviewer` does not need `Edit`.

**How claude-tech-squad implements it:**

| Mechanism | File | What it does |
|---|---|---|
| `tool_allowlist` per agent | Every agent `.md` frontmatter | Declares exactly which tools the agent may use |
| Category defaults | `runtime-policy.yaml` `tool_allowlists` | 5 categories: analysis, implementation, documentation, operations, orchestrator |
| Anti self-chaining | `validate.sh` | Only `incident-manager` can use the `Agent` tool — prevents agents from spawning agents |
| Namespace enforcement | `validate.sh` | All `subagent_type` values must use `claude-tech-squad:` prefix |

**Without this:** Any agent could execute `rm -rf /`, push to main, or spawn infinite sub-agents.

---

### Pillar 2 — Guardrails and Constraints

**What:** Deterministic rules that prevent dangerous actions — enforced mechanically, not by prompt.

**Why:** Prompts can be ignored. A hook that exits with code 2 cannot be ignored.

**How claude-tech-squad implements it:**

| Mechanism | File | What it does |
|---|---|---|
| PreToolUse hook | `hooks/pre-tool-guard.sh` | Blocks 9 destructive patterns: DROP TABLE, force-push, --no-verify, terraform destroy, rm -rf, eval $, production DB access |
| Global Safety Contract | Every SKILL.md | 11 prohibitions that apply to every teammate — cannot be overridden by urgency |
| Absolute Prohibitions | 27 execution agents | Role-specific prohibitions (e.g., backend-dev cannot hardcode secrets) |
| Token circuit breaker | `runtime-policy.yaml` `cost_guardrails` | Warns at 75%, halts at 100% of token budget |
| Severity policy | `runtime-policy.yaml` `severity_policy` | BLOCKING findings stop the pipeline; WARNING continues with log; INFO is optional |

**The key insight:** Prompts say "please don't do X". Hooks say "you literally cannot do X". In production, only the second is reliable.

---

### Pillar 3 — Error Recovery and Feedback Loops

**What:** When an agent fails, the system recovers automatically before asking the human.

**Why:** Agents fail. The question is not "if" but "how does the system respond when they do?"

**How claude-tech-squad implements it:**

| Mechanism | File | What it does |
|---|---|---|
| Retry (max 2) | `runtime-policy.yaml` `failure_handling` | Same agent, same prompt — catches transient failures |
| Fallback matrix | `runtime-policy.yaml` `fallback_matrix` | Different agent with same input — catches agent-specific failures |
| Doom loop detection | `runtime-policy.yaml` `doom_loop_detection` | 3 patterns (growing diff, oscillating fix, same error) — catches futile retries |
| Inline health check | Every orchestrator SKILL.md | 6 signals checked after every teammate — adjusts next agent's context |
| Gate consolidation | `implement` SKILL.md | Multiple failures → single user decision instead of N sequential prompts |
| User gate (R/S/X) | Every SKILL.md | Last resort: Retry / Skip with risk / Abort |
| Self-verification | Every agent `.md` | Agent checks own output before returning (catches ~20% of errors at source) |

**The recovery ladder:**

```
Agent fails
  → Doom loop check (is it diverging?)
    → If yes: skip to fallback
    → If no: retry (max 2)
      → Still fails: invoke fallback agent
        → Fallback also fails: surface gate to user (R/S/X)
```

**Without this:** One agent failure kills the entire run. The dev has to restart from scratch.

---

### Pillar 4 — Observability

**What:** Record every action, cost, and decision so humans can monitor and improve.

**Why:** If you can't see what happened, you can't fix it. Invisible failures are the most dangerous.

**How claude-tech-squad implements it:**

| Mechanism | File | What it does |
|---|---|---|
| Trace lines (18 types) | Every SKILL.md | `[Teammate Spawned]`, `[Gate]`, `[Doom Loop]`, etc. — visible proof of execution |
| SEP logs | `ai-docs/.squad-log/` | Structured YAML with tokens, duration, retries, fallbacks per run |
| Token tracking per teammate | SEP log `teammate_token_breakdown` | Know which agent costs the most |
| Live dashboard | `dashboard/live.html` | Real-time browser dashboard with auto-refresh every 2s |
| Health check signals | `[Health Check]` trace line | Per-teammate health status visible in dashboard |
| Factory retrospective | `/factory-retrospective` skill | Deep analysis of patterns across multiple runs |
| Developer feedback | SEP log `developer_feedback` | 1-4 satisfaction score correlated with metrics |
| Preflight chain validation | `/implement` preflight | Checks that upstream discovery SEP log exists |

**The observability stack:**

```
Real-time (during execution):
  └── Trace lines in CLI
  └── Live dashboard in browser
  └── Health check signals per teammate

Post-run (after execution):
  └── SEP log with full metrics
  └── Developer feedback score

Periodic (across multiple runs):
  └── /factory-retrospective analysis
  └── /dashboard health summary
```

---

### Pillar 5 — Human-in-the-Loop (HITL)

**What:** The human makes decisions at critical points. The agent handles everything else.

**Why:** Some decisions require human judgment (UAT, release, architecture). Others don't (retry, fallback, lint). The skill is knowing which is which.

**How claude-tech-squad implements it:**

| Mechanism | File | What it does |
|---|---|---|
| Gates at every phase | Every SKILL.md | User approves scope, architecture, UAT, release |
| Mandatory gates | `runtime-policy.yaml` `auto_advance.mandatory_gates` | UAT, release, deploy, conformance — NEVER auto-advanced |
| Auto-advance | `runtime-policy.yaml` `auto_advance` | Non-mandatory gates skip automatically when all agents return high confidence + zero BLOCKING |
| Escape hatch | `/squad` SKILL.md | User can jump forward from any gate (skip discovery → go to implement) |
| R/S/X pattern | Every failure gate | Retry / Skip with risk / Abort — standardized across all skills |
| Developer feedback | End of every run | Quick 1-4 score + optional comment |

**The HITL principle:** Automate what the agent can handle reliably. Escalate what requires judgment. Never surprise the human.

---

## The 5 Practical Concepts

### Concept 1 — Rule Files (CLAUDE.md / AGENTS.md)

**What:** Machine-readable files in the repository that instruct the agent about project conventions.

**Why:** Every project has conventions that are not in the code — architecture patterns, naming rules, forbidden patterns, deployment procedures. Without rule files, the agent guesses.

**How claude-tech-squad implements it:**

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project-level rules — validation commands, architecture, change classes |
| `docs/AGENT-CONTRACT.md` | Agent structure rules — required sections, frontmatter, verification |
| `docs/SKILL-CONTRACT.md` | Skill structure rules — required blocks, gates, checkpoints, SEP log |
| `runtime-policy.yaml` | Runtime rules — retry budgets, fallbacks, cost limits, doom loop detection |
| Each agent `.md` | Agent-specific rules — role boundary, prohibitions, verification checks |

**The rule file hierarchy:**

```
runtime-policy.yaml (global runtime behavior)
  └── SKILL-CONTRACT.md (skill structure requirements)
    └── Each SKILL.md (skill-specific execution rules)
      └── AGENT-CONTRACT.md (agent structure requirements)
        └── Each agent.md (agent-specific behavior rules)
          └── Project CLAUDE.md (project-specific conventions)
```

---

### Concept 2 — Progressive Disclosure

**What:** Give the agent a small map, not a full manual. Load details on demand.

**Why:** LLMs have limited context windows. Sending every agent the full output of every prior agent wastes tokens and dilutes focus.

**How claude-tech-squad implements it:**

| Mechanism | Where |
|---|---|
| Context digests (max 500 tokens) | Between sequential agents in discovery and implement |
| Full output only to agents that need it | Reviewer gets full diff; PM gets full ACs; others get digests |
| `(full)` vs `(digest)` labels in prompts | Every agent spawn prompt explicitly marks what is full vs summarized |
| `summarize()` instructions | Before each spawn, orchestrator produces digest of prior output |

**Example from /implement:**

```
TDD Specialist:  full test plan + full TDD delivery plan + architecture digest
Backend Dev:     full failing tests + their workstream + blueprint digest
Reviewer:        full implementation diff + architecture digest + test plan digest
QA:              full acceptance criteria + full test plan + implementation digest
Docs Writer:     full implementation + all other outputs as digests
PM UAT:          full acceptance criteria + QA/conformance/quality digests
```

**The savings:** ~20-30% fewer tokens per run because agents receive only what they need.

---

### Concept 3 — Mechanical Enforcers

**What:** Automated rules (hooks, scripts, CI) that enforce constraints without depending on prompts.

**Why:** A prompt can say "don't push to main". A CI check that blocks the push is more reliable.

**How claude-tech-squad implements it:**

| Enforcer | What it checks | How many checks |
|---|---|---|
| `validate.sh` | Agent contracts, skill contracts, runtime policy keys, Harness Engineering sections | 39 exit-1 checks |
| `smoke-test.sh` | Full validation ladder + dogfood + release bundle | ~50 assertions |
| `dogfood.sh` | Fixture integrity, scenario count, structure | ~20 assertions |
| `pre-tool-guard.sh` | Destructive Bash commands at runtime | 9 pattern blocks |
| GitHub Actions `validate.yml` | Runs smoke-test on every PR | CI gate |
| GitHub Actions `release.yml` | Runs smoke-test before publishing | Release gate |

**The enforcement pyramid:**

```
Runtime (during execution):
  └── pre-tool-guard.sh blocks destructive commands

PR time (before merge):
  └── validate.yml runs smoke-test.sh

Release time (before publish):
  └── release.yml runs smoke-test.sh + build bundle

Development time (before commit):
  └── Developer runs validate.sh locally
```

---

### Concept 4 — Reasoning Sandwich

**What:** High reasoning to plan → standard execution → high reasoning to verify.

**Why:** Agents that jump straight to execution skip planning (wrong approach) and verification (wrong output). The sandwich forces both.

**How claude-tech-squad implements it:**

| Phase | Section in agent | What happens |
|---|---|---|
| **Plan** | `## Pre-Execution Plan` (execution agents) or `## Analysis Plan` (analysis agents) | Agent declares: goal, inputs, approach, files to touch, tests to write first, risks |
| **Execute** | Agent's main body | Agent performs the work |
| **Verify** | `## Self-Verification Protocol` | 5 base checks + 3-4 role-specific checks per category |
| **Prove** | `verification_checklist` output block | Mechanically validated by orchestrator — missing = retry trigger |

**9 role-specific check categories:**

| Category | Checks |
|---|---|
| Implementation | Tests pass, no secrets, architecture boundaries, migrations reversible |
| Review | File:line references, severity classification, no false positives |
| Security | OWASP Top 10, no credentials in output, threat model |
| QA | ACs mapped to evidence, commands executed, regression scope |
| Architecture | Tradeoff analysis, repo conventions respected, no over-engineering |
| Documentation | References valid, examples tested, no stale content |
| Operations | Rollback plan, no unguarded destructive commands, monitoring |
| LLM/AI | Eval metrics defined, prompt injection assessed, cost estimate |
| Planning | Actionable outputs, repo constraints, bounded scope |

---

### Concept 5 — Entropy Management (Garbage Collection)

**What:** Periodic cleanup agents that detect drift, stale artifacts, and process degradation.

**Why:** Over time, repositories accumulate: orphaned branches, stale documentation, unremediated security findings, discoveries that were never implemented. Without cleanup, entropy grows silently.

**How claude-tech-squad implements it:**

| Mechanism | Where | What it does |
|---|---|---|
| Auto-trigger retrospective | `runtime-policy.yaml` `entropy_management` | After every 5 runs, suggests `/factory-retrospective` |
| Orphan detection at preflight | `/implement` and `/squad` preflight | Warns if discoveries older than 7 days were never implemented |
| Stale artifact detection | `/factory-retrospective` Step 9b | Finds files older than 30 days with no SEP log |
| Broken chain detection | `/factory-retrospective` Step 9c | Finds discovery→implement→hotfix→postmortem chains with missing links |
| Token cost trend analysis | `/factory-retrospective` Step 9d | Shows if cost per run is increasing, stable, or decreasing |
| Doom loop frequency | `/factory-retrospective` Step 9e | Counts doom loops and recommends prompt improvements |
| Retro counter file | `ai-docs/.squad-log/.retro-counter` | Tracks runs since last retrospective |

---

## The 5 Levels of Agentic Development

| Level | Name | What the human does | What the AI does |
|---|---|---|---|
| L0 | Spicy Autocomplete | Writes all code | Suggests the next line |
| L1 | AI as Coding Intern | Reviews output, owns architecture | Handles scoped tasks |
| L2 | AI as Junior Developer | Reviews all code as produced | Builds across files |
| **L3** | **Developer as Manager** | **Defines spec, reviews at feature/PR level** | **AI builds. Review at feature level.** |
| **L4** | **Product Engineer** | **Passes spec to agents, reviews product outcomes** | **AI builds and reviews. Human skims code.** |
| L5 | The Dark Factory | Nothing | Fully autonomous. Code is black box. |

**claude-tech-squad operates at L3-L4:**

| Skill | Level | Why |
|---|---|---|
| `/squad` | L4 | Human gives intent → gets delivery. Reviews UAT, not code. |
| `/discovery` | L4 | Human gives intent → gets blueprint. Reviews outcomes. |
| `/implement` | L3 | Human gives blueprint → AI builds. Reviews at gates. |
| `/bug-fix` | L3 | Human describes bug → AI diagnoses and fixes. |
| `/hotfix` | L3 | Human describes symptom → AI patches. |
| `/pr-review` | L3 | Human points to PR → AI reviews with 6 specialists. |
| `/security-audit` | L2.5 | AI analyzes → human decides what to fix. |

**Why not L5?** The plugin has mandatory gates (UAT, release, deploy, conformance) that never auto-advance. This is by design — L5 without guardrails is dangerous. L3-L4 with Harness Engineering is the sweet spot: **the productivity of automation with the safety of human oversight**.

---

## How It All Connects

```
Developer types: /squad APP-123

                    ┌─────────────────────────┐
                    │      PREFLIGHT           │
                    │  • Read ticket (Jira)    │
                    │  • Detect stack          │
                    │  • Load runtime policy   │
                    │  • Check cost budget     │
                    │  • Orphan detection       │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │      DISCOVERY           │
                    │  PM → BA → PO → Planner  │
                    │  → Architect → TechLead   │
                    │  → Specialists → TDD      │
                    │                           │
                    │  [Gates at each step]     │
                    │  [Health check after each]│
                    │  [Digests between agents] │
                    │  [Dashboard updates live] │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │     IMPLEMENTATION        │
                    │  TDD → Impl → Review     │
                    │  → QA → Conformance       │
                    │  → Quality Bench → Docs   │
                    │  → UAT                    │
                    │                           │
                    │  [Retry + fallback loops] │
                    │  [Doom loop detection]    │
                    │  [Cost circuit breaker]   │
                    │  [Token tracking]         │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │      POST-RUN            │
                    │  • Write SEP log         │
                    │  • Developer feedback    │
                    │  • Update Jira ticket    │
                    │  • Increment retro counter│
                    │  • Update live dashboard │
                    └─────────────────────────┘
```

**Every box in this diagram has:**
- A trace line that proves it executed
- A health check that monitors its output
- A fallback if it fails
- A gate if human judgment is needed
- A cost counter tracking tokens
- A checkpoint for resume if interrupted

**That is Harness Engineering.** Not one feature — a complete system that makes the agent reliable enough to trust with real work.

---

## Summary: Prompt Engineering vs Context Engineering vs Harness Engineering

| Dimension | Prompt Engineering | Context Engineering | Harness Engineering |
|---|---|---|---|
| **Focus** | How to ask better | What the model sees | How the environment works |
| **Scope** | One interaction | One context window | Complete autonomous system |
| **Artifact** | A prompt | A context assembly | Rules + tools + guardrails + feedback loops |
| **Failure mode** | Bad response | Missing context | Uncontrolled agent |
| **When it matters** | Always | When context is large | When the agent runs multi-step, long-duration, in production |

**You need all three.** Prompt engineering writes good agent prompts. Context engineering assembles the right information. Harness engineering makes the whole system reliable. `claude-tech-squad` is primarily a Harness Engineering artifact — the prompts and context are important, but the infrastructure around them is what makes it production-grade.
