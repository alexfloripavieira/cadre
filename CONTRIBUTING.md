# Contributing to Cadre

Thanks for considering a contribution. Cadre is pre-1.0 and solo-maintained;
contributions speed it up a lot. Read this before opening a PR.

## Code of conduct

Be technical, be civil, be concise. No off-topic drama. English preferred
for written artifacts (code, docs, commits, PRs); other languages are
fine in issue comments if that is clearer for the reporter.

## How to contribute

1. **Open an issue first** for anything non-trivial — a bug report, a
   design change, a new agent, a new skill. This lets us align before
   you write code.
2. **Small bug fixes** (typo, doc fix, one-line bug) can land as a PR
   directly without a prior issue.
3. **Large refactors or new modules** must be preceded by a short ADR
   under `docs/architecture/`. Open the ADR as a PR first; discuss;
   merge; then the implementation PR.

## Development setup

```bash
git clone https://github.com/alexfloripavieira/cadre.git
cd cadre
python3 -m venv .venv
source .venv/bin/activate
pip install -e services/runtime
pip install ruff pytest
```

Validate:

```bash
cd services/runtime
ruff check .
ruff format --check .
pytest -q
```

All three must pass before opening a PR.

## Pull request checklist

- [ ] Tests added for any new runtime behavior.
- [ ] `ruff check .` clean under `services/runtime/`.
- [ ] `ruff format --check .` clean.
- [ ] `pytest -q` green.
- [ ] New agent? All ADR 0004 spec-card fields present.
- [ ] New skill? Every role in `candidate_agents` and `required_agents`
  exists in `plugins/cadre/agents/`.
- [ ] Architectural change? ADR merged before this PR.
- [ ] No secrets, API keys, or credentials in committed files.
- [ ] Commit messages follow the rules below.

## Commit message rules

See also `CLAUDE.md` section 3 (binding for automated contributors).

- **Format**: `<type>: <imperative summary under 72 chars>`
- **Types**: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`,
  `ci`, `chore`, `revert`.
- **Body**: explain WHY, not WHAT. Wrap at 100 columns.
- **No AI self-reference anywhere.** No `Claude`, `Anthropic`, `AI`,
  `Copilot`, `Co-Authored-By` trailers referencing assistants,
  "Generated with" taglines. This rule is absolute and applies to every
  commit, PR title, and body.
- **No emojis or decorative icons** in commits, PRs, code comments, or
  documentation.

Correct:

```
feat: add fallback matrix to Runtime.call
fix: prevent retry budget underflow on transport errors
docs: clarify policy-profile resolution in the manual
```

Wrong:

```
feat: add fallback matrix

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Code style

- **Python 3.11+** with type hints.
- **Ruff** for lint and format (config in `services/runtime/pyproject.toml`).
- **No docstrings on trivial methods/functions/classes.** Code should
  be self-documenting through clear names.
- **No inline comments** that describe WHAT. Only comment WHY when the
  reason is non-obvious (hidden constraint, workaround, subtle invariant).
- **YAML/Markdown**: 2-space indent, LF line endings, UTF-8.
- **Shell scripts**: POSIX bash, `set -euo pipefail`, shellcheck clean,
  pin locale where numeric output matters.

## Adding an agent

See `docs/AGENT-CONTRACT.md`. Briefly:

1. Copy an existing agent in `plugins/cadre/agents/` as a template.
2. Update every field in the frontmatter.
3. Rewrite the body for the new role's responsibility.
4. Add a test that loads the agent via `AgentRegistry`.

## Adding a skill

See `docs/SKILL-CONTRACT.md`. Briefly:

1. Create `plugins/cadre/skills/<name>/SKILL.md` with Level 2
   frontmatter.
2. Every role in `candidate_agents` + `required_agents` must exist.
3. Pick a policy profile from `plugins/cadre/runtime-policy.yaml`.
4. Add a parametric entry to `tests/test_skill_runner.py` in the
   shipped-skills parametric test.
5. Add an entry to the skill table in `docs/MANUAL.md`.

## Adding a policy profile

Edit `plugins/cadre/runtime-policy.yaml` under `policies:`. Validate:

```bash
python3 -c "import yaml; yaml.safe_load(open('plugins/cadre/runtime-policy.yaml'))"
```

Add a test to `tests/test_policy_loader.py` if the profile is shipped
in this PR.

## Documentation

- Every user-facing change needs a doc update. For runtime API
  changes: `docs/API.md` and `docs/MANUAL.md`.
- ADRs live in `docs/architecture/NNNN-*.md`, numbered sequentially.
- `CHANGELOG.md` gets an entry under the Unreleased section.

## Releasing

Handled by maintainer. Contributors don't need to tag or publish.

## License

By contributing, you agree your contributions are licensed under the
same BSL 1.1 (converting to Apache 2.0 on 2030-04-21) as the project.
No CLA in v0.1; a lightweight DCO may be added before v1.0.

## Security

Do not file security issues in public Issues. Email the maintainer
directly (address in repo profile). See `SECURITY.md` when it ships.
