from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import CadreError


class SpecError(CadreError):
    pass


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    authority: str
    inputs_required: tuple[str, ...] = field(default_factory=tuple)
    inputs_optional: tuple[str, ...] = field(default_factory=tuple)
    outputs_produced: tuple[str, ...] = field(default_factory=tuple)
    invoke_when: tuple[str, ...] = field(default_factory=tuple)
    avoid_when: tuple[str, ...] = field(default_factory=tuple)
    cost_profile: str = "medium"
    typical_duration_seconds: int = 60
    requires_model_class: str = "chat"
    policy_profile: str = "default"
    description: str = ""
    body: str = ""


@dataclass(frozen=True)
class SkillSpec:
    name: str
    authority_level: int
    intent: str
    preconditions: tuple[str, ...] = field(default_factory=tuple)
    success_criteria: tuple[str, ...] = field(default_factory=tuple)
    candidate_agents: tuple[str, ...] = field(default_factory=tuple)
    required_agents: tuple[str, ...] = field(default_factory=tuple)
    policy_profile: str = "default"
    max_budget_usd: float | None = None
    max_duration_seconds: float | None = None
    max_review_cycles: int = 0
    description: str = ""
    body: str = ""


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        raise SpecError("document must start with '---' frontmatter delimiter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SpecError("document missing closing '---' frontmatter delimiter")
    _, raw_frontmatter, body = parts
    data = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(data, dict):
        raise SpecError(
            f"frontmatter must be a mapping, got {type(data).__name__}"
        )
    return data, body.lstrip()


def load_agent_spec(path: str | Path) -> AgentSpec:
    file_path = Path(path)
    if not file_path.exists():
        raise SpecError(f"agent spec not found: {file_path}")
    data, body = parse_frontmatter(file_path.read_text(encoding="utf-8"))
    required_fields = ("name", "role", "authority")
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise SpecError(f"agent spec {file_path.name} missing fields: {missing}")
    return AgentSpec(
        name=data["name"],
        role=data["role"],
        authority=data["authority"],
        inputs_required=tuple(data.get("inputs_required") or ()),
        inputs_optional=tuple(data.get("inputs_optional") or ()),
        outputs_produced=tuple(data.get("outputs_produced") or ()),
        invoke_when=tuple(data.get("invoke_when") or ()),
        avoid_when=tuple(data.get("avoid_when") or ()),
        cost_profile=data.get("cost_profile", "medium"),
        typical_duration_seconds=int(data.get("typical_duration_seconds", 60)),
        requires_model_class=data.get("requires_model_class", "chat"),
        policy_profile=data.get("policy_profile", "default"),
        description=data.get("description", ""),
        body=body,
    )


def load_skill_spec(path: str | Path) -> SkillSpec:
    file_path = Path(path)
    if not file_path.exists():
        raise SpecError(f"skill spec not found: {file_path}")
    data, body = parse_frontmatter(file_path.read_text(encoding="utf-8"))
    if "name" not in data:
        raise SpecError(f"skill spec {file_path.name} missing 'name' field")
    if "authority_level" not in data:
        raise SpecError(
            f"skill spec {file_path.name} missing 'authority_level' field (required per ADR 0004)"
        )
    level = int(data["authority_level"])
    if level not in (1, 2, 3):
        raise SpecError(f"authority_level must be 1, 2, or 3; got {level}")
    return SkillSpec(
        name=data["name"],
        authority_level=level,
        intent=data.get("intent", ""),
        preconditions=tuple(data.get("preconditions") or ()),
        success_criteria=tuple(data.get("success_criteria") or ()),
        candidate_agents=tuple(data.get("candidate_agents") or ()),
        required_agents=tuple(data.get("required_agents") or ()),
        policy_profile=data.get("policy_profile", "default"),
        max_budget_usd=_optional_float(data.get("max_budget_usd")),
        max_duration_seconds=_optional_float(data.get("max_duration_seconds")),
        max_review_cycles=int(data.get("max_review_cycles", 0)),
        description=data.get("description", ""),
        body=body,
    )


class AgentRegistry:
    def __init__(self, agents_dir: str | Path) -> None:
        self._agents_dir = Path(agents_dir)

    @property
    def agents_dir(self) -> Path:
        return self._agents_dir

    def load(self, role_or_name: str) -> AgentSpec:
        candidates = [
            self._agents_dir / f"{role_or_name}.md",
        ]
        for path in candidates:
            if path.exists():
                return load_agent_spec(path)
        raise SpecError(f"agent '{role_or_name}' not found in {self._agents_dir}")

    def load_many(self, roles: list[str]) -> dict[str, AgentSpec]:
        return {role: self.load(role) for role in roles}

    def load_all(self) -> list[AgentSpec]:
        if not self._agents_dir.exists():
            return []
        return [load_agent_spec(p) for p in sorted(self._agents_dir.glob("*.md"))]


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
