---
name: review
description: Agentic pull-request / diff review skill. Routes the diff through code-reviewer and, when security surface is touched, through security-reviewer. Emits structured findings and an overall verdict.

authority_level: 2
intent: >
  Produce a structured review of a pull request or diff, classify findings by
  severity, route security-sensitive changes through the security reviewer,
  and emit one overall verdict (approved, revision_requested, blocked).
preconditions:
  - "a diff or PR reference is available"
  - "intent or acceptance criteria of the change are stated or inferable"
success_criteria:
  - "code-reviewer findings are emitted with file + line citations"
  - "security-reviewer is invoked when change touches auth, input parsing,
    secrets, or external integrations"
  - "final verdict is one of approved | revision_requested | blocked"
  - "SEP log captures every review cycle and the final status"
candidate_agents:
  - code-reviewer
  - security-reviewer
required_agents:
  - code-reviewer
policy_profile: standard-delivery
max_budget_usd: 2.00
max_duration_seconds: 900
max_review_cycles: 1
---

# /review — Agentic PR Review

Run the review skill when you have a diff or PR and want a structured review
that classifies findings by severity and routes to security when relevant.

## Required Inputs

- `diff_or_pr_reference` — git diff, commit range, or PR URL.
- `intent_or_acceptance_criteria` — what the change is supposed to accomplish.

## Typical Path (orchestrator discretion)

1. **code-reviewer** — reads the diff + intent, emits `review_findings` with
   severity and citations, and a `review_status`.
2. **security-reviewer** — invoked when code-reviewer flags a security-
   relevant file or when the policy's `auth_touching_feature` heuristic
   matches. Emits `security_findings` + `security_status`.

The orchestrator combines the two status signals:

- Both `approved` → overall `approved`.
- Any `blocked` → overall `blocked`.
- Any `revision_requested` (and no blocked) → overall `revision_requested`.

## Output

- `review_findings`, `review_status` from code-reviewer.
- `security_findings`, `security_status` from security-reviewer (when
  invoked).
- A one-paragraph overall summary.
- Full SEP log entries under `phase: review`.

## Budget and Halt Behavior

- `max_budget_usd: 2.00` — review is cheaper than implement.
- `max_review_cycles: 1` — review is one-shot in v0.1; revision loops are a
  caller concern. If the diff is revised, invoke `/review` again.
- Doom-loop detection: not expected to trigger in a one-shot review.

## Non-goals in v0.1

- Not a review enforcer. Cadre emits findings; merging (or not) is the user's
  choice.
- Not a PR comment poster. The findings stay in the SEP log and the terminal
  output; integrations with GitHub PR comments ship in v0.2.
