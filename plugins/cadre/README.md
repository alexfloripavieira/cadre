# cadre (Claude Code plugin)

The plugin surface of Cadre — what Claude Code loads when you run
`/plugin install alexfloripavieira/cadre`.

For the full project, see the repository root `README.md`. For user
docs, see `/docs/` (install, manual, API reference). For the decision
records, see `/docs/architecture/`.

## Contents

```
.claude-plugin/plugin.json   plugin manifest (name, description, version)
agents/                      agent specifications (markdown + ADR 0004 spec cards)
skills/                      skill specifications
  inception/SKILL.md         /inception — PRD → TechSpec
  implement/SKILL.md         /implement — agentic feature delivery
  bug-fix/SKILL.md           /bug-fix — reproduce + fix + review
  review/SKILL.md            /review — structured diff / PR review
templates/                   PRD, TechSpec, Tasks, Task templates
runtime-policy.yaml          retry, fallback, budget, and doom-loop profiles
```

## Install from the Claude Code CLI

```
/plugin install alexfloripavieira/cadre
```

Then invoke any of the shipped skills:

```
/inception ai-docs/prd-<slug>/prd.md
/implement <one-sentence intent>
/bug-fix <bug report>
/review <diff path or PR URL>
```

Claude Code provides the LLM access via your subscription (Max, Teams,
or Pro). If you embed the Python runtime separately (for CI, dogfooding,
or non-Claude-Code callers), you provide your own credentials and the
runtime calls LiteLLM directly — see `/docs/PROVIDERS.md`.

## Runtime dependency

Every skill invocation goes through `cadre.Runtime.call()` under the
hood. The runtime is the Python package at `services/runtime/cadre/`.
The reliability primitives (retry budget, fallback, doom-loop
detection, cost ceiling, SEP audit log, checkpoints) are enforced at
that layer, not inside the plugin markdown.

For callers outside Claude Code, install the runtime:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../../services/runtime[dev]
```

## License

BSL 1.1 (converts to Apache 2.0 on 2030-04-21). See repository root
`LICENSE`.
