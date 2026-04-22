# Keel — Plan v2 (Reliability Runtime Pivot)

- Date: 2026-04-21
- Supersedes: `blueprint.md` sections 1, 2, 4, 5, 8 (rest still valid)
- Trigger: Compozy competitive analysis (MIT, 527 stars, owns "pipeline Idea→PR" space)
- Decision: Keel pivots from "pipeline orchestrator" to **reliability runtime for agent pipelines**

---

## 1. New Positioning

### One-liner
Keel is the reliability runtime for agent pipelines. You bring the agent (Compozy, LangChain, OpenAI Agents SDK, your own loop); Keel keeps it alive in production.

### Anti-positioning (what Keel is NOT)
- Not a pipeline orchestrator. Compozy, AutoGen, CrewAI, LangGraph do that.
- Not an agent framework. Keel does not define agent prompts, tools, or chains.
- Not an LLM gateway. LiteLLM and OpenRouter do routing; Keel sits above them.
- Not a logger. LangSmith, Langfuse, Helicone do that; Keel *acts* on observed state (halts, falls back, re-routes), not just describes it.

### The lane
Between the orchestrator (the agent loop) and the provider layer (LiteLLM or raw SDK), there is a reliability tier nobody packages well:

```
  Agent loop / orchestrator   <-- Compozy, LangChain, custom
  ============================
        KEEL (reliability)    <-- this project
  ============================
  Provider layer              <-- LiteLLM, raw SDKs
```

Keel enforces: retry budget, fallback matrix, doom-loop detection, cost ceiling,
checkpoint/resume, SEP audit log. It exposes these as a **library/SDK** and a **daemon**
that wrap the LLM call boundary.

### Elevator pitch (30 seconds)
> If your AI agent runs in production, you've debugged three things at 3am: a runaway
> retry loop, a silent provider outage, and a bill you can't explain. Keel is the
> runtime library that stops all three. It wraps your agent's LLM calls with retry
> budgets, multi-provider fallback, doom-loop detection, and cost ceilings — and
> writes a structured audit log that makes post-incident forensics a 5-minute job
> instead of a 3-hour one. Three lines of Python to integrate. Works with any
> orchestrator. BSL 1.1, converting to Apache 2.0.

---

## 2. Product Surface v0.1

### The three integration modes

**Mode A — Python library (primary surface for alpha)**

```python
from keel import Runtime, Policy

runtime = Runtime.from_file("keel.yaml")

# Drop-in replacement for a raw LiteLLM / SDK call
response = runtime.call(
    run_id="agent-refactor-42",
    model="anthropic/claude-opus-4-7",
    messages=[...],
    fallback=["openai/gpt-4.1", "groq/llama-3.3-70b"],
)
```

What `runtime.call()` does that a raw LiteLLM call doesn't:
- Enforces per-run retry budget from policy.
- Applies fallback matrix if primary fails; records fallback reason.
- Tracks cumulative cost against run ceiling; halts if exceeded.
- Detects doom-loop patterns against prior attempts in the run; halts if triggered.
- Writes an SEP log entry per call.
- Writes a checkpoint after each successful call; resumable on crash.

**Mode B — Daemon + IPC (for multi-language / long-running runs)**

```bash
keel daemon start
keel run agent-refactor-42 --config keel.yaml --stream
# in another terminal
keel log agent-refactor-42 --tail
```

Daemon owns run state and SEP log; client processes (any language) call via HTTP/UDS.
This is the surface that wraps non-Python orchestrators (Compozy, Go bots, etc.).

**Mode C — CLI for canonical skills (secondary, for dogfooding and demos)**

```bash
keel skill run inception --input feature-brief.md
```

Ships with a small set of reference skills (inception, review-triage, etc.) as
demo content. This is NOT the primary value — it's the "look, it works" surface.
Real customers write their own skills or don't use skills at all and just use
Mode A/B.

### What ships in v0.1 (alpha)

- Python library (`keel` package).
- CLI + daemon in the same binary (`keel` entry point).
- Policy format (`keel.yaml`, evolution of current `runtime-policy.yaml`).
- LiteLLM provider layer.
- SEP log schema v1 with YAML frontmatter.
- Filesystem checkpoint store (SQLite optional).
- 3 canonical demo skills (inception, review-triage, runbook-step).
- Reference integrations: LangChain callback, OpenAI Agents SDK wrapper, raw function.

