# Operational Playbook

This playbook shows how to use `claude-tech-squad` in common delivery scenarios inside a real repository.

Use it when you want a practical answer to: "which command should I run for this kind of work?"

## Core Rule

Choose the lightest command that still matches the real delivery scope:

- `/claude-tech-squad:onboarding` for bootstrapping a new repository
- `/claude-tech-squad:discovery` for shaping and planning
- `/claude-tech-squad:implement` for execution after approval
- `/claude-tech-squad:squad` for end-to-end or audit-style work
- `/claude-tech-squad:refactor` for safe technical debt reduction
- `/claude-tech-squad:release` for cutting a release from existing work
- `/claude-tech-squad:incident-postmortem` for learning after incidents

Default behavior note:

- `/claude-tech-squad:squad` is TDD-first by default for code changes

---

## Scenario 0: New Repository — Bootstrap

Use: `/claude-tech-squad:onboarding`

When:
- starting a new project from scratch
- adopting the squad workflow in an existing repository for the first time
- you want a CLAUDE.md template, ai-docs/ structure, and a security baseline before the first sprint

```text
/claude-tech-squad:onboarding
```

Run this once per repository before any other squad command.

---

## Scenario 1: New Feature

Use: `/claude-tech-squad:discovery`

When:
- the problem still needs shaping
- architecture is not yet confirmed
- acceptance criteria need to be clarified

```text
/claude-tech-squad:discovery
Design the next delivery slice for subscription management, including admin roles, audit trail, rollout boundaries, and acceptance criteria.
```

---

## Scenario 2: Implement Approved Blueprint

Use: `/claude-tech-squad:implement`

When:
- discovery is already done
- architecture and scope have been approved
- you want TDD cycles, build, review, QA, docs, and UAT coordination

```text
/claude-tech-squad:implement
Use the approved blueprint to implement the next delivery slice through TDD cycles, run validation, update docs, and produce release-ready output.
```

---

## Scenario 3: End-To-End Delivery

Use: `/claude-tech-squad:squad`

When:
- you want the full path from discovery to release preparation
- the task spans multiple specialties and approvals

```text
/claude-tech-squad:squad
Add SSO login with audit trail, admin approval flow, automated coverage, documentation, and release artifacts.
```

---

## Scenario 4: LLM Product — RAG Chatbot

Use: `/claude-tech-squad:squad`

When:
- building or improving a chatbot, AI agent, or RAG-powered feature
- specialists needed: agent-architect, rag-engineer, prompt-engineer, conversational-designer, llm-eval-specialist

```text
/claude-tech-squad:squad
Build a travel agent chatbot with RAG retrieval from the knowledge base. It should handle flight search, hotel recommendations, and iterative conversation memory. Include token optimization, hallucination evaluation, and chaos testing for LLM API failures.
```

```text
/claude-tech-squad:discovery
Design the RAG pipeline for the support chatbot. Define chunking strategy, embedding model, vector store, hybrid search approach, and retrieval quality metrics. Include an evaluation plan using RAGAS.
```

---

## Scenario 5: LLM Product — Multi-Agent System

Use: `/claude-tech-squad:discovery` then `/claude-tech-squad:implement`

When:
- designing orchestration between multiple AI agents
- MCP servers, tool use contracts, and agent loops need definition

```text
/claude-tech-squad:discovery
Design a multi-agent orchestration system where a coordinator agent delegates to specialist agents (flight search, hotel search, itinerary planner). Define MCP servers, tool schemas, handoff protocols, and loop safety guardrails.
```

---

## Scenario 6: Monitoring and Observability

Use: `/claude-tech-squad:squad`

When:
- adding production dashboards, SLO tracking, or LLM cost visibility
- specialists needed: observability-engineer, monitoring-specialist, analytics-engineer

```text
/claude-tech-squad:squad
Add real-time monitoring dashboards for token cost per user, RAG retrieval latency, and hallucination rate trends. Integrate with the existing Prometheus/Grafana stack and define alert thresholds.
```

---

## Scenario 7: Search Feature

Use: `/claude-tech-squad:squad`

When:
- adding or improving full-text or hybrid search
- specialists needed: search-engineer, rag-engineer (if hybrid), backend-architect

```text
/claude-tech-squad:squad
Implement knowledge base search using Elasticsearch with hybrid BM25 + vector retrieval. Include faceted filters, autocomplete, and relevance tuning. TDD required.
```

---

## Scenario 8: Mobile Feature

Use: `/claude-tech-squad:squad`

When:
- implementing features for iOS, Android, or React Native
- specialists needed: frontend-architect, mobile-dev

