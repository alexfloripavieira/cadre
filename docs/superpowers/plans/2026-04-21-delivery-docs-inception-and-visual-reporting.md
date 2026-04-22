# Delivery Docs, Inception Skill and Visual Reporting — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 specialist agents (prd-author, inception-author, tasks-planner, work-item-mapper), a new `inception` orchestrator skill, inline teammate token cards, and a final ASCII pipeline board — all vendor-neutral.

**Architecture:** Additive. New agents sit below the existing conceptual agents (`pm`, `techlead`, `planner`) and produce concrete artifacts from repo templates. A new `inception` skill separates technical refinement from discovery. Two Bash scripts render tokens/cost cards and a final board in the terminal, driven by data the plugin already emits. All taxonomy and gate rules are policy-driven in `runtime-policy.yaml`.

**Tech Stack:** Markdown (agents/skills), YAML (runtime policy), Bash + `awk` + `jq` (scripts, validators), existing Claude Code plugin contracts.

---

## File Structure

**New files**
- `plugins/claude-tech-squad/agents/prd-author.md`
- `plugins/claude-tech-squad/agents/inception-author.md`
- `plugins/claude-tech-squad/agents/tasks-planner.md`
- `plugins/claude-tech-squad/agents/work-item-mapper.md`
- `plugins/claude-tech-squad/skills/inception/SKILL.md`
- `plugins/claude-tech-squad/scripts/render-teammate-card.sh`
- `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`
- `scripts/test-render.sh`
- `scripts/test-fixtures/teammate-card-input.json`
- `scripts/test-fixtures/teammate-card-expected.txt`
- `scripts/test-fixtures/pipeline-board-input.json`
- `scripts/test-fixtures/pipeline-board-expected.txt`

**Modified files**
- `plugins/claude-tech-squad/runtime-policy.yaml` — add `work_item_taxonomy`, `delivery_gates`, `observability.teammate_cards`, `observability.pipeline_board`, fallback_matrix entries, tool_allowlists entries
- `plugins/claude-tech-squad/skills/discovery/SKILL.md` — insert PRD step + Visual Reporting Contract
- `plugins/claude-tech-squad/skills/implement/SKILL.md` — insert Tasks + work-item mapping step + Visual Reporting Contract
- `plugins/claude-tech-squad/skills/squad/SKILL.md` — insert full chain + Visual Reporting Contract
- `plugins/claude-tech-squad/skills/bug-fix/SKILL.md` — insert work-item-mapper call + Visual Reporting Contract
- `plugins/claude-tech-squad/skills/hotfix/SKILL.md` — insert work-item-mapper call + Visual Reporting Contract
- `scripts/validate.sh` — add 4 agents, add `inception` skill, check Visual Reporting Contract, check render scripts exist and are executable, check new policy sections
- `scripts/smoke-test.sh` — assert new agents, skill, and scripts present
- `scripts/dogfood.sh` — extend `layered-monolith` expectations to cover the 4 artifacts and board presence
- `templates/golden-run-scorecard.md` — add two rows
- `README.md` — register new agents + skill in rosters

---

## Sequencing Notes

Order below is not strict dependency order — the executing engineer can parallelize. Recommended: Tasks 1-2 first (policy + renderers are self-contained); Tasks 3-6 next (agents are independent of each other); Tasks 7-12 after that (skills depend on agents existing); Tasks 13-16 last (validation + docs).

Every task ends with a commit. Never use `--amend` or `--no-verify`. All commit messages must be plain technical text (no AI references, no emojis — project rule).

---

## Task 1: Add runtime policy sections for taxonomy, gates, and visual observability

**Files:**
- Modify: `plugins/claude-tech-squad/runtime-policy.yaml`

- [ ] **Step 1: Inspect current top-level keys**

Run: `grep -n "^[a-z_]*:$" plugins/claude-tech-squad/runtime-policy.yaml`
Expected: list including `version`, `retry_budgets`, `severity_policy`, `fallback_matrix`, `checkpoint_resume`, `reliability_metrics`, `cost_guardrails`, `doom_loop_detection`, `auto_advance`, `entropy_management`, `tool_allowlists`, `observability`.

- [ ] **Step 2: Append new top-level sections at the end of the file**

Append the following YAML block to `plugins/claude-tech-squad/runtime-policy.yaml` (do not overwrite existing content — append only):

```yaml

# ── Work-item taxonomy (vendor-neutral, configurable by team) ───────────────
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
      description: Issue in delivered functionality, not necessarily in production
    - name: bug
      description: Issue in active production
  estimation:
    effort_unit: hours       # hours | days | points
    completion_unit: days    # hours | days | points

# ── Delivery gates (opt-in, policy-driven) ──────────────────────────────────
delivery_gates:
  enabled: false
  rules:
    - id: code_requires_story_not_task
      severity: WARNING
      description: Items that produce code must be mapped as story, not task
    - id: epic_needs_end_criterion
      severity: WARNING
      description: Epics need an explicit completion criterion unless tagged continuous
    - id: qa_required_for_stories
      severity: INFO
      description: Stories should include a QA step in the flow
```

- [ ] **Step 3: Add keys to the existing `observability:` block**

Find the existing `observability:` key and add two sub-keys alongside `live_dashboard` and `sep_log_schema`. Insert this block as children of `observability:`:

```yaml
  teammate_cards:
    enabled: true
    format: ascii            # ascii | compact | silent
  pipeline_board:
    enabled: true
    include_budget_bar: true
    include_artifacts: true
```

- [ ] **Step 4: Add 4 entries to `fallback_matrix`**

Under the existing `fallback_matrix:` section, add:

```yaml
  prd-author: pm
  inception-author: tech-lead
  tasks-planner: planner
  work-item-mapper: jira-confluence-specialist
```

- [ ] **Step 5: Add 4 entries to `tool_allowlists.analysis` (or whichever list holds analysis agents)**

Open `plugins/claude-tech-squad/runtime-policy.yaml`, find the `tool_allowlists:` section, and under the analysis category add:

```yaml
  - prd-author
  - inception-author
  - tasks-planner
  - work-item-mapper
```

(Match the existing indentation and list style used for `planner`, `pm`, etc.)

- [ ] **Step 6: Validate YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('plugins/claude-tech-squad/runtime-policy.yaml'))" && echo OK`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add plugins/claude-tech-squad/runtime-policy.yaml
git commit -m "feat(policy): add work-item taxonomy, delivery gates, visual observability config"
```

---

## Task 2: Create the teammate card renderer

**Files:**
- Create: `plugins/claude-tech-squad/scripts/render-teammate-card.sh`
- Create: `scripts/test-fixtures/teammate-card-input.json`
- Create: `scripts/test-fixtures/teammate-card-expected.txt`

- [ ] **Step 1: Create fixture input JSON**

Write `scripts/test-fixtures/teammate-card-input.json`:

```json
{
  "agent": "prd-author",
  "status": "done",
  "tokens_input": 12400,
  "tokens_output": 3100,
  "estimated_cost_usd": 0.0483,
  "total_duration_ms": 18200,
  "confidence": "high",
  "gaps_count": 0,
  "artifacts_count": 1
}
```

- [ ] **Step 2: Create expected output fixture**

Write `scripts/test-fixtures/teammate-card-expected.txt`:

```
┌─ prd-author ─────────────────────────── ✓ done ─┐
│  tokens in:   12.4k   out:   3.1k   total: 15.5k │
│  cost:  $0.0483     duration: 18.2s              │
│  confidence: high   gaps: 0   artifacts: 1       │
└──────────────────────────────────────────────────┘
```

- [ ] **Step 3: Implement the renderer**

Write `plugins/claude-tech-squad/scripts/render-teammate-card.sh`:

```bash
#!/usr/bin/env bash
# Reads a teammate Result Contract JSON from stdin and prints an ASCII card.
# Respects FORMAT env (ascii | compact | silent). Default: ascii.
set -euo pipefail

FORMAT="${FORMAT:-ascii}"
[ "$FORMAT" = "silent" ] && exit 0

