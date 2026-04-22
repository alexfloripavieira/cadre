# The Three Disciplines of AI Engineering

Prompt Engineering, Context Engineering, and Harness Engineering are not competitors. They are layers. You need all three. But most teams stop at the first one.

---

## The Restaurant Analogy

Imagine you are opening a restaurant. The AI model is your chef.

| Discipline | Restaurant equivalent | What you are doing |
|---|---|---|
| **Prompt Engineering** | Writing a recipe for the chef | Telling the chef exactly what to cook and how |
| **Context Engineering** | Stocking the kitchen with ingredients | Making sure the chef has the right ingredients, tools, and reference cookbooks available |
| **Harness Engineering** | Building the restaurant itself | Kitchen layout, food safety inspections, fire suppression, ordering system, quality control, customer feedback |

A great recipe (prompt) with the right ingredients (context) in a kitchen with no fire suppression (no harness) will eventually burn down the restaurant.

---

## Side-by-Side Comparison

### Definition

| | Prompt Engineering | Context Engineering | Harness Engineering |
|---|---|---|---|
| **One-line definition** | How you ask | What the model sees | How the system works |
| **Focus** | The instruction to the model | The information available to the model | The infrastructure around the model |
| **Scope** | One request → one response | One context window | The complete autonomous system |
| **Time horizon** | Seconds (one interaction) | Minutes (one session) | Hours to days (multi-step, long-running) |
| **Primary artifact** | A prompt or prompt template | A context assembly pipeline | Rules, tools, guardrails, feedback loops, and observability |
| **Who does it** | Anyone using an LLM | Developers building LLM apps | Engineers building agent systems |
| **When it matters most** | Always | When context is large or dynamic | When the agent runs autonomously |

### What goes wrong without each

| Without | What happens | Real-world example |
|---|---|---|
| Prompt Engineering | Model gives vague, wrong, or unhelpful responses | "Write code" → gets pseudocode instead of working code |
| Context Engineering | Model hallucinates or uses outdated information | Agent uses deprecated API because it only has training data, not current docs |
| Harness Engineering | Agent runs off the rails with no way to stop it | Agent enters an infinite retry loop, consumes $50 in tokens, then force-pushes broken code to main |

---

## Prompt Engineering — Deep Dive

### What it is

The art of crafting instructions that make the model produce the desired output. Techniques include: role assignment, few-shot examples, chain-of-thought, structured output formatting, negative instructions.

### Real-world examples

**Bad prompt:**
```
Fix the bug in my code
```
Result: Model guesses which file, which bug, and which language. Output may be completely wrong.

**Good prompt (Prompt Engineering applied):**
```
You are a senior Python developer. The file src/auth/login.py has a bug 
on line 42 where the password hash comparison uses == instead of 
hmac.compare_digest(). Fix only this line. Return the corrected function 
with no other changes. Explain the security risk of the original code.
```
Result: Precise fix with explanation.

**How claude-tech-squad uses Prompt Engineering:**

Every agent file is a carefully crafted prompt:
```markdown
# Backend Dev Agent

You implement server-side changes only.

## Rules
- Verify framework and library APIs via context7 before using them
- Follow existing backend conventions in the repo
- Write the failing test first — then implement the minimum code to pass it
- Do not silently redesign architecture; flag issues if the plan is wrong
- Keep changes scoped to the backend slice you own

## Absolute Prohibitions
- Running destructive database migrations without a rollback script
- Committing directly to main
- Hardcoding secrets in source code
```

This is prompt engineering — clear role, boundaries, rules, and prohibitions.

### Limitations

Prompt engineering alone cannot:
- Prevent the model from ignoring the instructions (it sometimes does)
- Provide access to current documentation (training data gets stale)
- Recover from errors (the model does not retry itself)
- Track costs (the model does not know how many tokens it used)
- Coordinate multiple agents (one prompt = one agent)

