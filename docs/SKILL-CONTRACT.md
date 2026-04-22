# Skill Contract

Every skill in `plugins/claude-tech-squad/skills/` must implement this contract. Skills that omit required blocks break preflight validation, SEP log output, or gate behavior.

---

## File location

Each skill lives in its own directory:

```
plugins/claude-tech-squad/skills/<skill-name>/SKILL.md
```

Examples:
```
plugins/claude-tech-squad/skills/discovery/SKILL.md
plugins/claude-tech-squad/skills/implement/SKILL.md
plugins/claude-tech-squad/skills/squad/SKILL.md
```

---

## Required frontmatter

```yaml
---
name: <skill-slug>
description: <one-line description visible in the Claude Code skill picker>
---
```

---

## Required blocks

### 1. Global Safety Contract

Placed at the top of every skill, before any phase definition. Applies to every teammate spawned by the workflow. Cannot be overridden by urgency or user instructions.

The contract prohibits all teammates from executing:
- Destructive SQL (`DROP TABLE`, `DROP DATABASE`, `TRUNCATE`) without rollback script and explicit user confirmation
- Cloud resource deletion in production
- Any application destruction command (`tsuru app-remove`, `heroku apps:destroy`, or equivalent)
- Merge to `main`, `master`, or `develop` without an approved pull request
- Force-push to any protected branch
- Removal of secrets or environment variables from production
- Infrastructure destruction via `terraform destroy` or equivalent
- Disabling or bypassing authentication/authorization as a workaround
- Skipping pre-commit hooks without explicit user authorization
- Dynamic code execution with unsanitized external input
- Applying migrations to production without verifying a backup first

If any teammate believes a task requires one of these actions, it must STOP and surface the decision to the user.

### 2. Operator Visibility Contract

Every skill emits a standard set of trace lines. These lines are the observable proof that the pipeline executed correctly. A run without these lines is not a valid run.

Required trace lines:

```
[Preflight Start] <workflow-name>
[Preflight Warning] <summary>          ← only when a non-blocking issue is detected
[Preflight Passed] <workflow-name> | execution_mode=<mode> | architecture_style=<style> | lint_profile=<profile> | docs_lookup_mode=<mode> | runtime_policy=<version>
[Team Created] <team-name>
[Teammate Spawned] <role> | pane: <name>
[Teammate Done] <role> | Output: <one-line summary>
[Teammate Retry] <role> | Reason: <failure>
[Fallback Invoked] <failed-role> -> <fallback-subagent> | Reason: <summary>
[Resume From] <workflow-name> | checkpoint=<checkpoint>
[Checkpoint Saved] <workflow-name> | cursor=<checkpoint>
[Gate] <gate-name> | Waiting for user input
[Batch Spawned] <phase> | Teammates: <comma-separated names>
[Health Check] <role> | signals: ok     ← after every teammate, 0-token health check
[Health Check] <role> | signals: retry_detected, token_budget_pressure
[Health Warning] <description>          ← only when critical health signal triggers
[AI Detected] <summary>                ← only when LLM/AI code is found in the repo
```

### 2b. Inline Health Check Protocol (for orchestrator skills)

After every `[Teammate Done]`, `[Teammate Retry]`, or `[Fallback Invoked]`, the orchestrator runs a lightweight health check. This is NOT an agent call — it is orchestrator logic that costs zero extra tokens.

**Signals checked (from `inline_health_check` in `runtime-policy.yaml`):**

| Signal | Condition | Action |
|---|---|---|
| `retry_detected` | Teammate required 1+ retries | Append retry context to next teammate prompt |
| `fallback_used` | Primary replaced by fallback | Append fallback context to next teammate |
| `doom_loop_short_circuit` | Doom loop triggered | Append divergence evidence to fallback + next |
| `token_budget_pressure` | tokens_used > 75% of max | Instruct remaining teammates to minimize output |
| `low_confidence_chain` | 2+ consecutive low confidence | Surface warning to user |
| `blocking_findings_accumulating` | 3+ BLOCKING findings total | Recommend pausing to resolve |

**Rules:**
- Emit `[Health Check] <role> | signals: <list_or_ok>` after every teammate
- If any critical signal triggers: emit `[Health Warning] <description>` and update the live dashboard
- Health check context is prepended to the next teammate's prompt (not replacing, enriching)
- The health check itself costs zero tokens — it reads the `result_contract` and execution metadata only
- Write health signals to `.live-status.json` so the live dashboard shows them in real time

### 3. Preflight block

