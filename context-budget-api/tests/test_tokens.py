from context_budget_api.tokens import HeuristicCounter, count_tokens
from tests.helpers import msg


def test_empty_content_costs_overhead_only() -> None:
    assert HeuristicCounter().count_message(msg("")) == 4


def test_four_chars_is_one_token_plus_overhead() -> None:
    assert HeuristicCounter().count_message(msg("abcd")) == 5


def test_partial_token_rounds_up() -> None:
    assert HeuristicCounter().count_message(msg("abcde")) == 6


def test_non_ascii_counted_by_characters() -> None:
    assert HeuristicCounter().count_message(msg("é")) == 5
    assert HeuristicCounter().count_message(msg("🙂🙂🙂🙂🙂")) == 6


def test_count_tokens_sums_messages() -> None:
    assert count_tokens(HeuristicCounter(), [msg("abcd"), msg("abcde", "assistant")]) == 11


def test_count_tokens_empty_conversation_is_zero() -> None:
    assert count_tokens(HeuristicCounter(), []) == 0
