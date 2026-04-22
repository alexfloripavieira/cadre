import pytest

from cadre import Policy
from cadre.errors import PolicyError


def test_default_policy_validates():
    p = Policy()
    p.validate()
    assert p.max_retries == 3


def test_from_mapping_accepts_known_fields():
    p = Policy.from_mapping(
        {"max_retries": 5, "fallback_models": ["openai/gpt-4o", "groq/llama-3.3-70b"]}
    )
    assert p.max_retries == 5
    assert p.fallback_models == ("openai/gpt-4o", "groq/llama-3.3-70b")


def test_from_mapping_rejects_unknown_field():
    with pytest.raises(PolicyError, match="unknown policy fields"):
        Policy.from_mapping({"max_retries": 2, "hallucinate_factor": 0.9})


def test_validate_rejects_zero_retries():
    with pytest.raises(PolicyError, match="max_retries"):
        Policy(max_retries=0).validate()


def test_backoff_delay_is_exponential():
    p = Policy(retry_delay_seconds=1.0, retry_backoff_multiplier=2.0)
    assert p.backoff_delay(1) == 1.0
    assert p.backoff_delay(2) == 2.0
    assert p.backoff_delay(3) == 4.0


def test_backoff_delay_zero_for_non_positive_attempt():
    p = Policy(retry_delay_seconds=1.0)
    assert p.backoff_delay(0) == 0.0
