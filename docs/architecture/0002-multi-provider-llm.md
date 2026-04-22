# ADR 0002 — Multi-Provider LLM via LiteLLM

- Status: Accepted
- Date: 2026-04-21
- Deciders: Alexsander Vieira

## Context

Keel's value proposition is reliability for AI engineering agents. Reliability in
the LLM layer requires, at minimum:

- **Provider-agnostic calls.** A pipeline should not bind to a single vendor SDK.
- **Fallback across providers.** When Anthropic rate-limits, fall back to OpenAI or
  a local model without rewriting the agent.
- **Cost guardrails.** Observe token usage and pricing per call, enforce budget caps.
- **Unified streaming and tool-call semantics.** So retries and doom-loop detection
  work the same regardless of the backend.
- **Local/self-hosted support.** Customers running on-prem or behind strict data
  boundaries need to point Keel at vLLM, Ollama, or an internal OpenAI-compatible
  endpoint with zero code changes.

Building a provider abstraction layer from scratch is a significant engineering
effort that does not differentiate Keel — the differentiation is the reliability
layer on top, not the SDK adapters underneath.

## Decision

Use **LiteLLM** as the single provider-agnostic LLM client for the Keel runtime.

- All LLM calls inside `services/runtime/keel_runtime/providers/` go through LiteLLM's
  unified `completion()` / `acompletion()` interface.
- Provider selection is expressed as **model strings** (e.g. `anthropic/claude-opus-4-7`,
  `openai/gpt-4.1`, `groq/llama-3.3-70b`, `ollama/llama3`) and configured per agent/skill
  in `packages/policy/runtime-policy.yaml`.
- Credentials are loaded from environment variables; no provider-specific SDK is
  imported directly by Keel code.
- The fallback matrix (ADR TBD) is implemented on top of LiteLLM's `completion_with_fallbacks`,
  wrapped by Keel's retry-budget and doom-loop detection.
- Observability (token counts, cost, latency) is captured from LiteLLM's response
  metadata and emitted into the Keel SEP log.

## Consequences

Positive:

- Adding a new provider is a configuration change, not a code change.
- Local/self-hosted deployment works out of the box via OpenAI-compatible endpoints.
- Keel focuses engineering effort on the reliability layer, not SDK plumbing.
- One streaming/tool-call protocol to reason about in retries and checkpoints.
- Cost and token telemetry are uniform across providers.

Negative:

- LiteLLM becomes a critical dependency; a regression or breaking change upstream can
  impact all providers at once. Mitigated by pinning a known-good version and running
  Keel's golden-run suite on upgrades.
- Provider-specific features (e.g. Anthropic prompt caching, OpenAI structured outputs)
  are only available to the extent LiteLLM exposes them. Where a feature is critical
  and unsupported, Keel may bypass LiteLLM for that specific call path and document
  the exception.
- Debugging a provider-specific failure requires understanding both LiteLLM's
  translation layer and the underlying provider error — one more layer of indirection.

## Alternatives considered

- **Direct SDK integration per provider.** Rejected: triples the surface area to
  maintain and forces Keel to re-implement fallback/streaming uniformly across
  heterogeneous SDKs.
- **Build an in-house provider abstraction.** Rejected for MVP: no defensible reason
  to reinvent this layer, and LiteLLM already supports 100+ providers with active
  maintenance. Revisit only if LiteLLM becomes a blocker.
- **LangChain / LlamaIndex as the provider layer.** Rejected: both bring a large
  opinionated stack (chains, retrievers, agents) that conflicts with Keel's own
  orchestration model. Keel's orchestration is the product; we don't want to
  inherit someone else's.
- **OpenRouter as the only gateway.** Rejected: introduces a hard runtime
  dependency on a third-party service and makes on-prem/local deployment impossible.

## Follow-ups

- ADR on fallback matrix semantics and retry budget.
- ADR on cost guardrails and budget enforcement.
- Golden-run suite covering at minimum: Anthropic, OpenAI, Groq, local (Ollama or
  vLLM via OpenAI-compatible endpoint).
