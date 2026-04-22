# Getting Started

This guide explains:

- what `claude-tech-squad` is for
- how to install it
- how to enable teammate mode (each specialist in its own tmux pane)
- which commands to run and when
- example prompts for real delivery work
- how to interpret visible squad execution

## What `claude-tech-squad` Is

`claude-tech-squad` is the execution layer.

It is not a general config pack. It is the specialist team you run inside a real repository when you need coordinated product and engineering delivery.

Use it for:

- discovery and scope clarification
- architecture, TDD-first implementation planning, and implementation coordination
- multi-specialist delivery across 61 specialist agents
- test, review, documentation, Jira/Confluence, and release follow-through

If you need baseline commands, skills, rules, and templates, use `claude-config`.

## Prerequisites

Before installing, confirm the following:

| Requirement | Required for | Note |
|---|---|---|
| **Claude Code** (any recent version) | All modes | Plugin system was introduced in Claude Code. No minimum version enforced — use the latest available. |
| **Python 3.10+** | squad-cli (optional) | Enables the embedded orchestrator for faster preflight, health checks, and SEP log generation. The plugin works without it (falls back to LLM-driven logic at higher token cost). |
| **tmux** | Teammate mode only | Inline mode (default) works without tmux. Teammate mode requires Claude Code to be started inside a tmux session. |
| `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Teammate mode only | Set in `~/.claude/settings.json`. Not needed for inline mode. |
| `CLAUDE_CODE_TEAMMATE_MODE=tmux` | Teammate mode only | Set in `~/.claude/settings.json`. Not needed for inline mode. |
| **bash** | Validation scripts only | All `scripts/` require bash. Not required to run squad commands. |

> **Inline mode is the default and requires only Claude Code.** Python 3 is recommended (enables squad-cli for 80-85% token savings on orchestration overhead). Teammate mode adds tmux and two environment variables. Start with inline mode if you are new to the plugin.

**Estimated installation time:** < 5 minutes for inline mode, < 10 minutes including teammate mode setup.

---

## Install In Claude Code

### Step 1 — Add the Marketplace

Run once per machine:

```bash
claude plugin marketplace add alexfloripavieira/claude-tech-squad
```

Or inside Claude Code:

```text
/plugin marketplace add alexfloripavieira/claude-tech-squad
```

### Step 2 — Install the Plugin

**Global (available in any repository):**

```bash
claude plugin install -s user claude-tech-squad@alexfloripavieira-plugins
```

**Project only:**

```bash
claude plugin install -s project claude-tech-squad@alexfloripavieira-plugins
```

**Local (current Claude context only):**

```bash
claude plugin install -s local claude-tech-squad@alexfloripavieira-plugins
```

---

## Teammate Mode — Each Specialist in Its Own Pane

By default, agents run as inline subagents — one after another inside the same Claude session. With teammate mode enabled, each specialist spawns as an independent Claude Code instance in a separate tmux pane.

### Requirements

1. Claude Code must be started **inside a tmux session**
2. Two environment variables must be set in `~/.claude/settings.json`

### Step 1 — Configure settings.json

Open `~/.claude/settings.json` and add:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_TEAMMATE_MODE": "tmux"
  }
}
```

If the file already has an `"env"` section, add only the two keys inside it.

### Step 2 — Start Claude Code inside tmux

Every time you want teammate panes, open a terminal and run:

```bash
# Create a new tmux session named "squad"
tmux new-session -s squad

# Then start Claude Code inside it
claude
```

Or attach to an existing session:

```bash
tmux attach -t squad
claude
```

### Step 3 — Run any squad command

Once inside tmux with the env vars set, any `/discovery`, `/implement`, or `/squad` command will:

1. Create a team via `TeamCreate`
2. Spawn each specialist as a teammate in its own tmux pane
3. Show gates for user decisions at key points

### What to expect

When teammate mode is active you will see output like:

```text
[Team Created] discovery
[Teammate Spawned] pm | pane: pm
[Teammate Spawned] ba | pane: ba
[Gate] Scope Validation | Waiting for user input
[Batch Spawned] specialist-bench | Teammates: backend-arch, frontend-arch, api-designer
[Teammate Done] reviewer | Status: APPROVED
```

Each pane shows the specialist working independently. The orchestrator (your main pane) coordinates the flow and presents gates for your input.

### Without tmux

If you run the commands without tmux mode, the workflows still work correctly — agents run inline as subagents. You get the same outputs and gates, but no separate panes.

### SEP logs in teammate mode

