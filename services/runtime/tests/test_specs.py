import pathlib

import pytest

from cadre import AgentRegistry, load_agent_spec, load_skill_spec
from cadre.specs import SpecError, parse_frontmatter


def test_parse_frontmatter_basic():
    text = "---\nfoo: bar\nbaz: 1\n---\n\nbody here\n"
    data, body = parse_frontmatter(text)
    assert data == {"foo": "bar", "baz": 1}
    assert body == "body here\n"


def test_parse_frontmatter_missing_delimiter_raises():
    with pytest.raises(SpecError, match="must start with '---'"):
        parse_frontmatter("no frontmatter here\n")


def test_parse_frontmatter_unterminated_raises():
    with pytest.raises(SpecError, match="closing '---'"):
        parse_frontmatter("---\nfoo: bar\nbody\n")


def test_load_agent_spec_reads_real_orchestrator(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    spec = load_agent_spec(repo_root / "plugins" / "cadre" / "agents" / "orchestrator.md")
    assert spec.name == "orchestrator"
    assert spec.role == "orchestrator"
    assert spec.authority == "executor"
    assert "run_state" in spec.body or "skill_intent" in spec.body.lower()


def test_load_agent_spec_missing_required_field(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: foo\n---\n\nbody\n")
    with pytest.raises(SpecError, match="missing fields"):
        load_agent_spec(bad)


def test_load_skill_spec_reads_real_inception(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    spec = load_skill_spec(repo_root / "plugins" / "cadre" / "skills" / "inception" / "SKILL.md")
    assert spec.name == "inception"
    assert spec.authority_level == 2
    assert "inception-author" in spec.required_agents
    assert spec.max_budget_usd == 3.0
    assert spec.max_review_cycles == 1


def test_load_skill_spec_rejects_invalid_authority_level(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text(
        "---\nname: bad\nauthority_level: 9\nintent: test\n---\n\nbody\n"
    )
    with pytest.raises(SpecError, match="authority_level must be 1, 2, or 3"):
        load_skill_spec(bad)


def test_load_skill_spec_missing_authority_level_raises(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: bad\nintent: test\n---\n\nbody\n")
    with pytest.raises(SpecError, match="authority_level"):
        load_skill_spec(bad)


def test_agent_registry_loads_all_from_plugin_dir():
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    registry = AgentRegistry(repo_root / "plugins" / "cadre" / "agents")
    agents = registry.load_all()
    names = {a.name for a in agents}
    assert {"prd-author", "inception-author", "tasks-planner", "work-item-mapper", "orchestrator"} <= names


def test_agent_registry_load_unknown_role_raises(tmp_path):
    (tmp_path / "empty").mkdir()
    registry = AgentRegistry(tmp_path / "empty")
    with pytest.raises(SpecError, match="not found"):
        registry.load("nonexistent")


def test_agent_registry_load_many(tmp_path):
    repo_root = pathlib.Path(__file__).resolve().parents[3]
    registry = AgentRegistry(repo_root / "plugins" / "cadre" / "agents")
    loaded = registry.load_many(["prd-author", "inception-author"])
    assert set(loaded.keys()) == {"prd-author", "inception-author"}
