# Runtime Policy

`plugins/claude-tech-squad/runtime-policy.yaml` is the central configuration file for all skills. It defines retry budgets, fallback behavior, severity classification, checkpoint fields, and reliability tracking. Skills read this file at preflight — no skill hardcodes these values.

Current version: **5.22.0**

---

## docs_lookup

Controls how agents look up library and framework documentation.

```yaml
docs_lookup:
  preferred: context7
  fallback: repo-fallback
  fallback_requires:
    - cite repository files used
    - state assumptions explicitly
    - do not block the workflow on documentation tool absence alone
```

| Field | Meaning |
|---|---|
| `preferred: context7` | Every agent uses the Context7 MCP first for any library or API lookup |
| `fallback: repo-fallback` | When Context7 is unavailable, use repository files as evidence |
| `fallback_requires` | When using repo-fallback, agents must cite sources and flag assumptions |

An agent that uses training data as the source of truth for API signatures — without declaring it — violates this policy.

---

## failure_handling

Controls what happens when an agent fails to produce valid output.

```yaml
failure_handling:
  structural_retry_same_prompt_max: 2
  fallback_attempt_max: 1
  unresolved_action_gate:
    options: [R, S, X]
    meanings:
      R: retry once more with the same prompt
      S: skip and continue with explicit risk logging
      X: abort the run
```

| Field | Meaning |
|---|---|
| `structural_retry_same_prompt_max: 2` | An agent is retried at most 2 times before the fallback is invoked |
| `fallback_attempt_max: 1` | The fallback agent is tried at most once |
| `unresolved_action_gate` | If fallback also fails, the user sees R/S/X and decides |

When the user selects **S (skip)**, the risk must be logged in the SEP log before continuing. **X (abort)** ends the run immediately.

---

## retry_budgets

Caps the number of cycles per review/validation phase to prevent infinite loops.

```yaml
retry_budgets:
  review_cycles_max: 3
  qa_cycles_max: 2
  conformance_cycles_max: 2
  quality_fix_cycles_max: 2
  uat_cycles_max: 2
```

| Budget | What it limits |
|---|---|
| `review_cycles_max: 3` | Reviewer → implementation back-and-forth |
| `qa_cycles_max: 2` | QA → implementation back-and-forth |
| `conformance_cycles_max: 2` | TechLead conformance audit cycles |
| `quality_fix_cycles_max: 2` | Quality bench (security, privacy, etc.) fix cycles |
| `uat_cycles_max: 2` | PM UAT rejection → re-implementation cycles |

When a budget is exhausted, the pipeline presents a gate to the user.

---

## severity_policy

Classifies findings from reviewer agents into three levels. Skills use this classification to decide whether to block or continue.

```yaml
severity_policy:
  blocking:
    - security vulnerability
    - pii or secret leak
    - privacy violation
    - failing required tests
    - ci-breaking lint or static-analysis failure
    - wcag a or aa failure
    - contract-breaking api or schema regression
  warning:
    - performance regression without outage risk
    - non-critical accessibility issue
    - integration fragility
    - code quality debt
    - operational observability gap
  info:
    - optional refactor
    - style suggestion
    - documentation improvement
```

**BLOCKING** — the pipeline stops. The finding must be resolved before continuing. A `[Gate]` is emitted. The skill does not advance to the next phase or release.

**WARNING** — the finding is documented in the output and SEP log but does not stop the pipeline. The user can proceed.

**INFO** — informational only. Logged, not surfaced as a decision point.

---

## fallback_matrix

Maps each agent role (per skill context) to its fallback agents. When a primary agent fails twice, the skill invokes the first available fallback and emits `[Fallback Invoked]`.

Structure:

```yaml
fallback_matrix:
  <skill>:
    <primary-role>:
      - <fallback-subagent-type>
      - <second-fallback-if-needed>
```

Excerpt:

```yaml
fallback_matrix:
  discovery:
    pm:
      - claude-tech-squad:po
    architect:
      - claude-tech-squad:backend-architect
      - claude-tech-squad:solutions-architect
    tdd-specialist:
      - claude-tech-squad:test-planner

  implement:
    reviewer:
      - claude-tech-squad:code-quality
      - claude-tech-squad:techlead
    qa:
      - claude-tech-squad:integration-qa
      - claude-tech-squad:test-automation-engineer
    docs-writer:
      - claude-tech-squad:tech-writer

  squad:
    release:
      - claude-tech-squad:sre
    sre:
      - claude-tech-squad:release
```

Skills never hardcode fallback agents in their SKILL.md. All fallback resolution goes through this matrix.

---

## checkpoint_resume

Controls how checkpoints are written to the SEP log and which checkpoints each skill defines.

```yaml
checkpoint_resume:
  write_to_sep_log: true
  fields:
    - checkpoint_cursor
    - completed_checkpoints
    - resume_from
    - fallback_invocations
    - teammate_reliability
```

Checkpoints per skill:

| Skill | Checkpoints |
|---|---|
| `discovery` | `preflight-passed`, `gate-1-approved`, `gate-2-approved`, `gate-3-approved`, `gate-4-approved`, `specialist-bench-complete`, `quality-baseline-complete`, `blueprint-confirmed` |
| `implement` | `preflight-passed`, `commands-confirmed`, `blueprint-validated`, `tdd-ready`, `implementation-batch-complete`, `reviewer-approved`, `qa-pass`, `conformance-pass`, `quality-bench-cleared`, `docs-complete`, `uat-approved` |
| `squad` | `preflight-passed`, `discovery-confirmed`, `implementation-complete`, `release-signed-off` |

Resume rules:
- **discovery**: resume from the highest completed checkpoint unless inputs materially changed.
- **implement**: resume from the highest completed checkpoint and only rerun failed downstream gates.
- **squad**: resume from the last completed phase boundary unless the user requests a full rerun.

---

## reliability_metrics

Fields tracked per run for retrospective analysis by `/factory-retrospective`.

```yaml
reliability_metrics:
  tracked:
    - retry_count
    - fallback_invocations
    - checkpoint_cursor
    - completed_checkpoints
    - resume_from
    - teammate_reliability
  teammate_reliability_states:
    - primary            # ran successfully on first attempt
    - primary-after-retry  # succeeded after 1-2 retries
    - fallback-used      # primary failed; fallback ran
    - skipped-with-risk  # user chose S at the gate
    - unresolved         # user chose X or run aborted
```

These fields are written to the SEP log and consumed by `/factory-retrospective` to compute retry rates, fallback rates, and checkpoint stop patterns.
