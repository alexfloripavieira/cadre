# Delivery Docs, Inception Skill, and Visual Reporting

**Date:** 2026-04-21
**Status:** Approved — ready for implementation plan
**Change Class:** C (new agents + routing changes in multiple skills)

## Problem

The plugin delivers strong execution pipelines (discovery, implement, squad, bug-fix, hotfix) but has no structured, contract-driven way to produce the three canonical delivery artifacts that most software teams expect: a PRD (functional requirements), a TechSpec (technical approach), and a sequenced task list. Teams copy ad-hoc content between runs, and downstream automation (Jira, roadmap, release notes) has nothing stable to consume.

Additionally, the plugin conflates *discovery* (functional refinement) and *inception* (technical refinement) inside a single skill, which limits teams that want to gate technical work separately from product definition.

Finally, while token cost and duration are captured in SEP logs, operators have no inline visibility during a run — the dashboard is browser-only, and the terminal stays silent between teammate handoffs.

## Goals

1. Produce three canonical artifacts (`prd.md`, `techspec.md`, `tasks.md` + per-task files) through dedicated specialist agents that follow the existing plugin agent contract.
2. Separate Discovery (functional) from Inception (technical) as distinct phases, each callable standalone or chained inside `squad`.
3. Map completed work into a configurable, vendor-neutral work-item taxonomy so Jira/Linear/GitHub Issue automation has a stable input.
4. Render per-teammate token/cost cards inline after each agent completes, and a final pipeline board at end of every orchestrator skill, configurable and opt-out-able.
5. Keep all taxonomy and gate rules vendor-neutral — no hardcoded process names or company-specific conventions.

## Non-Goals

- No new application, server, or build step. Everything remains Markdown + YAML + Bash.
- No integration with specific Jira/Linear/GitHub APIs in this spec — `work-item-mapper` only produces a mapping file; publishing is delegated to the existing `jira-confluence-specialist` or a follow-up.
- No changes to `bug-fix`'s inline execution policy — delivery docs are not generated for bugs by default.
- No modification of auto-generated files (`CHANGELOG.md`, `marketplace.json`, `plugin.json`, `docs/MANUAL.md`).

## Design Overview

### New agents (4)

Each follows the full agent contract enforced by `scripts/validate.sh`: required frontmatter (`name`, `description`, `tool_allowlist`), `Result Contract`, `Self-Verification Protocol` with role-specific checks, `verification_checklist` block, `Analysis Plan` or `Pre-Execution Plan`, and `Documentation Standard — Context7 First, Repository Fallback`.

**`prd-author`** — analysis agent
- Input: feature slug, feature description, orchestrator context
- Output: `ai-docs/prd-<slug>/prd.md` following `templates/prd-template.md`
- Focus: WHAT/WHY, numbered functional requirements, <2000 words, PT-BR content
- Tool allowlist: `Read, Write, Glob, Grep, mcp__plugin_context7_context7__*`
- Idempotent: if file exists and validates against template, returns `reused: true`
- Result Contract fields: `artifact_path, confidence, gaps[], functional_requirements_count, reused`

**`inception-author`** — analysis agent
- Input: feature slug, existing `prd.md`
- Output: `ai-docs/prd-<slug>/techspec.md` (following `templates/techspec-template.md`) plus mandatory sections: technical viability, risks, quality gates, effort estimation (hours + days)
- Focus: HOW, architecture, interfaces, external deps, test/observability strategy, <2000 words
- Uses Context7 to validate every library/API referenced
- Blocks hard if PRD is missing
- Result Contract fields: `artifact_path, confidence, gaps[], components_identified, external_deps[], estimated_hours, estimated_days, risks[], reused`

**`tasks-planner`** — analysis agent
- Input: feature slug, `prd.md` + `techspec.md`
- Output: `ai-docs/prd-<slug>/tasks.md` summary + `ai-docs/prd-<slug>/<num>_task.md` individual files (max 15 main tasks, X.0 / X.Y format)
- Each task: incremental deliverable + unit and integration test subtasks
- Blocks hard if PRD or TechSpec is missing
- Result Contract fields: `summary_path, task_files[], total_tasks, confidence, gaps[], reused`

