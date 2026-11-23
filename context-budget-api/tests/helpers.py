"""Shared helpers for tests."""

from context_budget_api.schemas import Message, Role


def msg(content: str, role: Role = "user") -> Message:
    """Build a Message with less typing. Role defaults to "user"."""
    return Message(role=role, content=content)


class CharCounter:
    """Fake TokenCounter: one token per character, no overhead. Keeps test numbers obvious."""

    def count_message(self, message: Message) -> int:
        return len(message.content)