### What does NOT ship in v0.1
- Go gateway (deferred — only needed for managed cloud).
- Web dashboard (deferred — CLI + SEP viewer is enough).
- Managed cloud (Beta target).
- Premium connectors (Jira/Slack/etc. — Beta).
- Multi-tenant auth (single-operator assumption).
- Prompt management / versioning (out of scope permanently — that's an orchestrator concern).

---

## 3. Integration Plans (the Wedge)

Keel's go-to-market wedge is "3 lines to add to your existing agent". Each reference
integration must be real, tested, and documented.

### Integration 1 — Compozy (critical)

Write a Compozy extension (their JSON-RPC plugin SDK supports this) that routes
every ACP call through Keel's daemon:

```
compozy tasks run feat-42 --ext keel
```

The extension captures each agent invocation, wraps it through `keel.Runtime`,
and produces a parallel SEP log alongside Compozy's own `events.jsonl`.

**Deliverable:** `extensions/compozy-keel/` published as a Go or TS Compozy extension.

This integration turns Compozy users into Keel users without asking them to rip
anything out. Crucial positioning: "use Compozy for the pipeline, Keel for the
reliability layer."

### Integration 2 — LangChain / LangGraph

LangChain callbacks are the standard hook. Ship `keel.langchain.KeelCallback`
that hooks every LLM call:

```python
from langchain_anthropic import ChatAnthropic
from keel.langchain import KeelCallback

llm = ChatAnthropic(model="claude-opus-4-7", callbacks=[KeelCallback(run_id=...)])
```

Zero change to existing LangChain code other than adding the callback.

### Integration 3 — OpenAI Agents SDK

Similar wrapper pattern over the SDK's tool-call boundary.

### Integration 4 — Raw (no orchestrator)

The Mode A library itself is the raw integration. Users with a home-grown agent
loop add `runtime.call()` at the LLM boundary.

---

## 4. Refined ICP

### Primary ICP (was "secondary" in v1 blueprint)
**AI-native SaaS companies whose product is an agent.** 10–100 engineers, Series A/B. Their product-level SLA is tied to the agent's uptime. They already hit provider outages, runaway costs, or silent failures at least once. They cannot use local-only tools like Compozy because they run multi-tenant in the cloud, with auditable behavior for customers.

Why they buy Keel:
- Multi-provider fallback = product-level resilience during provider outages.
- Cost ceiling per tenant = billing predictability and anti-abuse.
- SEP log = artifact they expose to their own customers for audit.
- BSL 1.1 + future managed cloud = vendor they can write into their RFP responses.

### Secondary ICP
**Platform teams running internal agentic pipelines at large companies.** 50–500 total eng, embedded platform team of 3–10. Running an agent for code review, runbook automation, support triage, data remediation. The pipeline is mission-critical enough that a 3am break costs real money.

Why they buy Keel:
- Reliability layer they do not have to build.
- Structured audit log for SOX / compliance reasons.
- Cost attribution by team / initiative (via SEP log frontmatter).

### Anti-ICP
- Individual developers doing occasional scripting. Compozy is better for them; Keel is over-specified.
- Teams with no production agent yet. Keel is for when you already hurt.
- Academic / research usage. Use LangChain.

---

## 5. Architecture Deltas from Current Repo

Current layout (`services/runtime/keel_runtime/`) already anticipated this pivot:
`agents/`, `skills/`, `providers/`, `policy/`, `observability/` submodules. Deltas:

### Keep
- Polyglot monorepo (ADR 0001 still applies, gateway stays in scope for managed cloud).
- Multi-provider via LiteLLM (ADR 0002 unchanged).
- SEP log schema from claude-tech-squad heritage.
- `packages/policy/runtime-policy.yaml` as the policy contract.

### Change

**Rename at the package level:**
- `packages/agents/` → keep as-is for now, but rebrand in docs as "reference agents" (demo content, not product core).
- `packages/skills/` → keep, rebranded as "reference skills" (demo content).
- **New:** `packages/policies/` as the canonical policy directory. Users write their own policies here. `runtime-policy.yaml` moves into `packages/policies/default.yaml`.

**Public API surface (new):**
- `keel.Runtime` — main class.
- `keel.Policy` — policy loader / validator.
- `keel.SEPLogger` — audit log writer.
- `keel.callbacks.langchain.KeelCallback` — LangChain hook.
- `keel.agents.openai.wrap` — OpenAI Agents SDK wrapper.
- `keel.daemon` — daemon entry point (Mode B).

**Module renames inside `keel_runtime/`:**
- `agents/` → stays, but now internal — loader for reference agents, not a public API.
- `skills/` → stays, same treatment.
- `orchestrator/` → **drop** (was going to be here; now out of scope).
- New: `runtime/call.py` — the `Runtime.call()` entry point.
- New: `callbacks/` — LangChain, OpenAI Agents SDK integrations.

### CLI reshape

| v1 command | v2 command | Notes |
|---|---|---|
| `keel run <skill>` | `keel skill run <name>` | Skills are demo, not core |
| — | `keel daemon [start|stop|status]` | New |
| — | `keel run <run-id> --config keel.yaml` | New, Mode B |
| `keel resume <run-id>` | same | Unchanged |
| `keel log <run-id>` | same | Unchanged |
| `keel policy validate` | same | Unchanged |

---

## 6. License Decision

Compozy: MIT. Clean, no friction, pulls contributors and stars.

Keel: BSL 1.1 → Apache 2.0 in 2030. Slower community growth; defensible if managed cloud is real.

**Decision to confirm:** Keep BSL 1.1, because the pivot is compatible — the library is free to use anywhere, the managed cloud (SEP log viewer, multi-tenant policy store, audit export) is the commercial differentiation, and BSL prevents someone from shrink-wrapping Keel as a competing hosted SEP-viewer service during the 4-year window.

**Alternative worth weighing:** MIT for the library (`keel-runtime`), proprietary for the managed cloud components only. Faster community growth, but leaves the door open to a cloud competitor cloning the library. Pattern used by Temporal (MIT core + Cloud).

**Recommendation:** start BSL 1.1 as planned. If community traction stalls at day 90 due to BSL friction specifically (measured by: contributors citing license in issues/declines), revisit and consider relicensing to MIT before v1.0 GA. The BSL → MIT direction is a one-way door that the community rewards; MIT → BSL is not possible.

---

## 7. Terminology Hygiene (vs Compozy)

| Keel term | Risk of confusion | Action |
|---|---|---|
| `agent` | High — Compozy uses identical term | Keep in markdown/docs but always as "reference agent"; core API never takes "agent" as an input |
| `skill` | High — Compozy uses identical term | Same — "reference skills" in docs; core API is policy + provider calls |
| `pipeline` | Medium — Compozy owns the word | Avoid in Keel docs; use "run" or "workflow" |
| `policy` | Low — unique to Keel | Promote; make it the cover noun |
| `SEP log` | None | Unique to Keel; keep as branded artifact |
| `run` | Low — generic | Keep |
| `runtime policy` | None | Keep as flagship |

**Cover nouns in marketing copy, in priority order:** run, policy, reliability, fallback, audit log, budget.

---

## 8. MVP Release Gates (v0.1 alpha)

1. `keel.Runtime().call()` works for one provider with retry budget enforced. Reproducible test.
2. Fallback matrix survives forced primary failure; logs fallback reason in SEP.
3. Doom-loop detection halts a synthetic runaway run (3 pattern tests green).
4. Cost ceiling halts a runaway run within 10% of declared budget.
5. Resume-from-checkpoint after SIGKILL reconstructs run state.
6. LangChain callback integration works end-to-end in an example agent.
7. Compozy extension works end-to-end on one reference pipeline.
8. SEP log parses with an external YAML tool and documents every `runtime.call()`.
9. `docker-compose up` starts daemon + Postgres + Redis in under 5 minutes.
10. CI green on Python 3.11 and 3.12.
11. README rewritten around the v2 positioning (Section 1 of this doc).
12. LICENSE (BSL 1.1), ADRs, commercial.md all current.

---

## 9. 90-Day Plan (revised)

### Days 1–14 — Pivot foundations
- [ ] Rewrite README around v2 positioning (30 min task, high leverage).
- [ ] Draft `keel.Runtime.call()` API signature; ADR 0003 on the public API contract.
- [ ] Implement `Runtime.call()` with retry budget only (no fallback, no doom loop, no cost guard yet). Green test.
- [ ] Write SEP log writer; one entry per call.
- [ ] Publicize: soft announce in personal network, still no HN.
- [ ] Keep LICENSE on the to-do but do not block product progress.

### Days 15–45 — Reliability primitives
- [ ] Fallback matrix implemented and tested with provider-fault injection.
- [ ] Doom-loop detection (3 patterns from existing policy).
- [ ] Cost ceiling + warning threshold.
- [ ] Checkpoint/resume across library API and CLI.
- [ ] LangChain callback integration — publishable example repo.
- [ ] Start Compozy extension (scope: wraps one ACP call class first).

### Days 46–75 — Integrations and first users
- [ ] Finish Compozy extension; write joint blog post with Compozy team if possible (cross-promo wedge).
- [ ] OpenAI Agents SDK wrapper.
- [ ] Recruit 3 design partners from AI-native SaaS ICP. Direct outreach, not inbound.
- [ ] First customer case study: migrate one pipeline onto Keel, publish before/after.
- [ ] v0.1 release-candidate tag.

### Days 76–90 — Alpha launch
- [ ] v0.1 tagged against gates in Section 8.
- [ ] Public launch: HN, X, r/LocalLLaMA, AI-infra Slacks.
- [ ] Managed cloud prototype exploration (private alpha only).
- [ ] Decide Beta go/no-go: ≥3 active design partners, ≥1 case study, evidence of integration adoption (LangChain callback installs or Compozy extension usage).

### Kill criteria at day 90
- No integration adoption despite working examples → product-market timing wrong, consider pausing.
- Compozy or LangChain ships a competing reliability module natively → pivot to a narrower sub-feature (e.g. just the SEP log / cost ceiling) or fold the project.
- No design partners sign up after 10+ qualified conversations → ICP wrong, reassess.

---

## 10. Risks Specific to This Pivot

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LangChain / Compozy ships native retry budget + fallback before Keel lands | Medium | High | Ship fast (90 days); differentiate on SEP log + cost ceiling + doom-loop, not just retry |
| "Library under the orchestrator" is a smaller market than "the orchestrator itself" | High | Medium | Accepted tradeoff; smaller market but less crowded. Move up-stack only if traction allows |
| BSL 1.1 blocks contributors who would accept MIT | Medium | Medium | Monitor; relicense to MIT before v1.0 if explicit signal |
| Python-only library limits adoption in Go / TS shops | Medium | High | Daemon + IPC (Mode B) unblocks non-Python; ship early |
| Integration examples rot as upstream frameworks change | High | Low | CI runs integration tests against pinned upstream versions; document version compatibility |
| Compozy team sees Keel as competition, blocks extension ecosystem | Low | Medium | Engage them publicly and positively; position as complementary |
| Dogfooding cost blows the self-funded budget | Medium | Medium | Local-model fallback in dogfooding; use Keel's own cost ceiling on the CI runs |

---

## 11. Immediate Next Actions (concrete)

In order, smallest unit of progress first:

1. **README rewrite** (30 min) — new first 100 lines reflecting v2 positioning. High signal, zero code risk.
2. **ADR 0003 — Public API Surface** — write before coding it, commit so the contract is reviewable.
3. **`keel.Runtime` skeleton + `call()` with retry budget only** — minimum viable core. One test.
4. **SEP log writer** — write one entry per call, in YAML frontmatter format.
5. **LangChain callback example repo** (external) — smallest integration, highest visibility.
6. Then HANDOFF cleanup + LICENSE.

---

## Appendix — What Changes in the Repo Immediately

- `README.md` — rewrite first 100 lines.
- `docs/architecture/` — add ADR 0003 (public API contract).
- `services/runtime/keel_runtime/` — add `runtime/` submodule with `call.py`.
- `services/runtime/keel_runtime/callbacks/` — new folder for LangChain etc.
- `packages/policies/default.yaml` — copy of current `runtime-policy.yaml` at the new canonical path; old path kept as symlink during transition.
- `ai-docs/keel-discovery/blueprint.md` — add a note at top referencing this v2 plan.
- `HANDOFF.md` — reflect v2 direction; remove LICENSE as blocker for product progress.

No breaking changes to the existing scaffold. All deltas are additive or renames.