When running in teammate mode, each specialist runs in its own Claude Code instance. The **Squad Execution Protocol (SEP)** ensures observability regardless of mode: every skill writes a structured log to `ai-docs/.squad-log/` before the pane exits. This means `/factory-retrospective` always has a persistent trace of what ran, even when there is no shared conversation history to inspect. See MANUAL.md section 13 for the full SEP reference.

---

## squad-cli — Embedded Orchestrator

The plugin ships with `squad-cli`, a Python tool at `plugins/claude-tech-squad/bin/squad-cli` that handles deterministic tasks (stack detection, health checks, cost tracking, SEP logs) outside the LLM. This saves 80-85% of token overhead on orchestration.

**No setup required.** squad-cli auto-installs its dependencies (PyYAML, Click) on first run. It requires Python 3.10+.

### Preview a run before spending tokens

```bash
python3 plugins/claude-tech-squad/bin/squad-cli dry-run \
  --skill squad \
  --policy plugins/claude-tech-squad/runtime-policy.yaml \
  --project-root .
```

This shows the full execution plan: phases, teammates, gates, routing, and budget — in under 2 seconds, zero tokens.

### Supported stacks

squad-cli detects the project stack automatically from signal files (manage.py, package.json, go.mod, Cargo.toml, pom.xml, Gemfile, composer.json, *.csproj, mix.exs, etc.) and resolves the correct specialist agents. Supports monorepos with nested signal files up to 3 levels deep.

| Stack | Signal | Specialist routing |
|---|---|---|
| Django | manage.py + django in requirements | django-pm, tech-lead, django-backend, django-frontend, code-reviewer |
| React | package.json with react | react-developer, qa-tester |
| Vue | package.json with vue | vue-developer, qa-tester |
| TypeScript | tsconfig.json | typescript-developer |
| JavaScript | package.json (no framework) | javascript-developer |
| Python | pyproject.toml / requirements.txt | python-developer |
| Go | go.mod | backend-dev |
| Rust | Cargo.toml | backend-dev |
| Java | pom.xml / build.gradle | backend-dev |
| Ruby | Gemfile | backend-dev |
| PHP | composer.json | backend-dev |
| .NET | *.csproj / *.sln | backend-dev |
| Elixir | mix.exs | backend-dev |

### Without Python 3

All skills work without squad-cli. The LLM executes the same logic from prompt instructions at higher token cost. No features are lost — only cost efficiency.

---

## Commands

### `/claude-tech-squad:onboarding`

Run once in any new repository before using other squad commands. Detects the stack, creates `ai-docs/`, generates a `CLAUDE.md` template, and runs a security and dependency baseline.

```text
/claude-tech-squad:onboarding
```

### `/claude-tech-squad:release`

Use when implementation is done and you need to cut a release. Builds change inventory from git, validates CI/CD, generates rollback plan and release notes, creates the version tag.

```text
/claude-tech-squad:release
```

### `/claude-tech-squad:incident-postmortem`

Use after a production incident is resolved. Reconstructs timeline, identifies root cause with 5-whys, produces prioritized action items, and generates a blameless post-mortem document.

```text
/claude-tech-squad:incident-postmortem
```

### `/claude-tech-squad:refactor`

Use for safe technical debt reduction. Writes characterization tests to lock current behavior, then refactors incrementally — behavior does not change.

```text
/claude-tech-squad:refactor
```

### `/claude-tech-squad:hotfix`

Use quando produção está quebrada e você precisa de um patch agora. Mais rápido que `/bug-fix` — intake → root cause → patch mínimo → branch `hotfix/` → PR → deploy checklist.

```text
/claude-tech-squad:hotfix
```

### `/claude-tech-squad:pr-review`

Use para revisar qualquer pull request com bench especializado. Detecta os revisores relevantes pelos arquivos alterados, roda em paralelo, consolida findings, e abre threads no GitHub.

```text
/claude-tech-squad:pr-review
https://github.com/org/repo/pull/42
```

### `/claude-tech-squad:llm-eval`

Use após qualquer mudança em prompts, pipeline RAG, modelo de embedding, ou lógica de AI. Roda suite de evals (RAGAS, DeepEval, PromptFoo), compara contra baseline, e bloqueia o release se houver regressão de qualidade.

```text
/claude-tech-squad:llm-eval
```

Use também antes de qualquer release que inclua features de AI — é o equivalente de `npm test` para apps com LLM.

### `/claude-tech-squad:prompt-review`

