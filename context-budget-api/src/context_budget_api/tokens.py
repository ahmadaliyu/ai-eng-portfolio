"""Token estimates. Pure logic, no FastAPI."""

import math
from collections.abc import Sequence
from typing import Protocol

from context_budget_api.schemas import Message

MESSAGE_OVERHEAD = 4
"""Fixed tokens per message for role and formatting."""


class TokenCounter(Protocol):
    """Anything that can estimate the tokens in one message."""

    def count_message(self, message: Message) -> int: ...


class HeuristicCounter:
    """About 4 characters per token, plus a fixed overhead per message."""

    def count_message(self, message: Message) -> int:
        return math.ceil(len(message.content) / 4) + MESSAGE_OVERHEAD


def count_tokens(counter: TokenCounter, messages: Sequence[Message]) -> int:
    """Total tokens for a conversation. An empty conversation is 0."""
    return sum(counter.count_message(m) for m in messages)
