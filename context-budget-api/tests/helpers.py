"""Shared helpers for tests."""

from context_budget_api.schemas import Message, Role


def msg(content: str, role: Role = "user") -> Message:
    """Build a Message with less typing. Role defaults to "user"."""
    return Message(role=role, content=content)
