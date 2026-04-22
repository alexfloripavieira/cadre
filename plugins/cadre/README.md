# cadre (plugin)

Claude Code plugin surface for Cadre. Contains the agent specs, skill specs,
templates, and runtime policy that Claude Code loads when the plugin is
installed.

See the repository root `README.md` for the full product description.

## Layout

- `.claude-plugin/plugin.json` — plugin manifest.
- `agents/` — agent specifications (markdown + YAML frontmatter per ADR 0004).
- `skills/` — skill specifications.
- `templates/` — PRD, TechSpec, Tasks output templates.
- `runtime-policy.yaml` — retry budgets, fallback matrix, doom-loop patterns,
  cost ceilings, observability config.

## Runtime dependency

The Python runtime library `cadre` (source at `../../services/runtime/`) must be
installed in the user's environment for skills that invoke the reliability
wrapper. In v0.1 this is a manual step; in v0.2 the plugin bundles the runtime.

## License

BSL 1.1 (converts to Apache 2.0 on 2030-04-21). See repository root `LICENSE`.
