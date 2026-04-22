#!/usr/bin/env bash
# Reads a teammate Result Contract JSON from stdin and prints an ASCII card.
# Respects FORMAT env (ascii | compact | silent). Default: ascii.
set -euo pipefail
export LC_ALL=C LC_NUMERIC=C

FORMAT="${FORMAT:-ascii}"
[ "$FORMAT" = "silent" ] && exit 0

INPUT="$(cat)"
agent=$(echo "$INPUT"  | jq -r '.agent')
status=$(echo "$INPUT" | jq -r '.status')
tin=$(echo "$INPUT"    | jq -r '.tokens_input')
tout=$(echo "$INPUT"   | jq -r '.tokens_output')
cost=$(echo "$INPUT"   | jq -r '.estimated_cost_usd')
durms=$(echo "$INPUT"  | jq -r '.total_duration_ms')
conf=$(echo "$INPUT"   | jq -r '.confidence')
gaps=$(echo "$INPUT"   | jq -r '.gaps_count')
arts=$(echo "$INPUT"   | jq -r '.artifacts_count')

fmt_tokens() {
  awk -v n="$1" 'BEGIN{ if (n>=1000) printf "%.1fk", n/1000; else printf "%d", n }'
}
tin_f=$(fmt_tokens "$tin")
tout_f=$(fmt_tokens "$tout")
total_f=$(fmt_tokens "$((tin+tout))")
dur_f=$(awk -v m="$durms" 'BEGIN{ printf "%.1fs", m/1000 }')
cost_f=$(printf '$%.4f' "$cost")

if [ "$FORMAT" = "compact" ]; then
  printf '%-20s %s  in:%s out:%s cost:%s dur:%s conf:%s gaps:%s\n' \
    "$agent" "$status" "$tin_f" "$tout_f" "$cost_f" "$dur_f" "$conf" "$gaps"
  exit 0
fi

# ascii (default)
printf '┌─ %s ─────────────────────────── ✓ %s ─┐\n' "$agent" "$status"
printf '│  tokens in: %6s   out: %6s   total: %s │\n' "$tin_f" "$tout_f" "$total_f"
printf '│  cost: %8s     duration: %-6s              │\n' "$cost_f" "$dur_f"
printf '│  confidence: %-4s   gaps: %-2s  artifacts: %-2s    │\n' "$conf" "$gaps" "$arts"
printf '└──────────────────────────────────────────────────┘\n'