Executed before any agent is spawned. Detects execution context and emits `[Preflight Passed]`.

The preflight must detect and report:
- `execution_mode`: `inline` (default) or `tmux` (when `CLAUDE_CODE_TEAMMATE_MODE=tmux`)
- `architecture_style`: detected from the repository structure (`layered`, `hexagonal`, `microservices`, or `repo-native`)
- `lint_profile`: detected from config files present in the repo (e.g., `eslint,prettier`, `ruff,mypy`)
- `docs_lookup_mode`: `context7` if the MCP is available, `repo-fallback` otherwise
- `runtime_policy`: version from `plugins/claude-tech-squad/runtime-policy.yaml`

**Ticket Intake (optional):** If the user's input matches a ticket ID pattern (`[A-Z]+-[0-9]+` for Jira, `#[0-9]+` for GitHub Issues), the preflight should attempt to read the ticket via the appropriate MCP tool and extract title, description, acceptance criteria, priority, and subtasks. This enriches the skill input without requiring the user to retype the spec. If the MCP tool is unavailable, continue with the user's text as-is — do not block. Emit `[Ticket Read] {{source}} | {{ticket_id}}` if successful.

### 4. Teammate architecture block

Defines the tool sequence for spawning agents:

```markdown
## Teammate Architecture

1. `TeamCreate` — create the team for this workflow
2. `Agent` with `team_name` + `name` + `subagent_type` — spawn each specialist as a teammate
3. `SendMessage` — communicate with running teammates
4. `TaskCreate` + `TaskUpdate` — assign and track work per teammate

**Do NOT use Agent without team_name** — that runs an inline subagent, not a visible teammate pane.
```

### 5. Progressive Disclosure (Context Digest Protocol)

Skills must not forward full upstream agent output to every downstream agent. Instead, the orchestrator produces a **context digest** between phases to reduce token consumption and maintain agent focus.

**Rules:**

1. **Sequential agents** — When agent B depends on agent A's output, forward a context digest (max 500 tokens) unless agent B explicitly needs the full output. The digest summarizes: key decisions, artifacts produced, open questions, and blockers.
2. **Parallel batch agents** — Each agent in a batch receives only the context relevant to its specialty, not the complete output of all prior agents.
3. **Full output access** — Agents that explicitly need the full upstream output (e.g., Reviewer needs the complete implementation diff, QA needs the full test plan) receive it. All others receive the digest.
4. **Digest format:**

```markdown
## Context Digest — {{source_agent}} ({{phase}})

**Key decisions:** {{bullet_list}}
**Artifacts produced:** {{file_list}}
**Open questions:** {{list_or_none}}
**Blockers:** {{list_or_none}}
**Architecture style:** {{style}}
**Full output reference:** available on request from orchestrator
```

5. **Token savings target** — Progressive disclosure should reduce total token consumption by 20-30% compared to forwarding full outputs.

### 6. Agent chain definition

The ordered list of agents invoked by the skill, with their phase, purpose, and any gate that precedes or follows them.

Format:

```markdown
## Phase: <phase-name>

Spawn in order:

1. `<agent-subagent-type>` — <one-line purpose>
2. `<agent-subagent-type>` — <one-line purpose>

[Gate] <gate-name> — <what the user decides here>

3. `<agent-subagent-type>` — <one-line purpose> (parallel with 4)
4. `<agent-subagent-type>` — <one-line purpose> (parallel with 3)
```

### 7. Gate definitions

Gates pause the workflow and require a user decision before continuing. Each gate must define:
- Its name (used in the `[Gate]` trace line)
- What the user is deciding
- What counts as approval vs. rejection
- What happens on each path

Gates exist only where human judgment is irreplaceable. Do not add gates for decisions that agents can resolve autonomously.

**Gate Consolidation Rule:** When multiple agents fail in the same parallel batch (e.g., quality bench), the orchestrator must present a single consolidated gate instead of sequential individual gates. The consolidated gate lists all failed agents and offers batch actions:

```
[Gate] Batch Failure — Quality Bench | 3 of 6 agents failed

Failed agents:
1. security-rev — empty response after retry
2. perf-eng — structurally invalid output
3. access-rev — error: tool unavailable

Options:
- [R] Retry all 3 failed agents
- [1,3] Retry specific agents by number
- [S] Skip all failed agents and continue (log risk for each)
- [X] Abort the run
```

This prevents gate fatigue — the user makes one decision instead of N sequential ones.

