# Cadre Python API Reference

Reference for embedding Cadre in your own Python code. For install, see
`docs/GETTING-STARTED.md`. For concepts, see `docs/ARCHITECTURE.md` and
`docs/MANUAL.md`.

The public API is exported from the top-level `cadre` package:

```python
from cadre import (
    Runtime,
    CallResult,
    Policy,
    PolicyLoader,
    SEPLogger,
    CheckpointStore,
    SkillRunner,
    SkillRunResult,
    Plan,
    PlannedStep,
    StepOutcome,
    AgentRegistry,
    AgentSpec,
    SkillSpec,
    ModelPricing,
    PricedCostEstimator,
    litellm_cost_estimator,
    load_agent_spec,
    load_skill_spec,
    required_order_planner,
    errors,
)
```

---

## `cadre.Runtime`

The reliability wrapper. One `Runtime` instance serves many runs; state
per `run_id` is held in memory (budget ledger, step counter) and on disk
(SEP log, optional checkpoint store).

### Constructor

```python
Runtime(
    *,
    sep_log_dir: str | Path = ".cadre-log",
    provider: Callable | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    cost_estimator: Callable[[str, Any], float] | None = None,
    checkpoint_store: CheckpointStore | None = None,
)
```

- `sep_log_dir` — where `<run_id>.log.yaml` files land. Created if missing.
- `provider` — a `ProviderCallable`. Default uses LiteLLM; pass a fake for tests.
- `sleep`, `clock` — injectable for deterministic tests.
- `cost_estimator` — `(model, response) -> float`. Default returns 0.0.
  Use `litellm_cost_estimator` or `PricedCostEstimator` for real numbers.
- `checkpoint_store` — optional; if passed, writes one checkpoint per
  successful call.

### `Runtime.call(...)`

```python
runtime.call(
    *,
    run_id: str | None = None,
    agent_role: str,
    phase: Literal["plan", "execute", "delegate", "review", "decide"],
    model: str,
    messages: list[dict],
    policy: Policy | None = None,
) -> CallResult
```

Iterates primary + fallback models, enforces retries with backoff,
detects doom loops, enforces cost ceiling, writes SEP log per attempt,
writes checkpoint on success.

Raises:
- `RetryBudgetExceeded` when full chain exhausted without success.
- `DoomLoopDetected` when final model hits doom loop.
- `CostCeilingExceeded` when budget breached before an attempt.
- `PolicyError` when policy validation fails.

### Other methods

```python
runtime.sep_log              # SEPLogger instance
runtime.checkpoint_store     # CheckpointStore or None
runtime.budget_used(run_id)  # -> float
runtime.reset_run(run_id)    # clears budget + step counter
```

### Example

```python
from cadre import Runtime, Policy

runtime = Runtime(sep_log_dir="ai-docs/.cadre-log")
policy = Policy(
    max_retries=3,
    fallback_models=("groq/llama-3.3-70b-versatile",),
    max_budget_usd=1.0,
    doom_loop_same_error_threshold=3,
)

result = runtime.call(
    run_id="my-run",
    agent_role="prd-author",
    phase="execute",
    model="anthropic/claude-sonnet-4-6",
    messages=[{"role": "user", "content": "draft a PRD for a /ping endpoint"}],
    policy=policy,
)

print(result.model_used, result.attempts, result.fell_back, result.cost_usd)
```

---

## `cadre.CallResult`

Returned by `Runtime.call`. Frozen dataclass.

```python
CallResult(
    response: Any,                   # the provider's raw response
    model_used: str,                 # which model actually served it
    attempts: int,                   # total attempts including fallbacks
    fell_back: bool,                 # did we use a non-primary model?
    duration_seconds: float,
    sep_log_entries: tuple[dict, ...],
    cost_usd: float,
)
```

---

## `cadre.Policy`

Frozen dataclass describing retry budget, fallback chain, budgets, and
doom-loop threshold.

```python
Policy(
    max_retries: int = 3,
    retry_delay_seconds: float = 1.0,
    retry_backoff_multiplier: float = 2.0,
    fallback_models: tuple[str, ...] = (),
    max_budget_usd: float | None = None,
    max_duration_seconds: float | None = None,
    doom_loop_same_error_threshold: int = 0,  # 0 disables; >=2 enables
)
```

Methods:

- `Policy.from_mapping(data: dict) -> Policy`
- `policy.validate() -> None` (raises `PolicyError` on invalid config)
- `policy.backoff_delay(attempt: int) -> float`

---

## `cadre.PolicyLoader`

Loads a YAML document with a `policies:` section and returns `Policy`
instances by name.

```python
PolicyLoader.from_file(path) -> PolicyLoader
PolicyLoader.from_yaml(text: str) -> PolicyLoader

loader.profile_names() -> list[str]
loader.raw_profile(name: str) -> dict
loader.resolve(name: str) -> Policy
```

### Example

```python
from cadre import PolicyLoader

loader = PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml")
policy = loader.resolve("standard-delivery")
```

---

## `cadre.SEPLogger`

YAML-frontmatter audit log writer.

```python
SEPLogger(log_dir: str | Path)

logger.log_path(run_id: str) -> Path
logger.write(run_id: str, entry: dict) -> dict  # returns enriched entry
logger.read(run_id: str) -> list[dict]
```

Entries are one YAML document each, preceded by `---`. Every written
entry includes `timestamp` (ISO8601 UTC) and `run_id`.

---

## `cadre.CheckpointStore`

SQLite-backed run state.

```python
CheckpointStore(db_path: str | Path)

store.save(run_id, step_id, label, data: dict) -> None
store.latest(run_id) -> dict | None
store.all(run_id) -> list[dict]
store.clear(run_id) -> int   # rowcount deleted
```

