# Keel — Discovery Blueprint

- Date: 2026-04-21
- Owner: Alexsander Vieira
- Status: Alpha / pre-1.0
- Repo: https://github.com/alexfloripavieira/keel

---

## 1. Product Definition

### One-liner
Reliability backbone for AI engineering agents — multi-provider, contract-driven pipelines with retry budgets, fallbacks, checkpoints, doom-loop detection, cost guardrails, and observability.

### What Keel is
A runtime harness that sits between an AI engineering agent (the "brain") and the
systems it touches (code repos, CI, cloud, ticketing, data stores). Keel does not
generate code or make product decisions. Keel makes sure that when the agent does,
the outcome is safe, observable, affordable, and reproducible.

### What Keel is not
- Not an LLM and not a model wrapper.
- Not a code generator or IDE extension.
- Not a replacement for engineers.
- Not an agent framework competing with LangChain/LlamaIndex/AutoGen — Keel wraps those if needed, but its primary integration surface is contract-driven specs (agents + skills + policy).

### Core value proposition
Teams running agentic pipelines in production need five things that most agent frameworks leave to the operator:

1. **Provider independence** — swap Anthropic/OpenAI/Google/Groq/local without code changes.
2. **Retry discipline** — bounded retries, doom-loop detection, cost ceilings per run.
3. **Checkpoint/resume** — partial runs survive timeouts, network failures, rate limits.
4. **Observability** — SEP log schema gives structured, queryable audit of every step.
5. **Contract-first specs** — agents and skills live as versioned markdown/YAML, reviewable in PRs, not buried in code.

Keel is the "reliability layer" between experimentation and production for agentic workflows.

---

## 2. Target Users and ICPs

### Primary ICP — Platform/AI teams operating agentic workflows
**Profile:** 3–20 engineer platform or AI-infra team inside a larger eng org (50–500 engineers total). Already running at least one agentic pipeline (automated refactoring, PR review, runbook automation, support triage, data remediation). Burned by silent failures, runaway token spend, or provider outages at least once.

**Pains:**
- Production incidents caused by unbounded retries or doom loops.
- Token bills that jumped 5–10x without explanation.
- Provider rate limits or outages taking down the whole pipeline.
- Post-incident forensics blocked by unstructured logs.
- Moving from Anthropic to OpenAI (or adding a local model for compliance) requires a rewrite.

**Gains from Keel:**
- Drop-in runtime with retry budgets and provider fallbacks.
- SEP log gives one artifact to hand the CFO ("here is what we spent and why") and one for the postmortem ("here is where it broke").
- Contract files (`packages/agents`, `packages/policy`) make agent behavior reviewable and versioned.

### Secondary ICP — AI-native SaaS building agent products
**Profile:** Seed-to-Series-B company whose product is an agent (Devin-style, autonomous SRE, autonomous analyst, etc.). Engineering of 10–50. Reliability is the product.

**Pains:**
- Customer-visible failures when a single provider is down.
- Hard to add new providers because the agent loop is coupled to one SDK.
- No way to enforce per-customer cost budgets.
- Observability is roll-your-own; every customer incident requires reverse-engineering logs.

**Gains from Keel:**
- Multi-provider fallback built in, per-customer cost caps, structured audit trail they can expose to their customers.

### Anti-ICP (not a fit for MVP)
- Solo developers doing occasional scripting with LLMs. The reliability surface is over-specified for their scale.
- Companies with no production agent workload yet. Keel is for when you already hurt, not speculative adoption.
- Enterprises needing FedRAMP / SOC 2 / HIPAA out of the box. That is Enterprise-tier later, not MVP.

---

## 3. Problem Statement

> Agentic pipelines in production fail silently, cost unpredictably, and lock teams into one LLM provider. Existing agent frameworks optimize for experimentation, not for operating a pipeline on call at 3am.

Concretely, the operator today must:
- Hand-roll retry logic per provider.
- Detect doom loops by reading logs or watching token counts climb.
- Write custom cost guardrails outside the framework.
- Maintain a homemade observability layer that correlates agent steps with tool calls and provider responses.
- Choose one provider and accept outage risk, or write an abstraction layer themselves.

