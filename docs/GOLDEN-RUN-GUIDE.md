# Golden Run Guide — Your First Real Runs

This guide walks you through installing the plugin, running your first real executions against a production project, and capturing evidence that validates the pipeline works.

---

## What is a Golden Run?

A golden run is a **real execution** of the plugin against a **real project**, captured entirely (prompt, trace, output, metrics) as a quality reference. It is the E2E test of the plugin — not checking if files exist, but if **the output is useful**.

| Testing level | What it checks | Tool |
|---|---|---|
| Unit test | Agent has correct frontmatter | `validate.sh` |
| Integration test | Skills reference correct agents | `smoke-test.sh` |
| Fixture test | Fixtures have valid structure | `dogfood.sh` |
| **Golden run** | **Plugin produces useful output on a real repo** | You + `capture-golden-run.sh` |

---

## Pre-requisites

- Claude Code installed (CLI, Desktop App, or Web at claude.ai/code)
- A real project where you work (any stack — Django, React, Python, TypeScript, etc.)
- Optionally: Jira/GitHub Issues access with real tickets

---

## Step 1 — Install the plugin

```bash
claude plugin marketplace add alexfloripavieira/claude-tech-squad
claude plugin install -s user claude-tech-squad@alexfloripavieira-plugins
```

Verify:
```bash
claude plugin list
# Should show: claude-tech-squad v5.43.0 (or later)
```

---

## Step 2 — Activate safety hooks (recommended)

The `pre-tool-guard.sh` hook blocks destructive operations mechanically (DROP TABLE, force-push, rm -rf, etc.). Activate it by creating `.claude/settings.json` in your project:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash plugins/claude-tech-squad/hooks/pre-tool-guard.sh"
          }
        ]
      }
    ]
  }
}
```

> If the path doesn't work, find the installed plugin: `ls ~/.claude/plugins/cache/*/claude-tech-squad/*/hooks/`

---

## Step 3 — Open the live dashboard

The dashboard auto-updates every 2 seconds during execution, showing teammate status, token budget, and event timeline.

**Important:** The dashboard needs a local HTTP server to read the status file (browsers block direct `file://` access for security). Run from your project directory:

```bash
# Option A: Use the launcher script (recommended)
# Find the installed plugin path and run the script:
bash $(find ~/.claude/plugins/cache -path "*/claude-tech-squad/*/scripts/open-dashboard.sh" 2>/dev/null | head -1)

# Option B: Manual server (if Option A doesn't work)
mkdir -p ai-docs
echo '{"skill":null,"phase":"waiting","teammates":[],"events":[]}' > ai-docs/.live-status.json
# Copy the dashboard HTML to ai-docs/
cp $(find ~/.claude/plugins/cache -path "*/claude-tech-squad/*/dashboard/live.html" 2>/dev/null | head -1) ai-docs/dashboard.html
# Fix the status path in the copied file
sed -i "s|../../../ai-docs/.live-status.json|.live-status.json|g" ai-docs/dashboard.html
# Start the server
python3 -m http.server 3742 --bind 127.0.0.1 -d ai-docs &
# Open in browser
xdg-open http://localhost:3742/dashboard.html   # Linux
open http://localhost:3742/dashboard.html        # macOS
```

Leave the dashboard open in a browser tab. It will stay on "Waiting for data..." until you run a skill.

---

## Step 4 — Navigate to your real project

```bash
cd ~/your-real-project
claude
```

---

## Step 5 — Golden Run 1: Discovery from a ticket

Choose a **real Jira ticket** (Story or Task, not a bug) for a feature you plan to build.

```
/claude-tech-squad:discovery APP-123
```

Or without a ticket:
```
/claude-tech-squad:discovery build a notification system for user events
```

### What to observe

| Check | What to look for |
|---|---|
| Ticket read | Did `[Ticket Read]` appear? Were ACs extracted? |
| Dashboard | Is it showing teammates running with live timers? |
| PM output | Are the acceptance criteria measurable and useful? |
| Architecture | Does it respect your repo's existing patterns? |
| Gates | Are they asking the right questions at the right time? |
| Blueprint | Would you actually use this to implement the feature? |

