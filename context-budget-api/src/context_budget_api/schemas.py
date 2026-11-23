"""Pydantic request/response models."""

from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant"]


class Message(BaseModel):
    """One message in a conversation."""

    role: Role
    content: str


class CountRequest(BaseModel):
    messages: list[Message]


class CountResponse(BaseModel):
    tokens: int


class BudgetRequest(BaseModel):
    """Body for /fit and /trim."""

    messages: list[Message]
    model: str
    reserve_output_tokens: int = Field(1024, ge=0)


class FitResponse(BaseModel):
    fits: bool
    tokens: int
    budget: int
    remaining: int


class TrimResponse(BaseModel):
    messages: list[Message]
    tokens: int
    budget: int
    dropped: int


class ModelInfo(BaseModel):
    name: str
    context_window: int
