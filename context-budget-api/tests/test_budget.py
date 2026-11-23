import pytest

from context_budget_api.budget import (
    CannotFitError,
    FitResult,
    InvalidReserveError,
    TrimResult,
    check_fit,
    trim_to_fit,
)
from context_budget_api.schemas import Message
from tests.helpers import CharCounter, msg

# With CharCounter, tokens == characters, so window 20 - reserve 10 = budget 10.


def test_fits_exactly_at_budget() -> None:
    messages = [msg("aaaa"), msg("bbbbbb", "assistant")]  # 4 + 6 = 10
    assert check_fit(messages, CharCounter(), context_window=20, reserve=10) == FitResult(
        fits=True, tokens=10, budget=10, remaining=0
    )


def test_one_over_budget_does_not_fit() -> None:
    messages = [msg("aaaa"), msg("bbbbbbb", "assistant")]  # 4 + 7 = 11
    result = check_fit(messages, CharCounter(), context_window=20, reserve=10)
    assert result.fits is False
    assert result.remaining == -1


def test_empty_conversation_fits() -> None:
    result = check_fit([], CharCounter(), context_window=20, reserve=10)
    assert result.fits is True
    assert result.tokens == 0


def test_reserve_equal_to_window_is_invalid() -> None:
    with pytest.raises(InvalidReserveError):
        check_fit([msg("a")], CharCounter(), context_window=20, reserve=20)


# --- trim_to_fit: window is always 20, so reserve = 20 - budget ---


def trim(messages: list[Message], budget: int) -> TrimResult:
    return trim_to_fit(messages, CharCounter(), context_window=20, reserve=20 - budget)


def test_already_fits_returns_unchanged() -> None:
    messages = [msg("S", "system"), msg("aaaa"), msg("bb", "assistant")]  # 7
    result = trim(messages, budget=10)
    assert result.messages == messages
    assert result.dropped == 0


def test_empty_conversation() -> None:
    result = trim([], budget=10)
    assert result.messages == []
    assert result.dropped == 0


def test_drops_oldest_first() -> None:
    messages = [msg("S", "system"), msg("aaaa"), msg("bbbb", "assistant"), msg("cc")]  # 11
    result = trim(messages, budget=7)
    assert result.messages == [msg("S", "system"), msg("bbbb", "assistant"), msg("cc")]
    assert result.tokens == 7
    assert result.dropped == 1


def test_system_message_in_middle_is_kept() -> None:
    messages = [msg("aaaa"), msg("SS", "system"), msg("bb")]  # 8
    result = trim(messages, budget=4)
    assert result.messages == [msg("SS", "system"), msg("bb")]
    assert result.dropped == 1


def test_last_message_never_dropped() -> None:
    messages = [msg("a"), msg("bbbbbbbb")]  # 9
    assert trim(messages, budget=8).messages == [msg("bbbbbbbb")]
    with pytest.raises(CannotFitError, match="protected"):
        trim(messages, budget=7)


def test_last_message_is_system() -> None:
    messages = [msg("aaaa"), msg("SS", "system")]  # 6
    result = trim(messages, budget=2)
    assert result.messages == [msg("SS", "system")]
    assert result.dropped == 1


def test_does_not_modify_input() -> None:
    messages = [msg("S", "system"), msg("aaaa"), msg("bbbb", "assistant"), msg("cc")]
    before = list(messages)
    trim(messages, budget=7)  # forces a drop
    assert messages == before


def test_invalid_reserve_raises() -> None:
    with pytest.raises(InvalidReserveError):
        trim_to_fit([msg("a")], CharCounter(), context_window=20, reserve=25)
