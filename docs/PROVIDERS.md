# Provider Support

Cadre uses LiteLLM as its provider-agnostic LLM client (ADR 0002). Any
provider LiteLLM supports works in Cadre with zero code change — you set an
environment variable with the credential and reference the model via its
LiteLLM model string in your policy or runner.

## Provider cheat sheet

| Provider | Env var | Model-string prefix | Free tier? |
|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic/claude-*` | No (pay per token) |
| OpenAI | `OPENAI_API_KEY` | `openai/gpt-*` | No |
| Groq | `GROQ_API_KEY` | `groq/<model>` | Yes, 30 req/min |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter/<vendor>/<model>` | Several `:free` models |
| Google AI Studio | `GEMINI_API_KEY` | `gemini/gemini-*` | Yes (generous for flash models) |
| HuggingFace | `HF_TOKEN` | `huggingface/<repo>` | Yes (rate-limited serverless) |
| Mistral | `MISTRAL_API_KEY` | `mistral/<model>` | Limited free tier |
| Cohere | `COHERE_API_KEY` | `command-*` | Limited free tier |
| DeepSeek (direct) | `DEEPSEEK_API_KEY` | `deepseek/<model>` | No free tier |
| Z.ai (Zhipu) | `ZHIPUAI_API_KEY` | `zhipu_ai/<model>` | Limited free tier |
| Azure OpenAI | `AZURE_API_KEY` + endpoint | `azure/<deployment>` | No |
| AWS Bedrock | AWS creds | `bedrock/<model>` | No (AWS bill) |
| Vertex AI | GCP creds | `vertex_ai/<model>` | No (GCP bill) |
| Ollama (local) | none | `ollama/<model>` | Free, offline |
| vLLM / TGI (local) | none | `openai/<model>` + `api_base` | Free, offline |

LiteLLM supports 100+ providers; this is a representative subset. See the
[LiteLLM providers docs](https://docs.litellm.ai/docs/providers) for the
full list.

## Recommended defaults

For **development and CI without spending**:

- **Groq free tier** is the simplest single-provider option. Fast, good
  quality (Llama 3.3 70B), no credits to manage, 30 req/min is generous.
  `export GROQ_API_KEY=gsk_...`.
- **OpenRouter with `:free` models** gives breadth: DeepSeek V3 free,
  Llama 3.3 70B free, Gemini 2.0 Flash free, all behind one key. Use when
  you want fallback diversity for reliability testing.

For **production runs**:

- **Anthropic Claude Opus / Sonnet** direct via `anthropic/claude-*`.
- **OpenAI GPT-4.1** via `openai/gpt-4.1`.
- **Claude via OpenRouter** if you need a single billing surface across
  multiple vendors: `openrouter/anthropic/claude-sonnet-4-6`.

## Using the free-tier policy profile

`plugins/cadre/runtime-policy.yaml` ships a `free-tier` profile that chains
through three free-tier options:

```yaml
free-tier:
  max_retries: 2
  fallback_models:
    - openrouter/deepseek/deepseek-chat-v3:free
    - openrouter/meta-llama/llama-3.3-70b-instruct:free
    - gemini/gemini-2.0-flash-exp
```

To use it from Python:

```python
from cadre import PolicyLoader, Runtime
loader = PolicyLoader.from_file("plugins/cadre/runtime-policy.yaml")
policy = loader.resolve("free-tier")
runtime = Runtime()
result = runtime.call(
    agent_role="tester",
    phase="execute",
    model="groq/llama-3.3-70b-versatile",  # primary
    messages=[{"role": "user", "content": "hello"}],
    policy=policy,
)
```

Set the env vars for whichever providers are in your chain:
`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`.

## Smoke test script

`scripts/smoke-run.py` runs the `inception` skill end-to-end. Default
model: `groq/llama-3.3-70b-versatile` (requires `GROQ_API_KEY`). Override
with `CADRE_SMOKE_MODEL`:

```bash
export GROQ_API_KEY=gsk_...
python scripts/smoke-run.py

# or
export OPENROUTER_API_KEY=sk-or-...
CADRE_SMOKE_MODEL="openrouter/deepseek/deepseek-chat-v3:free" python scripts/smoke-run.py
```

## Adding a new provider

Because LiteLLM handles provider integration, adding a provider means:

1. Find its LiteLLM model-string prefix in the upstream docs.
2. Set the env var LiteLLM expects for credentials.
3. Reference the model string in your policy or runner invocation.

No Cadre code change required.