**Prompt engineering is necessary but not sufficient for production agents.**

---

## Context Engineering — Deep Dive

### What it is

The discipline of assembling the right information into the model's context window at the right time. Techniques include: RAG (retrieval-augmented generation), tool use, file reading, API lookups, context window management, summarization.

### Real-world examples

**Without Context Engineering:**
```
Developer: "Use the Django REST Framework serializer for user registration"
Model: "Here's a serializer using fields=['username', 'email', 'password']..."
```
Problem: The model used DRF 3.12 syntax from training data. The project uses DRF 3.15 which changed the `password` field handling. The code works in development but fails in production.

**With Context Engineering:**
```
1. Detect project uses DRF (read requirements.txt)
2. Look up current DRF docs via Context7 MCP
3. Read the project's existing serializers for convention patterns
4. Now generate the serializer with verified, current API usage
```
Result: Code matches the actual installed version and follows project conventions.

**How claude-tech-squad uses Context Engineering:**

The Documentation Standard in every agent:
```markdown
## Documentation Standard — Context7 First, Repository Fallback

Before using any library or API:
1. Resolve the library ID: mcp__context7__resolve-library-id("django-rest-framework")
2. Query the docs: mcp__context7__query-docs(libraryId, topic="serializers")

If Context7 is unavailable: use repository evidence and flag assumptions.
```

The Progressive Disclosure protocol:
```
PM output (3000 tokens) → digest (500 tokens) for Planner
Planner only gets what it needs, not the full PM output.
Architect gets full Planner output (immediately relevant) + PM digest.
```

The Ticket Intake:
```
/discovery APP-123
→ Reads Jira ticket via MCP
→ Extracts title, ACs, subtasks, priority
→ Feeds this as context to every agent in the chain
```

### Limitations

Context engineering alone cannot:
- Stop the model from executing `rm -rf /` (it knows the info, but nothing stops the action)
- Recover when an agent produces bad output (context does not include retry logic)
- Coordinate 20 agents in sequence with gates (context is per-agent, not per-pipeline)
- Track whether the output was useful (no feedback mechanism)
- Prevent infinite loops (the context does not include a cost counter)

**Context engineering makes the model informed. It does not make the system reliable.**

---

## Harness Engineering — Deep Dive

### What it is

The discipline of designing the infrastructure, constraints, and feedback loops that wrap around one or more AI agents to make them reliable in production. It includes: tool access control, mechanical guardrails, retry/fallback logic, observability, human-in-the-loop gates, cost management, entropy cleanup.

### Real-world examples

**Without Harness Engineering:**
```
Developer: "/squad build a notification system"

What happens:
- Agent starts writing code
- Makes an architecture decision (maybe wrong) without asking
- Writes tests after code (not TDD)
- Skips security review
- Pushes directly to main without PR
- Consumes 5M tokens ($30) with no way to stop
- No record of what happened or why
- Developer finds out hours later that the code is broken
```

**With Harness Engineering (claude-tech-squad):**
```
Developer: "/squad APP-123"

What happens:
- [Preflight] Reads ticket, detects stack, loads cost budget (4M max)
- [Gate 1] PM produces scope → user approves
- [Gate 2] PO prioritizes → user approves
- [Gate 3] Planner presents options → user selects
- [Gate 4] Architect designs → user confirms
- TDD Specialist writes failing tests FIRST
- Backend Dev implements (makes tests pass)
- Reviewer reviews → requests changes → retry (max 3)
  - [Health Check] retry detected → enriches QA context
- QA runs tests → PASS
- TechLead conformance audit → CONFORMANT
- Quality Bench (6 specialists in parallel) → 1 BLOCKING finding
  - [Gate] user decides: fix or accept as tech debt
- Docs updated
- PM UAT validates acceptance criteria → APPROVED
- [Cost: 3.2M tokens, $21, 45 minutes]
- [SEP log written with full metrics]
- [Developer feedback: 4/4]
```

