# Safety Model

The safety model is enforced at two levels: the **Global Safety Contract** in every skill (applies to all teammates in a workflow), and **Absolute Prohibitions** in every agent with execution authority (applies to that agent individually). Neither level can be overridden by urgency, deadline, business pressure, or user instructions.

---

## Global Safety Contract

Every skill file contains a Global Safety Contract section at the top. It applies to every teammate spawned by that workflow, regardless of the agent's individual role.

The contract prohibits execution of the following without explicit written user confirmation:

| Category | Prohibited actions |
|---|---|
| **Destructive SQL** | `DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, or any destructive schema operation without a verified rollback script |
| **Cloud resource deletion** | Deleting S3 buckets, databases, clusters, queues, or any cloud resource in production |
| **Application destruction** | `tsuru app-remove`, `heroku apps:destroy`, or any equivalent command |
| **Git safety** | Merging to `main`, `master`, or `develop` without an approved pull request |
| **Git safety** | Force-pushing to any protected branch |
| **Secrets** | Removing secrets or environment variables from production |
| **Infrastructure** | Running `terraform destroy` or any equivalent IaC destruction command |
| **Auth** | Disabling or bypassing authentication or authorization as a workaround |
| **Hooks** | Skipping pre-commit hooks without explicit user authorization |
| **Code injection** | Executing dynamic code with unsanitized external input |
| **Migrations** | Applying migrations to production without first verifying a backup exists |

If any teammate determines that completing a task requires one of these actions, it must stop and surface the decision to the user before proceeding.

---

## Absolute Prohibitions (per-agent)

Agents with execution authority carry their own Absolute Prohibitions block — a role-specific list that complements the Global Safety Contract with restrictions specific to what that agent can do.

**Agents that require this block:**

| Agent | Execution authority |
|---|---|
| `backend-dev` | Writes code, runs migrations, git operations |
| `frontend-dev` | Writes code, git operations |
| `mobile-dev` | Writes code, app store operations |
| `data-engineer` | Writes pipelines, touches production data |
| `devops` | Shell execution, infrastructure management |
| `ci-cd` | Pipeline configuration, deployment triggers |
| `dba` | Schema changes, direct database access |
| `platform-dev` | Platform-level changes |
| `cloud-architect` | Cloud resource provisioning and changes |
| `release` | Git tags, release artifacts, deployment |
| `sre` | Production operations, SLO changes |
| `incident-manager` | Production coordination, rollback triggers |

**Agents that do not require this block** (analysis and review roles only):
`pm`, `business-analyst`, `po`, `planner`, `architect`, `techlead`, `reviewer`, `qa`, `security-reviewer`, `privacy-reviewer`, `compliance-reviewer`, `accessibility-reviewer`, `performance-engineer`, `code-quality`, and all other specialist reviewers.

When an execution agent encounters a task that appears to require a prohibited action, it must stop, explain the risk, and ask the user explicitly before proceeding.

---

## Additional prohibitions for LLM/AI features

The following prohibitions apply to all agents when working in repositories with LLM or AI features:

| Prohibition | Reason |
|---|---|
| Prompt injection vulnerabilities are BLOCKING — no merge until fixed | Direct and indirect injection are high-severity attack vectors |
| Tool calls with destructive actions require a human-in-the-loop gate | LLM agents must not autonomously execute destructive operations |
| PII must not be passed to LLMs or eval services without masking | Privacy and data protection requirement |
| Model version must be pinned — no floating model aliases in production | Floating aliases cause silent behavioral regressions |
| Auto-updating prompts without eval regression testing is prohibited | Prompt changes can degrade model output quality undetected |

---

## Severity policy

The runtime policy classifies all findings into three levels. Skills use this classification to decide whether to stop or continue the pipeline.

### BLOCKING

The pipeline stops immediately. The finding must be resolved before the workflow advances. A `[Gate]` trace line is emitted.

| Finding type | Examples |
|---|---|
| Security vulnerability | Auth bypass, injection flaw, exposed secret |
| PII or secret leak | API key in code, unmasked PII passed to LLM |
| Privacy violation | User data processed without consent or masking |
| Failing required tests | Any test that was passing and now fails |
| CI-breaking lint or static-analysis failure | Linting failure that would break the CI pipeline |
| WCAG A or AA failure | Accessibility requirement failure |
| Contract-breaking API or schema regression | Breaking change to a published API or schema |

### WARNING

The finding is documented in the output and SEP log but does not stop the pipeline. The user can proceed.

| Finding type | Examples |
|---|---|
| Performance regression without outage risk | Slower query, higher memory usage |
| Non-critical accessibility issue | WCAG AA best practice (not a hard failure) |
| Integration fragility | Brittle external dependency without retry logic |
| Code quality debt | Duplication, inconsistent naming, complex function |
| Operational observability gap | Missing logs or metrics for a new code path |

### INFO

Informational. Logged but not surfaced as a decision point.

| Finding type | Examples |
|---|---|
| Optional refactor | Simplification opportunity with no correctness impact |
| Style suggestion | Formatting or naming improvement |
| Documentation improvement | Missing or outdated inline comment |

---

## What "explicit written user confirmation" means

A finding that triggers a prohibition requires the user to type a direct confirmation in the conversation — not just approving a plan that implies the action, and not assuming that prior context covers it.

The agent must present:
1. What action it wants to take
2. Why it is prohibited by default
3. The specific risk if it proceeds
4. A clear question asking for confirmation

Only after the user explicitly confirms in writing does the agent proceed.

---

## Relationship between the two levels

```
Skill (Global Safety Contract)
  └── applies to all teammates in this workflow run
        │
        ├── Agent A (Absolute Prohibitions — if execution agent)
        │     └── adds role-specific restrictions on top
        │
        ├── Agent B (no Absolute Prohibitions — analysis role)
        │     └── still bound by the skill's Global Safety Contract
        │
        └── Agent C (Absolute Prohibitions — if execution agent)
              └── adds role-specific restrictions on top
```

Both levels must be satisfied. An agent with Absolute Prohibitions cannot use the Global Safety Contract as a lower bound — its own block is additive, not a replacement.