Checkpoint rows: `{run_id, step_id, label, data, created_at}`. `data`
is a dict (serialized as JSON internally).

---

## `cadre.SkillRunner`

Executes a skill end-to-end.

```python
SkillRunner(
    *,
    runtime: Runtime,
    agent_registry: AgentRegistry,
    policy_loader: PolicyLoader | None = None,
    model_for_role: Callable[[AgentSpec], str] | None = None,
    planner: Planner = required_order_planner,
    message_builder: Callable | None = None,
)

runner.run(
    *,
    skill: SkillSpec,
    task_input: dict | None = None,
    run_id: str | None = None,
) -> SkillRunResult
```

The `planner` signature:

```python
Planner = Callable[
    [SkillSpec, Mapping[str, AgentSpec], Mapping[str, Any]],
    Plan,
]
```

### `SkillRunResult`

```python
SkillRunResult(
    skill_name: str,
    run_id: str,
    plan: Plan,
    step_outcomes: tuple[StepOutcome, ...],
    status: Literal["completed", "halted"],
    total_cost_usd: float,
)
```

### `StepOutcome`

```python
StepOutcome(
    step_id: int,
    agent_role: str,
    status: Literal["success", "failed"],
    call_result: CallResult | None,
    error: str = "",
)
```

### `Plan` and `PlannedStep`

```python
PlannedStep(
    step_id: int,
    agent_role: str,
    inputs: Mapping = {},
    success_criterion: str = "",
)

Plan(
    steps: tuple[PlannedStep, ...],
    rationale: str = "",
)
```

### Example

```python
from cadre import (
    AgentRegistry, PolicyLoader, Runtime, SkillRunner, load_skill_spec
)

runtime = Runtime(sep_log_dir="ai-docs/.cadre-log")
runner = SkillRunner(
    runtime=runtime,
    agent_registry=AgentRegistry("plugins/cadre/agents"),
    policy_loader=PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml"),
)

skill = load_skill_spec("plugins/cadre/skills/inception/SKILL.md")
result = runner.run(skill=skill, task_input={"prd_path": "ai-docs/prd-x/prd.md"})

assert result.status == "completed"
for outcome in result.step_outcomes:
    print(outcome.step_id, outcome.agent_role, outcome.status)
```

---

## `cadre.AgentRegistry`

Loads agent spec cards from a directory.

```python
AgentRegistry(agents_dir: str | Path)

registry.load(role_or_name: str) -> AgentSpec
registry.load_many(roles: list[str]) -> dict[str, AgentSpec]
registry.load_all() -> list[AgentSpec]
```

---

## `cadre.AgentSpec` and `cadre.SkillSpec`

Frozen dataclasses backing the spec cards. See `docs/MANUAL.md` for the
frontmatter schema each one reflects.

Parse from file:

```python
from cadre import load_agent_spec, load_skill_spec

agent = load_agent_spec("plugins/cadre/agents/code-reviewer.md")
skill = load_skill_spec("plugins/cadre/skills/review/SKILL.md")
```

---

## Cost estimators

```python
from cadre import ModelPricing, PricedCostEstimator, litellm_cost_estimator
```

### `litellm_cost_estimator`

```python
runtime = Runtime(cost_estimator=litellm_cost_estimator)
```

Delegates to `litellm.completion_cost()`. Returns 0.0 on error or when
LiteLLM is not installed.

### `PricedCostEstimator`

Deterministic cost computation from an explicit pricing table. Useful
for CI.

```python
pricing = {
    "anthropic/claude-sonnet-4-6": ModelPricing(
        input_per_1k_tokens_usd=0.003,
        output_per_1k_tokens_usd=0.015,
    ),
    "groq/llama-3.3-70b-versatile": ModelPricing(
        input_per_1k_tokens_usd=0.0,
        output_per_1k_tokens_usd=0.0,
    ),
}
runtime = Runtime(cost_estimator=PricedCostEstimator(pricing))
```

---

## Errors (`cadre.errors`)

```python
from cadre.errors import (
    CadreError,                  # base
    PolicyError,
    RetryBudgetExceeded,         # .attempts, .last_error
    ProviderCallError,
    CostCeilingExceeded,         # .run_id, .budget_used_usd, .max_budget_usd
    DoomLoopDetected,            # .model, .error_signature, .occurrences
)
```

All inherit from `CadreError`. Catch the base class to handle any Cadre
runtime failure uniformly:

```python
from cadre.errors import CadreError

try:
    runtime.call(...)
except CadreError as exc:
    log.warning("cadre call failed: %s", exc)
```

---

## Spec errors (`cadre.specs`)

```python
from cadre.specs import SpecError, parse_frontmatter
```

Raised by `load_agent_spec`, `load_skill_spec`, and the `AgentRegistry`
methods when a file is missing, frontmatter is invalid, or required
fields are absent.

---

## Providers

```python
from cadre.providers import default_provider, resolve_provider
```

The provider callable contract:

```python
class ProviderCallable(Protocol):
    def __call__(
        self, *, model: str, messages: list[dict], **kwargs: Any
    ) -> Any: ...
```

Default is a LiteLLM wrapper. To inject a test fake, pass any callable
matching that signature to `Runtime(provider=...)`.

---

## Stability

Cadre is pre-1.0. The surface documented here is the intended shape but
may shift across 0.x versions. After v1.0, this API is covered by
semver. Expect renames and small signature changes until then; major
runtime primitives (retry, fallback, SEP log, checkpoint) are stable in
behavior but may grow new optional parameters.
