"""Shared fixtures: a TestClient wired to a fake counter and a tiny model registry."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tests.helpers import CharCounter


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient where tokens == characters and the models are {"tiny": 20, "big": 2000}."""
    # Imported here, not at the top, so a broken main.py only fails tests that use this fixture.
    from context_budget_api.main import app, get_counter, get_registry

    app.dependency_overrides[get_counter] = CharCounter
    app.dependency_overrides[get_registry] = lambda: {"tiny": 20, "big": 2000}
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
