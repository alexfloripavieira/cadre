# Releasing `claude-tech-squad`

## How Auto-Update Works

When users install the plugin with `autoUpdate: true` in their `~/.claude/settings.json`, Claude Code periodically checks the marketplace for new versions by reading `marketplace.json` from the repository. When it detects a version bump, it updates automatically.

For this to work every release must:
1. Keep `marketplace.json` and `plugin.json` aligned
2. Keep `docs/MANUAL.md` on the same version
3. Have a CHANGELOG entry for the version
4. Publish a tagged GitHub Release from `main`

## Official Release Path

The official path is **GitHub Actions automation on `main`**.

When code lands on `main`, the repository pipeline now does the rest:

- derives the next semantic version from commit subjects since the last tag
- updates `CHANGELOG.md`
- updates `.claude-plugin/marketplace.json`
- updates `plugins/claude-tech-squad/.claude-plugin/plugin.json`
- updates `docs/MANUAL.md`
- runs `scripts/smoke-test.sh`
- verifies changelog and version alignment
- builds a release bundle and checksum
- commits the generated metadata back to `main`
- creates and pushes the git tag automatically
- creates or updates the GitHub Release
- uploads the bundle as a release asset

Before release, the expected quality bar is:

- `bash scripts/validate.sh`
- `bash scripts/smoke-test.sh`
- `bash scripts/dogfood.sh`
- `bash scripts/dogfood-report.sh --schema-only`

For release-critical workflow changes, also run real golden runs and validate them with:

```bash
bash scripts/dogfood-report.sh
```

## Versioning Policy

Use semantic versioning derived from conventional commit subjects on `main`.

- **major**: `BREAKING CHANGE` in the body or `type!:` in the subject
- **minor**: `feat:`
- **patch**: everything else, including `fix:`, `docs:`, `refactor:`, `chore:`

For reliable releases, squash-merge titles and direct commits to `main` must follow conventional commit style.

## Release Process (Automated)

### Step 1 — Merge releasable work to `main`

Use conventional commit subjects in the final commits that land on `main`. The release workflow derives:

- semver bump
- changelog sections
- plugin manifest versions
- manual version

README does not participate in per-release versioning today, so it is not auto-mutated.

### Step 2 — GitHub Actions prepares and publishes the release

When a non-metadata change lands on `main`, `.github/workflows/release.yml` runs automatically.
It updates release metadata, validates the repository, commits the generated files, creates `vX.Y.Z`, builds the bundle, and publishes the GitHub Release.

### Step 3 — Verify on GitHub

After pushing, check:
- GitHub Actions tab: `publish` workflow passes
- Releases page: release exists or was updated with the right notes
- release assets include the tarball and checksum
- `marketplace.json`, `plugin.json`, and `MANUAL.md` match the release version
- the workflow-created tag matches the release version
- the metadata commit on `main` has subject `chore: prepare release vX.Y.Z`

## Optional Fallback Script

If your automation is unavailable and you need an emergency fallback, `scripts/release.sh` still exists. It is no longer the primary path.

If you need to release manually:

```bash
./scripts/release.sh
```

The fallback script uses the same metadata generator as the publish workflow. It prepares the changelog and manifest versions automatically, validates the repository, pushes the metadata commit to `main`, and triggers the `publish` workflow with `workflow_dispatch`.

For the day-to-day operator checklist, see [HOW-TO-CHANGE-AND-PUBLISH.md](/home/alex/claude-tech-squad/docs/HOW-TO-CHANGE-AND-PUBLISH.md).

## User Configuration for Auto-Update

Users must have this in `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "alexfloripavieira-plugins": {
      "source": { "source": "github", "repo": "alexfloripavieira/claude-tech-squad" },
      "autoUpdate": true
    }
  }
}
```

With `autoUpdate: true`, Claude Code picks up new versions automatically when a new tag is published.