**Auto-advance Rule:** Non-mandatory gates may be auto-advanced when all conditions in `auto_advance` from `runtime-policy.yaml` are met. The auto-advance is logged with `[Auto-Advanced]` and the user is informed post-hoc. Mandatory gates (listed in `auto_advance.mandatory_gates`) always require explicit user input.

### 8. Checkpoint and resume block

Every skill must define checkpoints and the resume rule. Written to the SEP log via `checkpoint_resume.write_to_sep_log: true` in `runtime-policy.yaml`.

```markdown
## Checkpoints

Save a checkpoint after each of the following:
- `preflight-passed`
- `gate-<n>-approved` (one per gate)
- `<phase-name>-complete`

Resume rule: resume from the highest completed checkpoint unless inputs materially changed.
```

### 9. Run Cost Summary (end of every run)

After the last gate resolves and before asking for developer feedback, every skill must emit a one-line cost summary. This is **mandatory** and **not skippable** — the dev sees the cost of every run.

```
[Run Summary] /{{skill}} | teammates: {{N}} | tokens: {{input}}K in / {{output}}K out | est. cost: ~${{usd}} | duration: {{time}}
```

Example:
```
[Run Summary] /implement | teammates: 12 | tokens: 1,450K in / 210K out | est. cost: ~$12.40 | duration: 32m
```

**Rules:**
- Token counts are summed across all teammates (or the inline run if no teammates)
- Cost estimate uses: input tokens × $15/M + output tokens × $75/M (Opus pricing) — adjust if the model is different
- Duration is wall clock from `[Preflight Start]` to `[SEP Log Written]`
- For zero-agent skills (cost-estimate, dashboard), still emit the summary with the orchestrator's own token usage
- Write the same values to the SEP log fields: `tokens_input`, `tokens_output`, `estimated_cost_usd`, `total_duration_ms`

### 10. Developer Feedback Gate (end of every run)

Before writing the SEP log, every skill must ask the dev for a quick satisfaction signal. This is a **non-blocking** prompt — the dev can skip it. The response is recorded in the SEP log for `/factory-retrospective` to analyze.

```
Run complete. Quick feedback (optional — press Enter to skip):

How useful was this run?
[1] Not useful — I'll redo this manually
[2] Partially useful — some good output, some wasted
[3] Useful — saved me real time
[4] Very useful — I couldn't have done this alone
[S] Skip

One-line comment (optional): ___
```

Record in the SEP log as:
```yaml
developer_feedback:
  score: 1-4 | skipped
  comment: "..." | null
```

**Rules:**
- Never block the run on feedback — if the dev doesn't respond in 10 seconds, record `skipped`
- The feedback is for `/factory-retrospective` analysis only — it does not change the pipeline behavior
- Over time, the retrospective can correlate: "runs with 2+ retries get lower satisfaction scores" → actionable improvement

### 11. SEP log instruction

The skill must instruct the orchestrator to write a Squad Execution Protocol log to `ai-docs/.squad-log/` before the run ends.

Minimum fields required in the SEP log:
- `skill`
- `execution_mode`
- `architecture_style`
- `checkpoints` (array of cleared checkpoints)
- `fallbacks_invoked` (array, empty if none)
- `final_status`
- `timestamp`
- `developer_feedback` (score + comment, or `skipped`)

### 10. Live Status Protocol (for orchestrator skills)

Orchestrator skills (those that spawn teammates) must write a live status file to `ai-docs/.live-status.json` after every trace event. This enables the live dashboard (`plugins/claude-tech-squad/dashboard/live.html`) to show real-time teammate status, token budget, and event timeline.

**Update trigger:** Every time the orchestrator emits a trace line (`[Teammate Spawned]`, `[Teammate Done]`, `[Gate]`, etc.), it must also write the current state to `.live-status.json`.

**Required JSON schema:**

