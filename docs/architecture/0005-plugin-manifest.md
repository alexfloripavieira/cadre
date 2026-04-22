# ADR 0005 — Plugin Manifest and Repository Layout for Claude Code Distribution

- Status: Accepted
- Date: 2026-04-22
- Deciders: Alexsander Vieira
- Amends: ADR 0001 (monorepo layout — adds a `plugins/` tree alongside `services/` and `packages/`)
- Builds on: ADR 0003 (rebrand + pivot), ADR 0004 (agentic orchestration)

## Context

Cadre is distributed as a Claude Code plugin (ADR 0003). Claude Code's plugin
ecosystem expects a specific two-level structure:

1. A **marketplace manifest** at `.claude-plugin/marketplace.json` at the repository
   root, listing every plugin published from this repo.
2. A **plugin manifest** at `<plugin-root>/.claude-plugin/plugin.json` for each
   plugin, declaring its name, description, version, and author.

Inside the plugin root, Claude Code expects the plugin's capabilities in
well-known subdirectories:

- `agents/` — agent specifications (markdown with frontmatter).
- `skills/` — skill specifications (each in its own directory with `SKILL.md`).
- `commands/` — slash command definitions (optional in Cadre v0.1).
- `hooks/` — hook configurations (optional).
- `bin/` — executables shipped with the plugin.
- `scripts/` — helper scripts invoked by skills.

The reference for this shape is the sibling project `claude-tech-squad`
(`alexfloripavieira/claude-tech-squad`, publicly installable as
`@alexfloripavieira/claude-tech-squad` in Claude Code).

The repository currently follows the layout from ADR 0001: `services/` for code,
`packages/` for contracts (agents, skills, templates, policy), `docs/` for
documentation, `infra/` for deployment. That structure is valid for engineering
concerns but does not match Claude Code's expectations for plugin discovery.

This ADR defines how both structures coexist.

## Decision

### 1. Repository layout becomes dual-purpose

The root of the Cadre repository serves two distribution axes:

- **Plugin distribution axis:** `.claude-plugin/marketplace.json` + `plugins/cadre/`
  that Claude Code reads directly.
- **Engineering axis:** `services/`, `docs/`, `infra/`, `ai-docs/`, `scripts/`,
  `tests/` that developers of Cadre use.

The contracts currently under `packages/` (agents, skills, templates, policy) move
into `plugins/cadre/` to become the plugin's surface. The `packages/` directory is
retired.

Target top-level layout:

```
cadre/
  .claude-plugin/
    marketplace.json              # one entry pointing to plugins/cadre
  plugins/
    cadre/
      .claude-plugin/
        plugin.json               # this plugin's manifest
      agents/                     # moved from packages/agents
      skills/                     # moved from packages/skills
      templates/                  # moved from packages/templates
      runtime-policy.yaml         # moved from packages/policy/runtime-policy.yaml
      scripts/                    # plugin-local helpers (copied from /scripts as needed)
      README.md
  services/
    runtime/                      # unchanged — Python package used by plugin scripts
      cadre/
      tests/
      pyproject.toml
  docs/                           # unchanged
  infra/                          # unchanged
  ai-docs/                        # unchanged
  scripts/                        # repo-level tooling (CI helpers, release scripts)
  tests/                          # repo-level integration tests
```

### 2. Plugin manifest fields (v0.1)

`plugins/cadre/.claude-plugin/plugin.json`:

```json
{
  "name": "cadre",
  "description": "A cadre of AI agents for serious software delivery. Agentic delivery plugin for Claude Code with multi-provider fallback, retry budgets, doom-loop detection, cost guardrails, and structured audit log (SEP).",
  "version": "0.1.0",
  "author": {
    "name": "alexfloripavieira"
  }
}
```

### 3. Marketplace manifest fields (v0.1)