```text
/claude-tech-squad:squad
Add push notifications and deep link handling to the React Native app. Include offline support for the notification queue and app store release preparation.
```

---

## Scenario 9: Jira or Acceptance Audit

Use: `/claude-tech-squad:squad`

When:
- comparing a ticket to real implementation
- PM, QA, reviewer, and technical roles involved in the audit

```text
/claude-tech-squad:squad
Audit the linked Jira story against the current implementation, validate requirements and acceptance criteria, review structural design quality, run relevant checks, and show explicit agent execution lines with Agent Execution Log.
```

---

## Scenario 10: Refactor or Debt Reduction

Use: `/claude-tech-squad:discovery` then `/claude-tech-squad:implement`

When:
- the goal is technical improvement rather than new scope
- you still need design, risk analysis, and controlled implementation

```text
/claude-tech-squad:discovery
Plan a refactor of webhook retry handling to improve idempotency, observability, and rollback safety without changing user-facing behavior.
```

---

## Scenario 11: Release Readiness

Use: `/claude-tech-squad:implement` or `/claude-tech-squad:squad`

When:
- implementation is mostly done
- you need QA confidence, docs delta, Jira/Confluence updates, and rollout guidance

```text
/claude-tech-squad:implement
Run release-readiness validation for the approved scope, including QA, documentation delta, Jira/Confluence pack, and rollout preparation.
```

---

## Scenario 12: Production Incident Follow-Through

Use: `/claude-tech-squad:squad`

When:
- the issue crosses diagnosis, remediation, testing, operational safety, and release

```text
/claude-tech-squad:squad
Investigate the duplicate webhook incident, implement the fix, validate regressions, update operational docs, and prepare a safe rollout plan.
```

---

## Scenario 13: Technical Debt — Safe Refactor

Use: `/claude-tech-squad:refactor`

When:
- you want to improve code structure without changing behavior
- extracting classes, reducing coupling, removing duplication
- behavior must stay identical — if it needs to change, use `/squad`

```text
/claude-tech-squad:refactor
```

Escalate to `/squad` if root cause analysis reveals a design flaw requiring behavioral changes or the scope exceeds 15 files.

---

## Scenario 14: Release Preparation

Use: `/claude-tech-squad:release`

When:
- implementation is done and you need to cut a release
- you want release notes generated from commits and PRs
- you want a rollback plan, deploy checklist, and version tag

```text
/claude-tech-squad:release
```

---

## Scenario 15: Post-Incident Learning

Use: `/claude-tech-squad:incident-postmortem`

When:
- a production incident has been resolved
- you want a blameless root cause analysis and action items
- you need a post-mortem document to share with the team

```text
/claude-tech-squad:incident-postmortem
```

Complements `/cloud-debug` (active diagnosis) and `/hotfix` (emergency fix) to close the full incident lifecycle.

---

## Scenario 19: Production Emergency — Hotfix

Use: `/claude-tech-squad:hotfix`

When:
- production or staging is broken and a patch is needed now
- you know approximately where the issue is
- you need a branch, PR, and deploy checklist without discovery overhead

```text
/claude-tech-squad:hotfix
```

Escalate to `/squad` if the root cause reveals an architectural problem or the fix touches more than 5 files.

---

## Scenario 20: Pull Request Review

Use: `/claude-tech-squad:pr-review`

When:
- reviewing a non-trivial pull request before merge
- you want specialist coverage beyond a basic code review (security, privacy, performance, accessibility)
- you want findings posted as inline GitHub review threads automatically

```text
/claude-tech-squad:pr-review
https://github.com/org/repo/pull/42
```

---

## Scenario 21: Security Audit

Use: `/claude-tech-squad:security-audit`

When:
- periodic security review or pre-release check is needed
- runs bandit, pip-audit, npm audit, and secret scanning

```text
/claude-tech-squad:security-audit
```

---

## Scenario 22: Schema or Migration Planning

Use: `/claude-tech-squad:migration-plan` before any schema change

```text
/claude-tech-squad:migration-plan
```

---

## Scenario 23: Cloud or Production Debug

Use: `/claude-tech-squad:cloud-debug`

```text
/claude-tech-squad:cloud-debug
```

---

## What Good Execution Looks Like

You should expect:

- visible phase transitions
- role-specific handoff lines
- structural guidance before the implementation pass
- retries when review or QA fails
- batch lines when specialist benches run in parallel
- a final `Agent Execution Log`

If these markers are missing, see [EXECUTION-TRACE.md](EXECUTION-TRACE.md).
