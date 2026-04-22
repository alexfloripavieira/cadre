#!/usr/bin/env bash
# Cadre PreCompact hook.
#
# Claude Code invokes this hook before native context compaction. The hook runs
# the /rollover skill for the active Cadre run, produces the handoff artifacts,
# and returns their paths so Claude Code uses the produced summary as the
# compacted context.
#
# Fallback: if no active run is detectable, the hook exits 0 silently and
# allows Claude Code's native compaction to proceed. The operator can still
# invoke /rollover manually afterwards.
#
# Reference: docs/architecture/0006-context-rollover.md
#
# Environment expected:
#   CADRE_SEP_LOG_DIR   path to the run's SEP log directory (default: .cadre-log)
#   CADRE_AI_DOCS_DIR   path to the run's ai-docs directory (default: ai-docs)
#   CADRE_RUN_ID        optional; if unset, the hook picks the most recent run
#
# Exit codes:
#   0  — hook succeeded (artifacts produced or no-op)
#   1  — hook detected an active run but failed to produce artifacts; Claude
#        Code should fall back to native compaction and the operator should
#        invoke /rollover manually
#
# This hook is deliberately conservative. It never blocks Claude Code. A
# failure path always yields exit 0 unless a structural error left the
# repository in an inconsistent state.

set -euo pipefail
export LC_ALL=C LC_NUMERIC=C

SEP_LOG_DIR="${CADRE_SEP_LOG_DIR:-.cadre-log}"
AI_DOCS_DIR="${CADRE_AI_DOCS_DIR:-ai-docs}"
RUN_ID="${CADRE_RUN_ID:-}"

if [ ! -d "$SEP_LOG_DIR" ]; then
  # No Cadre runs have been logged. Let Claude Code compact natively.
  exit 0
fi

if [ -z "$RUN_ID" ]; then
  # Pick the most recent SEP log filename and extract its run_id field.
  latest=$(ls -1t "$SEP_LOG_DIR"/*.md 2>/dev/null | head -n1 || true)
  if [ -z "$latest" ]; then
    exit 0
  fi
  RUN_ID=$(awk '/^run_id:/ {print $2; exit}' "$latest" || true)
fi

if [ -z "$RUN_ID" ]; then
  exit 0
fi

mkdir -p "$AI_DOCS_DIR"

# Delegate to the Python runtime entry point. The runtime resolves the
# /rollover skill, invokes context-summarizer, validates artifacts, and writes
# the rollover-pending checkpoint.
if ! python3 -m cadre.cli rollover --run-id "$RUN_ID" \
      --sep-log-dir "$SEP_LOG_DIR" \
      --ai-docs-dir "$AI_DOCS_DIR" >/dev/null 2>"$AI_DOCS_DIR/precompact-hook.err"; then
  # Rollover failed. Do not block Claude Code's compaction — exit clean and
  # leave the error log for the operator.
  echo "Cadre PreCompact rollover failed; see $AI_DOCS_DIR/precompact-hook.err" >&2
  exit 0
fi

# On success, emit the brief path so Claude Code can fold it into the
# compacted context. The stdout contract is intentionally minimal:
#   one line:  CADRE_ROLLOVER_BRIEF=<path>
#   one line:  CADRE_ROLLOVER_STATE=<path>
echo "CADRE_ROLLOVER_BRIEF=$AI_DOCS_DIR/rollover-$RUN_ID.md"
echo "CADRE_ROLLOVER_STATE=$AI_DOCS_DIR/rollover-$RUN_ID.json"
exit 0