Use antes de mergar qualquer mudança em arquivos de prompt. Faz diff comportamental, testa regressão nos exemplos golden, escaneia prompt injection (direto e via documentos RAG), e estima impacto no custo de tokens.

```text
/claude-tech-squad:prompt-review
```

Se o veredicto for BLOCKED (risco de injection), o prompt não pode ser mergeado até corrigir.

### `/claude-tech-squad:multi-service`

Use when a change spans multiple services and requires coordinated deployment. Maps the dependency graph, validates contracts (Pact tests), sequences the deployment runbook, and assesses blast radius.

```text
/claude-tech-squad:multi-service
Services: payment-api (producer), order-service (consumer), notification-service (consumer)
Change: payment webhook payload adding new required field
```

### `/claude-tech-squad:iac-review`

Use before any `terraform apply`, `helm upgrade`, `cdk deploy`, or equivalent. Reviews the changeset for blast radius, security posture (IAM, open ports, encryption), and cost impact. Produces a safe apply sequence with rollback plan and a blocking gate for critical findings.

```text
/claude-tech-squad:iac-review
```

### `/claude-tech-squad:discovery`

Use when the problem or feature still needs shaping. Produces a complete Discovery & Blueprint Document.

Chain: PM → Business Analyst → PO → Planner → Architect → TechLead → Specialists → Quality Baselines → Design Principles → Test Planner → TDD Specialist

Gates at: PO (scope), Planner (tradeoffs), TechLead (architecture direction), TDD Specialist (blueprint confirmation)

```text
/claude-tech-squad:discovery
Design a customer support workspace with ticket routing, audit history, and role-based administration.
```

```text
/claude-tech-squad:discovery
Build a RAG-powered travel agent chatbot that learns from interactions and handles flight and hotel search.
```

### `/claude-tech-squad:implement`

Use after discovery when the blueprint is agreed. Requires a Discovery & Blueprint Document in the conversation.

Chain: TDD Specialist (failing tests) → Implementation batch → Reviewer → QA → Quality bench → Docs Writer → Jira/Confluence → PM UAT

```text
/claude-tech-squad:implement
Use the approved discovery package and implement the next delivery slice with TDD cycles.
```

### `/claude-tech-squad:squad`

Use when you want the full path from idea to release in one workflow.

Phases: Discovery (with gates) → Implementation (TDD-first) → Release (Release + SRE sign-off)

For code changes, this command is TDD-first by default.

```text
/claude-tech-squad:squad
Add SSO login, audit events, admin controls, automated coverage, documentation, and release artifacts.
```

```text
/claude-tech-squad:squad
Build a webhook reliability improvement package with idempotency, retries, dead-letter visibility, and release notes.
```

---

## Prompt Patterns That Work Well

Good inputs usually include:

- the business outcome
- the main user or persona
- the constraints (performance, compliance, incremental rollout)
- any repo-specific context that matters

More examples:

```text
/claude-tech-squad:discovery
Create an internal billing admin surface for support operators. Invoice search, refunds, and access control. Keep rollout incremental.
```

```text
/claude-tech-squad:squad
Implement vector search for the knowledge base. Use pgvector with hybrid BM25 + semantic retrieval. TDD required. Cover RAG quality metrics.
```

```text
/claude-tech-squad:discovery
Add real-time monitoring dashboards in Grafana for token cost per user and RAG retrieval quality. Integrate with existing Prometheus stack.
```

---

## Documentation Standard — Context7

Every agent in the squad uses **Context7** first when it is available. If Context7 is unavailable, the fallback is repository evidence, local installed docs, and explicit assumptions in the output. Training data is never used as the source of truth for API signatures or method behavior.

Required workflow for every library used:

```
mcp__plugin_context7_context7__resolve-library-id("library-name")
mcp__plugin_context7_context7__query-docs(libraryId, topic="specific feature")
```

If Context7 is unavailable or does not have documentation for the library, the agent declares it explicitly and flags assumptions in the output. This applies to all 61 agents.

---

## Specialist Roster Quick Reference