Each of those problems has been solved individually in ops-mature systems (HTTP client retries, circuit breakers, distributed tracing, feature flags). Agent runtimes treat them as exercises for the reader. Keel packages those solved problems into an agent-aware runtime.

---

## 4. Positioning and Competitive Landscape

### Adjacent categories

| Category | Example players | Keel relationship |
|---|---|---|
| Agent frameworks | LangChain, LlamaIndex, AutoGen, CrewAI | Keel wraps or replaces the orchestration loop. Focus differs: they ship tools; Keel ships reliability. |
| LLM gateways | LiteLLM, OpenRouter, Portkey | Keel *uses* LiteLLM as the provider abstraction. Keel's layer above is the differentiator. |
| Observability-for-LLMs | LangSmith, Langfuse, Helicone | Keel includes observability but also *acts* on it (auto-fallback, budget enforcement, doom-loop halt). Observability-only tools describe; Keel also controls. |
| Agent platforms | Devin, Cognition, Factory | Those are agent *products*. Keel is the runtime you would use to build one of those — or to make a reliability-focused competitor. |

### Sharpest statement of differentiation
LangChain is a toolkit. LiteLLM is a router. LangSmith is a logger. Keel is the
control-plane that ties retry, fallback, checkpoint, cost, and observability into
one contract-driven runtime. The contracts (`packages/agents`, `packages/skills`,
`packages/policy`) are the product surface — the runtime is the enforcer.

### Why now
- Agentic pipelines moved from demo to production in 2025.
- Multi-provider is table stakes after the Anthropic/OpenAI outages of 2025–26.
- Token costs hit CFO radar; eng teams under pressure to attribute spend.
- BSL-1.1 open-core is a proven model (MongoDB, Elastic, CockroachDB, MariaDB).

---

## 5. MVP Scope (in and out)

### In scope for v0.1 (alpha)

**Runtime (Python, `services/runtime`):**
- Agent loader that reads `packages/agents/*.md` specs and invokes them.
- Skill orchestrator that reads `packages/skills/*/SKILL.md` and sequences agent calls.
- Provider layer via LiteLLM with model-string selection.
- Retry budget enforced per run (configurable in `runtime-policy.yaml`).
- Fallback matrix enforced per run using `completion_with_fallbacks`.
- Doom-loop detection (3 patterns from existing policy: growing_diff, oscillating_fix, same_error).
- Cost guardrails: hard ceiling per run, warning threshold at 80%.
- Checkpoint/resume using filesystem state (no DB dep for alpha).
- SEP log written per run with YAML frontmatter (compatible with existing claude-tech-squad schema).

**CLI:**
- `keel run <skill> <args>` — execute a skill end-to-end.
- `keel resume <run-id>` — resume from last checkpoint.
- `keel log <run-id>` — pretty-print a SEP log.
- `keel policy validate` — validate `runtime-policy.yaml`.

**Contracts / specs:**
- Preserved from claude-tech-squad copy (prd-author, inception-author, tasks-planner, work-item-mapper).
- `runtime-policy.yaml` already adapted to `keel:` namespace.

**Deployment:**
- Local: `docker-compose up` with Postgres + Redis + runtime.
- Self-hosted: single-container runtime with external Postgres and Redis.

### Out of scope for v0.1 (explicitly deferred)

- Go gateway (`services/gateway`). Webhook/queue worker can be added in v0.3 once a customer needs it.
- TypeScript web dashboard (`services/web`). Replace with CLI + SEP log viewer for alpha.
- Managed cloud control plane. Billing, tenant isolation, autoscaling come in Beta.
- Premium connectors (Jira/Linear/Slack/Datadog). Integration via generic webhook only in alpha.
- Fine-grained RBAC / SSO. Single-operator deployment assumption for alpha.
- Custom model fine-tuning or training. Never — not the product.
- Agent development IDE. Use any editor; specs are markdown.

