import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping

from .errors import CadreError
from .policy import Policy
from .policy_loader import PolicyLoader
from .runtime import CallResult, Runtime
from .specs import AgentRegistry, AgentSpec, SkillSpec


class SkillRunError(CadreError):
    pass


@dataclass(frozen=True)
class PlannedStep:
    step_id: int
    agent_role: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    success_criterion: str = ""


@dataclass(frozen=True)
class Plan:
    steps: tuple[PlannedStep, ...]
    rationale: str = ""


@dataclass(frozen=True)
class StepOutcome:
    step_id: int
    agent_role: str
    status: Literal["success", "failed"]
    call_result: CallResult | None
    error: str = ""


@dataclass(frozen=True)
class SkillRunResult:
    skill_name: str
    run_id: str
    plan: Plan
    step_outcomes: tuple[StepOutcome, ...]
    status: Literal["completed", "halted"]
    total_cost_usd: float


Planner = Callable[
    [SkillSpec, Mapping[str, AgentSpec], Mapping[str, Any]],
    Plan,
]


def required_order_planner(
    skill: SkillSpec, agents: Mapping[str, AgentSpec], state: Mapping[str, Any]
) -> Plan:
    if not skill.required_agents:
        raise SkillRunError(
            f"skill '{skill.name}' has no required_agents; required_order_planner cannot build a plan"
        )
    steps = tuple(
        PlannedStep(step_id=i + 1, agent_role=role, inputs={})
        for i, role in enumerate(skill.required_agents)
    )
    return Plan(steps=steps, rationale="required_agents in declaration order")


class SkillRunner:
    def __init__(
        self,
        *,
        runtime: Runtime,
        agent_registry: AgentRegistry,
        policy_loader: PolicyLoader | None = None,
        model_for_role: Callable[[AgentSpec], str] | None = None,
        planner: Planner = required_order_planner,
        message_builder: Callable[[SkillSpec, PlannedStep, Mapping[str, Any]], list[dict]] | None = None,
    ) -> None:
        self._runtime = runtime
        self._agents = agent_registry
        self._policy_loader = policy_loader
        self._model_for_role = model_for_role or _default_model_for_role
        self._planner = planner
        self._message_builder = message_builder or _default_message_builder

    def run(
        self,
        *,
        skill: SkillSpec,
        task_input: Mapping[str, Any] | None = None,
        run_id: str | None = None,
    ) -> SkillRunResult:
        if skill.authority_level not in (1, 2):
            raise SkillRunError(
                f"skill '{skill.name}' is authority_level {skill.authority_level}; "
                f"only levels 1 and 2 are supported in v0.1"
            )
        if not skill.required_agents and not skill.candidate_agents:
            raise SkillRunError(
                f"skill '{skill.name}' declares no required_agents or candidate_agents"
            )

        resolved_run_id = run_id or f"skill-{uuid.uuid4().hex[:12]}"
        task = dict(task_input or {})
        roster = self._load_roster(skill)
        plan = self._planner(skill, roster, task)
        policy = self._resolve_policy(skill)

        step_outcomes: list[StepOutcome] = []
        total_cost = 0.0
        halted = False

        for step in plan.steps:
            agent_spec = roster.get(step.agent_role)
            if agent_spec is None:
                step_outcomes.append(
                    StepOutcome(
                        step_id=step.step_id,
                        agent_role=step.agent_role,
                        status="failed",
                        call_result=None,
                        error=f"agent '{step.agent_role}' not in candidate_agents",
                    )
                )
                halted = True
                break

            messages = self._message_builder(skill, step, task)
            model = self._model_for_role(agent_spec)

            try:
                call_result = self._runtime.call(
                    run_id=resolved_run_id,
                    agent_role=step.agent_role,
                    phase="execute",
                    model=model,
                    messages=messages,
                    policy=policy,
                )
            except CadreError as exc:
                step_outcomes.append(
                    StepOutcome(
                        step_id=step.step_id,
                        agent_role=step.agent_role,
                        status="failed",
                        call_result=None,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                halted = True
                break

            step_outcomes.append(
                StepOutcome(
                    step_id=step.step_id,
                    agent_role=step.agent_role,
                    status="success",
                    call_result=call_result,
                )
            )
            total_cost += call_result.cost_usd
            task = _update_task_with_output(task, agent_spec, call_result)

        status: Literal["completed", "halted"] = "halted" if halted else "completed"
        return SkillRunResult(
            skill_name=skill.name,
            run_id=resolved_run_id,
            plan=plan,
            step_outcomes=tuple(step_outcomes),
            status=status,
            total_cost_usd=round(total_cost, 6),
        )

    def _load_roster(self, skill: SkillSpec) -> dict[str, AgentSpec]:
        roles = list(skill.candidate_agents) or list(skill.required_agents)
        roster: dict[str, AgentSpec] = {}
        for role in roles:
            try:
                roster[role] = self._agents.load(role)
            except CadreError as exc:
                raise SkillRunError(f"failed loading agent '{role}': {exc}") from exc
        for required in skill.required_agents:
            if required not in roster:
                try:
                    roster[required] = self._agents.load(required)
                except CadreError as exc:
                    raise SkillRunError(
                        f"failed loading required agent '{required}': {exc}"
                    ) from exc
        return roster

    def _resolve_policy(self, skill: SkillSpec) -> Policy:
        if self._policy_loader is None:
            return Policy()
        profile = skill.policy_profile or "default"
        return self._policy_loader.resolve(profile)


def _default_model_for_role(agent: AgentSpec) -> str:
    mapping = {
        "reasoning": "anthropic/claude-opus-4-7",
        "coding": "anthropic/claude-opus-4-7",
        "chat": "anthropic/claude-sonnet-4-6",
    }
    return mapping.get(agent.requires_model_class, "anthropic/claude-sonnet-4-6")


def _default_message_builder(
    skill: SkillSpec, step: PlannedStep, task: Mapping[str, Any]
) -> list[dict]:
    prompt_parts = [
        f"# Skill: {skill.name}",
        f"Intent: {skill.intent}",
        f"Current step: {step.step_id} — invoke agent role '{step.agent_role}'",
    ]
    if step.inputs:
        prompt_parts.append("Inputs:")
        for k, v in step.inputs.items():
            prompt_parts.append(f"- {k}: {v}")
    if task:
        prompt_parts.append("Task context:")
        for k, v in task.items():
            prompt_parts.append(f"- {k}: {v}")
    return [{"role": "user", "content": "\n".join(prompt_parts)}]


def _update_task_with_output(
    task: Mapping[str, Any], agent: AgentSpec, call_result: CallResult
) -> dict[str, Any]:
    updated = dict(task)
    output_key = agent.outputs_produced[0] if agent.outputs_produced else f"{agent.role}_output"
    updated[output_key] = call_result.response
    return updated