| Category | Agents |
|---|---|
| Discovery | pm, business-analyst, po, planner, architect, techlead |
| Architecture | backend-architect, hexagonal-architect, frontend-architect, api-designer, data-architect, ux-designer, ai-engineer, agent-architect, integration-engineer, devops, ci-cd, dba, platform-dev, cloud-architect |
| LLM / AI | ai-engineer, prompt-engineer, rag-engineer, llm-eval-specialist, llm-safety-reviewer, agent-architect, conversational-designer, ml-engineer |
| Implementation | backend-dev, frontend-dev, mobile-dev, data-engineer, tdd-specialist |
| Search | search-engineer |
| Quality | reviewer, qa, test-planner, test-automation-engineer, integration-qa |
| Specialist Review | security-reviewer, security-engineer, privacy-reviewer, compliance-reviewer, accessibility-reviewer, performance-engineer, chaos-engineer, design-principles-specialist, code-quality |
| Observability | observability-engineer, monitoring-specialist, analytics-engineer |
| Design | design-system-engineer |
| Business & Growth | solutions-architect, growth-engineer |
| Docs / DX | docs-writer, tech-writer, devex-engineer, developer-relations, jira-confluence-specialist |
| Operations | release, sre, cost-optimizer, incident-manager |

Total: 61 specialists.

---

## Verifying Installation

Run this after installing to confirm the plugin is active and reachable:

```bash
# List all loaded skills — you should see 20 claude-tech-squad skills
claude /list-skills 2>/dev/null | grep claude-tech-squad | wc -l
```

Expected output: `20`

If you have the repository cloned locally, run the structural validation:

```bash
# Confirms all 61 agents, 20 skills, and contracts are intact
bash scripts/validate.sh

# Confirms schema-level SEP log compliance
bash scripts/dogfood-report.sh --schema-only
```

Both commands should exit with `0` and no errors. If `validate.sh` reports missing agents or failed contracts, re-run `claude plugin install` and verify the plugin scope (`-s user`, `-s project`, or `-s local`).

---

## Troubleshooting

### 1. Plugin not found after install (`/claude-tech-squad:squad not found`)

**Cause:** Plugin installed with a different scope than the current session uses.

**Fix:** Reinstall with `-s user` to make it available globally:

```bash
claude plugin install -s user claude-tech-squad@alexfloripavieira-plugins
```

Or check which scopes have the plugin loaded:

```bash
claude plugin list
```

---

### 2. Agents run inline instead of separate tmux panes

**Cause:** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` or `CLAUDE_CODE_TEAMMATE_MODE` not set, or Claude Code was not started inside a tmux session.

**Fix — step 1:** Confirm the env vars are in `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
    "CLAUDE_CODE_TEAMMATE_MODE": "tmux"
  }
}
```

**Fix — step 2:** Exit Claude Code, start a tmux session, then start Claude Code inside it:

```bash
tmux new-session -s squad
claude
```

> **Note:** Inline mode is fully functional. Tmux panes are a visibility enhancement, not a requirement. If you are new, start with inline mode.

---

### 3. `ai-docs/` directory missing when running `/discovery` or `/squad`

**Cause:** `/onboarding` was not run before other squad commands.

**Fix:** Run onboarding first in any new repository:

```text
/claude-tech-squad:onboarding
```

This creates `ai-docs/`, `.squad-log/`, and a `CLAUDE.md` template in under 2 minutes.

---

### 4. `scripts/smoke-test.sh` fails with `rg: command not found`

**Cause:** `ripgrep` is not installed on the machine. This affects the validation scripts only — it does not affect running squad commands.

**Fix (macOS):**

```bash
brew install ripgrep
```

**Fix (Ubuntu/Debian):**

```bash
apt-get install ripgrep
```

Squad commands (`/discovery`, `/implement`, `/squad`, etc.) work without `ripgrep`. The validation scripts are only needed when contributing to the plugin itself.

---

### 5. CLAUDE.md already exists — onboarding skips template generation

**Cause:** `/onboarding` detected an existing `CLAUDE.md` and skipped overwriting it (by design — Safety Contract).

**Expected behavior:** This is correct. The skill emits `[Onboarding] CLAUDE.md already exists — skipping template generation.`

**Action:** Manually merge the squad workflow rules into your existing `CLAUDE.md`:

```markdown
## Workflow Rules

- Bug fixes (1–2 files): fix directly or use `/claude-tech-squad:bug-fix`
- Features (3+ files): use `/claude-tech-squad:squad`
- Production emergency: use `/claude-tech-squad:hotfix`
- Never commit or push without explicit authorization
```

---

## Validation Ladder

Use this order after structural changes:

```bash
bash scripts/validate.sh
bash scripts/smoke-test.sh
bash scripts/dogfood.sh
bash scripts/dogfood-report.sh --schema-only
```

When you have real captured runs under `ai-docs/dogfood-runs/`, then run:

```bash
bash scripts/dogfood-report.sh
```