### Release gates (what must be true to tag v0.1)
1. One end-to-end skill runs reliably across two providers (Anthropic + OpenAI) with intentional failure injection.
2. Doom-loop detection triggers in a reproducible test case.
3. Cost ceiling halts a runaway test agent.
4. SEP log parses cleanly with a third-party YAML parser and documents every agent call.
5. Resume-after-SIGKILL restores a run to the last checkpoint.
6. `docker-compose up` works on a fresh machine in under 5 minutes.
7. README, CLAUDE.md, LICENSE, ADRs 0001 + 0002, commercial.md all in place.
8. CI green across Python 3.11 and 3.12.

---

## 6. Architecture at a Glance

```
                +------------------------+
   CLI ------>  | Skill Orchestrator     |  <-- packages/skills/*
                +-----------+------------+
                            |
                            v
                +------------------------+
                | Agent Loader / Invoker |  <-- packages/agents/*
                +-----------+------------+
                            |
                            v
                +------------------------+
                | Provider Layer         |  <-- LiteLLM
                | (retry, fallback,      |
                |  cost guard, doom loop)|  <-- packages/policy/runtime-policy.yaml
                +-----------+------------+
                            |
                            v
                 [ Anthropic | OpenAI | Google | Groq | local ]

  ^
  |  SEP log / Checkpoint store (Postgres + filesystem in v0.1)
  +-----------------------------------------------------------
```

Structural decisions:
- Polyglot monorepo (ADR 0001).
- Multi-provider via LiteLLM (ADR 0002).
- Contract-first: agents, skills, and policy are reviewable text, not code.
- Idempotent runs: every step writes a checkpoint; resume is deterministic.

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LiteLLM breaking change blocks a provider upgrade | Medium | High | Pin version; golden-run suite per release; fork if forced. |
| BSL 1.1 scares away contributors expecting MIT/Apache | Medium | Medium | Clear commercial.md; promised Apache-2.0 sunset in 2030; honor contributor CLA simplicity. |
| "Reliability layer" is too abstract to sell without a demo | High | High | Ship a golden-run video on day 1 of public repo; publish postmortem case studies from design partners. |
| Agent-framework incumbents (LangChain etc.) ship a reliability module first | Medium | High | Speed: public alpha in weeks, not quarters. Differentiate on contract-first approach and the SEP log schema — not features they can copy in a sprint. |
| No design partners sign up | Medium | High | Direct outreach to 20 named AI-platform teams before public alpha announce. Offer 24-month lock-in price. |
| Token cost of running Keel's own CI/dogfooding becomes unsustainable | Medium | Medium | Budget ceiling in CI; local-model fallback for dogfooding; cache golden-run fixtures. |
| Open-source users route around BSL's "no competing service" clause | Low | High | BSL language is well-tested (MongoDB precedent); lawyer review before GA, not alpha. |
| Solo-maintainer bus factor | High | High | Public, idiomatic codebase from day 1; write for the reader, not for "me next week"; recruit co-maintainer before Beta. |

---

## 8. 90-Day Plan

### Days 1–14 — Foundations (self)
- [ ] Finalize pending bootstrap items from HANDOFF: LICENSE (BSL 1.1) — all other bootstrap items done.
- [ ] First working slice: one skill end-to-end that invokes one agent with Anthropic only. No fallback yet, no doom loop, no cost guard. Just wire contracts → runtime → provider → SEP log.
- [ ] Golden-run fixture: record the canonical happy-path run as a reproducible test case.
- [ ] Publish public repo. Announce softly (personal network only, no HN/Twitter yet).

### Days 15–45 — Reliability layer (self + 1–2 early users)
- [ ] Retry budget + fallback matrix implemented and enforced by tests.
- [ ] Doom-loop detection implemented with 3 patterns.
- [ ] Cost ceiling implementation with warning threshold.
- [ ] Resume-from-checkpoint across the full skill surface.
- [ ] Multi-provider golden run (Anthropic + OpenAI + local via Ollama).
- [ ] Identify and land 3 design-partner conversations (even unpaid, observation-only).
- [ ] First case study: one real pipeline migrated onto Keel with before/after metrics.