```json
{
  "skill": "implement",
  "run_id": "abc123",
  "phase": "quality-bench",
  "started_at": "2026-04-12T10:30:00Z",
  "checkpoint_cursor": "qa-pass",
  "checkpoints": ["preflight-passed", "commands-confirmed", "..."],
  "completed_checkpoints": ["preflight-passed", "commands-confirmed"],
  "tokens_used": 1250000,
  "tokens_max": 4000000,
  "current_gate": null,
  "teammates": [
    {
      "name": "tdd-specialist",
      "subagent_type": "claude-tech-squad:tdd-specialist",
      "status": "completed",
      "started_at": "2026-04-12T10:30:05Z",
      "duration_ms": 45000,
      "tokens_input": 12000,
      "tokens_output": 8000,
      "output_summary": "failing tests written for user-auth",
      "retry_count": 0,
      "fallback_from": null,
      "doom_loop": null
    },
    {
      "name": "backend-dev",
      "subagent_type": "claude-tech-squad:backend-dev",
      "status": "running",
      "started_at": "2026-04-12T10:31:00Z",
      "duration_ms": null,
      "tokens_input": null,
      "tokens_output": null,
      "output_summary": null,
      "retry_count": 0,
      "fallback_from": null,
      "doom_loop": null
    }
  ],
  "events": [
    {"time": "10:30:00", "line": "[Preflight Passed] implement | execution_mode=inline | ..."},
    {"time": "10:30:05", "line": "[Teammate Spawned] tdd-specialist | pane: tdd-specialist"},
    {"time": "10:30:50", "line": "[Teammate Done] tdd-specialist | Output: failing tests written"},
    {"time": "10:31:00", "line": "[Teammate Spawned] backend-dev | pane: backend-dev"}
  ]
}
```

**Rules:**
- Write the file atomically (write to a temp file, then rename) to prevent the dashboard from reading a partial JSON
- On `[Gate]` events, set `current_gate` to the gate description; clear it when the gate resolves
- On `[Teammate Done]`, update the teammate's `status`, `duration_ms`, `tokens_input`, `tokens_output`, and `output_summary`
- On `[SEP Log Written]`, set phase to "completed" — the dashboard shows the final state
- The dev opens the dashboard with: `bash scripts/open-dashboard.sh`

---

## Teammate output validation (Reasoning Sandwich enforcement)

A teammate response is structurally valid only when it contains ALL of:
1. The role-specific body requested by that agent
2. A `result_contract` block with valid `status`, `confidence`, `blockers`, `artifacts`, `findings`, `next_action`
3. A `verification_checklist` block with `plan_produced: true`, non-empty `base_checks_passed`, non-empty `role_checks_passed`, and `confidence_after_verification` matching the `result_contract.confidence`

Missing `result_contract` OR missing `verification_checklist` = structurally invalid = trigger the Teammate Failure Protocol.

For execution agents, the output must also contain a `## Pre-Execution Plan` section. For analysis agents, it must contain a `## Analysis Plan` section. Absence of the plan section means the agent skipped Phase 1 of the Reasoning Sandwich and must be retried.

---

## Failure handling

Skills rely on `runtime-policy.yaml` for retry and fallback behavior. A skill does not define its own retry limits — it inherits them from the central policy:

| Situation | Policy |
|---|---|
| Agent produces invalid output | Retry same agent, max 2 times |
| Agent missing `verification_checklist` | Retry same agent (Phase 3 not completed) |
| Agent missing plan section | Retry same agent (Phase 1 not completed) |
| Agent fails after 2 retries | Invoke fallback from `fallback_matrix` |
| Fallback also fails | Present gate to user: R (retry) / S (skip with risk log) / X (abort) |
| Finding is BLOCKING | Pause pipeline, require resolution before continuing |

Skills reference the fallback matrix implicitly — they do not hardcode fallback agents.

### Doom Loop Detection

Before executing each retry, the orchestrator must check for divergence patterns defined in `doom_loop_detection` from `runtime-policy.yaml`. A doom loop is detected when:

1. **Growing diff** — the retry produces a larger diff than the previous attempt (agent is making more changes, not converging)
2. **Oscillating fix** — the retry reverts lines changed in the previous attempt (agent is alternating between two states)
3. **Same error** — the same test failure or lint error reappears unchanged after the retry

When a doom loop is detected:
- Emit: `[Doom Loop Detected] <agent> | pattern=<rule_name> | retries=<count>`
- Immediately stop retrying the same agent
- Invoke the fallback agent from `fallback_matrix` with the doom loop evidence as context
- If the fallback also loops or fails, surface the gate to the user with the doom loop pattern as evidence

This prevents wasted tokens on agents that are not converging toward a solution.

---

## What makes a skill invalid

| Problem | Effect |
|---|---|
| Missing Global Safety Contract | Agents spawned without prohibitions contract |
| Missing Operator Visibility Contract | Run produces no trace lines — not verifiable |
| Missing preflight | No `[Preflight Passed]` — run fails smoke test |
| No checkpoints defined | Interrupted runs cannot be resumed |
| No SEP log instruction | `/factory-retrospective` has no data to analyze |
| Gates with no decision criteria | User cannot meaningfully approve or reject |
