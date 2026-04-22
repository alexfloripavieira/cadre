#!/usr/bin/env bash
# Reads a pipeline summary JSON from stdin (or path arg) and prints an ASCII board.
# Honors ENABLED=false to emit nothing. Requires jq + awk.
set -euo pipefail
export LC_ALL=C LC_NUMERIC=C

ENABLED="${ENABLED:-true}"
[ "$ENABLED" != "true" ] && exit 0

if [ "${1:-}" ]; then
  INPUT=$(cat "$1")
else
  INPUT=$(cat)
fi

skill=$(echo "$INPUT"    | jq -r '.skill')
scenario=$(echo "$INPUT" | jq -r '.scenario // "-"')
durms=$(echo "$INPUT"    | jq -r '.duration_ms')
budget=$(echo "$INPUT"   | jq -r '.budget_usd')
cp=$(echo "$INPUT"       | jq -r '.checkpoints_passed')
ct=$(echo "$INPUT"       | jq -r '.checkpoints_total')
gp=$(echo "$INPUT"       | jq -r '.gates_passed')
gt=$(echo "$INPUT"       | jq -r '.gates_total')
retries=$(echo "$INPUT"  | jq -r '.retries')
arts=$(echo "$INPUT"     | jq -r '.artifacts | join(", ")')
sep=$(echo "$INPUT"      | jq -r '.sep_log_path')

dur_fmt=$(awk -v m="$durms" 'BEGIN{ s=int(m/1000); mn=int(s/60); sc=s%60; printf "%dm %02ds", mn, sc }')
fmt_k() { awk -v n="$1" 'BEGIN{ if (n>=1000) printf "%.1fk", n/1000; else printf "%d", n }'; }

printf '╔═══ SQUAD PIPELINE REPORT ═════════════════════════════════════╗\n'
printf '║  skill: %-13s scenario: %-13s duration: %-6s ║\n' "$skill" "$scenario" "$dur_fmt"
printf '╠════════════════════════════════════════════════════════════════╣\n'
printf '║  teammate              status    tokens    cost     gaps      ║\n'
printf '║  ─────────────────────────────────────────────────────────    ║\n'

echo "$INPUT" | jq -c '.teammates[]' | while read -r row; do
  name=$(echo "$row"  | jq -r '.name')
  st=$(echo "$row"    | jq -r '.status')
  tk=$(echo "$row"    | jq -r '.tokens_total')
  cost=$(echo "$row"  | jq -r '.cost_usd')
  gp2=$(echo "$row"   | jq -r '.gaps_count')
  sev=$(echo "$row"   | jq -r '.severity // empty')
  tk_f=$(fmt_k "$tk")
  cost_f=$(printf '$%.3f' "$cost")
  if [ -n "$sev" ]; then
    gaps_field=$(printf '%s (%s)' "$gp2" "$sev")
  else
    gaps_field="$gp2"
  fi
  printf '║  %-22s ✓ %-7s %-8s %-8s %-10s ║\n' "$name" "$st" "$tk_f" "$cost_f" "$gaps_field"
done

ttok=$(echo "$INPUT"  | jq '[.teammates[].tokens_total] | add')
tcost=$(echo "$INPUT" | jq '[.teammates[].cost_usd] | add')
tgap=$(echo "$INPUT"  | jq '[.teammates[].gaps_count] | add')
ttok_f=$(fmt_k "$ttok")
tcost_f=$(printf '$%.3f' "$tcost")

printf '║  ─────────────────────────────────────────────────────────    ║\n'
printf '║  %-30s %-8s %-8s %-10s ║\n' "TOTAL" "$ttok_f" "$tcost_f" "$tgap"
printf '╠════════════════════════════════════════════════════════════════╣\n'

pct=$(awk -v c="$tcost" -v b="$budget" 'BEGIN{ if (b==0) print 0; else printf "%.1f", (c/b)*100 }')
bar_filled=$(awk -v p="$pct" 'BEGIN{ n=int(p/5); if (n>20) n=20; for(i=0;i<n;i++) printf "█" }')
bar_empty=$(awk -v p="$pct" 'BEGIN{ n=20-int(p/5); if (n<0) n=0; for(i=0;i<n;i++) printf "░" }')

printf '║  budget:  $%.2f     used: %s%%     %s%s        ║\n' "$budget" "$pct" "$bar_filled" "$bar_empty"
printf '║  checkpoints: %d/%d   gates: %d/%d passed   retries: %d            ║\n' "$cp" "$ct" "$gp" "$gt" "$retries"
printf '║  artifacts: %-50s ║\n' "$arts"
printf '║  sep log:  %-51s ║\n' "$sep"
printf '╚════════════════════════════════════════════════════════════════╝\n'
