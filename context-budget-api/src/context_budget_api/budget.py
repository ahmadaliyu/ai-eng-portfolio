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


class CannotFitError(ValueError):
    """Even after dropping everything droppable, the conversation is over budget."""


@dataclass(frozen=True)
class TrimResult:
    messages: list[Message]
    tokens: int
    budget: int
    dropped: int


def trim_to_fit(
    messages: Sequence[Message], counter: TokenCounter, context_window: int, reserve: int
) -> TrimResult:
    """Drop the oldest messages until the conversation fits.

    System messages and the last message are protected and never dropped.
    Returns a new list; the input is not modified.
    """
    budget = _budget(context_window, reserve)
    costs = [counter.count_message(m) for m in messages]
    total = sum(costs)
    last = len(messages) - 1
    protected = {i for i, m in enumerate(messages) if m.role == "system" or i == last}

    dropped: set[int] = set()
    for i in range(len(messages)):
        if total <= budget:
            break
        if i not in protected:
            dropped.add(i)
            total -= costs[i]

    if total > budget:
        raise CannotFitError(
            f"protected messages (system messages and the last message) need {total} tokens "
            f"but the budget is {budget}"
        )

    kept = [m for i, m in enumerate(messages) if i not in dropped]
    return TrimResult(messages=kept, tokens=total, budget=budget, dropped=len(dropped))