**`work-item-mapper`** — analysis agent
- Input: `prd.md` + `techspec.md` + `tasks.md` (or just a bug report, for bug-fix/hotfix)
- Output: `ai-docs/prd-<slug>/work-items.md` — a structured YAML+Markdown mapping of tasks to the configured work-item taxonomy, with estimates and optional defect/bug classification
- Reads taxonomy from `runtime-policy.yaml` — no hardcoded level names
- Enforces policy-driven `delivery_gates` rules (see below); emits findings with configured severity
- Result Contract fields: `artifact_path, items[], severity_findings[], taxonomy_version, confidence`

### New skill `inception`

Standalone orchestrator skill at `plugins/claude-tech-squad/skills/inception/SKILL.md`, following the full orchestrator contract (Preflight Gate, Agent Result Contract, Runtime Resilience Contract, Checkpoint/Resume Rules, Progressive Disclosure, Live Status Protocol, Visual Reporting Contract).

- Preflight requires `prd.md` under `ai-docs/prd-<slug>/`
- Executes `inception-author`
- Writes SEP log at `ai-docs/.squad-log/inception-<timestamp>.md`
- Listed in `REQUIRED_SKILLS` in `validate.sh`
- Asserted in `smoke-test.sh`

### Updated skills

**`discovery`** — inserts `prd-author` invocation after preflight, before the existing specialist bench. Soft gate: if `prd.md` exists and is valid, skips regeneration. Exposes the PRD path in the final Result Contract.

**`implement`** — preflight reads existing `prd.md` and `techspec.md`; invokes `tasks-planner` then `work-item-mapper` before the TDD / build phase. Must still spawn teammates (existing rule unchanged).

**`squad`** — chains the full sequence: `prd-author → inception-author → tasks-planner → work-item-mapper → build bench → quality bench → release`. Must still spawn teammates.

**`bug-fix`** and **`hotfix`** — invoke `work-item-mapper` only, to classify defect vs bug per the configured `delivery_gates`. Does not invoke PRD/TechSpec/Tasks authors. Inline execution policy unchanged for these two skills.

### Configurable taxonomy and gates in `runtime-policy.yaml`

Two new top-level sections, both vendor-neutral and opt-configurable.

```yaml
work_item_taxonomy:
  levels:
    - name: initiative
      description: Strategic, cross-team work
    - name: epic
      description: Product-level value delivery
    - name: story
      description: Functional delivery with code
    - name: task
      description: Work without code (analysis, discovery, spike)
    - name: subtask
      description: Operational breakdown of any item above
  defect_classification:
    - name: defect
      description: Issue in delivered functionality
    - name: bug
      description: Issue in active production
  estimation:
    effort_unit: hours       # hours | days | points
    completion_unit: days    # hours | days | points

delivery_gates:
  enabled: false             # opt-in per team
  rules:
    - id: code_requires_story_not_task
      severity: WARNING
      description: Items with code should be mapped as story, not task
    - id: epic_needs_end_criterion
      severity: WARNING
      description: Epics need a completion criterion unless tagged continuous
    - id: qa_required_for_stories
      severity: INFO
      description: Stories should include a QA step in the flow
```

`work-item-mapper` reads both sections at runtime. Teams override names (e.g., `story` → `user-story`) in their project-local `runtime-policy.yaml` without touching the plugin.

### Visual reporting (inline teammate cards + final board)

Two new Bash renderers under `plugins/claude-tech-squad/scripts/`:

- `render-teammate-card.sh` — reads a teammate's Result Contract JSON from stdin, prints a compact ASCII card with tokens in/out, cost, duration, confidence, gaps, artifact count.
- `render-pipeline-board.sh` — reads the in-progress `.live-status.json` and prints a final board with per-teammate rows, totals, budget bar, checkpoint/gate summary, artifact list, SEP log path.

Both pure Bash + `awk` + `jq` (already assumed available for JSON handling in existing scripts). No Python.

