from dataclasses import dataclass, field, fields
from typing import Any

from .errors import PolicyError


@dataclass(frozen=True)
class Policy:
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    retry_backoff_multiplier: float = 2.0
    fallback_models: tuple[str, ...] = field(default_factory=tuple)
    max_budget_usd: float | None = None
    max_duration_seconds: float | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Policy":
        if not isinstance(data, dict):
            raise PolicyError(f"policy mapping must be a dict, got {type(data).__name__}")
        valid = {f.name for f in fields(cls)}
        unknown = set(data) - valid
        if unknown:
            raise PolicyError(f"unknown policy fields: {sorted(unknown)}")
        normalized = dict(data)
        if "fallback_models" in normalized and isinstance(normalized["fallback_models"], list):
            normalized["fallback_models"] = tuple(normalized["fallback_models"])
        return cls(**normalized)

    def validate(self) -> None:
        if self.max_retries < 1:
            raise PolicyError(f"max_retries must be >= 1, got {self.max_retries}")
        if self.retry_delay_seconds < 0:
            raise PolicyError(f"retry_delay_seconds must be >= 0, got {self.retry_delay_seconds}")
        if self.retry_backoff_multiplier < 1:
            raise PolicyError(
                f"retry_backoff_multiplier must be >= 1, got {self.retry_backoff_multiplier}"
            )
        if self.max_budget_usd is not None and self.max_budget_usd <= 0:
            raise PolicyError(f"max_budget_usd must be > 0 when set, got {self.max_budget_usd}")

    def backoff_delay(self, attempt: int) -> float:
        if attempt < 1:
            return 0.0
        return self.retry_delay_seconds * (self.retry_backoff_multiplier ** (attempt - 1))
