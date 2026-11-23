# AGENTS.md

## What this is

A small FastAPI service that counts tokens in a conversation, checks whether it
fits a model's context window, and trims it to fit. Design:
`docs/superpowers/specs/2026-11-23-context-budget-api-design.md`.
Build plan: `docs/superpowers/plans/2026-11-23-context-budget-api.md`.

## Commands

Run everything from this folder, always through `uv`:

- Install: `uv sync`
- Test: `uv run pytest`
- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Types: `uv run mypy src tests`
- Run the API: `uv run fastapi dev src/context_budget_api/main.py`

All four checks (format, lint, types, tests) must pass before work is done.

## How we work: tests first

1. Write a failing test for the behaviour you want.
2. Run it and see it fail for the right reason (missing feature, not a typo).
3. Write the minimum code to make it pass.
4. Run the whole suite and see it pass.
5. Refactor if needed, keeping the suite green.

Never change or delete a test just to make it pass. If a test looks wrong, say so.

## Layout

- `src/context_budget_api/tokens.py`, `models.py`, `budget.py`: pure logic, no FastAPI.
- `src/context_budget_api/schemas.py`: Pydantic request/response models.
- `src/context_budget_api/main.py`: HTTP only (routes, dependencies, error mapping).
- `tests/`: one test file per module. Shared test helpers go in `tests/helpers.py`.

## Rules

- No network access or secrets in tests.
- All code fully typed; mypy runs in strict mode.
- Add dependencies only with `uv add` (or `uv add --dev`), never by editing `pyproject.toml`.
