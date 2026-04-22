import pytest

from cadre import Policy, Runtime
from cadre.errors import PolicyError


def provider_with_usage(prompt_tokens: int, completion_tokens: int):
    def _provider(*, model, messages, **kwargs):
        return {
            "id": "ok",
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }

    return _provider


def provider_with_total_tokens(total: int):
    def _provider(*, model, messages, **kwargs):
        return {"id": "ok", "model": model, "usage": {"total_tokens": total}}

    return _provider


def provider_without_usage():
    def _provider(*, model, messages, **kwargs):
        return {"id": "ok", "model": model}

    return _provider


class FakeUsageObject:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class FakeResponseObject:
    def __init__(self, prompt: int, completion: int) -> None:
        self.usage = FakeUsageObject(prompt, completion)


def test_tokens_accumulate_across_calls(tmp_path):
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=40, completion_tokens=10),
    )
    runtime.call(
        run_id="r1",
        agent_role="inception-author",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    runtime.call(
        run_id="r1",
        agent_role="inception-author",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    assert runtime.tokens_used("r1") == 100


def test_tokens_prefer_total_over_prompt_plus_completion(tmp_path):
    runtime = Runtime(sep_log_dir=tmp_path, provider=provider_with_total_tokens(777))
    runtime.call(
        run_id="r1",
        agent_role="inception-author",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    assert runtime.tokens_used("r1") == 777


def test_tokens_missing_usage_is_zero(tmp_path):
    runtime = Runtime(sep_log_dir=tmp_path, provider=provider_without_usage())
    runtime.call(
        run_id="r1",
        agent_role="inception-author",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    assert runtime.tokens_used("r1") == 0


def test_tokens_handle_object_style_response(tmp_path):
    def _provider(*, model, messages, **kwargs):
        return FakeResponseObject(prompt=30, completion=20)

    runtime = Runtime(sep_log_dir=tmp_path, provider=_provider)
    runtime.call(
        run_id="r1",
        agent_role="inception-author",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    assert runtime.tokens_used("r1") == 50


def test_reset_run_clears_token_counter(tmp_path):
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=10, completion_tokens=5),
    )
    runtime.call(
        run_id="r1",
        agent_role="x",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    assert runtime.tokens_used("r1") == 15
    runtime.reset_run("r1")
    assert runtime.tokens_used("r1") == 0


def test_context_advisory_event_fires_once_when_threshold_crossed(tmp_path):
    policy = Policy(
        context_advisory_threshold_tokens=100,
        context_hard_threshold_tokens=200,
    )
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=30, completion_tokens=30),
    )

    outcomes = []
    for _ in range(4):
        result = runtime.call(
            run_id="r1",
            agent_role="x",
            phase="execute",
            model="m",
            messages=[{"role": "user", "content": "x"}],
            policy=policy,
        )
        outcomes.extend(entry["outcome"] for entry in result.sep_log_entries)

    assert outcomes.count("context_advisory") == 1
    advisory_index = outcomes.index("context_advisory")
    # advisory fires on the first call where cumulative crosses 100 (after 2nd call = 120 tokens)
    assert advisory_index > 0


def test_context_hard_event_fires_once_and_suppresses_advisory(tmp_path):
    policy = Policy(
        context_advisory_threshold_tokens=50,
        context_hard_threshold_tokens=80,
    )
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=50, completion_tokens=50),
    )

    outcomes = []
    for _ in range(3):
        result = runtime.call(
            run_id="r1",
            agent_role="x",
            phase="execute",
            model="m",
            messages=[{"role": "user", "content": "x"}],
            policy=policy,
        )
        outcomes.extend(entry["outcome"] for entry in result.sep_log_entries)

    assert outcomes.count("context_rollover_suggested") == 1
    # first call emits both advisory (100 > 50) and hard (100 > 80) — but hard suppresses advisory
    # per implementation order, so advisory is never emitted when the first crossing is already hard
    assert outcomes.count("context_advisory") == 0


def test_thresholds_disabled_by_default(tmp_path):
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=1_000_000, completion_tokens=1_000_000),
    )
    result = runtime.call(
        run_id="r1",
        agent_role="x",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    outcomes = [entry["outcome"] for entry in result.sep_log_entries]
    assert "context_advisory" not in outcomes
    assert "context_rollover_suggested" not in outcomes


def test_advisory_must_be_less_than_hard():
    with pytest.raises(PolicyError):
        Policy(
            context_advisory_threshold_tokens=200,
            context_hard_threshold_tokens=100,
        ).validate()


def test_negative_thresholds_rejected():
    with pytest.raises(PolicyError):
        Policy(context_advisory_threshold_tokens=0).validate()
    with pytest.raises(PolicyError):
        Policy(context_hard_threshold_tokens=-1).validate()


def test_sep_log_success_entry_includes_token_fields(tmp_path):
    runtime = Runtime(
        sep_log_dir=tmp_path,
        provider=provider_with_usage(prompt_tokens=7, completion_tokens=3),
    )
    result = runtime.call(
        run_id="r1",
        agent_role="x",
        phase="execute",
        model="m",
        messages=[{"role": "user", "content": "x"}],
    )
    success_entry = next(e for e in result.sep_log_entries if e["outcome"] == "success")
    assert success_entry["tokens_this_attempt"] == 10
    assert success_entry["tokens_run_total"] == 10
