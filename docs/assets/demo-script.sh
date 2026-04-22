#!/bin/bash
# Demo script for claude-tech-squad GIF recording
# Run with: terminalizer record demo -c docs/assets/terminalizer.yml

BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
RESET='\033[0m'

type_text() {
  local text="$1"
  local delay="${2:-0.05}"
  for ((i=0; i<${#text}; i++)); do
    printf "%s" "${text:$i:1}"
    sleep "$delay"
  done
}

pause() {
  sleep "${1:-1}"
}

clear
pause 0.5

# Prompt + command
printf "${GREEN}❯${RESET} "
pause 0.3
type_text "/claude-tech-squad:discovery add real-time order tracking to the checkout flow" 0.035
pause 0.8
echo ""
echo ""

pause 0.4
printf "${DIM}Scanning repository stack...${RESET}\n"
pause 0.5
printf "${DIM}Found: FastAPI · PostgreSQL · React · Redis · Celery${RESET}\n"
echo ""

pause 0.6

# Team created
printf "${BOLD}${CYAN}[Team Created]${RESET} discovery\n"
pause 0.5

# Teammates spawning
printf "${CYAN}[Teammate Spawned]${RESET} pm       | pane: pm\n"
pause 0.3
printf "${CYAN}[Teammate Spawned]${RESET} ba       | pane: ba\n"
pause 0.3
printf "${CYAN}[Teammate Spawned]${RESET} po       | pane: po\n"
pause 0.6
echo ""

# Gate 1
printf "${YELLOW}[Gate 1]${RESET} Scope Validation\n"
echo ""
printf "  ${BOLD}PM Summary:${RESET} 3 user stories, 9 acceptance criteria\n"
printf "  ${BOLD}PO Scope cut:${RESET} push notifications deferred to v2\n"
printf "  ${BOLD}Recommended sprint:${RESET} 1 week, backend-first\n"
echo ""
printf "  Confirm scope and continue? ${DIM}[y/n]${RESET} "
pause 0.8
type_text "y" 0.1
echo ""
echo ""

pause 0.5

# Planner + Architect
printf "${CYAN}[Teammate Spawned]${RESET} planner  | pane: planner\n"
pause 0.4
printf "${CYAN}[Teammate Spawned]${RESET} architect | pane: architect\n"
pause 0.3
printf "${CYAN}[Teammate Spawned]${RESET} techlead  | pane: techlead\n"
pause 0.8
echo ""

# Gate 2
printf "${YELLOW}[Gate 2]${RESET} Technical Tradeoffs\n"
echo ""
printf "  ${BOLD}Planner:${RESET} WebSocket vs polling — WebSocket chosen (Celery + Redis pub/sub)\n"
printf "  ${BOLD}Risk:${RESET} Redis connection pool sizing needs review\n"
echo ""
printf "  Approve technical direction? ${DIM}[y/n]${RESET} "
pause 0.8
type_text "y" 0.1
echo ""
echo ""

pause 0.5

# Specialist batch
printf "${CYAN}[Batch Spawned]${RESET} specialist-bench\n"
printf "  ${DIM}Teammates: backend-arch, api-designer, data-arch, dba, devops${RESET}\n"
pause 1.2
echo ""

printf "${CYAN}[Teammate Done]${RESET} backend-arch   | ${GREEN}hexagonal layers defined${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} api-designer   | ${GREEN}WebSocket contract drafted${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} data-arch      | ${GREEN}order_events table + CDC strategy${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} dba            | ${GREEN}migration safe — CONCURRENTLY index${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} devops         | ${GREEN}Redis pub/sub config defined${RESET}\n"
pause 0.8
echo ""

# Quality baseline
printf "${CYAN}[Batch Spawned]${RESET} quality-baseline\n"
printf "  ${DIM}Teammates: security-rev, privacy-rev, performance-eng${RESET}\n"
pause 1.0
echo ""

printf "${CYAN}[Teammate Done]${RESET} security-rev   | ${GREEN}no auth gaps in WebSocket handshake${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} privacy-rev    | ${GREEN}order data masked in logs${RESET}\n"
pause 0.2
printf "${CYAN}[Teammate Done]${RESET} performance-eng | ${GREEN}p99 < 200ms under 10k concurrent${RESET}\n"
pause 0.8
echo ""

# Gate 3
printf "${YELLOW}[Gate 3]${RESET} Architecture Direction\n"
echo ""
printf "  ${BOLD}Tech Lead:${RESET} WebSocket gateway → Celery consumer → Redis pub/sub → client\n"
printf "  ${BOLD}TDD plan:${RESET} 14 failing tests defined across 4 layers\n"
echo ""
printf "  Approve blueprint for implementation? ${DIM}[y/n]${RESET} "
pause 0.8
type_text "y" 0.1
echo ""
echo ""

pause 0.5

# TDD Specialist
printf "${CYAN}[Teammate Spawned]${RESET} tdd-specialist | pane: tdd-specialist\n"
pause 0.6

printf "${CYAN}[Teammate Done]${RESET} tdd-specialist | ${GREEN}TDD Delivery Plan ready — 14 failing tests${RESET}\n"
echo ""
pause 0.5

# Final gate
printf "${YELLOW}[Gate 4]${RESET} Blueprint Confirmation\n"
echo ""
printf "  ${BOLD}Discovery & Blueprint Document:${RESET} ready\n"
printf "  ${BOLD}TDD Delivery Plan:${RESET} ready\n"
printf "  ${BOLD}Next step:${RESET} run ${BOLD}/claude-tech-squad:implement${RESET}\n"
echo ""
printf "  Approve and proceed to implementation? ${DIM}[y/n]${RESET} "
pause 0.8
type_text "y" 0.1
echo ""
echo ""

pause 0.5

printf "${GREEN}${BOLD}Discovery complete.${RESET}\n"
printf "${DIM}Blueprint saved. Run /claude-tech-squad:implement to build.${RESET}\n"
echo ""

pause 2
