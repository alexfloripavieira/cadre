# CLAUDE.md — Working in the Cadre Repository

> **Repository status:** archived at v0.1.0-alpha (2026-04-22).
> No active development. See `README.md` for context.
> Rules below still apply to any contributor that opens a PR.

These are the rules any AI coding assistant (including Claude Code) MUST follow when
making changes in this repository. Human contributors are encouraged to follow them
too, but for automated assistants they are non-negotiable.

---

## 1. No AI self-reference, anywhere

FORBIDDEN in commits, PR titles, PR descriptions, code comments, documentation,
changelogs, release notes, and issue replies:

- The words: `Claude`, `Anthropic`, `AI`, `GPT`, `LLM`, `Copilot`, `ChatGPT`, `assistant`
  (when referring to an AI), or any equivalent.
- `Co-Authored-By:` trailers referencing an AI or AI service.
- "Generated with", "Written by AI", "AI-assisted" taglines.
- Badges, footnotes, or links advertising AI involvement.

This is absolute. If a template or third-party asset contains these, strip them before
committing.

## 2. No emojis or decorative icons

FORBIDDEN in commits, PRs, documentation, code, scripts, and UI strings:

- Emoji characters.
- Decorative unicode symbols used as icons (✅ ❌ ⚠️ 🚀 etc.).

Plain ASCII for status indicators when needed (`OK`, `FAIL`, `WARN`, `TODO`).

## 3. Commit messages

Format: conventional-commit-style prefix + short imperative subject.

Allowed prefixes: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`,
`chore`, `revert`.

- Technical, objective, lowercase subject.
- No trailing period on the subject line.
- Subject line under 72 characters.
- Body (optional) explains WHY, not WHAT. Wrap at 100 columns.

Correct:

```
feat: add provider fallback matrix to runtime policy
fix: prevent retry budget underflow on transport errors
docs: add ADR for multi-provider LLM strategy
```

Wrong:

```
feat: add provider fallback

Co-Authored-By: Claude <noreply@anthropic.com>
Generated with AI assistance
```

## 4. Code style

- **Python** (`services/runtime/`): Python 3.11+, type hints, `ruff` for lint+format.
  No docstrings on trivial methods/functions/classes; prefer self-documenting names.
  No inline comments explaining WHAT the code does — refactor to clearer names or
  smaller functions. Comments are allowed only to capture non-obvious WHY
  (hidden constraint, workaround, subtle invariant).
- **Shell** (`scripts/`): POSIX-compatible Bash, `set -euo pipefail`, `shellcheck`
  must pass. Locale must be pinned where numeric formatting matters
  (`export LC_ALL=C LC_NUMERIC=C`).
- **YAML/Markdown**: 2-space indent, LF line endings, UTF-8.

## 5. What NOT to do without explicit user approval

- Run destructive git operations (`reset --hard`, `push --force`, `branch -D`,
  `clean -fd`).
- Skip hooks (`--no-verify`) or bypass signing.
- Delete or overwrite files whose purpose is unclear.
- Upload files to third-party services (pastebins, gist, diagram renderers).
- Create GitHub releases, tags, or branch protection rules.
- Post to Slack, email, Jira, or Linear.
- Install system packages or modify the host machine outside the repo.

When unsure, stop and ask.

## 6. What you may do autonomously

- Edit, create, and delete files inside the repo working tree.
- Run tests, linters, and formatters locally.
- Start/stop services defined in `infra/docker/compose.yaml`.
- Create local branches, stage changes, and write commits.
- Read public documentation via Context7 or equivalent.

## 7. Repository layout reminders

- `.claude-plugin/marketplace.json` — Claude Code marketplace manifest (root).
- `plugins/cadre/` — Claude Code plugin surface. Contains `agents/`, `skills/`,
  `templates/`, `runtime-policy.yaml`, `.claude-plugin/plugin.json`.
  **No executable code.** Markdown, YAML, templating only.
- `services/runtime/` — Python runtime (`cadre` package). Library used by plugin.
- `services/gateway/` — reserved for Go gateway. Do not add Python or TS code here.
- `services/web/` — reserved for TypeScript dashboard. Do not add backend code here.
- `infra/docker/`, `infra/terraform/` — deployment artifacts. Keep production and
  local-dev concerns separated.
- `docs/architecture/` — ADRs. New architectural decisions get a numbered ADR here.
- `ai-docs/` — run-local artifacts, blueprints, archive.
- `scripts/` — cross-repo tooling. Must pass shellcheck.

## 8. Licensing awareness

Cadre is **BSL 1.1**, converting to **Apache 2.0** on **2030-04-21**.

- Do not add code under incompatible licenses (e.g. pure GPL, AGPL) without explicit
  approval.
- Do not add dependencies with unclear or restrictive licenses without checking first.
- Preserve the top-of-file notice pattern if one is established later. The root
  `LICENSE` is authoritative; do not duplicate license text into individual source
  files unless agreed.

## 9. Contract-first changes

Cadre is contract-driven. Before changing agent, skill, policy, or template files in
`plugins/cadre/`, consider downstream consumers:

- Runtime loaders in `services/runtime/`.
- Scripts in `scripts/` and `plugins/cadre/scripts/`.
- Templates referenced from other templates.

Breaking contract changes require a version bump in the affected spec and a note in
the PR description explaining the migration path.

## 10. Tests and verification before declaring done

- A task is not done until the relevant tests pass locally. For the runtime, that
  means `pytest -q` green in `services/runtime/`.
- CI failures are not "flakiness" by default — investigate the root cause before
  reruns.
- When editing scripts, run `shellcheck` locally.
- When editing `plugins/cadre/runtime-policy.yaml`, validate it parses as YAML.

---

When in doubt, follow the rule that produces the least ambiguous, least decorative,
least AI-branded artifact. Cadre's public surface must look like a serious
infrastructure project, not an AI demo.
