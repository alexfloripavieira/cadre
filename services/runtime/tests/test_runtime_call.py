import pytest

from cadre import Policy, Runtime
from cadre.errors import RetryBudgetExceeded


def fake_success(*, model, messages, **kwargs):
    return {"id": "fake-1", "content": "ok", "model": model}


def fake_always_fails(*, model, messages, **kwargs):
    raise RuntimeError("boom")


class FlakyProvider:
    def __init__(self, failures_before_success: int) -> None:
        self.failures_before_success = failures_before_success
        self.calls = 0

    def __call__(self, *, model, messages, **kwargs):
        self.calls += 1
        if self.calls <= self.failures_before_success:
            raise RuntimeError(f"transient failure {self.calls}")
        return {"id": f"ok-{self.calls}", "model": model}


class PerModelProvider:
    def __init__(self, outcomes: dict[str, str]) -> None:
        self.outcomes = outcomes
        self.calls_per_model: dict[str, int] = {}

    def __call__(self, *, model, messages, **kwargs):
        self.calls_per_model[model] = self.calls_per_model.get(model, 0) + 1
        outcome = self.outcomes[model]
        if outcome == "fail":
            raise RuntimeError(f"{model} failure")
        return {"id": f"{model}-ok", "model": model}


def build_runtime(tmp_path, provider, sleep=None, clock=None):
    return Runtime(
        sep_log_dir=str(tmp_path / "logs"),
        provider=provider,
        sleep=sleep or (lambda _: None),
        clock=clock or (lambda: 0.0),
    )


def test_call_succeeds_on_first_attempt(tmp_path):
    runtime = build_runtime(tmp_path, fake_success)
    result = runtime.call(
        run_id="r1",
        agent_role="tester",
        phase="execute",
        model="test/model",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result.attempts == 1
    assert result.model_used == "test/model"
    assert not result.fell_back
    assert result.response["id"] == "fake-1"
    assert len(result.sep_log_entries) == 1
    assert result.sep_log_entries[0]["outcome"] == "success"
    assert result.sep_log_entries[0]["is_primary"] is True


def test_call_retries_then_succeeds(tmp_path):
    provider = FlakyProvider(failures_before_success=2)
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(max_retries=5, retry_delay_seconds=0.0)

    result = runtime.call(
        run_id="r2",
        agent_role="tester",
        phase="execute",
        model="test/model",
        messages=[{"role": "user", "content": "hi"}],
        policy=policy,
    )

    assert result.attempts == 3
    assert provider.calls == 3
    assert [e["outcome"] for e in result.sep_log_entries] == ["error", "error", "success"]


def test_call_raises_retry_budget_exceeded(tmp_path):
    runtime = build_runtime(tmp_path, fake_always_fails)
    policy = Policy(max_retries=3, retry_delay_seconds=0.0)

    with pytest.raises(RetryBudgetExceeded) as excinfo:
        runtime.call(
            run_id="r3",
            agent_role="tester",
            phase="execute",
            model="test/model",
            messages=[{"role": "user", "content": "hi"}],
            policy=policy,
        )

    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.last_error, RuntimeError)


def test_call_writes_all_attempts_to_sep_log(tmp_path):
    runtime = build_runtime(tmp_path, fake_always_fails)
    policy = Policy(max_retries=2, retry_delay_seconds=0.0)

    with pytest.raises(RetryBudgetExceeded):
        runtime.call(
            run_id="r4",
            agent_role="tester",
            phase="delegate",
            model="test/model",
            messages=[{"role": "user", "content": "hi"}],
            policy=policy,
        )

    entries = runtime.sep_log.read("r4")
    assert len(entries) == 2
    assert all(e["outcome"] == "error" for e in entries)
    assert all(e["phase"] == "delegate" for e in entries)


def test_call_applies_backoff_between_retries(tmp_path):
    sleeps: list[float] = []
    provider = FlakyProvider(failures_before_success=3)
    runtime = build_runtime(tmp_path, provider, sleep=sleeps.append)
    policy = Policy(max_retries=5, retry_delay_seconds=1.0, retry_backoff_multiplier=2.0)

    runtime.call(
        run_id="r5",
        agent_role="tester",
        phase="execute",
        model="test/model",
        messages=[{"role": "user", "content": "hi"}],
        policy=policy,
    )

    assert sleeps == [1.0, 2.0, 4.0]


def test_call_autogenerates_run_id_when_omitted(tmp_path):
    runtime = build_runtime(tmp_path, fake_success)
    result = runtime.call(
        agent_role="tester",
        phase="execute",
        model="test/model",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result.sep_log_entries[0]["run_id"].startswith("run-")


def test_fallback_triggers_when_primary_exhausted(tmp_path):
    provider = PerModelProvider({"primary/x": "fail", "secondary/y": "ok"})
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(max_retries=2, retry_delay_seconds=0.0, fallback_models=("secondary/y",))

    result = runtime.call(
        run_id="f1",
        agent_role="tester",
        phase="execute",
        model="primary/x",
        messages=[{"role": "user", "content": "hi"}],
        policy=policy,
    )

    assert result.fell_back is True
    assert result.model_used == "secondary/y"
    assert provider.calls_per_model == {"primary/x": 2, "secondary/y": 1}


def test_fallback_second_level_when_primary_and_first_fallback_fail(tmp_path):
    provider = PerModelProvider(
        {"primary/x": "fail", "fallback1/y": "fail", "fallback2/z": "ok"}
    )
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(
        max_retries=2,
        retry_delay_seconds=0.0,
        fallback_models=("fallback1/y", "fallback2/z"),
    )

    result = runtime.call(
        run_id="f2",
        agent_role="tester",
        phase="execute",
        model="primary/x",
        messages=[{"role": "user", "content": "hi"}],
        policy=policy,
    )

    assert result.fell_back is True
    assert result.model_used == "fallback2/z"
    assert provider.calls_per_model == {"primary/x": 2, "fallback1/y": 2, "fallback2/z": 1}


def test_fallback_exhausted_raises_retry_budget_exceeded(tmp_path):
    provider = PerModelProvider({"primary/x": "fail", "fallback1/y": "fail"})
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(max_retries=2, retry_delay_seconds=0.0, fallback_models=("fallback1/y",))

    with pytest.raises(RetryBudgetExceeded) as excinfo:
        runtime.call(
            run_id="f3",
            agent_role="tester",
            phase="execute",
            model="primary/x",
            messages=[{"role": "user", "content": "hi"}],
            policy=policy,
        )

    assert excinfo.value.attempts == 4


def test_fallback_writes_transition_entry_to_sep_log(tmp_path):
    provider = PerModelProvider({"primary/x": "fail", "fallback1/y": "ok"})
    runtime = build_runtime(tmp_path, provider)
    policy = Policy(max_retries=2, retry_delay_seconds=0.0, fallback_models=("fallback1/y",))

    runtime.call(
        run_id="f4",
        agent_role="tester",
        phase="execute",
        model="primary/x",
        messages=[{"role": "user", "content": "hi"}],
        policy=policy,
    )

    entries = runtime.sep_log.read("f4")
    fallback_entries = [e for e in entries if e.get("outcome") == "fallback_triggered"]
    assert len(fallback_entries) == 1
    assert fallback_entries[0]["model"] == "primary/x"
    assert fallback_entries[0]["next_model"] == "fallback1/y"
    assert fallback_entries[0]["reason"] == "primary_retry_budget_exhausted"