**New contract block in orchestrator skills:** `## Visual Reporting Contract` — requires (a) invoking `render-teammate-card.sh` after every `Agent(...)` spawn, (b) invoking `render-pipeline-board.sh` once at the end before writing the SEP log, (c) respecting `observability.teammate_cards.format` (ascii | compact | silent) and `observability.pipeline_board.enabled`.

**New section in `runtime-policy.yaml`:**

```yaml
observability:
  teammate_cards:
    enabled: true
    format: ascii            # ascii | compact | silent
  pipeline_board:
    enabled: true
    include_budget_bar: true
    include_artifacts: true
```

The existing live dashboard (`dashboard/live.html`) remains unchanged — the board is complementary, for terminal operators.

### Card and board layouts

**Per-teammate card:**

```
┌─ prd-author ─────────────────────────── ✓ done ─┐
│  tokens in:   12.4k   out:   3.1k   total: 15.5k │
│  cost:  $0.0483     duration: 18.2s              │
│  confidence: high   gaps: 0   artifacts: 1       │
└──────────────────────────────────────────────────┘
```

**Final pipeline board:**

```
╔═══ SQUAD PIPELINE REPORT ═════════════════════════════════════╗
║  skill: squad        scenario: feature-x     duration: 4m 12s ║
╠════════════════════════════════════════════════════════════════╣
║  teammate              status    tokens    cost     gaps      ║
║  ─────────────────────────────────────────────────────────    ║
║  prd-author            ✓ done    15.5k    $0.048   0          ║
║  inception-author      ✓ done    22.1k    $0.067   1 (WARN)   ║
║  tasks-planner         ✓ done    18.3k    $0.055   0          ║
║  work-item-mapper      ✓ done     9.2k    $0.028   0          ║
║  backend-dev           ✓ done    41.7k    $0.126   0          ║
║  reviewer              ✓ done    12.8k    $0.039   2 (INFO)   ║
║  qa                    ✓ done    19.5k    $0.059   0          ║
║  ─────────────────────────────────────────────────────────    ║
║  TOTAL                           139.1k   $0.422   3          ║
╠════════════════════════════════════════════════════════════════╣
║  budget:  $2.00     used: 21.1%     ████░░░░░░░░░░░░░░        ║
║  checkpoints: 4/4   gates: 3/3 passed   retries: 0            ║
║  artifacts: prd.md, techspec.md, tasks.md, work-items.md      ║
║  sep log:  ai-docs/.squad-log/squad-20260421-1432.md          ║
╚════════════════════════════════════════════════════════════════╝
```

## Component Boundaries

| Component | Owns | Dependencies |
|---|---|---|
| `prd-author` | PRD generation and template adherence | `templates/prd-template.md`, Context7 (optional) |
| `inception-author` | TechSpec + viability/risks/gates/estimate | `prd.md`, `templates/techspec-template.md`, Context7 |
| `tasks-planner` | Task decomposition with tests | `prd.md`, `techspec.md`, `templates/task-template.md`, `templates/tasks-template.md` |
| `work-item-mapper` | Taxonomy mapping + gate enforcement | `work_item_taxonomy` and `delivery_gates` in `runtime-policy.yaml` |
| `inception` skill | Standalone technical refinement pipeline | `inception-author`, render scripts |
| Render scripts | Terminal visualization | Result Contract JSON, `.live-status.json` |
| Orchestrator skills | Flow, gating, teammate spawning, SEP log | All of the above |

Units stay small and focused. Each agent file ~200-300 lines. Each render script ~100 lines. Each skill delta is additive (insert one block, no cross-cutting rewrites).

## Data Flow

```
user prompt
  │
  ▼
orchestrator skill (discovery | inception | implement | squad | bug-fix | hotfix)
  │  preflight (reads runtime-policy.yaml, checks artifact reuse)
  ▼
[ prd-author ] ──> ai-docs/prd-<slug>/prd.md
  │  render-teammate-card
  ▼
[ inception-author ] ──> ai-docs/prd-<slug>/techspec.md
  │  render-teammate-card
  ▼
[ tasks-planner ] ──> ai-docs/prd-<slug>/tasks.md + <num>_task.md
  │  render-teammate-card
  ▼
[ work-item-mapper ] ──> ai-docs/prd-<slug>/work-items.md
  │  render-teammate-card
  ▼
existing build / quality / release bench (unchanged)
  │  render-teammate-card per teammate
  ▼
render-pipeline-board
  │
  ▼
SEP log written (ai-docs/.squad-log/<skill>-<timestamp>.md)
```

