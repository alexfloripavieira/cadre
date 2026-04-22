# Keel — Commercial Plan

## Model: open-core + managed cloud

Keel ships as a single open-source codebase under **BSL 1.1**, converting to
**Apache 2.0** on 2030-04-21. On top of the open codebase, Keel offers a managed
cloud service with operational guarantees and premium connectors.

## Tiers

### Community (free, self-hosted)

- Full Keel runtime under BSL 1.1.
- All agent/skill specs, templates, and runtime policy.
- Multi-provider LLM support via LiteLLM (Anthropic, OpenAI, Google, Groq, local).
- Docker Compose local dev stack.
- Community support on GitHub Issues / Discussions.
- **BSL restriction:** cannot be used to offer a competing hosted/managed service.

### Cloud (paid, managed)

- Fully managed Keel runtime with SLA.
- Horizontal autoscaling, multi-region failover, managed queue and checkpoint store.
- Hosted dashboard with SEP log explorer, cost analytics, and golden-run diff viewer.
- Premium connectors: Jira, Linear, GitHub Enterprise, Slack, PagerDuty, Datadog.
- Priority support with response-time SLAs.
- Billing on execution cost + per-seat dashboard access.

### Enterprise (paid, on-prem or dedicated)

- On-prem deployment with support for air-gapped environments.
- Dedicated single-tenant cloud instance with VPC peering.
- Custom SSO (SAML, OIDC), RBAC, and audit log export.
- Custom SLAs, dedicated support engineer, architecture reviews.
- Annual contract, volume pricing.

## Licensing

- **Source license:** BSL 1.1 during the change period (2026-04-21 → 2030-04-21),
  then Apache 2.0.
- **Additional Use Grant:** you may use Keel in production and internally without
  restriction. You may **not** offer Keel (or a substantially similar service) as
  a hosted/managed commercial service to third parties during the BSL period.
- **Contributor License Agreement:** contributors retain copyright; contributions are
  licensed under the same terms as the project.

## Positioning

Keel is **not** an LLM, a code generator, or a replacement for engineers. Keel is
the reliability layer between an AI engineering agent and the systems it touches.
The commercial offering monetizes operational value (managed ops, SLAs, integrations),
not the core runtime — which stays open.

## Pricing (provisional)

Pricing is set after the first design-partner cohort. Initial signals:

- Cloud base tier: monthly platform fee + usage-based execution billing.
- Enterprise: custom annual contract, starting floor to be determined with design
  partners.
- No per-agent or per-skill gating in Community.
- No restriction on provider or model choice in Community.

## Go-to-market sequence

1. **Alpha (now → Q3 2026)** — public repo, design-partner program, no public cloud.
2. **Beta (Q4 2026)** — managed cloud private beta with design partners; golden-run
   SLA commitment; premium connectors v1.
3. **GA (H1 2027)** — public cloud self-serve, Enterprise offering, published SLAs
   and pricing.

## Design-partner program

Early customers work directly with the core team in exchange for:

- Discounted pricing locked for 24 months.
- Input on roadmap priorities.
- Named case study (optional).

Design partners must run Keel in a non-trivial AI engineering workflow (agentic
delivery pipeline, automated review, large-scale refactor automation, etc.) and
commit to a monthly review cadence.
