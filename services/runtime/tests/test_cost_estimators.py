from types import SimpleNamespace

from cadre import ModelPricing, PricedCostEstimator
from cadre.cost_estimators import _extract_usage, litellm_cost_estimator


def test_priced_estimator_computes_cost_from_dict_response():
    pricing = {
        "anthropic/claude-opus-4-7": ModelPricing(
            input_per_1k_tokens_usd=0.015,
            output_per_1k_tokens_usd=0.075,
        ),
    }
    estimator = PricedCostEstimator(pricing)
    response = {"usage": {"prompt_tokens": 1000, "completion_tokens": 500}}
    cost = estimator("anthropic/claude-opus-4-7", response)
    assert cost == round(0.015 + 0.0375, 6)


def test_priced_estimator_returns_zero_for_unknown_model():
    estimator = PricedCostEstimator({})
    assert estimator("unknown/model", {"usage": {"prompt_tokens": 100}}) == 0.0


def test_priced_estimator_returns_zero_when_usage_missing():
    pricing = {
        "m/1": ModelPricing(input_per_1k_tokens_usd=1.0, output_per_1k_tokens_usd=2.0),
    }
    estimator = PricedCostEstimator(pricing)
    assert estimator("m/1", {"no": "usage"}) == 0.0


def test_extract_usage_handles_object_response():
    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=200, completion_tokens=50, total_tokens=250)
    )
    usage = _extract_usage(response)
    assert usage == {"prompt_tokens": 200, "completion_tokens": 50, "total_tokens": 250}


def test_litellm_cost_estimator_returns_zero_when_litellm_absent(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "litellm":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert litellm_cost_estimator("any/model", {"anything": True}) == 0.0


def test_priced_estimator_computes_cost_from_object_response():
    pricing = {
        "m/1": ModelPricing(input_per_1k_tokens_usd=0.002, output_per_1k_tokens_usd=0.004),
    }
    estimator = PricedCostEstimator(pricing)
    response = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=500, completion_tokens=500))
    cost = estimator("m/1", response)
    assert cost == round(0.001 + 0.002, 6)