INPUT="$(cat)"
agent=$(echo "$INPUT"     | jq -r '.agent')
status=$(echo "$INPUT"    | jq -r '.status')
tin=$(echo "$INPUT"       | jq -r '.tokens_input')
tout=$(echo "$INPUT"      | jq -r '.tokens_output')
cost=$(echo "$INPUT"      | jq -r '.estimated_cost_usd')
durms=$(echo "$INPUT"     | jq -r '.total_duration_ms')
conf=$(echo "$INPUT"      | jq -r '.confidence')
gaps=$(echo "$INPUT"      | jq -r '.gaps_count')
arts=$(echo "$INPUT"      | jq -r '.artifacts_count')

fmt_tokens() { awk -v n="$1" 'BEGIN{ printf (n>=1000 ? "%.1fk" : "%d"), (n>=1000 ? n/1000 : n) }'; }
tin_f=$(fmt_tokens "$tin")
tout_f=$(fmt_tokens "$tout")
total_f=$(fmt_tokens "$((tin+tout))")
dur_f=$(awk -v m="$durms" 'BEGIN{ printf "%.1fs", m/1000 }')
cost_f=$(printf '$%.4f' "$cost")
status_mark="✓ $status"

if [ "$FORMAT" = "compact" ]; then
  printf '%-20s %s  in:%s out:%s cost:%s dur:%s conf:%s gaps:%s\n' \
    "$agent" "$status_mark" "$tin_f" "$tout_f" "$cost_f" "$dur_f" "$conf" "$gaps"
  exit 0
fi

