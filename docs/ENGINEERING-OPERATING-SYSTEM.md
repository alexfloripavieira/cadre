# Engineering Operating System

This is the operating model for running `claude-tech-squad` like a high-discipline engineering organization.

## What "Big Tech" Means Here

For this plugin, "Big Tech" does not mean bigger prompts. It means:

- architecture is explicit and reviewable
- delivery is measured, not assumed
- reliability is part of the default path
- security and privacy are first-class gates
- every release has evidence
- incidents produce durable learning
- the team improves from execution data

## Operating Loop

Use this loop for every non-trivial change:

1. Shape the work with `/discovery` or `/squad`
2. Record tradeoffs in ADRs or RFCs
3. Build with `/implement` or `/squad`
4. Validate through review, QA, conformance, and quality bench
5. Prove behavior with golden runs for important workflow changes
6. Release with rollback and SRE sign-off
7. Learn through `/factory-retrospective` and incident post-mortems

## Change Classes

### Class A — Prompt or Doc Only

Examples:
- wording improvements
- examples
- non-structural documentation

Required:
- `scripts/validate.sh`
- `scripts/smoke-test.sh`

### Class B — Workflow Contract Change

Examples:
- retry logic
- fallback behavior
- checkpoint/resume
- new gates
- new SEP fields

Required:
- `scripts/validate.sh`
- `scripts/smoke-test.sh`
- `scripts/dogfood.sh`
- golden run scorecards planned or updated

### Class C — Orchestration or Specialist Model Change

Examples:
- new agents
- changed subagent routing
- architecture selection changes
- quality bench changes

Required:
- all Class B checks
- updated fixture expectations if behavior changed
- at least one real golden run per affected scenario family

### Class D — Release-Critical Change

Examples:
- release workflow changes
- incident management changes
- security/privacy gate changes
- anything that changes production decision quality

Required:
- all Class C checks
- real golden runs recorded
- explicit release note in changelog
- operator-facing doc update

## Required Evidence Per Workflow

### Discovery

- visible preflight
- architecture style selection
- specialist selection rationale
- blueprint artifact
- ADRs when tradeoffs matter

### Implement

- failing tests first when code changes apply
- completion blocks from implementation agents
- reviewer outcome
- QA outcome
- conformance audit
- quality bench findings and resolution

### Squad

- discovery evidence
- implementation evidence
- release and SRE outcome
- SEP log with checkpoint and fallback fields

### Hotfix / Incident

- diagnosis gate
- staging gate or explicit skip with reason
- rollback path
- postmortem recommendation or follow-through

## Metrics That Matter

Track these continuously through SEP and retrospectives:

- retry rate by skill
- fallback usage by agent
- checkpoint where runs most often stop
- UAT rejection rate
- quality bench blocking rate
- orphaned discoveries
- hotfixes without postmortem
- release runs with unresolved risk

## Review Cadence

### Every change

- validate
- smoke test
- dogfood fixture check

### Weekly

- run `/factory-retrospective`
- review top failure patterns
- review most used fallbacks
- decide prompt or workflow corrections

### Monthly

- review operating metrics
- inspect release friction
- inspect incident learnings
- retire stale or overlapping agents

## Governance Rules

- No workflow change ships without a changelog entry
- No release-critical change ships without an operator doc update
- No fallback is added without a concrete ownership reason
- No checkpoint is added unless resume semantics are clear
- No new agent should overlap heavily with an existing one without boundary text

## Recommended Templates

Use:

- [RFC template](/home/alex/claude-tech-squad/templates/rfc-template.md)
- [Service readiness review](/home/alex/claude-tech-squad/templates/service-readiness-review.md)
- [Golden run scorecard](/home/alex/claude-tech-squad/templates/golden-run-scorecard.md)
