from pathlib import Path
from typing import Any

import yaml

from .errors import PolicyError
from .policy import Policy


class PolicyLoader:
    def __init__(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise PolicyError(f"policy document root must be a mapping, got {type(data).__name__}")
        self._profiles = self._extract_profiles(data)

    @staticmethod
    def _extract_profiles(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        profiles = data.get("policies")
        if profiles is None:
            raise PolicyError("policy document is missing top-level 'policies' section")
        if not isinstance(profiles, dict):
            raise PolicyError(
                f"'policies' section must be a mapping of profile_name to fields, got {type(profiles).__name__}"
            )
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                raise PolicyError(
                    f"profile '{name}' must be a mapping, got {type(profile).__name__}"
                )
        return profiles

    @classmethod
    def from_file(cls, path: str | Path) -> "PolicyLoader":
        file_path = Path(path)
        if not file_path.exists():
            raise PolicyError(f"policy file not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as f:
            return cls(yaml.safe_load(f))

    @classmethod
    def from_yaml(cls, text: str) -> "PolicyLoader":
        return cls(yaml.safe_load(text))

    def profile_names(self) -> list[str]:
        return list(self._profiles.keys())

    def raw_profile(self, name: str) -> dict[str, Any]:
        if name not in self._profiles:
            raise PolicyError(
                f"policy profile '{name}' not found; available: {self.profile_names()}"
            )
        return dict(self._profiles[name])

    def resolve(self, name: str) -> Policy:
        raw = self.raw_profile(name)
        cleaned = {k: v for k, v in raw.items() if v is not None or k in _NULLABLE_FIELDS}
        policy = Policy.from_mapping(cleaned)
        policy.validate()
        return policy


_NULLABLE_FIELDS = {"max_budget_usd", "max_duration_seconds"}