# ascii (default)
pad_right() { awk -v s="$1" -v w="$2" 'BEGIN{ printf "%-*s", w, s }'; }
name_line=$(printf '┌─ %s ─' "$agent")
fill=$(( 50 - ${#name_line} - ${#status_mark} - 3 ))
(( fill < 1 )) && fill=1
dashes=$(printf '─%.0s' $(seq 1 "$fill"))
printf '%s%s %s ─┐\n' "$name_line" "$dashes" "$status_mark"
printf '│  tokens in: %6s   out: %6s   total: %s │\n' "$tin_f" "$tout_f" "$total_f"
printf '│  cost: %8s     duration: %s              │\n' "$cost_f" "$dur_f"
printf '│  confidence: %-4s   gaps: %-2s  artifacts: %-2s    │\n' "$conf" "$gaps" "$arts"
printf '└──────────────────────────────────────────────────┘\n'
```

- [ ] **Step 4: Make it executable**

Run: `chmod +x plugins/claude-tech-squad/scripts/render-teammate-card.sh`

- [ ] **Step 5: Run against fixture and verify output**

Run:
```bash
cat scripts/test-fixtures/teammate-card-input.json | plugins/claude-tech-squad/scripts/render-teammate-card.sh
```
Expected: output matching `scripts/test-fixtures/teammate-card-expected.txt` byte-for-byte (minor whitespace OK; update expected fixture if padding differs by one char).

If it does not match exactly, adjust the `printf` widths in the script OR update the expected fixture to reflect the true output. Do not ship a script that drifts from its fixture.

- [ ] **Step 6: Test silent mode**

Run: `FORMAT=silent echo '{}' | plugins/claude-tech-squad/scripts/render-teammate-card.sh | wc -c`
Expected: `0`

- [ ] **Step 7: Commit**

```bash
git add plugins/claude-tech-squad/scripts/render-teammate-card.sh scripts/test-fixtures/teammate-card-*
git commit -m "feat(observability): add teammate token/cost card renderer"
```

---

## Task 3: Create the pipeline board renderer

**Files:**
- Create: `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`
- Create: `scripts/test-fixtures/pipeline-board-input.json`
- Create: `scripts/test-fixtures/pipeline-board-expected.txt`

- [ ] **Step 1: Create input fixture**

Write `scripts/test-fixtures/pipeline-board-input.json`:

```json
{
  "skill": "squad",
  "scenario": "feature-x",
  "duration_ms": 252000,
  "budget_usd": 2.00,
  "teammates": [
    {"name": "prd-author",       "status": "done", "tokens_total": 15500, "cost_usd": 0.048, "gaps_count": 0, "severity": null},
    {"name": "inception-author", "status": "done", "tokens_total": 22100, "cost_usd": 0.067, "gaps_count": 1, "severity": "WARN"},
    {"name": "tasks-planner",    "status": "done", "tokens_total": 18300, "cost_usd": 0.055, "gaps_count": 0, "severity": null},
    {"name": "work-item-mapper", "status": "done", "tokens_total":  9200, "cost_usd": 0.028, "gaps_count": 0, "severity": null},
    {"name": "backend-dev",      "status": "done", "tokens_total": 41700, "cost_usd": 0.126, "gaps_count": 0, "severity": null},
    {"name": "reviewer",         "status": "done", "tokens_total": 12800, "cost_usd": 0.039, "gaps_count": 2, "severity": "INFO"},
    {"name": "qa",               "status": "done", "tokens_total": 19500, "cost_usd": 0.059, "gaps_count": 0, "severity": null}
  ],
  "checkpoints_passed": 4,
  "checkpoints_total": 4,
  "gates_passed": 3,
  "gates_total": 3,
  "retries": 0,
  "artifacts": ["prd.md", "techspec.md", "tasks.md", "work-items.md"],
  "sep_log_path": "ai-docs/.squad-log/squad-20260421-1432.md"
}
```

- [ ] **Step 2: Create expected output fixture**

Write `scripts/test-fixtures/pipeline-board-expected.txt`:

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

- [ ] **Step 3: Implement the renderer**

Write `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`:

```bash
#!/usr/bin/env bash
# Reads a pipeline summary JSON from stdin (or path arg) and prints an ASCII board.
# Honors ENABLED=false to emit nothing. Requires jq + awk.
set -euo pipefail

ENABLED="${ENABLED:-true}"
[ "$ENABLED" != "true" ] && exit 0

if [ "${1:-}" ]; then
  INPUT=$(cat "$1")
else
  INPUT=$(cat)
fi

skill=$(echo "$INPUT"     | jq -r '.skill')
scenario=$(echo "$INPUT"  | jq -r '.scenario // "-"')
durms=$(echo "$INPUT"     | jq -r '.duration_ms')
budget=$(echo "$INPUT"    | jq -r '.budget_usd')
cp=$(echo "$INPUT"        | jq -r '.checkpoints_passed')
ct=$(echo "$INPUT"        | jq -r '.checkpoints_total')
gp=$(echo "$INPUT"        | jq -r '.gates_passed')
gt=$(echo "$INPUT"        | jq -r '.gates_total')
retries=$(echo "$INPUT"   | jq -r '.retries')
arts=$(echo "$INPUT"      | jq -r '.artifacts | join(", ")')
sep=$(echo "$INPUT"       | jq -r '.sep_log_path')

dur_fmt=$(awk -v m="$durms" 'BEGIN{ s=int(m/1000); mn=int(s/60); sc=s%60; printf "%dm %02ds", mn, sc }')
fmt_k() { awk -v n="$1" 'BEGIN{ printf (n>=1000 ? "%.1fk" : "%d"), (n>=1000 ? n/1000 : n) }'; }

printf '╔═══ SQUAD PIPELINE REPORT ═════════════════════════════════════╗\n'
printf '║  skill: %-13s scenario: %-13s duration: %-6s ║\n' "$skill" "$scenario" "$dur_fmt"
printf '╠════════════════════════════════════════════════════════════════╣\n'
printf '║  teammate              status    tokens    cost     gaps      ║\n'
printf '║  ─────────────────────────────────────────────────────────    ║\n'

total_tokens=0
total_cost=0
total_gaps=0
echo "$INPUT" | jq -c '.teammates[]' | while read -r row; do
  name=$(echo "$row" | jq -r '.name')
  st=$(echo "$row"   | jq -r '.status')
  tk=$(echo "$row"   | jq -r '.tokens_total')
  ct2=$(echo "$row"  | jq -r '.cost_usd')
  gp2=$(echo "$row"  | jq -r '.gaps_count')
  sev=$(echo "$row"  | jq -r '.severity // empty')
  tk_f=$(fmt_k "$tk")
  cost_f=$(printf '$%.3f' "$ct2")
  gaps_field=$(if [ -n "$sev" ]; then printf '%s (%s)' "$gp2" "$sev"; else printf '%s' "$gp2"; fi)
  printf '║  %-22s ✓ %-7s %-8s %-8s %-10s ║\n' "$name" "$st" "$tk_f" "$cost_f" "$gaps_field"
done

# Totals — recompute from full input since the while-loop ran in a subshell
totals=$(echo "$INPUT" | jq '[.teammates[] | {t: .tokens_total, c: .cost_usd, g: .gaps_count}] | [add // {t:0,c:0,g:0}] | .[0] // {t:0,c:0,g:0}')
ttok=$(echo "$INPUT" | jq '[.teammates[].tokens_total] | add')
tcost=$(echo "$INPUT" | jq '[.teammates[].cost_usd] | add')
tgap=$(echo "$INPUT" | jq '[.teammates[].gaps_count] | add')
ttok_f=$(fmt_k "$ttok")
tcost_f=$(printf '$%.3f' "$tcost")

printf '║  ─────────────────────────────────────────────────────────    ║\n'
printf '║  %-30s %-8s %-8s %-10s ║\n' "TOTAL" "$ttok_f" "$tcost_f" "$tgap"
printf '╠════════════════════════════════════════════════════════════════╣\n'

pct=$(awk -v c="$tcost" -v b="$budget" 'BEGIN{ if (b==0) print 0; else printf "%.1f", (c/b)*100 }')
bar_filled=$(awk -v p="$pct" 'BEGIN{ n=int(p/5); if (n>20) n=20; for(i=0;i<n;i++) printf "█" }')
bar_empty=$(awk -v p="$pct" 'BEGIN{ n=20-int(p/5); if (n<0) n=0; for(i=0;i<n;i++) printf "░" }')

printf '║  budget:  $%.2f     used: %s%%     %s%s        ║\n' "$budget" "$pct" "$bar_filled" "$bar_empty"
printf '║  checkpoints: %d/%d   gates: %d/%d passed   retries: %d            ║\n' "$cp" "$ct" "$gp" "$gt" "$retries"
printf '║  artifacts: %-50s ║\n' "$arts"
printf '║  sep log:  %-51s ║\n' "$sep"
printf '╚════════════════════════════════════════════════════════════════╝\n'
```

- [ ] **Step 4: Make it executable**

Run: `chmod +x plugins/claude-tech-squad/scripts/render-pipeline-board.sh`

- [ ] **Step 5: Run against fixture**

Run:
```bash
plugins/claude-tech-squad/scripts/render-pipeline-board.sh scripts/test-fixtures/pipeline-board-input.json
```
Expected: output matching the board layout in the expected fixture. Column widths in the expected fixture and the `printf` width specifiers must agree. If they drift, adjust both together — fix the script first, update the fixture only if the script is clearly right.

- [ ] **Step 6: Test disabled mode**

Run: `ENABLED=false plugins/claude-tech-squad/scripts/render-pipeline-board.sh scripts/test-fixtures/pipeline-board-input.json | wc -c`
Expected: `0`

- [ ] **Step 7: Commit**

```bash
git add plugins/claude-tech-squad/scripts/render-pipeline-board.sh scripts/test-fixtures/pipeline-board-*
git commit -m "feat(observability): add end-of-pipeline board renderer"
```

---

## Task 4: Create the render test script

**Files:**
- Create: `scripts/test-render.sh`

- [ ] **Step 1: Write the test script**

Write `scripts/test-render.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0

check_diff() {
  local name="$1" actual="$2" expected="$3"
  if diff -u <(printf '%s' "$expected") <(printf '%s' "$actual") > /dev/null; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name"
    diff -u <(printf '%s' "$expected") <(printf '%s' "$actual") || true
    fail=1
  fi
}

# teammate card
actual=$(cat scripts/test-fixtures/teammate-card-input.json \
  | plugins/claude-tech-squad/scripts/render-teammate-card.sh)
expected=$(cat scripts/test-fixtures/teammate-card-expected.txt)
check_diff "teammate-card" "$actual" "$expected"

# pipeline board
actual=$(plugins/claude-tech-squad/scripts/render-pipeline-board.sh \
  scripts/test-fixtures/pipeline-board-input.json)
expected=$(cat scripts/test-fixtures/pipeline-board-expected.txt)
check_diff "pipeline-board" "$actual" "$expected"

exit "$fail"
```

- [ ] **Step 2: Make it executable and run it**

```bash
chmod +x scripts/test-render.sh
bash scripts/test-render.sh
```
Expected: `[PASS] teammate-card` and `[PASS] pipeline-board`, exit 0.
If either fails, go back and align the script output with the expected fixture — byte-for-byte.

- [ ] **Step 3: Commit**

```bash
git add scripts/test-render.sh
git commit -m "test: add render script byte-diff tests"
```

---

## Task 5: Create `prd-author` agent

**Files:**
- Create: `plugins/claude-tech-squad/agents/prd-author.md`

- [ ] **Step 1: Read an existing analysis agent as the structural reference**

Run: `cat plugins/claude-tech-squad/agents/planner.md | head -200`
Confirm the required sections order: frontmatter → role body → Analysis Plan → Self-Verification Protocol → Result Contract → Documentation Standard.

- [ ] **Step 2: Write the agent file**

Write `plugins/claude-tech-squad/agents/prd-author.md`:

````markdown
---
name: prd-author
description: Generates a Product Requirements Document (PRD) from a feature request or orchestrator context. Focuses on WHAT/WHY, writes numbered functional requirements, keeps content under 2000 words, and conforms strictly to templates/prd-template.md. Vendor-neutral and idempotent (reuses a valid existing PRD).
tool_allowlist: [Read, Write, Glob, Grep, mcp__plugin_context7_context7__resolve-library-id, mcp__plugin_context7_context7__query-docs]
---

# PRD Author Agent

You own the functional definition. You produce a single artifact: `ai-docs/prd-<slug>/prd.md`.

## Role

Translate a feature request plus orchestrator context into a PRD that a downstream technical author can use without guessing intent.

You do NOT propose architecture, stacks, APIs, or task breakdowns. That belongs to `inception-author` and `tasks-planner`.

## Rules

- Output language is PT-BR for the PRD body (tooling and metadata remain in EN).
- Strictly follow the template at `templates/prd-template.md` — do not reorder sections, do not invent new top-level sections.
- Numbered functional requirements are mandatory. Each requirement testable and atomic.
- Keep the total document under 2000 words.
- If the artifact already exists at `ai-docs/prd-<slug>/prd.md` and validates against the template (has all required headings), do not overwrite — return `reused: true`.
- Never ask the user questions directly. If clarifying information is missing, populate `gaps[]` in the Result Contract and let the orchestrator decide.

## Analysis Plan

Before writing, state:

1. **Scope:** the feature slug, the intended product surface, what the PRD will and will not cover.
2. **Inputs consumed:** orchestrator context digest, any existing repo docs/ADRs/tickets in `ai-docs/` or `docs/`.
3. **Template compliance:** list the template sections you will populate.

## Self-Verification Protocol

Before returning, verify:

**Base checks:**
1. **Completeness** — every section from `templates/prd-template.md` is present, in order.
2. **Accuracy** — every referenced file, system, or integration exists in the repo or is flagged as an assumption.
3. **Contract compliance** — output ends with `result_contract` and `verification_checklist` blocks with accurate values.
4. **Scope discipline** — no architecture, no tasks, no implementation details.
5. **Downstream readiness** — `inception-author` can read this PRD and derive a TechSpec without re-asking the user.

**Role-specific checks (PRD):**
6. **Functional requirements numbered and atomic** — each testable in isolation.
7. **Word count under 2000** — measured on the final body.
8. **PT-BR content** — headings localized per template; no untranslated English prose in the body.
9. **Reuse detection** — if an existing valid PRD is present, `reused: true` and no writes performed.

If any check fails, fix inline before returning.

## Result Contract

End every response with:

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts:
    - path: ai-docs/prd-<slug>/prd.md
      status: created | reused | overwritten
  findings: []
  next_action: "Invoke inception-author for slug <slug>"
metrics:
  tokens_input: <int>
  tokens_output: <int>
  estimated_cost_usd: <float>
  total_duration_ms: <int>
  confidence: high | medium | low
  gaps_count: <int>
  artifacts_count: <int>
functional_requirements_count: <int>
reused: <bool>
```

Include:

```yaml
verification_checklist:
  prd_produced: true
  base_checks_passed: [completeness, accuracy, contract, scope, downstream]
  role_checks_passed: [numbered_requirements, word_count, language, reuse_detection]
  issues_found_and_fixed: 0
  confidence_after_verification: high | medium | low
```

A response missing either block is structurally incomplete and will trigger a retry.

## Documentation Standard — Context7 First, Repository Fallback

Before referencing any library, framework, or external API in the PRD, use Context7. If unavailable, fall back to repository evidence and flag assumptions. Training data alone is never the source of truth.

**Required workflow:**

1. `mcp__plugin_context7_context7__resolve-library-id("library-name")`
2. `mcp__plugin_context7_context7__query-docs(id, topic="specific feature")`

If Context7 lacks documentation, note it and proceed with explicit assumptions.
````

- [ ] **Step 3: Sanity check required sections are present**

Run:
```bash
for s in "^name:" "^description:" "^tool_allowlist:" "^## Result Contract$" "^## Self-Verification Protocol$" "^## Analysis Plan$" "^## Documentation Standard — Context7 First, Repository Fallback$" "verification_checklist:"; do
  grep -q "$s" plugins/claude-tech-squad/agents/prd-author.md && echo "OK: $s" || { echo "MISSING: $s"; exit 1; }
done
```
Expected: eight `OK:` lines.

- [ ] **Step 4: Commit**

```bash
git add plugins/claude-tech-squad/agents/prd-author.md
git commit -m "feat(agents): add prd-author agent"
```

---

## Task 6: Create `inception-author` agent

**Files:**
- Create: `plugins/claude-tech-squad/agents/inception-author.md`

- [ ] **Step 1: Write the agent file**

Write `plugins/claude-tech-squad/agents/inception-author.md`:

````markdown
---
name: inception-author
description: Generates a Technical Specification (TechSpec) from an existing PRD. Produces architecture, interfaces, impact analysis, test strategy, risks, gates, and effort estimation. Strictly follows templates/techspec-template.md. Vendor-neutral, idempotent, Context7-first.
tool_allowlist: [Read, Write, Glob, Grep, mcp__plugin_context7_context7__resolve-library-id, mcp__plugin_context7_context7__query-docs]
---

# Inception Author Agent

You own technical refinement. You produce one artifact: `ai-docs/prd-<slug>/techspec.md`.

## Role

Read a validated PRD and translate it into a TechSpec that defines HOW the feature will be built. You own architecture, interface contracts, data flow, impact, test/observability strategy, risks, quality gates, and effort estimation — in days.

You do NOT redefine product scope. You do NOT generate tasks. If the PRD is missing or invalid, you block.

## Rules

- Output language is PT-BR for the body.
- Strictly follow `templates/techspec-template.md` structure.
- Add required sections beyond the template: **Viabilidade Técnica**, **Riscos**, **Gates de Qualidade**, **Estimativa (horas/dias)**.
- Validate every library, framework, or cloud SDK referenced against Context7 before writing. No API signature may come from training data.
- Block hard if `ai-docs/prd-<slug>/prd.md` is missing or fails template validation.
- Idempotent: if an existing valid techspec is present, return `reused: true`.
- Keep body under 2000 words excluding diagrams.

## Analysis Plan

1. **Scope:** confirm the PRD slug, identify technical components and external integrations.
2. **Inputs consumed:** `prd.md`, existing repo code structure, existing ADRs or architecture docs.
3. **Research plan:** list every library or API you will verify via Context7 before writing.
4. **Risk surface:** enumerate high-level risk categories to probe (performance, security, data, cost, operational).

## Self-Verification Protocol

**Base checks:**
1. **Completeness** — every template section populated plus the four required additions.
2. **Accuracy** — every API and library verified via Context7 (or flagged as assumption).
3. **Contract compliance** — `result_contract` and `verification_checklist` present and accurate.
4. **Scope discipline** — no product/feature redefinition; no task breakdown.
5. **Downstream readiness** — `tasks-planner` can decompose without further input.

**Role-specific checks (inception):**
6. **Architecture grounded in repo** — all components either exist or are explicitly marked "to be created".
7. **Estimation present** — hours and days, with assumptions listed.
8. **Risks and gates explicit** — at least one risk per category probed and at least one quality gate defined.
9. **Context7 usage documented** — every external library appears in the Result Contract under `external_deps[]` with a resolved library id.

If any check fails, fix inline.

## Result Contract

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts:
    - path: ai-docs/prd-<slug>/techspec.md
      status: created | reused | overwritten
  findings: []
  next_action: "Invoke tasks-planner for slug <slug>"
metrics:
  tokens_input: <int>
  tokens_output: <int>
  estimated_cost_usd: <float>
  total_duration_ms: <int>
  confidence: high | medium | low
  gaps_count: <int>
  artifacts_count: <int>
components_identified: <int>
external_deps:
  - name: <string>
    context7_id: <string | null>
    assumed: <bool>
estimated_hours: <float>
estimated_days: <float>
risks:
  - category: <string>
    severity: low | medium | high
    description: <string>
reused: <bool>
```

```yaml
verification_checklist:
  techspec_produced: true
  base_checks_passed: [completeness, accuracy, contract, scope, downstream]
  role_checks_passed: [architecture_grounded, estimation_present, risks_and_gates, context7_usage]
  issues_found_and_fixed: 0
  confidence_after_verification: high | medium | low
```

## Documentation Standard — Context7 First, Repository Fallback

Before referencing any library, framework, or external API, use Context7. If Context7 is unavailable for a library, note it explicitly in `external_deps[].assumed = true` and proceed.

**Required workflow:**

1. `mcp__plugin_context7_context7__resolve-library-id("library-name")`
2. `mcp__plugin_context7_context7__query-docs(id, topic="specific feature")`
````

- [ ] **Step 2: Sanity check required sections**

```bash
for s in "^name:" "^description:" "^tool_allowlist:" "^## Result Contract$" "^## Self-Verification Protocol$" "^## Analysis Plan$" "^## Documentation Standard — Context7 First, Repository Fallback$" "verification_checklist:"; do
  grep -q "$s" plugins/claude-tech-squad/agents/inception-author.md && echo "OK: $s" || { echo "MISSING: $s"; exit 1; }
done
```

- [ ] **Step 3: Commit**

```bash
git add plugins/claude-tech-squad/agents/inception-author.md
git commit -m "feat(agents): add inception-author agent"
```

---

## Task 7: Create `tasks-planner` agent

**Files:**
- Create: `plugins/claude-tech-squad/agents/tasks-planner.md`

- [ ] **Step 1: Write the agent file**

Write `plugins/claude-tech-squad/agents/tasks-planner.md`:

````markdown
---
name: tasks-planner
description: Decomposes a validated PRD + TechSpec into a sequenced, incremental task list with test subtasks. Produces tasks.md summary and individual task files using templates/tasks-template.md and templates/task-template.md. Max 15 main tasks. Vendor-neutral, idempotent.
tool_allowlist: [Read, Write, Glob, Grep]
---

# Tasks Planner Agent

You own operational decomposition.

## Role

Read the PRD and TechSpec and emit a task list in which every main task is an incremental, functional deliverable with unit + integration test subtasks.

## Rules

- Output language is PT-BR.
- Follow `templates/tasks-template.md` for the summary and `templates/task-template.md` for each task.
- Max 15 main tasks. If more are needed, group them.
- Main task numbering: X.0. Subtasks: X.Y.
- Each main task must have at least one unit test subtask and one integration test subtask.
- Block hard if `prd.md` OR `techspec.md` is missing.
- Idempotent: if `tasks.md` and all expected task files exist and validate against the templates, return `reused: true` and do not overwrite.
- Do not repeat content already in the TechSpec — reference it.

## Analysis Plan

1. **Scope:** confirm slug and the full set of components from the TechSpec.
2. **Inputs consumed:** `prd.md`, `techspec.md`, existing task files (for reuse detection).
3. **Ordering strategy:** dependency order (data → service → UI → e2e), not time order.

## Self-Verification Protocol

**Base checks:**
1. **Completeness** — summary present + one file per main task.
2. **Accuracy** — every referenced component matches the TechSpec.
3. **Contract compliance** — required output blocks present.
4. **Scope discipline** — no architecture invention beyond the TechSpec.
5. **Downstream readiness** — implementation agents can pick tasks sequentially without further input.

**Role-specific checks (tasks):**
6. **Test subtasks present** — every main task has unit + integration test subtasks.
7. **Max 15 main tasks** — count verified.
8. **Dependency order** — no task depends on a later-numbered task.
9. **Reuse detection** — if valid tasks already exist, `reused: true` and no writes performed.

If any fails, fix inline.

## Result Contract

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts:
    - path: ai-docs/prd-<slug>/tasks.md
      status: created | reused | overwritten
    - path: ai-docs/prd-<slug>/01_task.md
      status: created | reused | overwritten
  findings: []
  next_action: "Invoke work-item-mapper for slug <slug>"
metrics:
  tokens_input: <int>
  tokens_output: <int>
  estimated_cost_usd: <float>
  total_duration_ms: <int>
  confidence: high | medium | low
  gaps_count: <int>
  artifacts_count: <int>
total_tasks: <int>
reused: <bool>
```

```yaml
verification_checklist:
  tasks_produced: true
  base_checks_passed: [completeness, accuracy, contract, scope, downstream]
  role_checks_passed: [test_subtasks_present, max_tasks, dependency_order, reuse_detection]
  issues_found_and_fixed: 0
  confidence_after_verification: high | medium | low
```

## Documentation Standard — Context7 First, Repository Fallback

When referencing any library in a task's steps, use Context7 first. Training data alone is never the source of truth.

**Required workflow:**

1. `mcp__plugin_context7_context7__resolve-library-id("library-name")`
2. `mcp__plugin_context7_context7__query-docs(id, topic="specific feature")`

If Context7 is unavailable, note the assumption in the task file itself.
````

- [ ] **Step 2: Sanity check**

```bash
for s in "^name:" "^description:" "^tool_allowlist:" "^## Result Contract$" "^## Self-Verification Protocol$" "^## Analysis Plan$" "^## Documentation Standard — Context7 First, Repository Fallback$" "verification_checklist:"; do
  grep -q "$s" plugins/claude-tech-squad/agents/tasks-planner.md && echo "OK: $s" || { echo "MISSING: $s"; exit 1; }
done
```

- [ ] **Step 3: Commit**

```bash
git add plugins/claude-tech-squad/agents/tasks-planner.md
git commit -m "feat(agents): add tasks-planner agent"
```

---

## Task 8: Create `work-item-mapper` agent

**Files:**
- Create: `plugins/claude-tech-squad/agents/work-item-mapper.md`

- [ ] **Step 1: Write the agent file**

Write `plugins/claude-tech-squad/agents/work-item-mapper.md`:

````markdown
---
name: work-item-mapper
description: Maps a PRD/TechSpec/Tasks set (or a bug report) into the configured vendor-neutral work-item taxonomy defined in runtime-policy.yaml. Emits a structured work-items.md file and enforces opt-in delivery_gates rules. Handles defect vs bug classification for fixes.
tool_allowlist: [Read, Write, Glob, Grep]
---

# Work Item Mapper Agent

You own taxonomy mapping.

## Role

Given delivery artifacts (PRD, TechSpec, Tasks) or a bug/incident report, produce a structured mapping to the configured work-item hierarchy (initiative/epic/story/task/subtask by default, but renameable by teams via `runtime-policy.yaml`).

You do NOT create tickets in Jira, Linear, or GitHub. You only emit the mapping file; a downstream specialist publishes it.

## Rules

- Read `work_item_taxonomy` and `delivery_gates` from `plugins/claude-tech-squad/runtime-policy.yaml` at the start of every run. Never hardcode taxonomy level names.
- If `delivery_gates.enabled: true`, evaluate every rule and include findings in the Result Contract with the configured severity.
- Defect vs bug classification follows `defect_classification`. Default: "in active production" → `bug`; otherwise → `defect`. If ambiguous, mark `needs_input`.
- Output language of descriptions is PT-BR.
- Each item includes: level, title, description, estimate (per `estimation.effort_unit` and `estimation.completion_unit`), parent reference.

## Analysis Plan

1. **Taxonomy load:** read `work_item_taxonomy` and `delivery_gates` from runtime-policy.
2. **Source artifacts:** list the files consumed (`prd.md`, `techspec.md`, `tasks.md`, or a bug report path).
3. **Mapping rules:** state how each source artifact maps to levels (e.g., PRD → epic; TechSpec components → stories; Tasks → subtasks).
4. **Gates evaluated:** list gate ids that will run.

## Self-Verification Protocol

**Base checks:**
1. **Completeness** — every source task is represented in the mapping.
2. **Accuracy** — no hardcoded level names; every name comes from the policy file.
3. **Contract compliance** — required output blocks present.
4. **Scope discipline** — no ticket creation, no external API calls.
5. **Downstream readiness** — a publishing agent can consume `work-items.md` without translation.

**Role-specific checks (work item):**
6. **Taxonomy version captured** — include `taxonomy_version` in the output (sha of the policy file at read time).
7. **Gates executed when enabled** — `severity_findings[]` non-empty when any configured gate fired.
8. **Defect/bug classification** — present and justified for every fix-class input.

If any fails, fix inline.

## Result Contract

```yaml
result_contract:
  status: completed | needs_input | blocked | failed
  confidence: high | medium | low
  blockers: []
  artifacts:
    - path: ai-docs/prd-<slug>/work-items.md
      status: created | reused | overwritten
  findings: []
  next_action: "Hand off to jira-confluence-specialist or equivalent publisher"
metrics:
  tokens_input: <int>
  tokens_output: <int>
  estimated_cost_usd: <float>
  total_duration_ms: <int>
  confidence: high | medium | low
  gaps_count: <int>
  artifacts_count: <int>
items:
  - level: <string>
    title: <string>
    parent: <string | null>
    estimate:
      effort: <number>
      completion: <number>
severity_findings:
  - rule_id: <string>
    severity: BLOCKING | WARNING | INFO
    item_ref: <string>
    message: <string>
taxonomy_version: <string>
```

```yaml
verification_checklist:
  mapping_produced: true
  base_checks_passed: [completeness, accuracy, contract, scope, downstream]
  role_checks_passed: [taxonomy_version, gates_executed, defect_bug_classification]
  issues_found_and_fixed: 0
  confidence_after_verification: high | medium | low
```

## Documentation Standard — Context7 First, Repository Fallback

This agent does not consume external libraries. Context7 is generally not invoked. If the input artifacts mention a library, defer to the upstream agent's validation — do not re-validate here. If an issue-tracker reference appears (e.g., `jira://`), resolve it via the repository's existing specialists, not via training data.
````

- [ ] **Step 2: Sanity check**

```bash
for s in "^name:" "^description:" "^tool_allowlist:" "^## Result Contract$" "^## Self-Verification Protocol$" "^## Analysis Plan$" "^## Documentation Standard — Context7 First, Repository Fallback$" "verification_checklist:"; do
  grep -q "$s" plugins/claude-tech-squad/agents/work-item-mapper.md && echo "OK: $s" || { echo "MISSING: $s"; exit 1; }
done
```

- [ ] **Step 3: Commit**

```bash
git add plugins/claude-tech-squad/agents/work-item-mapper.md
git commit -m "feat(agents): add work-item-mapper agent"
```

---

## Task 9: Create the `inception` skill

**Files:**
- Create: `plugins/claude-tech-squad/skills/inception/SKILL.md`

- [ ] **Step 1: Read a reference orchestrator skill for shape**

Run:
```bash
grep -n "^## \|^### " plugins/claude-tech-squad/skills/discovery/SKILL.md | head -40
```
Note the required sections: frontmatter, Global Safety Contract, Operator Visibility Contract, Preflight Gate, Progressive Disclosure, Agent Result Contract (ARC), Runtime Resilience Contract, Checkpoint / Resume Rules, Live Status Protocol, Visual Reporting Contract (new), SEP log instruction.

- [ ] **Step 2: Write the skill**

Write `plugins/claude-tech-squad/skills/inception/SKILL.md`:

````markdown
---
name: inception
description: Stand-alone technical refinement skill. Consumes an existing PRD and produces a validated TechSpec plus a viability / risk / gate / estimate report via the inception-author agent. Vendor-neutral, Context7-first, idempotent.
---

# /inception — Technical Refinement

Run technical refinement on a feature that already has a validated PRD. Produces `techspec.md` and structured metrics (risks, gates, estimates). Standalone or chained by `squad`.

## Global Safety Contract

Same contract as other orchestrator skills in this plugin. Teammates spawned here may not execute destructive SQL or IaC, may not merge to protected branches, may not force-push, may not bypass pre-commit hooks, and may not remove secrets. See `discovery/SKILL.md` for the full list — this skill applies the identical contract verbatim.

## Operator Visibility Contract

Emit for every teammate action:

- `[Preflight Start] inception`
- `[Preflight Passed] inception | runtime_policy=<version> | slug=<slug>`
- `[Team Created] inception-team`
- `[Teammate Spawned] inception-author | pane: inception-author`
- `[Teammate Done] inception-author | Output: techspec at ai-docs/prd-<slug>/techspec.md`
- `[Teammate Retry] inception-author | Reason: <failure>`
- `[Fallback Invoked] inception-author -> tech-lead | Reason: <summary>`
- `[Checkpoint Saved] inception | cursor=techspec-produced`
- `[Gate] inception-confidence | Waiting for user input` (only when confidence=low)

## Preflight Gate

Before spawning teammates:

1. Read `plugins/claude-tech-squad/runtime-policy.yaml`. Confirm `work_item_taxonomy`, `delivery_gates`, `observability.teammate_cards`, `observability.pipeline_board` are present.
2. Verify `ai-docs/prd-<slug>/prd.md` exists. If missing: block with a clear message telling the operator to run `/claude-tech-squad:discovery` first.
3. If `ai-docs/prd-<slug>/techspec.md` exists and validates against `templates/techspec-template.md`, note reuse intent in the preflight line.

## Progressive Disclosure — Context Digest Protocol

This skill has a single teammate. No digest compression is needed. The PRD is passed by reference (path), not inlined.

## Agent Result Contract (ARC)

Expect from `inception-author`:

```yaml
result_contract:
  status: completed
  confidence: high | medium | low
  artifacts:
    - path: ai-docs/prd-<slug>/techspec.md
      status: created | reused | overwritten
metrics:
  tokens_input: <int>
  tokens_output: <int>
  estimated_cost_usd: <float>
  total_duration_ms: <int>
  confidence: <string>
  gaps_count: <int>
  artifacts_count: <int>
external_deps: [...]
estimated_hours: <float>
estimated_days: <float>
risks: [...]
verification_checklist:
  techspec_produced: true
```

If `metrics` is missing, treat the run as incomplete and retry once before escalating.

## Runtime Resilience Contract

- Retries: up to `retry_budgets.inception.max_retries` (default 2).
- Fallback: after retries exhaust, invoke `tech-lead` with expanded context once.
- Doom-loop check: identical blocker message on consecutive retries triggers a short-circuit to the user gate.

### Checkpoint / Resume Rules

- Checkpoint: `techspec-produced` after `inception-author` completes.
- Resume: if restarted and the techspec file exists and validates, skip the teammate and emit `[Resume From] inception | checkpoint=techspec-produced`.

## Live Status Protocol

Write `ai-docs/.live-status.json` before and after the teammate runs, using the schema defined in `runtime-policy.yaml` under `observability.live_dashboard`. Include `current_artifact: techspec.md` during the run.

## Visual Reporting Contract

- After `inception-author` returns, pipe its Result Contract metrics JSON to `plugins/claude-tech-squad/scripts/render-teammate-card.sh` and print the card. Respect `observability.teammate_cards.format`.
- Before writing the SEP log, assemble the pipeline summary JSON and pipe to `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`. Respect `observability.pipeline_board.enabled`.
- On render-script non-zero exit, log a WARNING in the SEP log; never fail the pipeline on a renderer error.

## SEP Log

Write `ai-docs/.squad-log/inception-<YYYYMMDD-HHMMSS>.md` with `tokens_input`, `tokens_output`, `estimated_cost_usd`, `total_duration_ms`, the techspec artifact path, risks summary, and the exit checkpoint.
````

- [ ] **Step 3: Sanity check all required skill sections present**

```bash
for s in "^### Preflight Gate$" "^## Agent Result Contract (ARC)$" "^## Runtime Resilience Contract$" "^### Checkpoint / Resume Rules$" "^## Progressive Disclosure — Context Digest Protocol$" "^## Live Status Protocol$" "^## Visual Reporting Contract$"; do
  grep -q "$s" plugins/claude-tech-squad/skills/inception/SKILL.md && echo "OK: $s" || { echo "MISSING: $s"; exit 1; }
done
```

- [ ] **Step 4: Commit**

```bash
git add plugins/claude-tech-squad/skills/inception/SKILL.md
git commit -m "feat(skills): add standalone inception skill"
```

---

## Task 10: Insert PRD step and Visual Reporting Contract into `discovery` skill

**Files:**
- Modify: `plugins/claude-tech-squad/skills/discovery/SKILL.md`

- [ ] **Step 1: Find the insertion anchor for the PRD step**

Run: `grep -n "TeamCreate\|Preflight Passed\|spawn" plugins/claude-tech-squad/skills/discovery/SKILL.md | head -20`
Pick the first line AFTER preflight completes and BEFORE the existing specialist bench spawns. Record the line number as `<ANCHOR_N>`.

- [ ] **Step 2: Insert the PRD invocation block at `<ANCHOR_N>`**

Add this block verbatim:

````markdown
## Phase 0 — Delivery Docs: PRD

After preflight and before spawning the specialist bench:

1. Check if `ai-docs/prd-<slug>/prd.md` exists and validates against `templates/prd-template.md`. If yes, emit `[Teammate Done] prd-author | Output: reused ai-docs/prd-<slug>/prd.md` and proceed.
2. Otherwise, spawn `prd-author` as a teammate with the orchestrator context digest:
   - `Agent(team_name="discovery-team", name="prd-author", subagent_type="claude-tech-squad:prd-author", prompt=<digest>)`
3. Wait for completion. Validate the Result Contract `metrics` block is present.
4. If `confidence: low` and `gaps_count > 0`, open a user gate before continuing.
5. Pipe the `metrics` JSON to `render-teammate-card.sh` per the Visual Reporting Contract below.

Checkpoint after this phase: `prd-produced`.
````

- [ ] **Step 3: Append the Visual Reporting Contract**

Find the existing `## Live Status Protocol` section. Add a new section immediately after it:

````markdown
## Visual Reporting Contract

- After every teammate returns, pipe `result_contract.metrics` JSON to `plugins/claude-tech-squad/scripts/render-teammate-card.sh`. Respect `observability.teammate_cards.format` (ascii | compact | silent).
- Immediately before writing the SEP log, assemble the pipeline summary JSON (schema identical to `scripts/test-fixtures/pipeline-board-input.json`) and pipe to `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`. Respect `observability.pipeline_board.enabled`.
- Renderer failures are non-fatal: log a WARNING to the SEP log and continue.
````

- [ ] **Step 4: Add fallback policy reference**

Under `## Runtime Resilience Contract`, ensure the `prd-author` fallback target (`pm`) is mentioned if the skill lists specific fallbacks. If the section already delegates to `runtime-policy.yaml`, no change needed.

- [ ] **Step 5: Verify structural checks still pass**

```bash
bash scripts/validate.sh 2>&1 | tail -20
```
Expected: validation PASS. If it complains about missing Visual Reporting Contract in a skill we have not yet updated, that is expected — we will resolve it in Task 15 (when validate.sh is updated).

For now, verify no NEW failures were introduced in `discovery/SKILL.md`. If the validator runs cleanly minus the expected post-update gap, proceed.

- [ ] **Step 6: Commit**

```bash
git add plugins/claude-tech-squad/skills/discovery/SKILL.md
git commit -m "feat(discovery): add PRD phase and visual reporting contract"
```

---

## Task 11: Insert Tasks + work-item mapping into `implement` skill

**Files:**
- Modify: `plugins/claude-tech-squad/skills/implement/SKILL.md`

- [ ] **Step 1: Find the insertion anchor**

Run: `grep -n "Preflight Passed\|TDD\|backend-dev\|frontend-dev" plugins/claude-tech-squad/skills/implement/SKILL.md | head -20`
Choose the line AFTER preflight completes and BEFORE any build/TDD teammate spawns.

- [ ] **Step 2: Insert the block**

````markdown
## Phase 0 — Delivery Docs: Tasks + Work Items

After preflight, before spawning build/TDD teammates:

1. Verify `ai-docs/prd-<slug>/prd.md` and `ai-docs/prd-<slug>/techspec.md` exist. If either is missing, block with a message directing the operator to run `/claude-tech-squad:discovery` and `/claude-tech-squad:inception` first.
2. If `ai-docs/prd-<slug>/tasks.md` exists and validates, reuse. Else spawn `tasks-planner`:
   - `Agent(team_name="implement-team", name="tasks-planner", subagent_type="claude-tech-squad:tasks-planner", prompt=<digest>)`
3. After tasks are produced, spawn `work-item-mapper`:
   - `Agent(team_name="implement-team", name="work-item-mapper", subagent_type="claude-tech-squad:work-item-mapper", prompt=<digest+taxonomy-context>)`
4. If `delivery_gates.enabled: true` and any BLOCKING finding is returned, open a user gate.
5. Pipe both teammates' `metrics` JSON through `render-teammate-card.sh`.

Checkpoints after this phase: `tasks-produced`, `work-items-produced`.
````

- [ ] **Step 3: Append the Visual Reporting Contract**

Same block as Task 10 Step 3, appended after `## Live Status Protocol`.

- [ ] **Step 4: Run validate.sh, confirm no new failures**

```bash
bash scripts/validate.sh 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-tech-squad/skills/implement/SKILL.md
git commit -m "feat(implement): add tasks-planner and work-item-mapper phase + visual reporting"
```

---

## Task 12: Insert full delivery-docs chain into `squad` skill

**Files:**
- Modify: `plugins/claude-tech-squad/skills/squad/SKILL.md`

- [ ] **Step 1: Find the anchor**

Run: `grep -n "Preflight Passed\|discovery\|implement" plugins/claude-tech-squad/skills/squad/SKILL.md | head -20`
Insert after preflight, before first existing phase spawn.

- [ ] **Step 2: Insert the block**

````markdown
## Phase 0 — Delivery Docs Chain

Squad runs the full delivery docs chain inline. Each step reuses existing artifacts when valid.

1. `prd-author` → `ai-docs/prd-<slug>/prd.md`
2. `inception-author` → `ai-docs/prd-<slug>/techspec.md`
3. `tasks-planner` → `ai-docs/prd-<slug>/tasks.md` + `<num>_task.md`
4. `work-item-mapper` → `ai-docs/prd-<slug>/work-items.md`

Each teammate runs sequentially (downstream depends on upstream artifact). Between steps:

- Pipe `result_contract.metrics` to `render-teammate-card.sh`.
- If any agent returns `confidence: low`, open a user gate before continuing.
- Record a checkpoint per step: `prd-produced`, `techspec-produced`, `tasks-produced`, `work-items-produced`.

If `delivery_gates.enabled: true` and `work-item-mapper` reports a BLOCKING finding, stop the pipeline and open a user gate.
````

- [ ] **Step 3: Append the Visual Reporting Contract**

Same block as Task 10 Step 3.

- [ ] **Step 4: Run validate.sh**

```bash
bash scripts/validate.sh 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-tech-squad/skills/squad/SKILL.md
git commit -m "feat(squad): run full delivery docs chain + visual reporting"
```

---

## Task 13: Insert work-item-mapper into `bug-fix` and `hotfix` skills

**Files:**
- Modify: `plugins/claude-tech-squad/skills/bug-fix/SKILL.md`
- Modify: `plugins/claude-tech-squad/skills/hotfix/SKILL.md`

- [ ] **Step 1: For each of the two skills, find the anchor**

Run: `grep -n "SEP\|root cause\|minimal patch" plugins/claude-tech-squad/skills/bug-fix/SKILL.md | head -10`
Insert the work-item-mapper call after the fix is produced and before the SEP log is written.

- [ ] **Step 2: Insert the block (same wording in both files)**

````markdown
## Post-Fix Classification

After the fix is produced and before writing the SEP log:

1. Spawn `work-item-mapper` with the bug report + fix summary as input.
2. Expect a Result Contract with the defect-vs-bug classification (`defect` for delivered-but-not-yet-prod issues; `bug` for active-production issues — hotfix always classifies as `bug`).
3. Pipe its `metrics` JSON through `render-teammate-card.sh`.
4. Record the classification in the SEP log under `delivery_docs.work_items`.
````

- [ ] **Step 3: Append the Visual Reporting Contract**

Same block as Task 10 Step 3 appended to both files.

- [ ] **Step 4: Run validate.sh**

```bash
bash scripts/validate.sh 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-tech-squad/skills/bug-fix/SKILL.md plugins/claude-tech-squad/skills/hotfix/SKILL.md
git commit -m "feat(bug-fix,hotfix): classify defect vs bug via work-item-mapper + visual reporting"
```

---

## Task 14: Extend `validate.sh` to cover new agents, skill, scripts, and contract

**Files:**
- Modify: `scripts/validate.sh`

- [ ] **Step 1: Add the 4 new agents to `REQUIRED_AGENTS`**

Find the `REQUIRED_AGENTS=(` block and append before the closing `)`:

```bash
  prd-author
  inception-author
  tasks-planner
  work-item-mapper
```

- [ ] **Step 2: Add `inception` to `REQUIRED_SKILLS`**

Find the `REQUIRED_SKILLS=(` block and append before the closing `)`:

```bash
  inception
```

- [ ] **Step 3: Add a check that the two render scripts exist and are executable**

After the `for skill in "${REQUIRED_SKILLS[@]}"; do ... done` block (around line 87 in current version), add:

```bash
# ── Render scripts present and executable ──────────────────────────────────
for script in render-teammate-card.sh render-pipeline-board.sh; do
  path="$PLUGIN_DIR/scripts/$script"
  if [ ! -f "$path" ]; then
    echo "Missing render script: $script"
    exit 1
  fi
  if [ ! -x "$path" ]; then
    echo "Render script not executable: $script"
    exit 1
  fi
done
```

(If `$PLUGIN_DIR` is not already defined, use `$ROOT/plugins/claude-tech-squad` — match the convention already in the script.)

- [ ] **Step 4: Add Visual Reporting Contract check for orchestrator skills**

Find the loop `for skill in discovery implement squad; do` and extend it to also include `inception bug-fix hotfix`. Inside the loop, add:

```bash
  if ! grep -q "^## Visual Reporting Contract$" "$skill_file"; then
    echo "Skill missing Visual Reporting Contract section: $skill"
    exit 1
  fi
```

- [ ] **Step 5: Add a runtime-policy key check for the new sections**

Find the runtime-policy key check (search for `work_item_taxonomy` — if absent, add a new block). Add:

```bash
# ── Runtime policy: new sections ───────────────────────────────────────────
for key in work_item_taxonomy delivery_gates; do
  if ! grep -q "^$key:" "$PLUGIN_DIR/runtime-policy.yaml"; then
    echo "runtime-policy.yaml missing top-level key: $key"
    exit 1
  fi
done
for key in teammate_cards pipeline_board; do
  if ! grep -q "^  $key:" "$PLUGIN_DIR/runtime-policy.yaml"; then
    echo "runtime-policy.yaml observability missing key: $key"
    exit 1
  fi
done
```

- [ ] **Step 6: Run the validator**

```bash
bash scripts/validate.sh
```
Expected: clean PASS. If anything fails, fix the referenced file.

- [ ] **Step 7: Commit**

```bash
git add scripts/validate.sh
git commit -m "test(validate): enforce new agents, inception skill, render scripts, visual reporting contract"
```

---

## Task 15: Update `smoke-test.sh` and `dogfood.sh`

**Files:**
- Modify: `scripts/smoke-test.sh`
- Modify: `scripts/dogfood.sh`
- Modify: `templates/golden-run-scorecard.md`

- [ ] **Step 1: Inspect current smoke-test.sh**

Run: `grep -n "inception\|prd-author\|render-\|discovery\|implement" scripts/smoke-test.sh | head -30`

- [ ] **Step 2: Add assertions for new assets in smoke-test.sh**

Append or insert near other asset assertions:

```bash
# New delivery-docs agents
for a in prd-author inception-author tasks-planner work-item-mapper; do
  test -f "$ROOT/plugins/claude-tech-squad/agents/$a.md" || { echo "smoke: missing agent $a"; exit 1; }
done

# New skill
test -f "$ROOT/plugins/claude-tech-squad/skills/inception/SKILL.md" || { echo "smoke: missing skill inception"; exit 1; }

# Render scripts
for s in render-teammate-card.sh render-pipeline-board.sh; do
  test -x "$ROOT/plugins/claude-tech-squad/scripts/$s" || { echo "smoke: missing or non-executable $s"; exit 1; }
done

# Render fixtures + test
bash "$ROOT/scripts/test-render.sh"
```

- [ ] **Step 3: Inspect dogfood.sh and extend the `layered-monolith` expectations**

Run: `grep -n "layered-monolith\|expected\|artifact" scripts/dogfood.sh | head -30`

Add an assertion section (or extend the existing one) that, when dogfood is run in integration mode, the following files are produced under `fixtures/dogfooding/layered-monolith/.expected/`:

- `ai-docs/prd-layered-monolith/prd.md`
- `ai-docs/prd-layered-monolith/techspec.md`
- `ai-docs/prd-layered-monolith/tasks.md`
- `ai-docs/prd-layered-monolith/work-items.md`

And that the captured terminal output contains both the string `TOTAL` (from the pipeline board) and at least one teammate card header (e.g., `┌─ prd-author ─`).

Full snippet to append:

```bash
if [ "${INTEGRATION:-0}" = "1" ]; then
  for f in prd.md techspec.md tasks.md work-items.md; do
    test -f "fixtures/dogfooding/layered-monolith/.expected/ai-docs/prd-layered-monolith/$f" \
      || { echo "dogfood: missing expected artifact $f"; exit 1; }
  done
  grep -q "TOTAL" fixtures/dogfooding/layered-monolith/.expected/terminal-out.txt \
    || { echo "dogfood: terminal out missing pipeline board TOTAL row"; exit 1; }
  grep -q "┌─ prd-author ─" fixtures/dogfooding/layered-monolith/.expected/terminal-out.txt \
    || { echo "dogfood: terminal out missing prd-author card"; exit 1; }
fi
```

(The `.expected/` directory and its contents are populated by real golden runs — not by this plan. This task only installs the assertions.)

- [ ] **Step 4: Extend `templates/golden-run-scorecard.md`**

Open `templates/golden-run-scorecard.md`. In the main checklist table, add two rows:

```markdown
| Delivery docs present and valid (prd.md, techspec.md, tasks.md, work-items.md) | ☐ |
| Teammate cards and final pipeline board rendered in terminal output | ☐ |
```

Place them near other per-skill output checks — keep list order logical.

- [ ] **Step 5: Run smoke-test.sh**

```bash
bash scripts/smoke-test.sh
```
Expected: PASS. If a dogfood assertion fails because the fixture directory does not yet contain expected files, that is acceptable only if `INTEGRATION` is unset; the smoke-test should only hard-fail on INTEGRATION runs.

- [ ] **Step 6: Commit**

```bash
git add scripts/smoke-test.sh scripts/dogfood.sh templates/golden-run-scorecard.md
git commit -m "test: extend smoke, dogfood, scorecard for delivery docs and visual reporting"
```

---

## Task 16: Update README.md rosters

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Find the agent roster section**

Run: `grep -n "^## \|agents\|skills\|roster" README.md | head -40`

- [ ] **Step 2: Add the 4 new agents to the agent roster**

Locate the alphabetical or categorical list of agents. Insert:

- `prd-author` — generates PRD from orchestrator context
- `inception-author` — generates TechSpec with risks, gates, estimate
- `tasks-planner` — decomposes PRD+TechSpec into sequenced tasks
- `work-item-mapper` — maps delivery artifacts to configured taxonomy

- [ ] **Step 3: Add the `inception` skill to the skill roster**

Locate the skill list and add:

- `/claude-tech-squad:inception` — standalone technical refinement; consumes PRD, emits TechSpec

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): register new agents and inception skill"
```

---

## Task 17: Final validation pass

**Files:** none modified — read-only validation.

- [ ] **Step 1: Run the full validator**

```bash
bash scripts/validate.sh
```
Expected: clean PASS.

- [ ] **Step 2: Run smoke-test + render tests**

```bash
bash scripts/smoke-test.sh
bash scripts/test-render.sh
```
Expected: all PASS.

- [ ] **Step 3: Run dogfood in non-integration mode**

```bash
bash scripts/dogfood.sh
```
Expected: PASS.

- [ ] **Step 4: If any step fails, fix and commit with a targeted message**

Do not amend prior commits. Create a new fix commit referencing the specific check that failed:

```bash
git commit -m "fix(validate): <specific thing that was off>"
```

- [ ] **Step 5: Final commit if all clean**

```bash
git log --oneline -20
```
Confirm the commit history tells a clean story: one commit per task, technical messages, no AI references, no emoji.

---

## Post-Plan Steps (outside the plan, required for Class C)

This plan lands all code. Class C (per the project's change-class rules) then requires at least one real golden run per affected skill. Those runs are executed by an operator with the plugin active — not by the implementation plan itself. The runs populate `ai-docs/dogfood-runs/` and `fixtures/dogfooding/layered-monolith/.expected/`. Only after those exist can the PR merge.

---

## Self-Review

**Spec coverage:**
- 4 new agents ✓ Tasks 5–8
- New `inception` skill ✓ Task 9
- Updates to `discovery` / `implement` / `squad` / `bug-fix` / `hotfix` ✓ Tasks 10–13
- Policy sections (taxonomy, gates, teammate_cards, pipeline_board, fallback_matrix, tool_allowlists) ✓ Task 1
- Render scripts + test ✓ Tasks 2–4
- `validate.sh` enforcement ✓ Task 14
- `smoke-test.sh`, `dogfood.sh`, scorecard ✓ Task 15
- `README.md` rosters ✓ Task 16
- Final pass ✓ Task 17

**Placeholder scan:** no TBD/TODO; every agent template is full; every script has complete code; every insertion block has the exact markdown to paste.

**Type consistency:** agent names stable across tasks (prd-author, inception-author, tasks-planner, work-item-mapper). Checkpoint names stable (prd-produced, techspec-produced, tasks-produced, work-items-produced). Policy keys stable (`work_item_taxonomy`, `delivery_gates`, `observability.teammate_cards`, `observability.pipeline_board`). Script paths stable. Artifact paths stable (`ai-docs/prd-<slug>/...`).

Any drift discovered during execution must be fixed inline in the plan before proceeding to the next task.
