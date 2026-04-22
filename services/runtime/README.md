# cadre (runtime)

Python runtime powering Cadre — the agentic delivery plugin for Claude Code. Provides retry budget, multi-provider fallback, doom-loop detection, cost guardrails, checkpoint/resume, and SEP log writing that the Cadre skills and agents use under the hood.

## Install (editable)

```bash
cd services/runtime
pip install -e ".[dev]"
```

## Test

```bash
pytest
```

## Lint and format

```bash
ruff check .
ruff format .
```
