import pathlib

import pytest

from cadre import (
    AgentRegistry,
    Plan,
    PlannedStep,
    PolicyLoader,
    Runtime,
    SkillRunner,
    load_skill_spec,
)
from cadre.errors import CadreError
from cadre.skill_runner import SkillRunError, required_order_planner


REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PLUGIN_DIR = REPO_ROOT / "plugins" / "cadre"


def fake_success_provider(*, model, messages, **kwargs):
    return {"id": f"ok-{model}", "model": model, "content": "agent output"}


class CountingProvider:
    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, *, model, messages, **kwargs):
        self.calls.append(model)
        return {"id": f"ok-{len(self.calls)}", "model": model}


def build_runtime(tmp_path, provider):
    return Runtime(
        sep_log_dir=str(tmp_path / "logs"),
        provider=provider,
        sleep=lambda _: None,
        clock=lambda: 0.0,
    )


def build_runner(tmp_path, provider=None, planner=required_order_planner):
    runtime = build_runtime(tmp_path, provider or fake_success_provider)
    registry = AgentRegistry(PLUGIN_DIR / "agents")
    loader = PolicyLoader.from_file(PLUGIN_DIR / "runtime-policy.yaml")
    return SkillRunner(
        runtime=runtime,
        agent_registry=registry,
        policy_loader=loader,
        planner=planner,
    )


def test_runner_executes_inception_skill_end_to_end(tmp_path):
    runner = build_runner(tmp_path)
    skill = load_skill_spec(PLUGIN_DIR / "skills" / "inception" / "SKILL.md")
    result = runner.run(skill=skill, task_input={"prd_path": "ai-docs/prd-x/prd.md"})
    assert result.status == "completed"
    assert result.skill_name == "inception"
    assert len(result.step_outcomes) == 1
    assert result.step_outcomes[0].agent_role == "inception-author"
    assert result.step_outcomes[0].status == "success"


def test_runner_rejects_level_3_skills(tmp_path):
    runner = build_runner(tmp_path)
    spec_path = tmp_path / "l3-skill.md"
    spec_path.write_text(
        "---\n"
        "name: emergent-x\n"
        "authority_level: 3\n"
        "intent: test\n"
        "required_agents:\n"
        "  - prd-author\n"
        "---\n\nbody\n"
    )
    skill = load_skill_spec(spec_path)
    with pytest.raises(SkillRunError, match="only levels 1 and 2"):
        runner.run(skill=skill)


def test_runner_calls_each_required_agent_in_order(tmp_path):
    provider = CountingProvider()
    runner = build_runner(tmp_path, provider=provider)

    spec_path = tmp_path / "multi-step.md"
    spec_path.write_text(
        "---\n"
        "name: multi\n"
        "authority_level: 2\n"
        "intent: test multi-step\n"
        "candidate_agents:\n"
        "  - prd-author\n"
        "  - inception-author\n"
        "  - tasks-planner\n"
        "required_agents:\n"
        "  - prd-author\n"
        "  - inception-author\n"
        "  - tasks-planner\n"
        "policy_profile: default\n"
        "---\n\nbody\n"
    )
    skill = load_skill_spec(spec_path)
    result = runner.run(skill=skill, run_id="multi-1")

    assert result.status == "completed"
    assert [s.agent_role for s in result.step_outcomes] == [
        "prd-author",
        "inception-author",
        "tasks-planner",
    ]
    assert len(provider.calls) == 3


def test_runner_halts_and_reports_when_agent_call_fails(tmp_path):
    call_count = {"n": 0}

    def flaky(*, model, messages, **kwargs):
        call_count["n"] += 1
        if call_count["n"] <= 10:
            raise RuntimeError("hard failure")
        return {"id": "never", "model": model}

    runner = build_runner(tmp_path, provider=flaky)

    spec_path = tmp_path / "multi-step.md"
    spec_path.write_text(
        "---\n"
        "name: multi\n"
        "authority_level: 2\n"
        "intent: test\n"
        "candidate_agents:\n"
        "  - prd-author\n"
        "  - inception-author\n"
        "required_agents:\n"
        "  - prd-author\n"
        "  - inception-author\n"
        "policy_profile: orchestrator\n"
        "---\n\nbody\n"
    )
    skill = load_skill_spec(spec_path)
    result = runner.run(skill=skill)

    assert result.status == "halted"
    assert len(result.step_outcomes) == 1
    assert result.step_outcomes[0].status == "failed"
    assert "RetryBudgetExceeded" in result.step_outcomes[0].error


def test_required_order_planner_raises_when_no_required_agents(tmp_path):
    spec_path = tmp_path / "bad.md"
    spec_path.write_text(
        "---\nname: x\nauthority_level: 2\nintent: test\ncandidate_agents: [prd-author]\n---\n\nbody\n"
    )
    skill = load_skill_spec(spec_path)
    with pytest.raises(SkillRunError, match="no required_agents"):
        required_order_planner(skill, {}, {})


def test_custom_planner_is_invoked(tmp_path):
    captured: dict = {}

    def my_planner(skill, agents, state):
        captured["skill"] = skill.name
        captured["agent_count"] = len(agents)
        return Plan(
            steps=(PlannedStep(step_id=1, agent_role="inception-author", inputs={}),),
            rationale="custom",
        )

    runner = build_runner(tmp_path, planner=my_planner)
    skill = load_skill_spec(PLUGIN_DIR / "skills" / "inception" / "SKILL.md")
    result = runner.run(skill=skill)

    assert captured["skill"] == "inception"
    assert result.plan.rationale == "custom"
    assert result.status == "completed"


def test_runner_aggregates_total_cost(tmp_path):
    def priced_provider(*, model, messages, **kwargs):
        return {"id": f"ok-{model}", "_cost": 0.10}

    runner = build_runner(tmp_path, provider=priced_provider)
    runner._runtime._cost_estimator = lambda m, r: float(r.get("_cost", 0.0))

    spec_path = tmp_path / "multi.md"
    spec_path.write_text(
        "---\n"
        "name: multi\n"
        "authority_level: 2\n"
        "intent: test\n"
        "candidate_agents: [prd-author, inception-author]\n"
        "required_agents: [prd-author, inception-author]\n"
        "policy_profile: default\n"
        "---\n\nbody\n"
    )
    skill = load_skill_spec(spec_path)
    result = runner.run(skill=skill)

    assert result.total_cost_usd == pytest.approx(0.20)
