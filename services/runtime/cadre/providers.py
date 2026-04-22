import contextlib
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
    with contextlib.suppress(Exception):
        litellm_module.suppress_debug_info = True
    with contextlib.suppress(Exception):
        litellm_module.set_verbose = False
    for attr in ("telemetry",):
        with contextlib.suppress(Exception):
            setattr(litellm_module, attr, False)


def resolve_provider(provider: Callable | None) -> Callable:
    return provider if provider is not None else default_provider
