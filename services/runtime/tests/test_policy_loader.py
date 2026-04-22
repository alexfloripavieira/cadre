import pytest

from cadre.errors import PolicyError
from cadre.policy import Policy
from cadre.policy_loader import PolicyLoader

YAML_SAMPLE = """
policies:
  default:
    max_retries: 3
    retry_delay_seconds: 1.0
    retry_backoff_multiplier: 2.0
    fallback_models: []

  with-fallback:
    max_retries: 2
    retry_delay_seconds: 0.5
    retry_backoff_multiplier: 2.0
    fallback_models:
      - openai/gpt-4.1
      - groq/llama-3.3-70b
    max_budget_usd: 3.50
    max_duration_seconds: 900
"""


def test_from_yaml_loads_profiles():
    loader = PolicyLoader.from_yaml(YAML_SAMPLE)
    assert loader.profile_names() == ["default", "with-fallback"]


def test_resolve_returns_policy_for_profile():
    loader = PolicyLoader.from_yaml(YAML_SAMPLE)
    policy = loader.resolve("with-fallback")
    assert isinstance(policy, Policy)
    assert policy.max_retries == 2
    assert policy.fallback_models == ("openai/gpt-4.1", "groq/llama-3.3-70b")
    assert policy.max_budget_usd == 3.50
    assert policy.max_duration_seconds == 900


def test_resolve_unknown_profile_raises():
    loader = PolicyLoader.from_yaml(YAML_SAMPLE)
    with pytest.raises(PolicyError, match="not found"):
        loader.resolve("nonexistent")


def test_missing_policies_section_raises():
    with pytest.raises(PolicyError, match="missing top-level 'policies'"):
        PolicyLoader.from_yaml("version: 1.0\n")


def test_unknown_field_in_profile_rejected():
    bad = """
policies:
  x:
    max_retries: 2
    hallucinate_factor: 0.9
"""
    loader = PolicyLoader.from_yaml(bad)
    with pytest.raises(PolicyError, match="unknown policy fields"):
        loader.resolve("x")


def test_from_file_reads_runtime_policy_yaml(tmp_path):
    file_path = tmp_path / "policy.yaml"
    file_path.write_text(YAML_SAMPLE)
    loader = PolicyLoader.from_file(file_path)
    assert "default" in loader.profile_names()


def test_from_file_missing_file_raises(tmp_path):
    with pytest.raises(PolicyError, match="not found"):
        PolicyLoader.from_file(tmp_path / "does-not-exist.yaml")


def test_real_runtime_policy_file_loads():
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[3]
    policy_path = repo_root / "plugins" / "cadre" / "runtime-policy.yaml"
    loader = PolicyLoader.from_file(policy_path)
    names = loader.profile_names()
    assert "default" in names
    assert "orchestrator" in names
    assert "standard-delivery" in names
    delivery = loader.resolve("standard-delivery")
    assert delivery.fallback_models == ("openai/gpt-4.1", "groq/llama-3.3-70b")
    assert delivery.max_budget_usd == 5.0
