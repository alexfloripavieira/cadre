---
name: bug-fix
description: Agentic bug-resolution skill that reproduces the bug with a failing test, then drives a minimal fix through review. Produces a test that locks the fix, a scoped diff, and a review verdict.

authority_level: 2
intent: >
  Reproduce the reported bug in a failing test, apply a minimal fix, confirm the
  test now passes without regression, and gate the change through code review.
preconditions:
  - "a bug report or failing behavior is stated"
  - "repository tests can be run locally"
  - "working tree is clean or isolated"
success_criteria:
  - "a test exists that fails before the fix and passes after"
  - "no regression in the pre-existing test suite"
  - "code-reviewer returns approved or only nitpick findings"
  - "SEP log records the reproduction, the fix, and the review cycle"
candidate_agents:
  - test-planner
  - code-reviewer
  - security-reviewer
required_agents:
  - test-planner
  - code-reviewer
policy_profile: standard-delivery
max_budget_usd: 3.00
max_duration_seconds: 1200
max_review_cycles: 2
---

# /bug-fix — Agentic Bug Resolution

Run the bug-fix skill when you have a reproducible failure and want Cadre to
drive the resolution. The skill optimizes for the smallest possible diff that
locks in correct behavior.

## Required Inputs

- `bug_report` — the symptom, the expected behavior, and reproduction steps.
- Working branch with current failing behavior on the base branch.

## Typical Path (orchestrator discretion)

1. **test-planner** — writes one reproduction test that fails on the current
   base. Emits the test case definition and expected-vs-actual description.
2. **code-reviewer** — reviews the diff that makes the reproduction test pass.
   Checks for scope creep (unrelated changes), regression risk, and minimal
   surface area.

Optional: `security-reviewer` is invoked when the bug touches auth,
credential handling, or external input parsing. Invocation is automatic when
policy flags `auth_touching_feature: true` for the affected code path.

## Output

- A reproduction test committed to the test suite.
- A minimal-surface fix staged for user review.
- `review_findings` + `security_findings` (when applicable) appended to the
  SEP log.
- No regression in pre-existing tests.

## Budget and Halt Behavior

- `max_budget_usd: 3.00` — tighter than /implement because scope is narrower.
- `max_review_cycles: 2` — at most two producer-reviewer loops.
- Doom-loop detection halts if the reviewer and fix oscillate.

## Non-goals in v0.1

- Not a root-cause-analysis writer. Produces the test + fix; RCA narrative
  belongs in `/incident-postmortem` (deferred to v0.2).
- Not a regression suite builder. Fixes one bug at a time, does not retrofit
  coverage for adjacent untested code.