### At the end

The skill will ask:
```
How useful was this run? [1] [2] [3] [4] [S]
One-line comment (optional): ___
```

Answer honestly — this data feeds `/factory-retrospective`.

### Record what happened

Note down:
- How long the run took
- How many gates you approved/rejected
- Whether the blueprint is usable or needs major edits
- Any agent output that was off-target or useless
- Anything surprising (positive or negative)

---

## Step 6 — Golden Run 2: Bug fix from a ticket

Choose a **real bug ticket** (open, not yet resolved).

```
/claude-tech-squad:bug-fix APP-456
```

### What to observe

| Check | What to look for |
|---|---|
| Symptom extraction | Did the plugin correctly identify the bug from the ticket? |
| Root cause | Is the diagnosis plausible? |
| TDD | Was a failing test written BEFORE the fix? |
| Fix quality | Does the fix actually resolve the bug? No side effects? |
| Review | Did the reviewer catch anything the fix missed? |

---

## Step 7 — Golden Run 3: Implement from the blueprint

If Golden Run 1 produced a good blueprint, use it:

```
/claude-tech-squad:implement ai-docs/<feature-slug>/blueprint.md
```

Or from a ticket:
```
/claude-tech-squad:implement APP-789
```

### What to observe

| Check | What to look for |
|---|---|
| TDD tests | Are the failing tests meaningful and complete? |
| Implementation | Does the code compile, pass tests, follow your conventions? |
| Review cycles | Did the reviewer require retries? How many? |
| QA | Did QA validate all acceptance criteria? |
| Quality bench | Did security/performance/accessibility find anything real? |
| UAT | Did the PM validate against original acceptance criteria? |
| Health check | Were there any `[Health Warning]` lines? |
| Cost | How many tokens were consumed? Check the SEP log. |

---

## Step 8 — Check your SEP logs

After 3 runs, you should have 3 SEP logs:

```bash
ls ai-docs/.squad-log/
```

Each file contains metrics: tokens, duration, retries, fallbacks, checkpoints, teammate reliability.

---

## Step 9 — Run factory-retrospective

```
/claude-tech-squad:factory-retrospective
```

This analyzes all 3 runs and produces:
- Retry rates per skill and agent
- Fallback frequency
- Token cost per run (real, not estimated)
- Developer satisfaction correlation
- Improvement recommendations

---

## Step 10 — Capture golden runs for the repository

If you want to commit the results as quality evidence:

```bash
bash scripts/capture-golden-run.sh <scenario-id> <your-name>
```

This reads the latest SEP log and creates a golden run directory with metadata, trace, and output.

---

## What to do with the results

| Finding | Action |
|---|---|
| An agent produced useless output | Adjust that agent's prompt in `agents/<slug>.md` |
| Cost was too high for a simple task | Use `/cost-estimate` next time, or adjust `cost_guardrails` |
| A gate asked an irrelevant question | Adjust the gate criteria in the skill's SKILL.md |
| TDD was skipped or tests were weak | Adjust `tdd-specialist.md` prompt |
| Review cycles were excessive (3+) | Check if the reviewer's prompt is too strict or vague |
| Blueprint was unusable | Adjust PM and Architect prompts, or add repo-specific CLAUDE.md |
| Token cost doesn't match estimate | Update the Cost vs Scope Guide in SKILL-SELECTOR.md |
| Dashboard didn't update | Check if `.live-status.json` was written (may need teammate mode) |

---

## Success criteria

After 3 golden runs, you should be able to answer:

1. **Does the plugin save time?** Compare: how long would this have taken without the plugin?
2. **Is the output usable?** Can you merge the code or use the blueprint without major rewrites?
3. **Are the gates calibrated?** Too many = friction. Too few = risk. Right amount = the dev feels like a manager.
4. **Is the cost justified?** A $20 /squad run that saves 2 days of work = excellent ROI. A $20 run for a typo = waste.
5. **What needs to improve?** Every run will reveal something — prompts, gates, routing, or cost.

The goal is not perfection on the first run. The goal is **evidence** that enables iterative improvement.
