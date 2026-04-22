# Claude Tech Squad — Technical Manual

**Version:** 5.51.0
**Plugin:** `claude-tech-squad`

---

## Table of Contents

1. [What the plugin is](#1-what-the-plugin-is)
2. [Installation and activation](#2-installation-and-activation)
3. [squad-cli — embedded orchestrator](#3-squad-cli--embedded-orchestrator)
4. [Teammate Mode — tmux pane per agent](#4-teammate-mode--tmux-pane-per-agent)
5. [Available skills and when to use each](#5-available-skills-and-when-to-use-each)
6. [Full flow for each skill](#6-full-flow-for-each-skill)
7. [The 74 agents — roles and specialties](#7-the-74-agents--roles-and-specialties)
8. [Pipeline architecture](#8-pipeline-architecture)
9. [User gates](#9-user-gates)
10. [Execution visibility](#10-execution-visibility)
11. [Usage rules](#11-usage-rules)
12. [Quick reference](#12-quick-reference)
13. [Absolute Prohibitions — safety guardrails](#13-absolute-prohibitions--safety-guardrails)
14. [Squad Execution Protocol (SEP) — artifacts and traceability](#14-squad-execution-protocol-sep--artifacts-and-traceability)

---

## 1. What the plugin is

`claude-tech-squad` is a complete software delivery team running inside Claude Code. Each skill starts a pipeline where specialist agents work in sequence or in parallel — each with an exact scope and no overlap.

**Core principles:**

- Each agent owns exactly one specialty.
- The pipeline can run in two modes: inline (subagent) or teammate (tmux pane per agent).
- TDD is the standard for any code change.
- User gates exist only at points where human decision is irreplaceable.
- Every execution emits visibility lines in the terminal.

---

## 2. Installation and activation

### Via marketplace (recommended)

```bash
# Add the marketplace once per machine
claude plugin marketplace add alexfloripavieira/claude-tech-squad

# Install globally (any repository)
claude plugin install -s user claude-tech-squad@alexfloripavieira-plugins

# Or only for the current project
claude plugin install -s project claude-tech-squad@alexfloripavieira-plugins
```

### Auto-update

To receive updates automatically, add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "alexfloripavieira-plugins": {
      "source": { "source": "github", "repo": "alexfloripavieira/claude-tech-squad" },
      "autoUpdate": true
    }
  }
}
```

---

## 3. squad-cli — embedded orchestrator

The plugin includes `squad-cli` at `plugins/claude-tech-squad/bin/squad-cli` — a Python tool that handles deterministic orchestration tasks outside the LLM.

### What it does

Skills like `/squad`, `/implement`, `/discovery`, `/hotfix`, and `/bug-fix` call squad-cli automatically during execution to:

| Task | Without squad-cli (LLM) | With squad-cli (Python) |
|---|---|---|
| Detect project stack and route to correct agents | LLM reads files, parses JSON, resolves table (~5K tokens) | Instant JSON response (<100ms) |
| Health check after each teammate (6 signals) | LLM evaluates rules from prompt (~2K tokens each) | Deterministic if/else in Python |
| Detect doom loops in retries | LLM compares outputs "in its head" (~2K tokens) | `difflib` comparison with 3 rules |
| Track token budget and cost | LLM estimates (~2K tokens) | Real arithmetic from collected data |
| Save/restore checkpoints for resume | LLM re-interprets Markdown (~3K tokens) | JSON state machine |
| Generate SEP execution logs | LLM writes 60+ line YAML template (~5K tokens) | Template from real data |

### Estimated savings

- `/squad` (~20 teammates): ~$3-4.50 overhead reduced to ~$0.40-0.75 (80-85% reduction)
- `/bug-fix` (~5 teammates): ~$1-1.50 reduced to ~$0.20-0.30

### Supported stacks

Django, React, Vue, TypeScript, JavaScript, Python, Go, Rust, Java, Ruby, PHP, .NET, Elixir. Detects signal files up to 3 subdirectory levels deep (monorepo support).

### Requirements

- Python 3.10+
- PyYAML and Click (auto-installed on first run)

### Dry-run mode

Preview the full execution plan without spending any tokens:

```bash
python3 plugins/claude-tech-squad/bin/squad-cli dry-run \
  --skill squad \
  --policy plugins/claude-tech-squad/runtime-policy.yaml \
  --project-root .
```

### Without Python 3

All skills work without squad-cli. The LLM falls back to executing the same logic from prompt instructions. No features are lost — only cost efficiency.

---

## 4. Teammate Mode — tmux pane per agent

By default, agents run as inline subagents in the same Claude session. With teammate mode active, each specialist opens in its own tmux pane — one independent Claude Code instance per agent.

### Configuration

Add to `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_TEAMMATE_MODE": "tmux"
  }
}
```

### How to start

```bash
# Create tmux session
tmux new-session -s squad

# Start Claude Code inside the session
claude
```

### What happens

With teammate mode active, each `/discovery`, `/implement`, and `/squad`:

1. Creates a team via `TeamCreate`
2. Spawns each specialist with `Agent(team_name=..., name=..., subagent_type=...)`
3. Each specialist opens in its own pane
4. The orchestrator coordinates and presents gates

Without tmux mode, the same workflows run correctly as inline subagents — same outputs, same gates, no visual panes.

---

## 5. Available skills and when to use each

| Skill | When to use |
|---|---|
| `/onboarding` | First command in any new repo. Bootstrap of ai-docs/, CLAUDE.md, security baseline. |
| `/squad` | Complete feature from scratch to deploy. Includes discovery + build + release. |
| `/discovery` | Plan before implementing. Produces a complete blueprint without writing code. |
| `/implement` | Implement from an existing blueprint (output of `/discovery`). |
| `/refactor` | Safe refactoring with characterization tests. Behavior does not change. |
| `/bug-fix` | Fix a specific bug with a stack trace or repro steps. 1–5 files. |
| `/hotfix` | Production is broken. Minimal patch + `hotfix/` branch + PR + deploy checklist. |
| `/release` | Cut a release: change inventory, rollback plan, release notes, tag. |
| `/pr-review` | Review any PR. Parallel specialist bench + GitHub threads. |
| `/incident-postmortem` | Post-incident. Timeline, root cause, 5-whys, action items, shareable doc. |
| `/security-audit` | Periodic or pre-release security audit. Runs bandit, pip-audit, npm audit. |
| `/migration-plan` | Plan a database schema change before modifying models. |
| `/cloud-debug` | Investigate a problem in cloud/production with logs and infra. |
| `/dependency-check` | Check outdated dependencies, vulnerabilities, licenses, supply chain. |
| `/factory-retrospective` | Analyze recent executions and improve the team process. |
| `/pre-commit-lint` | Configure automatic lint hook on commits. |
| `/llm-eval` | **[AI]** Run eval suite as CI gate. Detects quality regressions before deploy. |
| `/prompt-review` | **[AI]** Review prompt changes: regression on golden examples, prompt injection, token cost. |
| `/multi-service` | **[Distributed]** Coordinate changes affecting multiple services: contracts, deployment ordering, blast radius. |
| `/iac-review` | **[Infra]** Review IaC changes before apply: blast radius, IAM/network security, cost impact, safe sequence. |

### Stack-aware vs Stack-agnostic skills

**Stack-aware** skills detect the project stack at preflight and automatically route to the correct specialist agent — you never have to specify which agent to use.

| Routing variable | Django | React | Vue | TypeScript | JavaScript | Python | Generic |
|---|---|---|---|---|---|---|---|
| `{{backend_agent}}` | `django-backend` | `backend-dev` | `backend-dev` | `backend-dev` | `backend-dev` | `python-developer` | `backend-dev` |
| `{{frontend_agent}}` | `django-frontend` | `react-developer` | `vue-developer` | `typescript-developer` | `javascript-developer` | `frontend-dev` | `frontend-dev` |
| `{{reviewer_agent}}` | `code-reviewer` | `reviewer` | `reviewer` | `reviewer` | `reviewer` | `reviewer` | `reviewer` |
| `{{qa_agent}}` | `qa-tester` | `qa-tester` | `qa-tester` | `qa-tester` | `qa-tester` | `qa` | `qa` |
| `{{impl_agent}}` | `django-backend` | `react-developer` | `vue-developer` | `typescript-developer` | `javascript-developer` | `python-developer` | `backend-dev` |

Skills with stack routing: `/squad`, `/implement`, `/discovery`, `/bug-fix`, `/hotfix`, `/refactor`, `/pr-review`.

**Stack-agnostic** skills always spawn the same specialist regardless of stack — no routing needed:

| Skill | Why agnostic |
|---|---|
| `/security-audit` | Always spawns `security-reviewer` — stack-independent analysis |
| `/dependency-check` | Reads lock files directly; `security-reviewer` handles all ecosystems |
| `/cloud-debug` | Infrastructure domain — spawns `cloud-architect` + `sre` |
| `/iac-review` | Terraform/Pulumi is stack-neutral; spawns `cloud-architect` |
| `/llm-eval` | AI domain — spawns `ai-engineer` + `ml-engineer` |
| `/prompt-review` | Prompt analysis — spawns `ai-engineer` |
| `/onboarding` | Read-only repo analysis; no implementation agent |
| `/release` | Pipeline scripts — no app-stack agent |
| `/incident-postmortem` | Documentation — no implementation agent |
| `/factory-retrospective` | Analyzes SEP logs — no implementation agent |
| `/pre-commit-lint` | Configures lint hooks — the lint command varies, not the agent |
| `/migration-plan` | Schema/SQL review — `dba` is appropriate for all stacks |
| `/multi-service` | Contract testing across services — stack-neutral orchestration |

---

**Escalation rule:**

```
new repo                    → /onboarding (first)
production broken           → /hotfix
incident resolved           → /incident-postmortem
bug 1–5 files               → /bug-fix
tech debt                   → /refactor
new feature                 → /squad  (auto-detects LLM → activates AI bench)
plan first                  → /discovery → /implement
schema will change          → /migration-plan (before /squad or /implement)
release ready               → /release
periodic audit              → /security-audit
review PR                   → /pr-review
changed prompt/RAG          → /llm-eval + /prompt-review (before merging)
cross-service change        → /multi-service (before implementing)
about to run terraform apply → /iac-review (before apply)
```

---

## 6. Full flow for each skill

### /discovery

**Objective:** Produce a complete Discovery & Blueprint Document without writing code.

**Input:** Feature or problem description.

**Flow (with teammate mode: each node = separate tmux pane):**

```
/discovery "feature X"
    │
    ├─ Repository recon (README, CLAUDE.md, package.json, pyproject.toml)
    ├─ TeamCreate → team "discovery"
    │
    └─ pm
         └─ ba
              └─ po ────────────────────────── [GATE 1: scope validation]
                   └─ planner
                        └─ [GATE 2: technical tradeoffs approved]
                             └─ architect
                                  └─ techlead ─────────────── [GATE 3: architecture direction]
                                       └─ PARALLEL BENCH (specialist notes)
                                            ├─ backend-architect
                                            ├─ frontend-architect
                                            ├─ api-designer
                                            ├─ data-architect
                                            ├─ ux-designer
                                            ├─ ai-engineer / agent-architect / rag-engineer (if LLM)
                                            ├─ prompt-engineer (if LLM)
                                            └─ others by context
                                       └─ PARALLEL QUALITY BASELINE
                                            ├─ security-reviewer
                                            ├─ privacy-reviewer
                                            ├─ performance-engineer
                                            └─ others by context
                                       └─ design-principles-specialist
                                            └─ test-planner
                                                 └─ tdd-specialist ── [GATE 4: final blueprint]
```

**Output:** Discovery & Blueprint Document with 13 sections + SEP artifacts:
- `ai-docs/{feature}/blueprint.md`
- `ai-docs/{feature}/adr/ADR-NNN-{slug}.md` — one per architectural decision (automatic)
- `ai-docs/.squad-log/{timestamp}-discovery-{run_id}.md`

**Proactive behaviors (no gate, automatic):**
- **ADRs**: after blueprint confirmation, generates one ADR per significant architectural tradeoff
- **Feature flag**: evaluates if the feature needs a flag — if yes, adds strategy to blueprint

**User gates:** 4 + 1 bridge gate (Contract 3)

The last gate after the blueprint presents:
```
Ready to start implementation now? [Y/N]
```
If Y: invokes `/implement` immediately with the blueprint.
If N: records `implement_triggered: false` in the log — detectable by `/factory-retrospective` as orphaned discovery.

---

### /implement

**Objective:** Implement from an existing blueprint.

**Required input:** Discovery & Blueprint Document.

**Flow:**

```
/implement
    │
    ├─ Step 0: Stack Command Detection (SEP)
    │   Reads Makefile / package.json / pyproject.toml / pom.xml
    │   → detects test_command, migrate_command, lint_command
    │   → override from CLAUDE.md if it exists
    │   Injects {{project_commands}} into all agents
    │
    ├─ Validation: blueprint exists in conversation?
    │   No → asks user to run /discovery first
    │
    ├─ TeamCreate → team "implement"
    │
    └─ tdd-specialist (failing tests first)
         └─ PARALLEL IMPLEMENTATION
              ├─ backend-dev
              ├─ frontend-dev
              ├─ mobile-dev (if mobile)
              └─ data-engineer (if pipeline)
         └─ reviewer ◄──────────────────────── loop ──┐
              APPROVED → qa                            │
              CHANGES  → impl agent ──────────────────┘
         └─ qa (real test execution)
              PASS → quality bench
              FAIL → impl agent
         └─ PARALLEL QUALITY BENCH
              ├─ security-reviewer / security-engineer
              ├─ privacy-reviewer
              ├─ performance-engineer
              ├─ accessibility-reviewer
              ├─ chaos-engineer (if distributed system / LLM)
              └─ integration-qa
         └─ docs-writer
              └─ tech-writer (if external docs)
                   └─ jira-confluence-specialist
                        └─ coverage-gate (Step 9b) ─────────── [GATE if coverage dropped]
              │  Blocks UAT if delta < 0
              │  Options: [C]ontinue or [T]est more
              └─ pm ─────────────── [GATE 5: UAT]
                   REJECTED → [GATE: re-queue or skip]
                       R → impl agents with gap context ──────────────┐
                           reviewer → qa → quality bench → UAT ────────────┘
                   APPROVED → done
```

**User gates:** 1 UAT + 1 coverage (conditional) + 1 rejection re-queue (conditional)

**Proactive behavior (automatic):** load-test agent in quality bench when there are HTTP endpoints, queues, or batch jobs.

**SEP output:** `ai-docs/.squad-log/{timestamp}-implement-{run_id}.md` with `parent_run_id`, Completion Blocks, and `load_test_run`.

---

### /squad

**Objective:** Complete end-to-end delivery: discovery + build + release.

**Flow:** Full `/discovery` + full `/implement` + release chain with persistent team:

```
TeamCreate → team "squad" (persists across all phases)

[Discovery Chain — Gates 1-4]
    └─ [Build Chain — Gate 5: UAT]
         └─ release
              └─ sre ──[GO / NO-GO]
```

**User gates:** 5

**SEP output:** `ai-docs/.squad-log/{timestamp}-squad-{run_id}.md` with `runtime_policy_version`, `checkpoint_cursor`, `fallback_invocations`, and `release_result`.

---

### /bug-fix

```
/bug-fix
    ├─ [GATE: symptom + expected + repro + context]
    ├─ Stack detection → resolves {{backend_agent}}, {{frontend_agent}}, {{reviewer_agent}}, {{qa_agent}}
    └─ techlead (root cause)
         └─ tdd-specialist (failing test that proves the bug)
              └─ {{backend_agent}} or {{frontend_agent}} (minimal fix — PERFUMARIA GUARD active)
                   └─ {{reviewer_agent}} (only blocking findings: regression, crash, wrong fix)
                        └─ {{qa_agent}} (confirms fix + no regression)
```

**Escalate to /squad if:** root cause reveals an architectural problem or > 5 files.

**PERFUMARIA GUARD:** The implementation agent is prohibited from extracting helpers, eliminating duplication, renaming or reorganizing code beyond the direct path of the bug. The reviewer may only issue CHANGES REQUESTED for: fix does not resolve root cause, regression, crash, or corrupted shared state. DRY/refactor/style → always LOW/NIT, never blocks merge.

---

### /hotfix

**Objective:** Minimal emergency patch for broken production. Faster than `/bug-fix` — no deep investigation phase.

**Input:** Symptom, scope, deploy environment, base branch.

**Flow:**

```
/hotfix
    │
    ├─ [GATE 1: intake — symptom + scope + deploy target]
    │
    ├─ Stack detection → resolves {{impl_agent}}, {{reviewer_agent}}
    │
    ├─ git checkout -b hotfix/{{slug}} origin/{{base}}
    │
    ├─ techlead in root-cause mode (analysis without implementing)
    │
    ├─ [GATE 2: diagnosis confirmation]
    │
    ├─ {{impl_agent}} (minimal patch)
    │   Rule: no refactor, no new dependencies
    │
    ├─ {{reviewer_agent}} (lightweight — focus on regressions)
    │   CHANGES → back to impl
    │
    ├─ security-reviewer (conditional — only if auth/input/data)
    │
    ├─ git commit + git push + gh pr create
    │
    └─ [GATE 3: deploy checklist — staging → prod → monitor 15min]
```

**Escalate to /squad if:** fix requires > 5 files or reveals an architectural flaw.

**SEP output:** `ai-docs/.squad-log/{timestamp}-hotfix-{run_id}.md`

---

### /pr-review

**Objective:** Specialized code review with automatic thread creation on GitHub.

**Input:** PR URL or number, repo, confirmation to open threads.

**Flow:**

```
/pr-review
    │
    ├─ [GATE 1: PR URL + repo + open threads? Y/N]
    │
    ├─ gh pr view → metadata (title, base, head, files, diff)
    │
    ├─ Stack detection → resolves {{reviewer_agent}} (code-reviewer for Django, reviewer for others)
    │
    ├─ Detects relevant reviewers from changed files:
    │   always: {{reviewer_agent}}
    │   auth/input/secrets → security-reviewer
    │   PII/external data → privacy-reviewer
    │   queries/loops/render → performance-engineer
    │   UI/HTML/ARIA → accessibility-reviewer
    │   APIs/contracts → api-designer
    │   schema/migrations → dba
    │
    ├─ PARALLEL BENCH (all detected reviewers)
    │   Each receives the full diff
    │
    ├─ Consolidates findings + deduplicates file:line
    │   Severity conflict → uses the highest
    │
    ├─ Presents summary to user
    │
    ├─ [GATE 2: confirm opening threads on GitHub]
    │
    └─ gh api .../pulls/{n}/reviews --input /tmp/payload.json
       (uses --input with JSON file to avoid HTTP 422 array serialization bug)
```

**SEP output:** `ai-docs/.squad-log/{timestamp}-pr-review-{run_id}.md`

---

### /security-audit

In addition to the main report (`ai-docs/security-audit-YYYY-MM-DD.md`), automatically generates:
- `ai-docs/security-remediation-YYYY-MM-DD.md` — severity-organized checkboxes for tracking fixes (Contract 2)
- `ai-docs/.squad-log/{timestamp}-security-audit-{run_id}.md` — SEP log with finding counts

### /dependency-check

In addition to the main report (`ai-docs/dependency-check-YYYY-MM-DD.md`), automatically generates:
- `ai-docs/dependency-remediation-YYYY-MM-DD.md` — checkboxes per CVE and major updates
- `ai-docs/.squad-log/{timestamp}-dependency-check-{run_id}.md` — SEP log

### /factory-retrospective

Reads `ai-docs/.squad-log/` as the primary source (SEP-aware since v5.4.0). Detects:
- **Orphaned discoveries**: logs with `implement_triggered: false`
- **Remediation rate**: `- [x]` / `- [ ]` ratio in remediation files
- **Retry rate**: average `retry_count` per skill
- **UAT rejection rate**: logs with `uat_result: REJECTED`

Falls back to git log and markdown inference when no SEP logs exist.

### /onboarding

**Objective:** Complete bootstrap of a new repo for squad usage.

**Flow:**

```
/onboarding
    │
    ├─ Detects stack (package.json, pyproject.toml, pom.xml, go.mod, etc.)
    ├─ Evaluates current state (commits, tests, CI/CD)
    ├─ mkdir -p ai-docs/.squad-log
    ├─ Creates ai-docs/README.md
    ├─ Generates CLAUDE.md template (if not exists)
    ├─ Quick security scan (bandit/npm audit)
    ├─ Dependency scan (pip-audit/npm audit)
    └─ Generates ai-docs/project-baseline-YYYY-MM-DD.md
```

**SEP output:** `ai-docs/.squad-log/{timestamp}-onboarding-{run_id}.md`

---

### /release

**Objective:** Cut a release with change inventory, validation, rollback plan, release notes, and tag.

**Input:** Version, base branch, deploy target.

**Flow:**

```
/release
    │
    ├─ [GATE 1: version + base + target]
    │
    ├─ git log since last tag → categorizes by commit type
    ├─ gh pr list merged → included PRs
    ├─ Validates CI/CD + pending migrations
    │
    ├─ release agent → rollback plan + deploy checklist + GO/NO-GO
    ├─ sre → blast radius + canary recommendation + GO/NO-GO
    │
    ├─ Generates release notes (internal + user-facing)
    │
    ├─ [GATE 2: final confirmation — tag and publish?]
    │
    ├─ git tag + git push origin {{version}}
    └─ gh release create (if available)
```

**Proactive behaviors (automatic, no gate):**
- **cost-optimizer** analyzes every release before the final gate
- **Feature flag audit** detects pending flags and adds them to the deploy checklist

**Blocks** if release agent or SRE return NO-GO.

**SEP output:** `ai-docs/.squad-log/{timestamp}-release-{run_id}.md`

---

### /incident-postmortem

**Objective:** Blameless post-mortem after a production incident.

**Input:** Incident summary, impact, known timeline, artifacts (logs, stack traces).

**Flow:**

```
/incident-postmortem
    │
    ├─ [GATE 1: intake — impact + resolution required]
    │
    ├─ Collects evidence (git log, CI runs, hotfix PRs)
    ├─ Reconstructs timeline
    │
    ├─ incident-manager → root cause + 5-whys + contributing factors
    ├─ sre → observability gaps + reliability action items
    │
    ├─ Consolidates P1/P2/P3 action items
    └─ Generates ai-docs/postmortem-YYYY-MM-DD-{slug}.md
```

**Blameless principle:** focus on systems and processes, never on individuals.

**Proactive behavior (automatic):** runbook generated for each P1 action item, written to `ai-docs/runbook-{service}.md`.

**SEP output:** `ai-docs/.squad-log/{timestamp}-incident-postmortem-{run_id}.md` with `parent_run_id` and `runbook_artifact`.

---

### /refactor

**Objective:** Safe refactoring with characterization tests. Behavior does not change.

**Input:** Target (file/module/class), refactor objective, constraints.

**Flow:**

```
/refactor
    │
    ├─ [GATE 1: target + goal + constraints]
    ├─ Stack detection → resolves {{backend_agent}}, {{frontend_agent}}, {{reviewer_agent}}
    │
    ├─ design-principles-specialist → analysis + incremental plan
    │
    ├─ [GATE 2: plan approved?]
    │
    ├─ test-automation-engineer → characterization tests
    │   All tests MUST pass on current code before proceeding
    │
    ├─ For each step in the plan:
    │   ├─ {{backend_agent}} / {{frontend_agent}} → implements step
    │   ├─ {{test_command}} → MUST pass
    │   └─ [GATE if tests broke: Fix / Skip / Abort]
    │
    ├─ {{reviewer_agent}} → final review
    └─ {{test_command}} → final confirmation
```

**Escalate to /squad if:** behavior must change, or > 15 files.

**SEP output:** `ai-docs/.squad-log/{timestamp}-refactor-{run_id}.md`

---

### /migration-plan, /cloud-debug, /pre-commit-lint

See [OPERATIONAL-PLAYBOOK.md](OPERATIONAL-PLAYBOOK.md) for usage examples for each.

---

### /llm-eval

**Objective:** Run eval suite as CI gate for any feature with LLM.

**Input:** Project with prompt files and/or eval datasets (`.jsonl`, `*golden*.json`, etc.)

**Flow:**

```
/llm-eval
    │
    ├─ Discovers prompt files, eval datasets, installed framework
    ├─ Detects framework (RAGAS / DeepEval / PromptFoo) or emits SETUP_REQUIRED
    │
    ├─ llm-eval-specialist → eval plan + regression thresholds
    │
    ├─ Executes evals with available framework
    │    └─ Metrics: faithfulness, answer_relevance, context_precision, hallucination_rate
    │
    ├─ Compares against baseline (ai-docs/llm-eval-baseline.json)
    │    PASS        → proceeds
    │    REGRESSION  → [GATE] Investigate / Override / Update baseline
    │    WARNING     → notifies, does not block
    │    SETUP_REQUIRED → instructions to install framework + create golden dataset
    │
    ├─ rag-engineer → retrieval quality review (if RAG detected)
    │
    └─ Report: ai-docs/llm-eval-YYYY-MM-DD.md
       Baseline:  ai-docs/llm-eval-baseline.json
```

**CI gate:** Blocks release if any critical metric (faithfulness, answer_relevance) regressed > 5% vs. baseline.

**SEP output:** `ai-docs/.squad-log/{timestamp}-llm-eval-{run_id}.md`

---

### /prompt-review

**Objective:** Review prompt changes before merging — like code review, but for the model contract.

**Input:** Modified prompt file (detected via `git diff`) or prompt pasted by user.

**Flow:**

```
/prompt-review
    │
    ├─ git diff on prompt files (*.prompt, *.jinja2, prompts/*.*)
    │   No diff → asks user for file and previous version
    │
    ├─ Loads golden examples (if they exist)
    │
    ├─ prompt-engineer →
    │    ├─ Behavioral diff (what actually changed in model behavior?)
    │    ├─ Regression per golden example: STABLE / BETTER / REGRESSION / RISK
    │    ├─ Prompt injection check (direct + indirect via RAG documents)
    │    ├─ Token cost estimate (delta)
    │    └─ Verdict: APPROVED / CHANGES REQUESTED / BLOCKED
    │
    ├─ Automatic injection vulnerability scan
    │    └─ Input interpolation without delimiters
    │    └─ Retrieved documents treated as trusted content
    │
    ├─ GATE if BLOCKED (injection risk) → do not proceed until fixed
    │
    └─ Versions approved prompt: ai-docs/prompt-versions/YYYY-MM-DD/
```

**SEP output:** `ai-docs/.squad-log/{timestamp}-prompt-review-{run_id}.md`

---

### /multi-service

**Objective:** Coordinate changes affecting multiple services, ensuring contracts, deployment ordering, and blast radius are handled before any implementation.

**Input:** List of services involved (producers and consumers), nature of change (breaking vs. backward-compatible), repos and service mesh.

**Flow:**

```
/multi-service
    │
    ├─ [GATE 1: intake — service list + change + repos required]
    │
    ├─ Dependency map (contract files, event definitions, APIs)
    │
    ├─ integration-engineer →
    │    ├─ Contract analysis: breaking vs. backward-compatible
    │    ├─ Recommended Pact tests
    │    └─ Deployment ordering
    │
    ├─ architect →
    │    ├─ Cross-service design (Saga / outbox / circuit breakers)
    │    ├─ Failure modes and observability
    │    └─ Rollback strategy per service
    │
    ├─ [GATE 2: contract and architecture alignment]
    │
    ├─ techlead → delivery sequencing (work breakdown per service, mocks for parallel dev)
    │
    ├─ sre → blast radius + rollback readiness + canary per service
    │
    └─ Delivery package:
         ├─ ASCII dependency graph
         ├─ Contract changes table
         ├─ Deploy sequence staging → production
         └─ Rollback sequence
```

**Blocks** deploy of any service if contract tests are not passing yet.

**SEP output:** `ai-docs/.squad-log/{timestamp}-multi-service-{run_id}.md`

---

### /iac-review

**Objective:** Review IaC changes before `terraform apply`, `helm upgrade`, `cdk deploy`, or equivalent.

**Input:** IaC changeset (detected via `terraform plan`, `helm diff`, `git diff` on `.tf`/`.yaml` files).

**Flow:**

```
/iac-review
    │
    ├─ Detects stack (Terraform / Pulumi / CloudFormation / CDK / Ansible / Helm / K8s raw)
    │
    ├─ Gets changeset (plan/diff) — soft gate if not available
    │
    ├─ Static analysis: tfsec / checkov / kubesec (if available)
    │    CRITICAL/HIGH → blocking items
    │
    ├─ PARALLEL:
    │    ├─ devops → blast radius: stateful resources, shared resources, dependency order
    │    ├─ cloud-architect → IAM / network / encryption security / Well-Architected
    │    └─ cost-optimizer → estimated monthly delta
    │
    ├─ Consolidates report with safe apply sequence + rollback plan
    │
    ├─ [GATE: apply approval]
    │    CRITICAL findings or blast radius HIGH → requires written confirmation
    │
    └─ Saves ai-docs/iac-review-YYYY-MM-DD.md
```

**Blocks** apply if there are CRITICAL security findings or blast radius classified as HIGH without explicit confirmation.

**SEP output:** `ai-docs/.squad-log/{timestamp}-iac-review-{run_id}.md`

---

## 7. The 74 agents — roles and specialties

### Discovery & Planning

| Agent | Specialty |
|---|---|
| `pm` | Problem statement, user stories, ACs |
| `business-analyst` | Domain rules, workflows, edge cases |
| `po` | Prioritization, scope cuts, release increments |
| `planner` | Stack validation, technical feasibility, tradeoffs |
| `architect` | Solution design, workstreams, sequencing |
| `techlead` | Orchestrator: execution strategy, sequencing, ownership |

### Architecture Specialists

| Agent | Specialty |
|---|---|
| `backend-architect` | APIs, services, domain layer, auth, storage |
| `hexagonal-architect` | Ports & Adapters specialist, port contracts, adapter seams, migration to Hexagonal |
| `frontend-architect` | UI structure, routing, state, client error handling |
| `api-designer` | REST/GraphQL/RPC contracts, versioning, error models |
| `data-architect` | Schema evolution, migrations, event flows, data contracts |
| `ux-designer` | User flows, interaction states, microcopy, friction |
| `ai-engineer` | Model integrations, prompt contracts, tool use, evals, latency |
| `agent-architect` | Multi-agent orchestration, MCP, tool use design, agent loops |
| `integration-engineer` | Third-party contracts, retries, idempotency, failure handling |
| `devops` | Containers, IaC, secrets, scaling, DR |
| `ci-cd` | Pipelines, quality gates, artifact flow, deploy stages |
| `dba` | Migration safety, locking, indexes, rollback feasibility |
| `platform-dev` | Background workers, job queues, developer tooling |
| `cloud-architect` | VPC topology, IAM strategy, multi-region HA, DR, Well-Architected |

### LLM / AI Specialists

| Agent | Specialty |
|---|---|
| `ai-engineer` | Model pinning, context window budget, output schema validation, caching, LLM tracing, streaming failure handling, multi-modal inputs, agent loop safety |
| `prompt-engineer` | Prompt design, chain-of-thought, token optimization, caching, versioning |
| `rag-engineer` | Chunking, embedding, vector stores, hybrid search, reranking, HyDE, RAPTOR + RAGAS quality gates |
| `llm-eval-specialist` | RAGAS, DeepEval, PromptFoo, hallucination detection, regression suites, LLM-as-judge |
| `llm-safety-reviewer` | Prompt injection (direct + indirect), jailbreak, tool call authorization, PII leakage, data exfiltration |
| `llm-cost-analyst` | Token cost attribution per user/feature/template, model routing, prompt compression, caching ROI, spend anomaly detection |
| `agent-architect` | Multi-agent orchestration, MCP, tool use design, loops with safe termination |
| `conversational-designer` | Dialog flows, intent mapping, personas, fallback, escalation |
| `ml-engineer` | Fine-tuning (LoRA/QLoRA), training pipelines, MLOps, drift monitoring |

### Implementation

| Agent | Specialty |
|---|---|
| `backend-dev` | APIs, services, auth, persistence, queues |
| `frontend-dev` | UI, routing, state, accessibility, frontend tests |
| `mobile-dev` | React Native, Flutter, iOS (SwiftUI), Android (Compose) |
| `data-engineer` | ETL/ELT, Kafka, Spark, dbt, Airflow, data quality, CDC |
| `tdd-specialist` | Red-green-refactor cycles, failing test blueprints |

### Search

| Agent | Specialty |
|---|---|
| `search-engineer` | Elasticsearch/OpenSearch, full-text, faceted, relevance tuning, hybrid |

### Quality & Review

| Agent | Specialty |
|---|---|
| `reviewer` | Code review: bugs, correctness, TDD compliance, complexity |
| `qa` | Real test execution, AC validation, regression check |
| `test-planner` | Test matrix: unit/integration/e2e/regression |
| `test-automation-engineer` | Test suites, fixtures, harnesses, quality gates |
| `integration-qa` | Contract validation, cross-service flows, external deps |

### Specialist Reviewers

| Agent | Specialty |
|---|---|
| `security-reviewer` | Auth, authz, injection, secrets, OWASP — code review |
| `security-engineer` | Implements OAuth2/OIDC/MFA, WAF, SAST/DAST, threat modeling |
| `privacy-reviewer` | PII exposure, data minimization, consent, masking |
| `compliance-reviewer` | Audit trail, LGPD/GDPR/PCI, regulated data |
| `accessibility-reviewer` | WCAG, keyboard nav, ARIA, contrast, focus |
| `performance-engineer` | Latency, throughput, queries, caching, load |
| `chaos-engineer` | Fault injection, circuit breaker validation, LLM agent resilience |
| `design-principles-specialist` | SOLID, DRY, Clean Arch, coupling/cohesion, testability |
| `code-quality` | Lint config, tech debt, coding standards, SonarQube |

### Observability & Monitoring

| Agent | Specialty |
|---|---|
| `observability-engineer` | Structured logs, metrics, traces, alerting rules |
| `monitoring-specialist` | Grafana/New Relic/Datadog dashboards, APM, SLO tracking, LLM cost dashboards |
| `analytics-engineer` | Product events, funnels, A/B tests, product dashboards |

### Design

| Agent | Specialty |
|---|---|
| `design-system-engineer` | Component libraries, design tokens, Storybook, Figma → code |

### Documentation & Developer Experience

| Agent | Specialty |
|---|---|
| `docs-writer` | Internal technical docs, migration notes, operator guidance |
| `tech-writer` | User guides, public API references, tutorials, customer changelogs |
| `devex-engineer` | Local dev setup, CLI tooling, scaffolding, contribution, onboarding |
| `jira-confluence-specialist` | Jira issues, epics, stories, Confluence pages (via Atlassian MCP) |
| `developer-relations` | External dev community, SDKs, tutorials, technical content, dev feedback |

### Business & Growth

| Agent | Specialty |
|---|---|
| `solutions-architect` | Enterprise integrations, pre-sales technical, RFPs, customer PoCs |
| `growth-engineer` | A/B testing, feature flags, funnels, growth loops, experimentation |

### Operations & Release

| Agent | Specialty |
|---|---|
| `release` | Release plan, change inventory, rollback, communication |
| `sre` | SLOs, blast radius, rollback readiness, canary strategy |
| `cost-optimizer` | Cloud spend, API costs, query costs, rightsizing |
| `incident-manager` | Production incident coordination |

### Stack Specialists

Django stack (Context7 + Playwright for browser verification agents):

| Agent | Specialty | Context7 | Playwright |
|---|---|---|---|
| `django-pm` | Problem shaping, user stories, UAT for Django projects | ✅ | ✅ |
| `tech-lead` | Technical lead for Django projects — planning, decomposition | ✅ | — |
| `django-backend` | Django models, views, forms, admin, ORM, migrations, API endpoints | ✅ | — |
| `django-frontend` | Django Template Language + TailwindCSS — templates, layouts, components | ✅ | ✅ |
| `code-reviewer` | Django backend/frontend code review — correctness, security, N+1, TDD | — | — |
| `qa-tester` | Full E2E Playwright validation of running Django applications | — | ✅ |

React / Vue stack:

| Agent | Specialty | Context7 | Playwright |
|---|---|---|---|
| `react-developer` | React components, hooks, state management, Django backend integration | ✅ | ✅ |
| `vue-developer` | Vue 3 SFCs, Composition API, Pinia, Vue Router, Django backend integration | ✅ | ✅ |

Python / TypeScript / JavaScript / Shell stack:

| Agent | Specialty | Context7 | Playwright |
|---|---|---|---|
| `python-developer` | Python utilities, CLI tools, Celery tasks, service integrations | ✅ | — |
| `typescript-developer` | TypeScript modules, type definitions, SDK clients, strict type safety | ✅ | ✅ |
| `javascript-developer` | Vanilla JavaScript browser scripts, Node.js utilities | ✅ | ✅ |
| `shell-developer` | Shell scripts — automation, CI/CD, deployment, developer tooling | ✅ | — |

---

## 8. Pipeline architecture

### Full diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  DISCOVERY CHAIN                                                         │
│                                                                         │
│  skill → pm → ba → po ──[GATE 1]── planner ──[GATE 2]── architect      │
│                                                              │           │
│                              ┌───────────────────────────────┘           │
│                              ▼                                           │
│                          techlead ──[GATE 3]                             │
│                              │                                           │
│          ┌───────────────────┼──────────────────────┐                   │
│          ▼                   ▼                       ▼                   │
│   backend-arch         frontend-arch            api-designer             │
│   data-arch → dba      ux-designer              integ-engineer           │
│   ai-engineer          agent-architect           rag-engineer            │
│   prompt-engineer      search-engineer           cloud-architect         │
│          └───────────────────┼──────────────────────┘                   │
│                              ▼                                           │
│                    QUALITY BASELINE BENCH                                │
│                    security-rev, privacy-rev, performance, observ        │
│                              ▼                                           │
│              design-principles → test-planner → tdd-specialist          │
│                                                        │                 │
│                                               [GATE 4: blueprint]       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  BUILD CHAIN                                                             │
│                                                                         │
│  tdd-specialist (failing tests)                                         │
│          │                                                              │
│          ├─── backend-dev                                               │
│          ├─── frontend-dev       (parallel)                             │
│          ├─── mobile-dev                                                │
│          └─── data-engineer                                             │
│                    │                                                    │
│                 reviewer ◄──────────────────────── loop ───┐           │
│              APPROVED │    CHANGES REQUESTED               │           │
│                    ▼                                        │           │
│                   qa ──── FAIL ────────────────────────────┘           │
│                 PASS │                                                  │
│                    ▼                                                    │
│              QUALITY BENCH (parallel)                                   │
│              security-rev, security-eng, privacy-rev                    │
│              perf-eng, access-rev, chaos-eng, integ-qa                  │
│                    │                                                    │
│              docs-writer → tech-writer → jira-confluence                │
│                    │                                                    │
│                   pm ─────────────────────────── [GATE 5: UAT]         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  RELEASE CHAIN (/squad only)                                             │
│                                                                         │
│  release → sre ──[GO]── done                                            │
│                └─[NO-GO]── resolve blockers                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. User gates

| Gate | Skill | Who presents | What to decide |
|---|---|---|---|
| **Gate 1** — Scope Validation | `/discovery` | `po` | Is the defined scope correct? Cuts needed? |
| **Gate 2** — Technical Tradeoffs | `/discovery` | `planner` | Which technical approach to follow? |
| **Gate 3** — Architecture Direction | `/discovery` | `techlead` | Does the proposed architecture make sense? |
| **Gate 4** — Blueprint Confirmation | `/discovery` | `tdd-specialist` | Is the blueprint approved for implementation? |
| **Gate Bridge** — Implement Now? | `/discovery` | orchestrator | Start `/implement` immediately? (SEP Contract 3) |
| **Gate 5** — UAT | `/implement` | `pm` | Does the delivered feature meet the ACs? |
| **Coverage Gate** — Coverage Drop | `/implement` | orchestrator | Coverage dropped. Continue or test more? |
| **UAT Re-queue** — Rejection Loop | `/implement` | orchestrator | UAT rejected. Re-queue with gaps or end? |
| **Gate 1** — Hotfix Intake | `/hotfix` | orchestrator | Confirm symptom + scope + deploy target |
| **Gate 2** — Root Cause Confirm | `/hotfix` | orchestrator | Diagnosis correct? Proceed with patch? |
| **Gate 3** — Deploy Checklist | `/hotfix` | orchestrator | Staging verified → prod deploy → monitor 15min |
| **Gate 1** — PR Intake | `/pr-review` | orchestrator | PR URL + repo |
| **Gate 2** — Post Threads? | `/pr-review` | orchestrator | Confirm opening threads on GitHub |

No gate can be skipped. Responding to the gate is what moves the pipeline to the next phase.

The **Gate Bridge** is the only gate that does not block the pipeline — answering N records `implement_triggered: false` in the log and ends `/discovery` normally. The **Coverage Gate** and **UAT Re-queue** only appear when the condition is triggered (coverage dropped / UAT rejected).

---

## 10. Execution visibility

### Inline mode (default)

```
[Phase Start] discovery
[Agent Start] PM | claude-tech-squad:pm | Problem framing and user stories
[Agent Done] PM | Status: completed | Output: 3 user stories, 8 ACs defined
[Agent Blocked] PO | Waiting on: user scope validation (Gate 1)
[Agent Batch Start] specialist-bench | Agents: backend-architect, frontend-architect, rag-engineer
[Agent Done] Backend Architect | Status: completed | Output: hexagonal layers defined
[Agent Batch Done] specialist-bench | Outcome: specialist notes ready
```

### Teammate mode (tmux)

```
[Team Created] discovery
[Teammate Spawned] pm | pane: pm
[Teammate Spawned] ba | pane: ba
[Gate] Scope Validation | Waiting for user input
[Batch Spawned] specialist-bench | Teammates: backend-arch, frontend-arch, rag-engineer, prompt-engineer
[Teammate Done] reviewer | Status: APPROVED
[Teammate Done] qa | Status: PASS
[SEP Log Written] ai-docs/.squad-log/2026-03-24T21-00-00-implement-abc123.md
```

### SEP lines (v5.4.0+)

```
[SEP Log Written] ai-docs/.squad-log/{filename}
[Remediation Tasks Written] ai-docs/security-remediation-YYYY-MM-DD.md
[Gate] implement-bridge | Waiting for user input
[Gate] Coverage Drop | Waiting for user input
[Teammate Retry] pm-uat | Reason: UAT REJECTED — re-queuing implementation
[Review Posted] N threads opened on PR #N
[Hotfix Branch] hotfix/{slug} created from {base}
[Cache Synced] N skill(s) updated in installed plugin
```

These lines appear at the end of each skill that implements the Squad Execution Protocol. `[Gate] implement-bridge` appears only in `/discovery`. `[Gate] Coverage Drop` and `[Teammate Retry] pm-uat` are conditional — only emitted when the condition is triggered.

---

## 11. Usage rules

### Which skill to use

```
New repo, never used the squad        → /onboarding (first)
Production broken                     → /hotfix
Incident resolved, want to learn      → /incident-postmortem
Bug with stack trace                  → /bug-fix
Tech debt, no behavior change         → /refactor
Want to plan before implementing      → /discovery
Have a blueprint, want to implement   → /implement
Want everything at once               → /squad
Implementation ready, want release    → /release
Need to review a PR                   → /pr-review
Going to change DB models             → /migration-plan BEFORE /squad or /implement
Need security audit                   → /security-audit
Problem in production                 → /cloud-debug
Outdated deps                         → /dependency-check
Improve squad process                 → /factory-retrospective
```

### TDD

- `/squad` and `/implement`: TDD mandatory by default
- `/bug-fix`: TDD mandatory (failing test before the fix)
- Exception declared explicitly when the repository does not have a viable test stack

### Autonomy

Agents work autonomously between gates. There is no need to interact between one gate and the next — the pipeline moves on its own.

---

## 12. Quick reference

### Skills by context

```bash
# First command in any new repo
/claude-tech-squad:onboarding

# Complete new feature
/claude-tech-squad:squad "implement authentication with Google OAuth"

# LLM product: travel agent with RAG
/claude-tech-squad:squad "build travel chatbot with RAG, vector search, and tool use"

# Plan only, implement later
/claude-tech-squad:discovery "refactor payment system to support PIX"

# Implement with ready blueprint
/claude-tech-squad:implement

# Specific bug
/claude-tech-squad:bug-fix

# Production broken — emergency patch
/claude-tech-squad:hotfix

# Post-incident — blameless post-mortem
/claude-tech-squad:incident-postmortem

# Tech debt — safe refactor
/claude-tech-squad:refactor

# Implementation ready — cut release
/claude-tech-squad:release

# Review a PR with specialized bench
/claude-tech-squad:pr-review

# Before any model change
/claude-tech-squad:migration-plan

# Security audit
/claude-tech-squad:security-audit

# Problem in production
/claude-tech-squad:cloud-debug

# Check dependencies
/claude-tech-squad:dependency-check

# Process retrospective
/claude-tech-squad:factory-retrospective
```

### Alternative flows by context

```
AI feature:        backend-architect → ai-engineer → agent-architect → techlead
RAG feature:       rag-engineer → llm-eval-specialist → prompt-engineer → techlead
Chatbot:           conversational-designer → prompt-engineer → rag-engineer → techlead
Schema change:     data-architect → dba → techlead
External APIs:     api-designer → integration-engineer → techlead
UI feature:        frontend-architect → ux-designer → design-system-engineer → techlead
Search feature:    search-engineer → rag-engineer (if hybrid) → techlead
Mobile feature:    frontend-architect → mobile-dev → techlead
Cloud infra:       cloud-architect → devops → sre → techlead
Tech debt:         reviewer → code-quality → reviewer
Incident:          incident-manager → {sre + devops + observability-engineer}
Enterprise client: solutions-architect → integration-engineer → techlead
Growth / A/B:      growth-engineer → analytics-engineer → techlead
Dev community:     developer-relations → tech-writer → techlead
```

---

## 13. Absolute Prohibitions — safety guardrails

All agents with execution authority carry an **Absolute Prohibitions** block in the pre-prompt. These restrictions cannot be overridden by incident urgency, deadline pressure, or verbal request.

### Globally blocked operations (all agents)

Require **explicit written user confirmation** before any execution:

| Operation | Context |
|---|---|
| `DROP TABLE`, `DROP DATABASE`, `TRUNCATE` | any environment |
| `tsuru app-remove`, PaaS/cloud equivalents | production |
| Delete cloud resources with data (S3/GCS buckets, RDS, clusters) | production |
| Merge to `main`/`master`/`develop` without approved PR | always |
| `git push --force` on protected branch | always |
| Remove secrets or env vars from production | production |
| Deploy without documented and tested rollback plan | production |
| Disable authentication, authorization, monitoring, or SLO alerts | always |
| Destroy infrastructure (`terraform destroy`) | always |

### Per-agent restrictions

| Agent | Specific critical restriction |
|---|---|
| `chaos-engineer` | Production experiments require maintenance window + on-call + abort procedure. Staging is the default. |
| `security-engineer` | Never revoke tokens without a replacement ready. Never disable auth or CORS. WAF tested in staging first. |
| `cost-optimizer` | Never delete buckets, databases, or instances to "save". Validate with DevOps/SRE first. |
| `ml-engineer` | Never promote model without rollback. Never delete version serving traffic. Same standard as a code deploy. |
| `mobile-dev` | Never submit directly to App Store/Play Store production. Staged rollout mandatory. |
| `sre` | GO without documented rollback is prohibited. Business pressure does not override NO-GO. |
| `incident-manager` | Incident urgency does not override any restriction. Propose less destructive mitigation first. |
| `techlead` | As execution authority, intercepts and blocks any specialist requesting a prohibited operation. |

### Additional prohibited operations (v5.8.0+)

| Operation | Reason |
|---|---|
| `git commit --no-verify` | Bypasses lint/security hooks — prohibited without explicit authorization |
| `eval()`, shell injection, external input in commands | Risk of arbitrary code execution |
| Deploy to production without staging verified | A staging failure is infinitely cheaper than a production one |
| Create tag/release with CI failing | Untested code is not a deploy — it's a bet |
| Migrate database without confirmed backup | Irreversible operation without a safety net |

### Rationale for absolute prohibitions

This section documents the **reason** behind each prohibition. Without rationale, future contributors may weaken guardrails thinking they are overly conservative. The reason also helps operators communicate restrictions to their teams.

#### Destructive data operations

| Prohibition | Rationale |
|---|---|
| `DROP TABLE`, `DROP DATABASE`, `TRUNCATE` | Production data loss is irreversible — no rollback exists if the backup was not verified first. An error in a migration script can destroy years of data in seconds. |
| Delete cloud resources with data (S3/GCS buckets, RDS, clusters) | Cloud resource deletion often has no undo. Recovery cost (if possible) is orders of magnitude greater than the cost of confirming with the user. |
| Migrate database without confirmed backup | The migration can fail mid-way — data can end up in an inconsistent state. Backup + restore-test is the only real safety net. |

#### Code control and deploy operations

| Prohibition | Rationale |
|---|---|
| Merge to `main`/`master`/`develop` without approved PR | Code review catches bugs that tests don't cover. An approved PR is the minimum quality contract — bypassing it removes the only barrier between agent code and production. |
| `git push --force` on protected branch | Rewrites public history — other collaborators lose commits silently. Irreversible if the ref was deleted on the remote. |
| `git commit --no-verify` | Bypasses lint/security hooks. Hooks exist to prevent exactly the type of error agents make most frequently: secrets in code, broken lint, failing tests. |
| Create tag/release with CI failing | A tag with red CI is a false promise — "this code works" when the tests say otherwise. Downstream (users, automations) trust the tag. |
| Deploy to production without staging verified | Staging exists to absorb failures without impacting users. Skipping staging increases the probability of a production incident by at least an order of magnitude. |
| Deploy without documented and tested rollback plan | If the deploy fails, every minute without a clear rollback is a minute of impact. An untested rollback can be as dangerous as the original problem. |

#### Security and access

| Prohibition | Rationale |
|---|---|
| Remove secrets or env vars from production | Application may enter a broken state (crash loop, silent failure) if the variable was needed. Production secret changes require coordinated deploy. |
| Disable authentication/authorization, monitoring, or SLO alerts | Disabling auth opens the system to unauthorized access. Disabling monitoring blinds the team — subsequent failures go undetected. |
| Destroy infrastructure (`terraform destroy`, equivalents) | Destroyed infrastructure can take down dependent services. Infrastructure dependencies are rarely fully documented — the risk is systemic. |
| Chaos experiments in production without maintenance window + on-call + abort procedure | Chaos engineering without preparation is simply sabotage. The value of chaos comes from controlled learning — without an abort procedure, the experiment can become a real incident. |
| Publishing directly to App Store/Play Store production without staged rollout | Mobile apps cannot be force-uninstalled. A critical bug in mobile production affects all users until the fix is approved by the store (hours to days). |

#### LLM/AI feature security

| Prohibition | Rationale |
|---|---|
| Prompt injection vulnerabilities without fix | Prompt injection allows malicious actors to control LLM behavior — extracting data, executing unauthorized actions, bypassing guardrails. It is the XSS/SQLi of AI systems. |
| Destructive tool calls without human-in-the-loop gate | Agents with destructive tools (delete, send email, execute query) can cause irreversible harm if the reasoning loop fails or is manipulated. Human-in-the-loop is the only reliable safeguard. |
| PII passed to LLMs or eval services without masking | LLMs can leak PII in outputs, logs, or caches. Third-party eval services (PromptFoo, hosted DeepEval) may store the data. PII exposure violates GDPR/LGPD and destroys user trust. |
| Model version without pin (floating alias in production) | Floating aliases (`gpt-4`, `claude-latest`) point to different models over time. A model change without a deploy silently changes application behavior — no release, no rollback, no warning. |
| Auto-updating prompts without eval regression gate | Prompts are business code. Updating without testing against golden cases is the equivalent of deploying without running tests — quality regressions reach production undetected. |

#### Code and injection execution

| Prohibition | Rationale |
|---|---|
| Dynamic code execution, shell injection, external input in commands | Enables arbitrary code execution from any user input or external document. It is the most exploited vulnerability class in automations. Agents process untrusted input by nature — dynamic execution turns this into RCE. |

### Additional prohibitions for LLM/AI features (v5.8.0+)

When the project uses LLM/AI, these restrictions are active — in addition to the globals above:

| Operation | Severity |
|---|---|
| Prompt injection vulnerability without fix | BLOCKING — no merge or release until fixed |
| Destructive tool calls without human-in-the-loop gate | BLOCKING |
| PII passed to LLMs or eval services without masking | BLOCKING |
| Model version without pin (floating alias in production) | BLOCKING |
| Auto-updating prompts without eval regression gate | BLOCKING |

These restrictions are verified by `llm-safety-reviewer` during `/security-audit` and `/squad` when LLM/AI code is detected.

### Documentation Standard — Context7 First, Repository Fallback (v5.21.0+)

All **74 agents** use Context7 first when available to look up current documentation before using any library, framework, or external API — regardless of stack. If Context7 is unavailable, the fallback is repository evidence, locally installed docs, and explicit assumptions in the output. Training data is never the source of truth for API signatures, method names, or default behavior.

**Required workflow for every library used:**
1. `mcp__plugin_context7_context7__resolve-library-id("library-name")`
2. `mcp__plugin_context7_context7__query-docs(libraryId, topic="specific feature")`

If Context7 is unavailable or does not have documentation for the library, the agent declares it explicitly and flags assumptions in the output.

### Global Safety Contract

Since v5.8.0, **all 20 skills** carry the **Global Safety Contract** — not just the 3 main orchestrators. Each skill explicitly prohibits the operations above in the SKILL.md header.

Additionally, implementation agent prompts (`backend-dev`, `frontend-dev`) and release agents carry safety restrictions inline so agents receive them even when operating as subagents without direct access to the skill header.

The contract is read by all agents regardless of whether they operate as an inline subagent or as a teammate in a separate tmux pane.

### Additional security gates (v5.8.0+)

| Gate | Skill | Behavior |
|---|---|---|
| CI green gate | `/release` | HARD BLOCK — tag prohibited if CI failed. `CI_UNKNOWN` requires explicit acceptance and is logged. |
| Staging gate | `/hotfix`, `/release` | Checklist includes "staging deploy verified" before "production". Skip requires "SKIP STAGING" written + reason in SEP log. |
| Backup gate | `/migration-plan` | Before finalizing the plan: backup date/time, location, whether restore-tested. HIGH risk migrations require a tested rollback script. |
| PII sanitization | `/hotfix`, `/cloud-debug`, `/incident-postmortem` | Tokens and emails masked before passing logs to agents. PII prohibited in SEP logs. |
| .squad-log gitignore | `/onboarding` | Ensures `ai-docs/.squad-log/` is in `.gitignore` on initialization. CVEs/findings do not go to the repository. |

---

## 14. Squad Execution Protocol (SEP) — artifacts and traceability

The SEP is a set of six stack-agnostic contracts covering observability, continuity, and remediation across all squad workflows. It works both when Claude operates as an **inline subagent** and as a **teammate in a separate tmux pane** — the log persists on disk regardless of execution mode.

### Contracts

| Contract | Name | Skills that implement |
|---|---|---|
| C1 | Execution Log | `/discovery`, `/implement`, `/squad`, `/security-audit`, `/dependency-check`, `/hotfix`, `/pr-review`, `/onboarding`, `/release`, `/incident-postmortem`, `/refactor` |
| C2 | Remediation Tasks | `/security-audit`, `/dependency-check` |
| C3 | Discovery → Implement Bridge Gate | `/discovery` |
| C4 | Task Completion Block | `/implement` (per implementation agent) |
| C5 | Runtime Fallback Matrix | `/discovery`, `/implement`, `/squad` |
| C6 | Checkpoint / Resume Cursor | `/discovery`, `/implement`, `/squad` |

---

### C1 — Execution Log

Each skill writes a structured log to `ai-docs/.squad-log/` on completion:

```
ai-docs/.squad-log/YYYY-MM-DDTHH-MM-SS-{skill}-{run_id}.md
```

The formal schema is in `ai-docs/.squad-log/sep-log.schema.json` (JSON Schema 2020-12). `scripts/dogfood-report.sh` validates any `.md` log present in `.squad-log/` against this schema.

#### Required fields (formal schema v5.29+)

| Field | Type | Description |
|---|---|---|
| `run_id` | string | Unique run identifier (short alphanumeric slug) |
| `skill` | string (enum) | Name of the skill that produced the log |
| `timestamp` | string (ISO 8601) | Skill completion time |
| `final_status` | string | Terminal state: `completed`, `failed`, `partial`, `aborted` |
| `execution_mode` | string | `inline` (subagent) \| `tmux` (teammate) \| `n/a` |
| `architecture_style` | string | Style detected at preflight; `n/a` if skill does not detect |
| `checkpoints` | array | Ordered list of completed checkpoints |
| `fallbacks_invoked` | array | List of fallback invocations (empty if none) |

#### Common optional fields

| Field | Type | When present |
|---|---|---|
| `lint_profile` | string | Skills with lint detection preflight |
| `docs_lookup_mode` | string | `context7`, `web-search`, `repository-fallback`, `n/a` |
| `runtime_policy_version` | string | Active `runtime-policy.yaml` version |
| `agent_results` | array | Result per agent (orchestrator skills) |
| `retry_count` | integer | Retry cycles consumed |
| `gates_blocked` | array | Gates that blocked (required user confirmation) |
| `teammate_reliability` | object | Reliability classification per teammate |
| `implement_triggered` | boolean | Whether `/implement` was triggered (only `/discovery`) |
| `uat_result` | string | `PASS` or `REJECTED` (only `/implement`) |
| `release_result` | string | `GO` or `NO-GO` (only `/squad` and `/release`) |
| `postmortem_recommended` | boolean | Whether postmortem was recommended (only `/hotfix`) |
| `findings_critical` | integer | CRITICAL findings (only `/security-audit`) |
| `findings_high` | integer | HIGH findings (only `/security-audit`) |
| `vulnerabilities_critical` | integer | Critical CVEs (only `/dependency-check`) |
| `remediation_artifact` | string | Path to remediation file (C2) |

**Canonical example:**

```yaml
---
run_id: xf8q2
skill: discovery
timestamp: 2026-04-05T14:43:15Z
final_status: completed
execution_mode: inline
architecture_style: ai-native
checkpoints: [preflight-passed, gate-1-approved, gate-2-approved, blueprint-confirmed]
fallbacks_invoked: []
parent_run_id: null
runtime_policy_version: 5.29.0
lint_profile: ruff
docs_lookup_mode: context7
implement_triggered: false
retry_count: 0
checkpoint_cursor: blueprint-confirmed
resume_from: none
gates_blocked: []
teammate_reliability:
  pm: primary
  ai-engineer: primary
  llm-eval-specialist: primary
---

## Discovery Summary
Context-aware document retrieval feature — HyDE retrieval design approved.
```

The logs are the primary source for `/factory-retrospective` to compute metrics: UAT rejection rate, most frequently blocked gates, retry rate per skill, fallback usage per agent, unimplemented discoveries, and most frequent resume points.

---

### C2 — Remediation Tasks

`/security-audit` and `/dependency-check` produce remediation files with checkboxes:

```
ai-docs/security-remediation-YYYY-MM-DD.md
ai-docs/dependency-remediation-YYYY-MM-DD.md
```

**Structure:**

```markdown
# Security Remediation Tasks — YYYY-MM-DD

> Auto-generated by /security-audit. Check off items as they are fixed.

## Phase 1 — Immediate (Critical + High)
- [ ] [CRIT-1] SQL injection in views.py:142 — parameterize query
- [x] [HIGH-1] Hardcoded secret in config.py:89 — use env var

## Phase 2 — Short-term (Medium)
- [ ] [MED-1] ...
```

`/factory-retrospective` computes the **closure rate** (`[x]` / total) per file to measure remediation progress between runs.

---

### C3 — Discovery → Implement Bridge Gate

At the end of `/discovery`, the orchestrator asks:

```
Discovery complete. Ready to start implementation now? [Y/N]
```

- **Y**: updates `implement_triggered: true` in the SEP log and invokes `/implement` automatically with the generated blueprint.
- **N**: keeps `implement_triggered: false`. `/factory-retrospective` detects these as **orphaned discoveries** — plans that were never implemented.

This eliminates the gap where the blueprint existed but implementation was never started, making abandonment visible in metrics.

---

### C4 — Task Completion Block

Each implementation agent in `/implement` must return a structured block when completing its task:

```markdown
## Completion Block
- Task: implement lead creation endpoint
- Status: completed
- Files changed: [src/api/leads/views.py, src/api/leads/serializers.py]
- Tests run: {{test_command}} → PASS
- Test count: 14 passed, 0 failed
```

The orchestrator uses these blocks to validate progress and detect silent failures where the agent "completed" without running tests.

---

### C5 — Runtime Fallback Matrix

`plugins/claude-tech-squad/runtime-policy.yaml` is the single source of truth for runtime fallback. When an agent fails twice with the same prompt, the orchestrator consults `fallback_matrix` before opening a gate for the user.

Examples:
- `reviewer` → `code-quality`, then `techlead`
- `qa` → `integration-qa`, then `test-automation-engineer`
- `architect` → `backend-architect`, then `solutions-architect`

Every successful fallback must appear:
- in the visible output: `[Fallback Invoked] ...`
- in the SEP log: `fallback_invocations` + `teammate_reliability`

---

### C6 — Checkpoint / Resume Cursor

`/discovery`, `/implement`, and `/squad` record phase/gate checkpoints and can resume from the last consistent boundary when the input has not changed materially.

SEP fields used:
- `checkpoint_cursor` — most advanced checkpoint reached
- `completed_checkpoints` — full list of completed milestones
- `resume_from` — checkpoint where execution resumed, or `none`

Checkpoint examples:
- `/discovery`: `gate-1-approved`, `specialist-bench-complete`, `blueprint-confirmed`
- `/implement`: `commands-confirmed`, `qa-pass`, `quality-bench-cleared`, `uat-approved`
- `/squad`: `discovery-confirmed`, `implementation-complete`, `release-signed-off`

---
