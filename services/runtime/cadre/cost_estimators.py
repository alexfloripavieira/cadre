from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelPricing:
    input_per_1k_tokens_usd: float
    output_per_1k_tokens_usd: float


class PricedCostEstimator:
    def __init__(self, pricing: Mapping[str, ModelPricing]) -> None:
        self._pricing = dict(pricing)

    def __call__(self, model: str, response: Any) -> float:
        if model not in self._pricing:
            return 0.0
        usage = _extract_usage(response)
        if usage is None:
            return 0.0
        rates = self._pricing[model]
        prompt = float(usage.get("prompt_tokens", 0))
        completion = float(usage.get("completion_tokens", 0))
        input_cost = (prompt / 1000.0) * rates.input_per_1k_tokens_usd
        output_cost = (completion / 1000.0) * rates.output_per_1k_tokens_usd
        return round(input_cost + output_cost, 6)


def litellm_cost_estimator(model: str, response: Any) -> float:
    try:
        import litellm
    except ImportError:
        return 0.0
    try:
        return float(litellm.completion_cost(completion_response=response))
    except Exception:
        return 0.0


def _extract_usage(response: Any) -> dict[str, Any] | None:
    if isinstance(response, dict):
        usage = response.get("usage")
        if isinstance(usage, dict):
            return usage
        return None
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage
    extracted: dict[str, Any] = {}
    for attr in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = getattr(usage, attr, None)
        if value is not None:
            extracted[attr] = value
    return extracted or None
