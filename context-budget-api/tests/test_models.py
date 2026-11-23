import pytest

from context_budget_api.models import DEFAULT_MODELS, UnknownModelError, context_window


def test_context_window_known_model() -> None:
    assert context_window({"tiny": 20}, "tiny") == 20


def test_unknown_model_lists_known_models() -> None:
    with pytest.raises(UnknownModelError, match="alpha, beta"):
        context_window({"beta": 1, "alpha": 2}, "nope")


def test_default_reserve_valid_for_every_builtin_model() -> None:
    # /fit and /trim default to reserving 1024 output tokens; that must be
    # valid (less than the window) for every model we ship.
    assert DEFAULT_MODELS, "registry must not be empty"
    for name, window in DEFAULT_MODELS.items():
        assert window > 1024, name