### Days 46–90 — First public beta signal
- [ ] Tag v0.1 against the release gates from Section 5.
- [ ] Announce publicly (HN, X/Twitter, r/LocalLLaMA, AI-infra Slacks).
- [ ] Start docs site (MkDocs or Docusaurus) separate from repo docs.
- [ ] First managed-cloud prototype (private alpha): one-click deploy via Docker + a hosted SEP log viewer.
- [ ] Decide Beta go/no-go based on: design partner usage (≥3 actively running), unique GitHub stars (target 300+ within 4 weeks of public launch — not a vanity target, a signal of market surface).

### What success looks like at day 90
- ≥3 design partners running Keel weekly.
- ≥1 public case study with measurable reliability or cost improvement.
- Issues/PRs from external contributors (non-zero signal that code is approachable).
- Decision taken on managed-cloud Beta launch window (Q4 2026).

### What failure looks like at day 90
- No design partners ship on Keel despite trying.
- Every user complaint is about setup friction or docs, not about the product value itself.
- Token cost of running Keel's own CI > budget.
- Competing reliability layer from an incumbent (LangChain, LiteLLM itself) closes the window.

If day-90 signals land in failure territory, reassess: is the product wrong, the go-to-market wrong, or the timing wrong? Only one of those three is fatal.

---

## 9. Success Metrics

### Alpha (v0.1 → day 90)
- Golden-run reliability: ≥99% success across 100 consecutive runs of the canonical skill.
- Fallback activation: survives forced-failure of the primary provider in <5s with no user-visible error.
- Cost guardrail: terminates a runaway run within 10% of the declared ceiling.
- Install-to-first-run time: ≤10 minutes on a fresh machine for a developer following docs.

### Product-market signals
- GitHub stars: leading indicator, not goal. Threshold 300 in first 4 weeks of public launch = attention signal, not adoption.
- Design partners actively running weekly: this is the real adoption metric.
- Unsolicited external contribution (issue or PR from a non-design-partner): signals approachability.
- Conversation quality: are inbound questions about product fit, or about basic setup? Setup-heavy = docs problem; fit-heavy = product signal (good or bad).

### Commercial (Beta → GA)
- Design partners → paid conversion rate: ≥30% within 6 months of Beta availability.
- Managed cloud MAU: 10 paying tenants within 6 months of Beta.
- Gross revenue retention among design partners: ≥95%.

---

## 10. Immediate Next Actions

1. **LICENSE** — write BSL 1.1 with Change Date 2030-04-21, Change License Apache-2.0, Additional Use Grant restricting competing hosted services.
2. **First skill end-to-end** — pick the smallest useful skill (likely a single-agent ARC-conformant run), wire it to LiteLLM + SEP log + checkpoint, green test.
3. **Landing page / README polish** — the repo README is the first sales asset. Currently alpha-grade; needs the positioning from Section 4 distilled into the first 100 lines of the README.
4. **Design-partner outreach list** — 20 named teams, warm intros preferred. Week 1 deliverable.
5. **Public announce timing** — do not announce until the golden run is recorded on video and a working `docker-compose up` demo is in the README. Self-imposed gate.

---

## Appendix — Open Questions to Resolve Before Beta

- Naming of the binary (`keel`, `keelctl`, `keel-cli`).
- Whether to adopt Pydantic-AI or keep a hand-rolled agent loop (revisit after first slice).
- SEP log storage: filesystem (v0.1), SQLite (v0.2), Postgres (Beta) — confirmed path, but SQLite-as-default deserves a call.
- Whether to ship a minimal web dashboard for alpha or wait until Beta (currently: wait).
- CLA vs DCO for external contributors — CLA gives flexibility for license change at 2030 but adds friction. Lean DCO unless a lawyer pushes back.
- Telemetry: ship opt-in anonymous usage telemetry in alpha, or defer to Beta? Recommendation: ship opt-in from v0.1, disabled by default, documented in README.
