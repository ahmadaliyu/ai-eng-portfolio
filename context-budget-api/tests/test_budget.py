import pytest

from context_budget_api.budget import FitResult, InvalidReserveError, check_fit
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
