from collections.abc import Callable
from typing import Any, Protocol


class ProviderCallable(Protocol):
    def __call__(self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any: ...


def default_provider(*, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
    try:
        import litellm
    except ImportError as exc:
        raise RuntimeError(
            "default_provider requires 'litellm' to be installed; pass a custom provider to Runtime otherwise"
        ) from exc
    _quiet_litellm(litellm)
    return litellm.completion(model=model, messages=messages, **kwargs)


def _quiet_litellm(litellm_module: Any) -> None:
    try:
        litellm_module.suppress_debug_info = True
    except Exception:
        pass
    try:
        litellm_module.set_verbose = False
    except Exception:
        pass
    for attr in ("telemetry",):
        try:
            setattr(litellm_module, attr, False)
        except Exception:
            pass


def resolve_provider(provider: Callable | None) -> Callable:
    return provider if provider is not None else default_provider