## Error Handling

- **Missing upstream artifact:** `inception-author` blocks hard if `prd.md` is absent; `tasks-planner` blocks hard if PRD or TechSpec is absent. These are BLOCKING in `severity_policy` terms.
- **Template file missing:** agent returns `confidence: low` with gap `template_missing: <path>` and halts. Orchestrator surfaces to user gate.
- **Context7 unavailable (inception-author):** falls back to repository-only analysis, flags `context7_unavailable: true` in Result Contract, confidence caps at `medium`.
- **Reuse with invalid existing artifact:** if `<artifact>.md` exists but fails template validation, agent regenerates and notes `overwritten: true`.
- **Render script failure:** non-fatal — caught by orchestrator, logged as WARNING in SEP log, pipeline continues.
- **Delivery gate violation:** severity drives behavior per `severity_policy` — `BLOCKING` halts pipeline, `WARNING` logs and continues, `INFO` logs only.
- **Retry and fallback:** standard `runtime-policy.yaml` `retry_budgets` applies; fallback matrix adds cross-refs (prd-author → pm; inception-author → tech-lead; tasks-planner → planner; work-item-mapper → jira-confluence-specialist) — these are fallback agents that re-attempt with expanded context, not replacements.

## Testing

- **`validate.sh`** — add 4 new agents to `REQUIRED_AGENTS`, `inception` skill to `REQUIRED_SKILLS`, new contract check: orchestrator skills must contain a `## Visual Reporting Contract` section.
- **`smoke-test.sh`** — assert presence of new agents, new skill, and both render scripts (executable bit).
- **`dogfood.sh`** — extend `layered-monolith` scenario to exercise the full chain and assert the 4 artifacts plus a final board containing `TOTAL` row.
- **New golden run scorecard** — `templates/golden-run-scorecard.md` gains rows: "delivery docs present and valid" and "teammate cards + pipeline board rendered".
- **Unit coverage of render scripts** — `scripts/test-render.sh` feeds fixture JSON and diffs against expected ASCII output.

## Observability

- Every agent still populates `tokens_input`, `tokens_output`, `estimated_cost_usd`, `total_duration_ms` — unchanged.
- SEP log schema gains optional top-level `delivery_docs: { prd, techspec, tasks, work_items }` with path + status per artifact.
- `.live-status.json` schema gains optional `current_artifact` and `artifact_chain` fields for the live dashboard to show which doc is being produced.
- Card and board are stateless — they read only what the orchestrator already writes.

## Migration / Rollout

All additive. No existing agent or skill is renamed or removed. Order:

1. Add 4 new agent files + `inception` skill + 2 render scripts + template usage.
2. Update `runtime-policy.yaml` with new sections; keep `delivery_gates.enabled: false` by default.
3. Update `discovery`, `implement`, `squad`, `bug-fix`, `hotfix` with the new blocks (small, localized diffs).
4. Update `validate.sh`, `smoke-test.sh`, golden run scorecard.
5. Run one real golden run per affected skill to meet Class C gate.
6. Update `README.md` agent and skill rosters.

## Change Class

**C** — new agents, new skill, routing changes in 5 skills.

Required validation:
- `bash scripts/validate.sh`
- `bash scripts/smoke-test.sh`
- `bash scripts/dogfood.sh`
- Updated golden run scorecards
- At least one real golden run per affected scenario (`layered-monolith`, `hexagonal-billing`, `hotfix-checkout`)

## Out of Scope / Follow-ups

- Actual Jira/Linear/GitHub Issue creation from `work-items.md` — a later skill/agent can consume the mapping.
- Web-dashboard surfacing of the terminal board — the existing live dashboard already covers live status; a static HTML mirror of the final board is a follow-up.
- Rename of existing generic agents (`pm`, `techlead`, `planner`) — out of scope; they remain for higher-level conceptual work. The new agents are the artifact-producing layer below them.
