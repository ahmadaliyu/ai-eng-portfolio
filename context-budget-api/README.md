# Context Budget API

[![context-budget-api](https://github.com/ahmadaliyu/ai-eng-portfolio/actions/workflows/context-budget-api.yml/badge.svg)](https://github.com/ahmadaliyu/ai-eng-portfolio/actions/workflows/context-budget-api.yml)

A small FastAPI service that answers one question: *does this conversation fit in a model's
context window, and if not, what should be dropped?* It estimates the tokens in a list of
messages, checks them against a model's context window minus a reserve for the reply, and trims
the conversation to fit by dropping the oldest messages. System messages and the latest message
are never dropped.

Token counts are a deterministic heuristic (`ceil(characters / 4) + 4` per message), not an
exact count for any model. No network calls, no API keys.

## Endpoints

| Method | Path      | Does                                                        |
| ------ | --------- | ----------------------------------------------------------- |
| GET    | `/health` | Liveness check: `{"status": "ok"}`                          |
| GET    | `/models` | Known models and their context windows, sorted by name      |
| POST   | `/count`  | Estimated tokens in `messages`                              |
| POST   | `/fit`    | Whether `messages` fit `model`'s budget, and what's left    |
| POST   | `/trim`   | `messages` with the oldest droppable ones removed until they fit |

`/fit` and `/trim` take `model` and an optional `reserve_output_tokens` (default `1024`).
The budget is `context_window - reserve_output_tokens`. An unknown model, a reserve that isn't
below the context window, or a conversation whose protected messages alone are over budget
returns `422` with a `detail` message.

## Example

```bash
curl -s http://127.0.0.1:8000/trim \
  -H "Content-Type: application/json" \
  -d '{
        "model": "claude-haiku-5-5",
        "reserve_output_tokens": 999985,
        "messages": [
          {"role": "system", "content": "Be brief."},
          {"role": "user", "content": "An old question that can go."},
          {"role": "user", "content": "Hi"}
        ]
      }'
```

```json
{
  "messages": [
    {"role": "system", "content": "Be brief."},
    {"role": "user", "content": "Hi"}
  ],
  "tokens": 12,
  "budget": 15,
  "dropped": 1
}
```

Interactive docs are at `http://127.0.0.1:8000/docs` while the server runs.

## Run it

Needs [uv](https://docs.astral.sh/uv/). From this folder:

```bash
uv sync
uv run fastapi dev src/context_budget_api/main.py
```

## Tests and checks

```bash
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
```

## How this was built

This is a portfolio project about the *workflow* of building with a coding agent (Claude Code)
using the guard rails a professional team would use:

- **Tests first.** Every behaviour started as a failing test, then the minimum code to pass it
  (red, green, refactor). Fakes for the token counter and model registry keep test numbers easy
  to follow.
- **Agent instructions.** [`AGENTS.md`](AGENTS.md) tells any coding agent the commands, layout
  and rules; [`CLAUDE.md`](CLAUDE.md) imports it and adds the Claude Code specifics.
- **Hooks.** After every Python edit, a Claude Code hook formats and lints the file and shows
  remaining errors to the agent ([`.claude/hooks/format_py.py`](.claude/hooks/format_py.py)).
  When the agent tries to stop, another hook runs the tests and blocks the stop if they fail
  ([`.claude/hooks/run_tests.py`](.claude/hooks/run_tests.py)).
- **CI.** GitHub Actions runs format, lint, types and tests on every push and pull request that
  touches this folder ([workflow](../.github/workflows/context-budget-api.yml)).

Design: [spec](docs/superpowers/specs/2026-11-23-context-budget-api-design.md).
Build plan: [plan](docs/superpowers/plans/2026-11-23-context-budget-api.md).
