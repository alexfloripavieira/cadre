import pytest

from cadre import CheckpointStore, Policy, Runtime
from cadre.errors import (
    CostCeilingExceeded,
    DoomLoopDetected,
    PolicyError,
    RetryBudgetExceeded,
)


def fake_success_with_cost(cost_per_call: float):
    def _provider(*, model, messages, **kwargs):
        return {"id": "ok", "model": model, "_cost_usd": cost_per_call}

    return _provider


def identity_cost_estimator(model, response):
    return float(response.get("_cost_usd", 0.0))


def fake_always_fails_same(*, model, messages, **kwargs):
    raise ValueError("identical boom")


class AlternatingError:
    def __init__(self):
        self.n = 0

    def __call__(self, *, model, messages, **kwargs):
        self.n += 1
        if self.n % 2 == 1:
            raise ValueError("odd boom")
        raise RuntimeError("even boom")


def build_runtime(tmp_path, provider, **kwargs):
    defaults = dict(
        sep_log_dir=str(tmp_path / "logs"),
        provider=provider,
        sleep=lambda _: None,
        clock=lambda: 0.0,
    )
    defaults.update(kwargs)
    return Runtime(**defaults)


def test_cost_accumulates_across_calls_under_same_run_id(tmp_path):
    runtime = build_runtime(
        tmp_path,
        fake_success_with_cost(0.10),
        cost_estimator=identity_cost_estimator,
    )
    policy = Policy(max_retries=3, retry_delay_seconds=0.0, max_budget_usd=1.00)

    for _ in range(3):
        runtime.call(
            run_id="budget-1",
            agent_role="tester",
            phase="execute",
            model="m/1",
            messages=[{"role": "user", "content": "hi"}],
            policy=policy,
        )

    assert runtime.budget_used("budget-1") == pytest.approx(0.30)


def test_cost_ceiling_halts_further_calls_when_exceeded(tmp_path):
    runtime = build_runtime(
        tmp_path,
        fake_success_with_cost(0.40),
        cost_estimator=identity_cost_estimator,
    )
    policy = Policy(max_retries=3, retry_delay_seconds=0.0, max_budget_usd=1.00)

    runtime.call(
        run_id="budget-2",
        agent_role="tester",
        phase="execute",
        model="m/1",
        messages=[],
        policy=policy,
    )
    runtime.call(
        run_id="budget-2",
        agent_role="tester",
        phase="execute",
        model="m/1",
        messages=[],
        policy=policy,
    )
    runtime.call(
        run_id="budget-2",
        agent_role="tester",
        phase="execute",
        model="m/1",
        messages=[],
        policy=policy,
    )

    with pytest.raises(CostCeilingExceeded) as excinfo:
        runtime.call(
            run_id="budget-2",
            agent_role="tester",
            phase="execute",
            model="m/1",
            messages=[],
            policy=policy,
        )
    assert excinfo.value.run_id == "budget-2"
    assert excinfo.value.max_budget_usd == 1.00
    assert excinfo.value.budget_used_usd == pytest.approx(1.20)


def test_reset_run_clears_budget_ledger(tmp_path):
    runtime = build_runtime(
        tmp_path,
        fake_success_with_cost(0.50),
        cost_estimator=identity_cost_estimator,
    )
    policy = Policy(max_retries=3, retry_delay_seconds=0.0, max_budget_usd=1.00)
    runtime.call(
        run_id="budget-3",
        agent_role="tester",
        phase="execute",
        model="m/1",
        messages=[],
        policy=policy,
    )
    assert runtime.budget_used("budget-3") == pytest.approx(0.50)
    runtime.reset_run("budget-3")
    assert runtime.budget_used("budget-3") == 0.0


def test_doom_loop_detection_halts_retries_on_same_model(tmp_path):
    runtime = build_runtime(tmp_path, fake_always_fails_same)
    policy = Policy(
        max_retries=5,
        retry_delay_seconds=0.0,
        doom_loop_same_error_threshold=3,
    )

    with pytest.raises(DoomLoopDetected) as excinfo:
        runtime.call(
            run_id="doom-1",
            agent_role="tester",
            phase="execute",
            model="m/1",
            messages=[],
            policy=policy,
        )

    assert excinfo.value.model == "m/1"
    assert excinfo.value.occurrences == 3
    assert excinfo.value.error_signature[0] == "ValueError"


