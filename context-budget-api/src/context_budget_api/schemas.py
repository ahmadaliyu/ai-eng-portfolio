"""Pydantic request/response models."""

from typing import Literal

from pydantic import BaseModel

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """One message in a conversation."""

    role: Role
    content: str
