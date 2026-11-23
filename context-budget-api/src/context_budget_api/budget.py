"""Fit and trim logic. Pure functions, no FastAPI."""

from collections.abc import Sequence
from dataclasses import dataclass

from context_budget_api.schemas import Message
from context_budget_api.tokens import TokenCounter, count_tokens


class InvalidReserveError(ValueError):
    """The output reserve leaves no room for the conversation."""


@dataclass(frozen=True)
class FitResult:
    fits: bool
    tokens: int
    budget: int
    remaining: int


def _budget(context_window: int, reserve: int) -> int:
    if reserve >= context_window:
        raise InvalidReserveError(
            f"reserve_output_tokens ({reserve}) must be less than "
            f"the context window ({context_window})"
        )
    return context_window - reserve


def check_fit(
    messages: Sequence[Message], counter: TokenCounter, context_window: int, reserve: int
) -> FitResult:
    """Does the conversation fit in context_window minus the output reserve?"""
    budget = _budget(context_window, reserve)
    tokens = count_tokens(counter, messages)
    remaining = budget - tokens
    return FitResult(fits=remaining >= 0, tokens=tokens, budget=budget, remaining=remaining)