`.claude-plugin/marketplace.json`:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "cadre-labs",
  "owner": {
    "name": "alexfloripavieira"
  },
  "plugins": [
    {
      "name": "cadre",
      "description": "Agentic delivery plugin for Claude Code — retry budgets, multi-provider fallback, doom-loop detection, cost guardrails, SEP audit log.",
      "version": "0.1.0",
      "source": "./plugins/cadre"
    }
  ]
}
```

The `owner.name` remains `alexfloripavieira` until the `cadre-labs` GitHub org is
created and the repo is transferred; on transfer, the owner field updates to
`cadre-labs` and the repo path in the marketplace URL updates accordingly.

### 4. Contract file relocation rules

When content moves from `packages/` to `plugins/cadre/`:

- File **content** does not change — all frontmatter and body stay byte-identical.
- Only **paths** change.
- Any cross-reference (docs, CI config, Python imports, Dockerfile paths) that
  pointed to `packages/...` must be updated in the same commit as the move.
- The runtime-policy.yaml keeps its `cadre:` namespace from ADR 0003 — no rename.

### 5. Services layer separation

`services/runtime/` does not move. It remains an independent Python package
(`cadre`) that:

- Can be imported by plugin scripts via `PYTHONPATH=/path/to/services/runtime` or
  via `pip install -e services/runtime` in development.
- Does not ship inside the plugin itself in v0.1. The plugin invokes the runtime
  indirectly via `bin/` executables that wrap the Python library, or directly
  when the user has installed the runtime as a Python dep.
- For v0.1, plugin scripts depend on a locally installed `cadre` Python package.
  Simplification: users install `pip install cadre` before using the plugin, or
  the plugin's `bin/` ships a self-contained Python script that pulls the
  library as a single dependency.

Packaging the runtime as a bundled binary (py-spy / shiv) is deferred to v0.2.

### 6. Plugin discovery and versioning

- The plugin version (in `plugin.json`) drives Claude Code's plugin installer and
  the user-facing version string.
- The marketplace version (implicit in `marketplace.json`) lists available plugins
  from this repo; one entry per plugin.
- Both files are machine-readable and CI validates them on every commit.
- The `cadre` Python package's `pyproject.toml` version tracks the runtime
  library semver, which is decoupled from the plugin version in v0.1 (they will
  be aligned when the runtime is bundled into the plugin in v0.2).

## Consequences

Positive:

- Claude Code's plugin installer can consume this repo directly without any
  packaging shim.
- Users get `/install cadre` or equivalent and receive the full plugin surface
  (agents, skills, runtime-policy, scripts) in one go.
- The engineering structure (services, docs, infra) stays out of the plugin's
  shipped surface — plugin consumers do not download the runtime dev env,
  infrastructure code, or documentation artifacts they do not need.
- Multi-plugin distribution is possible later: additional plugins can live at
  `plugins/<other>/` and be listed in the same `marketplace.json`.

Negative:

- Doubled directory depth for contract files: what was at `packages/agents/foo.md`
  is now at `plugins/cadre/agents/foo.md`. Tooling and docs that reference
  old paths must be updated.
- The `packages/` → `plugins/cadre/` migration is a breaking change for any
  external consumer that was importing by path. For Cadre v0.1 this is zero
  consumers, so the cost is local only.
- Developers working on the repo now see `plugins/cadre/` as the canonical
  contract location and `packages/` as legacy. Clear README + CLAUDE.md update
  required to avoid confusion during the transition.
- Two "runtime-policy.yaml" locations could emerge if the move is partial.
  Enforce: one canonical file at `plugins/cadre/runtime-policy.yaml`; no
  duplicates.

## Alternatives considered

- **Keep `packages/` and symlink into `plugins/cadre/`.** Rejected: symlinks are
  fragile under git on Windows/macOS edge cases and confuse some tools
  (file watchers, diff viewers, IDE indexers).

- **Build-time copy from `packages/` to `plugins/cadre/` via a Makefile.**
  Rejected: introduces a build step before contracts are usable, which defeats
  the "contracts are readable markdown" discipline from ADR 0001. Also creates
  two sources of truth during development.

- **Flat plugin at the repository root (no `plugins/` subdir).** Rejected: blocks
  multi-plugin distribution later and conflicts with the engineering tree
  (`services/`, `docs/`). The marketplace schema supports `source: "."` but this
  couples the plugin bundle to everything in the repo, including dev artifacts.

- **Keep current structure and ship a separate `cadre-plugin` repo that vendors
  from this one.** Rejected: doubles maintenance overhead for a solo founder
  with no clear benefit. The monorepo already has the expressive structure.

## Migration plan

Executed in one commit to avoid broken intermediate states:

1. Create `.claude-plugin/marketplace.json` at root.
2. Create `plugins/cadre/.claude-plugin/plugin.json`.
3. `git mv packages/agents plugins/cadre/agents`
4. `git mv packages/skills plugins/cadre/skills`
5. `git mv packages/templates plugins/cadre/templates`
6. `git mv packages/policy/runtime-policy.yaml plugins/cadre/runtime-policy.yaml`
7. Remove empty `packages/` directory.
8. Update `CLAUDE.md` Section 7 (Repository layout reminders) with the new paths.
9. Update `README.md` architecture block with the new tree.
10. Update `docs/architecture/0001-monorepo-layout.md` with an amendment note
    pointing to this ADR.
11. Grep-replace any `packages/agents`, `packages/skills`, `packages/templates`,
    `packages/policy` references across `docs/`, `services/`, `infra/`, `.github/`,
    `scripts/`, and top-level files. Verify with `grep -r "packages/" . --include='*.md' --include='*.yaml' --include='*.py' --include='*.toml'`.
12. Run `pytest` and confirm green.
13. Run `python -c "import yaml; yaml.safe_load(open('plugins/cadre/runtime-policy.yaml'))"` to validate the moved policy.
14. Commit with message `refactor: adopt claude code plugin layout per ADR 0005`.

## Follow-ups

- ADR 0006 — orchestrator prompt versioning strategy and regression tests for
  agentic behavior (foreshadowed in ADR 0004).
- Implementation of the migration itself (next commit after this ADR lands).
- `packages/` removal must be a clean git mv, not a copy-and-delete — preserve
  blame history for every contract file.