def test_doom_loop_advances_to_fallback_when_available(tmp_path):
    call_count = {"n": 0}

    def provider(*, model, messages, **kwargs):
        call_count["n"] += 1
        if model == "primary/x":
            raise ValueError("identical boom")
        return {"id": "fallback-ok", "model": model}

    runtime = build_runtime(tmp_path, provider)
    policy = Policy(
        max_retries=5,
        retry_delay_seconds=0.0,
        fallback_models=("fallback/y",),
        doom_loop_same_error_threshold=3,
    )

    result = runtime.call(
        run_id="doom-2",
        agent_role="tester",
        phase="execute",
        model="primary/x",
        messages=[],
        policy=policy,
    )

    assert result.fell_back is True
    assert result.model_used == "fallback/y"
    entries = runtime.sep_log.read("doom-2")
    doom_triggers = [e for e in entries if e["outcome"] == "doom_loop_triggered"]
    fallback_triggers = [e for e in entries if e["outcome"] == "fallback_triggered"]
    assert len(doom_triggers) == 1
    assert len(fallback_triggers) == 1
    assert fallback_triggers[0]["reason"] == "doom_loop_on_model"


def test_doom_loop_ignores_alternating_errors(tmp_path):
    provider = AlternatingError()
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(
        max_retries=4,
        retry_delay_seconds=0.0,
        doom_loop_same_error_threshold=3,
    )

    with pytest.raises(RetryBudgetExceeded):
        runtime.call(
            run_id="doom-3",
            agent_role="tester",
            phase="execute",
            model="m/1",
            messages=[],
            policy=policy,
        )

    entries = runtime.sep_log.read("doom-3")
    assert all(e["outcome"] != "doom_loop_triggered" for e in entries)


def test_policy_rejects_threshold_of_one():
    with pytest.raises(PolicyError, match="meaningless"):
        Policy(doom_loop_same_error_threshold=1).validate()


def test_runtime_writes_checkpoint_on_each_success(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.db")
    runtime = build_runtime(tmp_path, fake_success_with_cost(0.01), checkpoint_store=store)
    policy = Policy(max_retries=3, retry_delay_seconds=0.0)

    runtime.call(run_id="cp-1", agent_role="a", phase="plan", model="m/1", messages=[], policy=policy)
    runtime.call(run_id="cp-1", agent_role="b", phase="execute", model="m/1", messages=[], policy=policy)

    checkpoints = store.all("cp-1")
    assert [c["step_id"] for c in checkpoints] == [1, 2]
    assert [c["label"] for c in checkpoints] == ["call_success", "call_success"]
    assert checkpoints[0]["data"]["phase"] == "plan"
    assert checkpoints[1]["data"]["phase"] == "execute"


def test_runtime_does_not_write_checkpoint_when_store_absent(tmp_path):
    runtime = build_runtime(tmp_path, fake_success_with_cost(0.01))
    runtime.call(
        run_id="cp-2",
        agent_role="a",
        phase="plan",
        model="m/1",
        messages=[],
        policy=Policy(retry_delay_seconds=0.0),
    )
    assert runtime.checkpoint_store is None


def test_runtime_does_not_write_checkpoint_on_failure(tmp_path):
    store = CheckpointStore(tmp_path / "checkpoints.db")

    def always_fails(*, model, messages, **kwargs):
        raise RuntimeError("boom")

    runtime = build_runtime(tmp_path, always_fails, checkpoint_store=store)
    with pytest.raises(RetryBudgetExceeded):
        runtime.call(
            run_id="cp-3",
            agent_role="a",
            phase="plan",
            model="m/1",
            messages=[],
            policy=Policy(max_retries=2, retry_delay_seconds=0.0),
        )
    assert store.all("cp-3") == []


def test_cost_usd_reflected_in_call_result(tmp_path):
    runtime = build_runtime(
        tmp_path,
        fake_success_with_cost(0.25),
        cost_estimator=identity_cost_estimator,
    )
    result = runtime.call(
        run_id="cost-1",
        agent_role="a",
        phase="plan",
        model="m/1",
        messages=[],
        policy=Policy(retry_delay_seconds=0.0),
    )
    assert result.cost_usd == 0.25
    assert result.sep_log_entries[-1]["cost_usd"] == 0.25
    assert result.sep_log_entries[-1]["run_budget_used_usd"] == 0.25
