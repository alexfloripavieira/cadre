from typing import Any, Callable, Protocol


class ProviderCallable(Protocol):
    def __call__(self, *, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any: ...


def default_provider(*, model: str, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
    try:
        import litellm
    except ImportError as exc:
        raise RuntimeError(
            "default_provider requires 'litellm' to be installed; pass a custom provider to Runtime otherwise"
        ) from exc
    return litellm.completion(model=model, messages=messages, **kwargs)


def resolve_provider(provider: Callable | None) -> Callable:
    return provider if provider is not None else default_provider
