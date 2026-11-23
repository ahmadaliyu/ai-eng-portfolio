from typing import Any

from fastapi.testclient import TestClient

from context_budget_api.main import app


def m(content: str, role: str = "user") -> dict[str, str]:
    """A message as JSON."""
    return {"role": role, "content": content}


# The four messages from the trim tests: 1 + 4 + 4 + 2 = 11 characters.
FOUR = [m("S", "system"), m("aaaa"), m("bbbb", "assistant"), m("cc")]


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_models_lists_registry_sorted(client: TestClient) -> None:
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == [
        {"name": "big", "context_window": 2000},
        {"name": "tiny", "context_window": 20},
    ]


def test_count(client: TestClient) -> None:
    response = client.post("/count", json={"messages": [m("abc")]})
    assert response.status_code == 200
    assert response.json() == {"tokens": 3}


def test_fit_exactly_at_budget(client: TestClient) -> None:
    body = {"messages": [m("aaaaa"), m("bbbbb")], "model": "tiny", "reserve_output_tokens": 10}
    response = client.post("/fit", json=body)
    assert response.status_code == 200
    assert response.json() == {"fits": True, "tokens": 10, "budget": 10, "remaining": 0}


def test_fit_uses_default_reserve(client: TestClient) -> None:
    response = client.post("/fit", json={"messages": [m("a")], "model": "big"})
    assert response.status_code == 200
    assert response.json()["budget"] == 976  # 2000 - 1024


def test_trim_drops_oldest(client: TestClient) -> None:
    body = {"messages": FOUR, "model": "tiny", "reserve_output_tokens": 13}  # budget 7
    response = client.post("/trim", json=body)
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["dropped"] == 1
    assert data["tokens"] == 7
    assert data["budget"] == 7
    assert [message["content"] for message in data["messages"]] == ["S", "bbbb", "cc"]


def test_unknown_model_is_422(client: TestClient) -> None:
    response = client.post("/fit", json={"messages": [m("a")], "model": "nope"})
    assert response.status_code == 422
    assert "tiny" in response.json()["detail"]


def test_reserve_not_below_window_is_422(client: TestClient) -> None:
    body = {"messages": [m("a")], "model": "tiny", "reserve_output_tokens": 20}
    response = client.post("/fit", json=body)
    assert response.status_code == 422
    assert "reserve" in response.json()["detail"]


def test_negative_reserve_is_422(client: TestClient) -> None:
    body = {"messages": [m("a")], "model": "tiny", "reserve_output_tokens": -1}
    assert client.post("/fit", json=body).status_code == 422


def test_bad_role_is_422(client: TestClient) -> None:
    assert client.post("/count", json={"messages": [m("a", "robot")]}).status_code == 422


def test_trim_impossible_is_422(client: TestClient) -> None:
    body = {"messages": [m("aaaaa")], "model": "tiny", "reserve_output_tokens": 19}  # budget 1
    response = client.post("/trim", json=body)
    assert response.status_code == 422
    assert "protected" in response.json()["detail"]


def test_real_counter_is_wired_by_default() -> None:
    response = TestClient(app).post("/count", json={"messages": [m("abcd")]})
    assert response.status_code == 200
    assert response.json() == {"tokens": 5}  # ceil(4 / 4) + 4
