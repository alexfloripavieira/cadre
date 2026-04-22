"""Smoke test script for Cadre.

Runs the inception skill end-to-end using a real LLM provider, writes the
SEP log to disk, and prints a summary.

Provider is chosen via the CADRE_SMOKE_MODEL env var. Defaults to a free
Groq Llama model. Any LiteLLM-supported model string works.

Examples:
    export GROQ_API_KEY=gsk_...
    python scripts/smoke-run.py

    export OPENROUTER_API_KEY=sk-or-...
    export CADRE_SMOKE_MODEL="openrouter/deepseek/deepseek-chat-v3:free"
    python scripts/smoke-run.py

    export ANTHROPIC_API_KEY=sk-ant-...
    export CADRE_SMOKE_MODEL="anthropic/claude-sonnet-4-6"
    python scripts/smoke-run.py

    export GEMINI_API_KEY=...
    export CADRE_SMOKE_MODEL="gemini/gemini-2.0-flash-exp"
    python scripts/smoke-run.py

    export HF_TOKEN=hf_...
    export CADRE_SMOKE_MODEL="huggingface/meta-llama/Llama-3.3-70B-Instruct"
    python scripts/smoke-run.py
"""

import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "services" / "runtime"
PLUGIN_ROOT = REPO_ROOT / "plugins" / "cadre"

sys.path.insert(0, str(RUNTIME_ROOT))

from cadre import (  # noqa: E402
    AgentRegistry,
    PolicyLoader,
    Runtime,
    SkillRunner,
    litellm_cost_estimator,
    load_skill_spec,
)


DEFAULT_MODEL = os.environ.get("CADRE_SMOKE_MODEL", "groq/llama-3.3-70b-versatile")
SEP_LOG_DIR = REPO_ROOT / "ai-docs" / ".cadre-log"


def build_runner() -> SkillRunner:
    runtime = Runtime(
        sep_log_dir=str(SEP_LOG_DIR),
        cost_estimator=litellm_cost_estimator,
    )
    return SkillRunner(
        runtime=runtime,
        agent_registry=AgentRegistry(PLUGIN_ROOT / "agents"),
        policy_loader=PolicyLoader.from_file(PLUGIN_ROOT / "runtime-policy.yaml"),
        model_for_role=lambda agent: DEFAULT_MODEL,
    )


def main() -> int:
    print(f"cadre smoke run — model: {DEFAULT_MODEL}")
    print(f"sep log: {SEP_LOG_DIR}")
    print()

    runner = build_runner()
    skill = load_skill_spec(PLUGIN_ROOT / "skills" / "inception" / "SKILL.md")

    task_input = {
        "prd_summary": (
            "Add a /ping endpoint to the existing API that returns "
            "{\"status\": \"ok\", \"timestamp\": \"<iso8601>\"} with 200 "
            "within 50ms p95. Used by external uptime monitors."
        ),
        "expected_inputs": "HTTP GET /ping, no auth, no body.",
        "expected_outputs": "JSON payload with status and timestamp.",
    }

    try:
        result = runner.run(skill=skill, task_input=task_input, run_id="smoke-001")
    except Exception as exc:
        print(f"RUN FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f"status:          {result.status}")
    print(f"skill:           {result.skill_name}")
    print(f"run_id:          {result.run_id}")
    print(f"steps executed:  {len(result.step_outcomes)}")
    print(f"total cost USD:  ${result.total_cost_usd}")
    print()
    for outcome in result.step_outcomes:
        print(f"  step {outcome.step_id} — {outcome.agent_role} — {outcome.status}")
        if outcome.call_result:
            r = outcome.call_result
            print(f"    model: {r.model_used}  attempts: {r.attempts}  "
                  f"fell_back: {r.fell_back}  duration: {r.duration_seconds}s")
            content = _extract_response_content(r.response)
            if content:
                preview = content.strip()[:400]
                ellipsis = "..." if len(content) > 400 else ""
                print(f"    response preview: {preview}{ellipsis}")
        if outcome.error:
            print(f"    error: {outcome.error}")
    print()
    print(f"SEP log file: {SEP_LOG_DIR / (result.run_id + '.log.yaml')}")
    return 0 if result.status == "completed" else 2


def _extract_response_content(response) -> str:
    try:
        if hasattr(response, "choices") and response.choices:
            msg = response.choices[0].message
            return msg.content if hasattr(msg, "content") else str(msg)
        if isinstance(response, dict):
            choices = response.get("choices")
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return response.get("content", "")
    except Exception:
        return ""
    return str(response)[:400]


if __name__ == "__main__":
    sys.exit(main())
