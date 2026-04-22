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
        return {"id": f"ok-{self.calls}"}


@pytest.fixture
def no_sleep():
    return lambda _: None


@pytest.fixture
def fake_clock():
    state = {"t": 0.0}

    def tick():
        state["t"] += 0.1
        return state["t"]

    return tick


def build_runtime(tmp_path, provider, sleep=None, clock=None):
    return Runtime(
        sep_log_dir=str(tmp_path / "logs"),
        provider=provider,
        sleep=sleep or (lambda _: None),
        clock=clock or (lambda: 0.0),
    )


def test_call_succeeds_on_first_attempt(tmp_path, fake_clock):
    runtime = build_runtime(tmp_path, fake_success, clock=fake_clock)
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


def test_call_retries_then_succeeds(tmp_path, fake_clock):
    provider = FlakyProvider(failures_before_success=2)
    runtime = build_runtime(tmp_path, provider, clock=fake_clock)
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
    assert len(result.sep_log_entries) == 3
    assert [e["outcome"] for e in result.sep_log_entries] == ["error", "error", "success"]


def test_call_raises_retry_budget_exceeded(tmp_path, fake_clock):
    runtime = build_runtime(tmp_path, fake_always_fails, clock=fake_clock)
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


def test_call_writes_all_attempts_to_sep_log(tmp_path, fake_clock):
    runtime = build_runtime(tmp_path, fake_always_fails, clock=fake_clock)
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
    assert [e["attempt"] for e in entries] == [1, 2]


def test_call_applies_backoff_between_retries(tmp_path, fake_clock):
    sleeps: list[float] = []
    provider = FlakyProvider(failures_before_success=3)
    runtime = build_runtime(tmp_path, provider, sleep=sleeps.append, clock=fake_clock)
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


def test_call_autogenerates_run_id_when_omitted(tmp_path, fake_clock):
    runtime = build_runtime(tmp_path, fake_success, clock=fake_clock)
    result = runtime.call(
        agent_role="tester",
        phase="execute",
        model="test/model",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result.sep_log_entries[0]["run_id"].startswith("run-")
