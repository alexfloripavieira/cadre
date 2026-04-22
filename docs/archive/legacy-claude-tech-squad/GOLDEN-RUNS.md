# Golden Runs

Golden runs are real Claude executions captured against controlled scenarios. They are the highest-signal proof that `claude-tech-squad` still behaves correctly after orchestration changes.

## Why This Exists

Static validation proves structure.
Golden runs prove behavior.

Use golden runs whenever you change:

- orchestration rules
- retry or fallback logic
- checkpoint/resume logic
- architecture routing
- release or incident behavior

## Scenarios

The source of truth is [scenarios.json](/home/alex/claude-tech-squad/fixtures/dogfooding/scenarios.json).

Current scenarios:

- `layered-monolith`
- `hexagonal-billing`
- `hotfix-checkout`

## Artifact Contract

For each scenario, store one run under:

```text
ai-docs/dogfood-runs/<scenario-id>/<timestamp>/
```

Required files:

- `prompt.txt`
- `trace.md`
- `final.md`
- `metadata.yaml`
- `scorecard.md`

## Metadata Contract

`metadata.yaml` must contain:

```yaml
scenario_id: layered-monolith
workflow: discovery
execution_mode: inline | tmux
timestamp: 2026-04-02T12:00:00Z
operator: your-name
score: pass | fail
notes: "short summary"
```

## How To Run

1. Scaffold the run directory:

```bash
bash scripts/start-golden-run.sh <scenario-id> <operator>
```

2. Print the prompt pack:

```bash
bash scripts/dogfood.sh --print-prompts
```

3. Open Claude inside the fixture repository.
4. Run the scenario prompt.
5. Paste the visible trace and final answer into the scaffolded files under `ai-docs/dogfood-runs/<scenario-id>/<timestamp>/`.
6. Fill `metadata.yaml` and `scorecard.md`.
7. Validate:

```bash
bash scripts/dogfood-report.sh
```

## Schema Check Only

When you want to validate the contract without requiring real runs:

```bash
bash scripts/dogfood-report.sh --schema-only
```

## Scorecard Guidance

Use the template at [golden-run-scorecard.md](/home/alex/claude-tech-squad/templates/golden-run-scorecard.md).

At minimum score:

- preflight visibility
- architecture style correctness
- expected agents present
- forbidden agents absent
- retries/fallbacks clearly explained
- `result_contract` evidence present

## Release Guidance

For Class C and D changes in the engineering operating system:

- update or review golden run expectations
- run at least one real golden run for every affected scenario family
- do not treat static smoke tests as a substitute