Every step is visible, recoverable, and auditable.

### The 5 Pillars with real examples

**Pillar 1 — Tool Orchestration:**
```
Real example: A docs-writer agent accidentally ran `git push --force origin main`
because it had access to Bash with no restrictions.

With Harness: docs-writer's tool_allowlist is [Read, Glob, Grep, Edit, Write].
No Bash access. It literally cannot push to git.
```

**Pillar 2 — Guardrails:**
```
Real example: An agent was asked to "clean up the database" and ran DROP TABLE
on the production database.

With Harness: pre-tool-guard.sh hook intercepts the Bash call, detects the
DROP TABLE pattern, and exits with code 2 — the command never executes.
The agent sees: "BLOCKED by pre-tool-guard: Destructive SQL detected."
```

**Pillar 3 — Error Recovery:**
```
Real example: A reviewer agent keeps requesting changes. The implementation
agent "fixes" the issues but introduces new ones. After 5 cycles, nothing
is resolved and $15 in tokens have been wasted.

With Harness:
- review_cycles_max: 3 (stops after 3 cycles)
- Doom loop detection: if the diff grows each retry, the cycle stops immediately
- Fallback: reviewer → code-quality agent (different perspective)
- Health check: next agent (QA) receives context about the review struggle
- Gate: if everything fails, user decides (R/S/X)
```

**Pillar 4 — Observability:**
```
Real example: A /squad run completed but the developer has no idea which
agents ran, how long each took, or how many tokens were consumed.

With Harness:
- Live dashboard: browser tab showing all 20 teammates with live timers
- SEP log: YAML file with tokens_input, tokens_output, duration_ms per teammate
- Trace lines: [Teammate Spawned], [Teammate Done], [Health Check] in CLI
- /factory-retrospective: "reviewer agent has 40% retry rate — adjust prompt"
```

**Pillar 5 — Human-in-the-Loop:**
```
Real example: An agent auto-merged a PR to main without anyone reviewing it.
The code had a SQL injection vulnerability. It shipped to production.

With Harness:
- UAT gate: PM must approve before the run ends (mandatory, never auto-advanced)
- Release gate: SRE must sign off before deploy (mandatory)
- Auto-advance: only for non-critical gates when ALL agents return high confidence
- Escape hatch: user can jump forward but skipped phases are logged as risk
```

---

## Comparison Table — Same Task, Three Approaches

### Task: "Add password reset functionality"

**Prompt Engineering only:**
```
Prompt: "You are a senior developer. Add password reset functionality
to the Django project. Include: model, view, URL, template, email
sending, and tests. Follow the existing patterns in the codebase."

Result:
+ Code generated in one shot
+ Follows prompt instructions
- May use deprecated Django API (no doc lookup)
- No security review (CSRF? rate limiting? token expiration?)
- No TDD (tests written after code, if at all)
- No architecture review (does it fit the existing patterns?)
- Developer must read every line to verify
- No record of what was done
- If it's wrong, start over from scratch
```

**Prompt + Context Engineering:**
```
1. Read requirements.txt → detect Django 4.2
2. Context7 lookup → current password reset API
3. Read existing views.py → detect class-based views pattern
4. Read existing tests/ → detect pytest + factory_boy pattern
5. Generate code with verified APIs and project conventions

Result:
+ Code uses correct, current Django API
+ Follows project conventions (not generic)
+ Tests match existing test patterns
- Still no security review
- Still no TDD (tests may be afterthought)
- No reviewer, no QA, no conformance check
- Developer still must verify everything manually
- No cost tracking, no recovery from errors
```

