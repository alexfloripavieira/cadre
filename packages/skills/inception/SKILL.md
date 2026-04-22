---
name: inception
description: Stand-alone technical refinement skill. Consumes an existing PRD and produces a validated TechSpec plus a viability / risk / gate / estimate report via the inception-author agent. Vendor-neutral, Context7-first, idempotent.
---

# /inception — Technical Refinement

Run technical refinement on a feature that already has a validated PRD. Produces `techspec.md` and structured metrics (risks, gates, estimates). Standalone or chained by `squad`.

## Global Safety Contract

**This contract applies to every teammate spawned by this workflow. Violating it requires explicit written user confirmation.**

No teammate may, under any circumstances:
- Execute `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, or any destructive SQL without a verified rollback script and explicit user confirmation
- Delete cloud resources (S3 buckets, databases, clusters, queues) in production
- Run `tsuru app-remove`, `heroku apps:destroy`, or any equivalent application deletion command
- Merge to `main`, `master`, or `develop` without an approved pull request
- Force-push (`git push --force`) to any protected branch
- Remove secrets or environment variables from production
- Destroy infrastructure via `terraform destroy` or equivalent IaC commands
- Disable or bypass authentication/authorization as a workaround
- Skip pre-commit hooks (`git commit --no-verify`) without explicit user authorization
- Execute `eval()`, dynamic shell injection, or unsanitized external input in commands
- Apply migrations or schema changes to production without first verifying a backup exists

If any teammate believes a task requires one of these actions, it must STOP and surface the decision to the user before proceeding.

## Core Principle

All technical decisions must be grounded in the repository's real stack, conventions, and current documentation via Context7.

## Teammate Architecture

This workflow creates a team and spawns `inception-author` as a real teammate:

1. `TeamCreate` — create the inception team
2. `Agent` with `team_name="inception-team"` + `name="inception-author"` + `subagent_type="claude-tech-squad:inception-author"`
3. `SendMessage` — communicate with the running teammate
4. `TaskCreate` + `TaskUpdate` — track work

## Operator Visibility Contract

Emit for every teammate action:

- `[Preflight Start] inception`
- `[Preflight Warning] <summary>`
- `[Preflight Passed] inception | runtime_policy=<version> | slug=<slug>`
- `[Team Created] inception-team`
- `[Teammate Spawned] inception-author | pane: inception-author`
- `[Teammate Done] inception-author | Output: techspec at ai-docs/prd-<slug>/techspec.md`
- `[Teammate Retry] inception-author | Reason: <failure>`
- `[Fallback Invoked] inception-author -> tech-lead | Reason: <summary>`
- `[Resume From] inception | checkpoint=techspec-produced`
- `[Checkpoint Saved] inception | cursor=techspec-produced`
- `[Gate] inception-confidence | Waiting for user input`

### Preflight Gate

Before spawning teammates:

1. Read `plugins/claude-tech-squad/runtime-policy.yaml`. Confirm `work_item_taxonomy`, `delivery_gates`, `observability.teammate_cards`, `observability.pipeline_board` are present.
2. Verify `ai-docs/prd-<slug>/prd.md` exists. If missing: block with a clear message telling the operator to run `/claude-tech-squad:discovery` first.
3. If `ai-docs/prd-<slug>/techspec.md` exists and validates against `templates/techspec-template.md`, note reuse intent in the preflight line.
4. Emit `[Preflight Passed] inception | runtime_policy=<version> | slug=<slug>`.

## Progressive Disclosure — Context Digest Protocol

This skill has a single teammate. No digest compression is needed between phases. The PRD is passed by reference (path), not inlined, keeping prompt size bounded.

**Digest format (if passed to fallback tech-lead):**

```markdown
## Context Digest — inception-author (technical-refinement)

**Key decisions:** {{bullet_list}}
**Artifacts produced:** {{file_list}}
**Open questions:** {{list_or_none}}
**Blockers:** {{list_or_none}}
**Architecture style:** {{style}}
**Full output reference:** available on request from orchestrator
```

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

- Retries: up to `retry_budgets.inception.max_retries` (default 2 from runtime-policy).
- Fallback: after retries exhaust, invoke `claude-tech-squad:tech-lead` with expanded context once.
- Doom-loop check: identical blocker message on consecutive retries triggers a short-circuit to the user gate.
- Cost guardrail: if cumulative tokens exceed the per-skill budget in `cost_guardrails`, halt and open a user gate.

### Checkpoint / Resume Rules

- Checkpoint: `techspec-produced` after `inception-author` completes successfully.
- Resume: if restarted and the techspec file exists and validates, skip the teammate and emit `[Resume From] inception | checkpoint=techspec-produced`.
- The SEP log is written on every successful completion or user-abort; partial runs preserve `last_updated_at` so `stale_in_flight` detection works.

## Live Status Protocol

Write `ai-docs/.live-status.json` before and after the teammate runs, using the schema defined in `runtime-policy.yaml` under `observability.live_dashboard`. Include `current_artifact: techspec.md` during the run.

## Visual Reporting Contract

- After `inception-author` returns, pipe its Result Contract `metrics` JSON to `plugins/claude-tech-squad/scripts/render-teammate-card.sh` and print the card. Respect `observability.teammate_cards.format` (ascii | compact | silent).
- Before writing the SEP log, assemble the pipeline summary JSON (schema identical to `scripts/test-fixtures/pipeline-board-input.json`) and pipe to `plugins/claude-tech-squad/scripts/render-pipeline-board.sh`. Respect `observability.pipeline_board.enabled`.
- On render-script non-zero exit, log a WARNING in the SEP log; never fail the pipeline on a renderer error.

## SEP Log

Write `ai-docs/.squad-log/inception-<YYYYMMDD-HHMMSS>.md` with:

- `run_id`, `skill: inception`, `timestamp`, `last_updated_at`, `final_status`, `execution_mode`, `architecture_style`
- `checkpoints: [preflight-passed, techspec-produced]`
- `fallbacks_invoked`, `retry_count`
- `tokens_input`, `tokens_output`, `estimated_cost_usd`, `total_duration_ms`
- `teammates:` entry for `inception-author` with per-teammate fields from `observability.sep_log_schema.teammate_fields`
- `delivery_docs.techspec`: path and status
- Risks summary and exit checkpoint
