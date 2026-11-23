"""Model registry: model name -> context window in tokens. Pure logic, no FastAPI."""

from collections.abc import Mapping

# Source: https://platform.claude.com/docs/en/about-claude/models/overview
# (checked 2026-11-23). All four current models have a 1M-token context window.
DEFAULT_MODELS: dict[str, int] = {
    "claude-fable-5-2": 1_000_000,
    "claude-opus-5-5": 1_000_000,
    "claude-sonnet-5-5": 1_000_000,
    "claude-haiku-5-5": 1_000_000,
}


class UnknownModelError(ValueError):
    """The requested model isn't in the registry."""


def context_window(registry: Mapping[str, int], model: str) -> int:
    """Look up a model's context window, or raise UnknownModelError listing known models."""
    try:
        return registry[model]
    except KeyError:
        known = ", ".join(sorted(registry))
        raise UnknownModelError(f"Unknown model '{model}'. Known models: {known}") from None
