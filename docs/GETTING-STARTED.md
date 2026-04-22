# Getting Started with Cadre

This guide takes you from a fresh machine to your first Cadre run in about
15 minutes. Cadre ships as a Claude Code plugin plus a Python runtime; this
guide covers both surfaces.

## Prerequisites

- **Python 3.11+** on your machine.
- **git** for checking out the repo.
- One of these LLM credentials (free options work):
  - `GROQ_API_KEY` — signup at https://console.groq.com (recommended for smoke tests)
  - `OPENROUTER_API_KEY` — signup at https://openrouter.ai (broadest free-model access)
  - `ANTHROPIC_API_KEY` — signup at https://console.anthropic.com (paid per token, highest quality)
- Optional: **Claude Code CLI** installed, for using Cadre as a plugin inside Claude Code workflows.

See `docs/PROVIDERS.md` for the full provider list.

## Install from source

Use a virtual environment. Modern Debian/Ubuntu (PEP 668) refuse
system-wide pip installs; venv is the only clean path. Works on any OS.

```bash
git clone https://github.com/alexfloripavieira/cadre.git
cd cadre

python3 -m venv .venv
source .venv/bin/activate         # on Windows: .venv\Scripts\activate

pip install -e services/runtime[dev]
```

To deactivate: `deactivate`. To reactivate in a new shell:
`source /path/to/cadre/.venv/bin/activate`.

Verify the install:

```bash
cd services/runtime
pytest -q
# expected: 77 passed
```

## First run — smoke test (no Claude Code needed)

The fastest way to prove Cadre works end-to-end is the smoke script. It
runs the `inception` skill against a real provider and writes a SEP log.

```bash
# choose ONE provider and export the credential:
export GROQ_API_KEY=gsk_...
# or
export OPENROUTER_API_KEY=sk-or-...
# or
export ANTHROPIC_API_KEY=sk-ant-...

# Run. Default model is groq/llama-3.3-70b-versatile (free tier).
python scripts/smoke-run.py
```

If you are not using Groq, override the model:

```bash
export CADRE_SMOKE_MODEL="openrouter/deepseek/deepseek-chat-v3:free"
python scripts/smoke-run.py
```

Expected output (abbreviated):

```
cadre smoke run — model: groq/llama-3.3-70b-versatile
sep log: /path/to/cadre/ai-docs/.cadre-log

============================================================
status:          completed
skill:           inception
run_id:          smoke-001
steps executed:  1
total cost USD:  $0.0

  step 1 — inception-author — success
    model: groq/llama-3.3-70b-versatile  attempts: 1  fell_back: False  duration: 1.32s
    response preview: ## Technical Specification ...

SEP log file: /path/to/cadre/ai-docs/.cadre-log/smoke-001.log.yaml
```

Inspect the SEP log:

```bash
cat ai-docs/.cadre-log/smoke-001.log.yaml
```

You will see one YAML document per agent call with run_id, phase, model,
cost, and duration. This is the audit format Cadre writes for every run.

## Install as a Claude Code plugin

If you have Claude Code CLI installed, you can use Cadre's skills
(`/inception`, `/implement`, `/bug-fix`, `/review`) directly from inside a
Claude Code workspace.

```bash
# from inside Claude Code
/plugin install alexfloripavieira/cadre
```

After install, the skills appear as slash commands. Run:

```
/inception ai-docs/prd-example/prd.md
```

The orchestrator loads the skill, picks an agent (per ADR 0004), and
executes. Claude Code uses its own model access (your Claude Code
subscription); the separate Python runtime with an API key is needed only
when you embed Cadre in your own code.

## Common first-run gotchas

**`ModuleNotFoundError: No module named 'cadre'`** — you ran outside the
`services/runtime/` directory and did not install the package. Either `cd
services/runtime` first, or `pip install -e services/runtime` from the
repo root.

**`RuntimeError: default_provider requires 'litellm' to be installed`** —
the Python dependencies did not install. Re-run `pip install -e ".[dev]"`
in `services/runtime/` and check for errors.

**`401 Unauthorized` or similar** — your API key is not set or is wrong.
Check with `echo $GROQ_API_KEY` etc.

**`CostCeilingExceeded`** — the skill's policy hit its budget cap.
Intentional safety. See `docs/MANUAL.md` for how to adjust budgets.

## Next steps

- Read `docs/MANUAL.md` for the full reference: skills, agents, policies,
  customization.
- Read `docs/ARCHITECTURE.md` for the system-level view.
- Read `docs/API.md` if you want to embed Cadre in your own Python code.
- Read `docs/PROVIDERS.md` to choose providers for your use case.
- Read `docs/architecture/` for the ADR series.

## Where to ask for help

- GitHub Issues: https://github.com/alexfloripavieira/cadre/issues
- Discussions: use the same repo's Discussions tab.
