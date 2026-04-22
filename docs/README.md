# Documentation Index

This folder contains all operator and contributor documentation for `claude-tech-squad`.

---

## Getting Started

| Document | Purpose |
|---|---|
| [GETTING-STARTED.md](GETTING-STARTED.md) | Installation, teammate mode setup, commands, and prompt examples |
| [USAGE-BOUNDARIES.md](USAGE-BOUNDARIES.md) | When to use `claude-tech-squad` vs `claude-config` |
| [MANUAL.md](MANUAL.md) | Full technical reference: agents, skills, SEP, gates, and safety guardrails |

---

## Using the Squad

| Document | Purpose |
|---|---|
| [SKILL-SELECTOR.md](SKILL-SELECTOR.md) | Decision tree: which skill to run for each situation (start here if unsure) |
| [OPERATIONAL-PLAYBOOK.md](OPERATIONAL-PLAYBOOK.md) | Which command to run for each delivery scenario |
| [EXECUTION-TRACE.md](EXECUTION-TRACE.md) | How to interpret visible agent execution lines |

---

## Guidelines and Patterns

| Document | Purpose |
|---|---|
| [AGENT-CONTRACT.md](AGENT-CONTRACT.md) | Required structure for every agent: result_contract, handoff protocol, documentation standard, absolute prohibitions |
| [SKILL-CONTRACT.md](SKILL-CONTRACT.md) | Required structure for every skill: global safety contract, operator visibility, preflight, gates, checkpoints, SEP log |
| [RUNTIME-POLICY.md](RUNTIME-POLICY.md) | Reference for `runtime-policy.yaml`: retry budgets, fallback matrix, severity policy, checkpoint fields |
| [SAFETY.md](SAFETY.md) | Safety model: global safety contract, absolute prohibitions, severity levels (BLOCKING / WARNING / INFO) |

---

## Contributing and Development

| Document | Purpose |
|---|---|
| [ENGINEERING-OPERATING-SYSTEM.md](ENGINEERING-OPERATING-SYSTEM.md) | Governance model, change classes (A/B/C/D), and review cadence |
| [HOW-TO-CHANGE-AND-PUBLISH.md](HOW-TO-CHANGE-AND-PUBLISH.md) | Operator checklist for changing the plugin and shipping a new version |

---

## Validation and Release

| Document | Purpose |
|---|---|
| [RELEASING.md](RELEASING.md) | Official GitHub Actions publish path and versioning policy |
| [DOGFOODING.md](DOGFOODING.md) | Controlled validation scenarios and how to run them locally |
| [GOLDEN-RUNS.md](GOLDEN-RUNS.md) | Real-run capture and scorecard validation |

---

## Quick Reference

```bash
# Install
claude plugin marketplace add alexfloripavieira/claude-tech-squad
claude plugin install -s user claude-tech-squad@alexfloripavieira-plugins

# Core commands
/claude-tech-squad:discovery   # shape the problem and produce a blueprint
/claude-tech-squad:implement   # build from an approved blueprint
/claude-tech-squad:squad       # end-to-end: discovery + implementation + release

# Validate before shipping
bash scripts/validate.sh
bash scripts/smoke-test.sh
bash scripts/dogfood.sh
bash scripts/dogfood-report.sh --schema-only
```