**Prompt + Context + Harness Engineering (claude-tech-squad):**
```
/discovery APP-123  (ticket: "Add password reset")

Phase 1 — Discovery:
  PM: defines 5 acceptance criteria from ticket
  Architect: designs within existing Django patterns
  TechLead: assigns workstreams, identifies security-reviewer needed
  TDD Specialist: plans test-first delivery cycles

Phase 2 — Implementation:
  TDD Specialist: writes failing tests for password reset flow
  Backend Dev: implements until tests pass (verified against Context7 docs)
  Reviewer: reviews → finds missing rate limiting → requests changes
    [Health Check] retry_detected → QA will focus on rate limiting
  Backend Dev: adds rate limiting, tests pass
  Reviewer: APPROVED
  QA: runs full test suite → PASS
  TechLead: conformance audit → CONFORMANT
  Quality Bench:
    - Security Reviewer: checks CSRF, token expiration, rate limiting → PASS
    - Privacy Reviewer: checks PII in reset emails → PASS
    - Performance: checks email sending is async → INFO (suggestion)
  Docs Writer: updates API docs and operator guide
  PM UAT: validates all 5 acceptance criteria → APPROVED

Result:
+ Correct API (Context7)
+ TDD-first (tests before code)
+ Security reviewed (OWASP checks)
+ Privacy reviewed
+ Architecture conformance verified
+ All acceptance criteria validated
+ Developer made 4 decisions (gates), not 400 (line-by-line review)
+ Cost tracked: 2.1M tokens, $14
+ SEP log with full audit trail
+ Developer feedback: 4/4
```

---

## The Maturity Ladder

Most teams follow this progression:

```
Stage 1: "Just use ChatGPT/Claude"
  → Prompt Engineering only
  → Works for: one-off questions, small code snippets
  → Breaks at: multi-file changes, production code

Stage 2: "Let's give it access to our docs and codebase"
  → Prompt + Context Engineering
  → Works for: informed code generation, API-aware output
  → Breaks at: multi-step workflows, error recovery, safety

Stage 3: "Let's build a real agent system"
  → Prompt + Context + Harness Engineering
  → Works for: production autonomous agents, multi-agent pipelines
  → Breaks at: nothing yet — this is the current frontier
```

**claude-tech-squad exists at Stage 3.** It uses all three disciplines:
- Prompt Engineering: 74 carefully crafted agent prompts with role boundaries, rules, and verification protocols
- Context Engineering: Context7 documentation lookup, Progressive Disclosure digests, ticket intake from Jira/GitHub
- Harness Engineering: 5 pillars fully implemented with mechanical enforcement

---

## When to Use Which

| Situation | What you need | Example |
|---|---|---|
| "Help me write this function" | Prompt Engineering | Good system prompt + clear instructions |
| "Use the latest API, not training data" | + Context Engineering | RAG, tool use, Context7 |
| "Build this feature end-to-end safely" | + Harness Engineering | claude-tech-squad /squad |
| "Fix this bug without breaking anything" | + Harness Engineering | claude-tech-squad /bug-fix with TDD + review |
| "Run this agent unattended overnight" | Harness Engineering is mandatory | Without it, you wake up to a $200 bill and broken production |

---

## Summary

| | Prompt Engineering | Context Engineering | Harness Engineering |
|---|---|---|---|
| **Metaphor** | Writing the recipe | Stocking the kitchen | Building the restaurant |
| **Question it answers** | "How do I ask?" | "What does the model know?" | "How does the system work?" |
| **Primary risk without it** | Bad output | Outdated/wrong output | Uncontrolled agent |
| **Artifact** | Prompts | Context pipeline | Infrastructure |
| **Cost of getting it wrong** | Wasted time | Wrong code shipped | Production incident |
| **Effort to implement** | Low | Medium | High |
| **ROI** | Immediate | Session-level | System-level |

**The key insight: the model is not the product. The harness is.** OpenAI and LangChain showed in 2026 that changing the harness — keeping the same model — can move an agent from top 30 to top 5 in benchmarks. The same Claude model, with different infrastructure around it, produces dramatically different reliability.

This plugin is proof of that principle.
