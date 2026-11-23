# Context Budget API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A small FastAPI service that counts tokens in a conversation, checks whether it fits a model's context budget, and trims it to fit. Built test-first by a coding agent, with AGENTS.md/CLAUDE.md, Claude Code hooks and GitHub Actions CI.

**Architecture:** Pure logic (`tokens.py`, `models.py`, `budget.py`) is kept apart from the HTTP layer (`main.py`). The token counter and model registry reach routes through FastAPI dependencies, so tests swap in a fake counter and a fake registry. Errors from the logic layer are mapped to HTTP 422 in one place.

**Tech Stack:** Python 3.14, uv, FastAPI, Pydantic v2, pytest + httpx (TestClient), ruff, mypy (strict), Claude Code hooks, GitHub Actions.

**Spec:** `context-budget-api/docs/superpowers/specs/2026-11-23-context-budget-api-design.md`

## Global Constraints

- Project root: `ai-eng-portfolio/context-budget-api/`. All commands below run from there unless stated otherwise.
- `requires-python = ">=3.14"`; dependencies managed only with `uv add` / `uv add --dev`.
- Dev group: `pytest`, `ruff`, `mypy`, `httpx`.
- mypy `strict = true`.
- No network or secrets in tests.
- Message roles: exactly `"system" | "user" | "assistant"`.
- Heuristic: per message `ceil(len(content) / 4) + 4`; empty list → `0`.
- `reserve_output_tokens` default `1024`, must be `>= 0` and `< context_window`.
- `budget = context_window - reserve_output_tokens`; `remaining = budget - tokens`.
- Unknown model, invalid reserve, impossible trim → HTTP `422`.
- Work happens on `main`. Every commit needs the owner's OK first.
- **Walkthrough mode:** after each "fails" and each "passes" step, stop and explain to the owner what happened and why before moving on.

## Review Focus

1. A conversation exactly at the budget (`tokens == budget`) fits with `remaining == 0`. Off-by-one here is the most likely bug. → Task 3.
2. `/trim` must not modify the caller's list; it returns a new one. → Task 4.
3. The default reserve (1024) must be valid for every built-in model, or `/fit` with no reserve errors on a real model. → Task 3.
4. Non-ASCII content (accents, emoji) is counted by characters, consistently. → Task 2.
5. When the last message is itself a system message, it's protected once, not twice, and trim still works. → Task 4.

---

### Task 1: Scaffold, agent instructions, formatting hook, first green test

**Files:**
- Create: `pyproject.toml`, `src/context_budget_api/__init__.py`, `src/context_budget_api/main.py`, `tests/__init__.py`, `tests/test_api.py`
- Create: `AGENTS.md`, `CLAUDE.md`, `README.md`
- Create: `.claude/settings.json`, `.claude/hooks/format_py.py`
- Create: `.gitignore` (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`)

**Interfaces:**
- Produces: `context_budget_api.main.app: FastAPI`

- [ ] **Step 1: Initialise the uv project in the existing folder**

Run: `uv init --package --vcs none --name context-budget-api .` then `uv add fastapi` and `uv add --dev pytest ruff mypy httpx`.
Expected: `pyproject.toml` and `uv.lock` exist; `uv run python -c "import fastapi"` works. Delete any sample code uv generated in `__init__.py` (no `main()` script entry is needed).

- [ ] **Step 2: Add tool config to `pyproject.toml`**

`[tool.mypy] strict = true`, `[tool.pytest.ini_options] testpaths = ["tests"]`, `[tool.ruff] line-length = 100`, `[tool.ruff.lint] select = ["E", "F", "I", "UP", "B"]`.

- [ ] **Step 3: Write the failing test** in `tests/test_api.py`

```python
from fastapi.testclient import TestClient
from context_budget_api.main import app

def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run it and see it fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL. `ModuleNotFoundError`/`ImportError` for `context_budget_api.main`.

- [ ] **Step 5: Implement `app = FastAPI(title="Context Budget API")` with `GET /health` in `src/context_budget_api/main.py`**

- [ ] **Step 6: Run it and see it pass**

Run: `uv run pytest -v`
Expected: 1 passed.

- [ ] **Step 7: Write `AGENTS.md`**

Sections: *What this is* (one paragraph + link to the spec); *Commands* (`uv sync`, `uv run pytest`, `uv run ruff format .`, `uv run ruff check .`, `uv run mypy src tests`); *How we work: TDD* (write a failing test, run it and see it fail for the right reason, write the minimum code, run it and see it pass, then refactor; never change a test just to make it pass); *Layout* (logic in `tokens.py`/`models.py`/`budget.py`, HTTP only in `main.py`); *Rules* (no network or secrets in tests; all code fully typed for mypy strict; add dependencies only with `uv add`).

- [ ] **Step 8: Write `CLAUDE.md`**

First line `@AGENTS.md` (imports it). Then a short *Hooks* section: after every edit to a `.py` file, a hook formats and lints it, and if lint errors remain they're shown to you, so fix them; when you try to stop, a hook runs the tests (added in Task 6).

- [ ] **Step 9: Write the formatting hook `.claude/hooks/format_py.py`**

Reads the hook JSON from stdin, takes `tool_input.file_path`. If it doesn't end in `.py`, exit 0. Otherwise run `uv run ruff format <path>` then `uv run ruff check --fix <path>`. If `ruff check` still reports errors, write its output to stderr and exit 2 (Claude sees it). Otherwise exit 0.

`.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command",
            "command": "uv run --project \"$CLAUDE_PROJECT_DIR\" python \"$CLAUDE_PROJECT_DIR/.claude/hooks/format_py.py\"" }
        ]
      }
    ]
  }
}
```

- [ ] **Step 10: Test the hook by hand**

Run (Git Bash): `echo '{"tool_input":{"file_path":"src/context_budget_api/main.py"}}' | CLAUDE_PROJECT_DIR="$PWD" uv run python .claude/hooks/format_py.py; echo "exit=$?"`
Expected: `exit=0`. Then do the same with a scratch `.py` file whose only line uses an undefined name (`x = y`). Expected: ruff errors printed, `exit=2`. Delete the scratch file.

- [ ] **Step 11: Run every check**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy src tests && uv run pytest`
Expected: all clean, 1 passed.

- [ ] **Step 12: Commit (ask the owner first)**

`git add context-budget-api` from the repo root, then commit with the message `feat(context-budget-api): scaffold, agent instructions, format hook`.

- [ ] **Step 13: Switch sessions**

Hooks only load in a Claude Code session started in `context-budget-api/`. Continue Tasks 2–7 in such a session. The first `.py` edit there should show the formatting hook running.

---

### Task 2: Message schema and heuristic token counter

**Files:**
- Create: `src/context_budget_api/schemas.py`, `src/context_budget_api/tokens.py`, `tests/helpers.py`, `tests/test_tokens.py`

**Interfaces:**
- Produces (`schemas.py`): `Role = Literal["system", "user", "assistant"]`; `class Message(BaseModel): role: Role; content: str`
- Produces (`tokens.py`):
  - `class TokenCounter(Protocol): def count_message(self, message: Message) -> int: ...`
  - `class HeuristicCounter` (implements it, rule from Global Constraints)
  - `def count_tokens(counter: TokenCounter, messages: Sequence[Message]) -> int` (sum)
- Produces (`tests/helpers.py`): `def msg(content: str, role: Role = "user") -> Message`. Tests import it with `from tests.helpers import msg`.

- [ ] **Step 1: Write the failing tests** in `tests/test_tokens.py`

```python
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
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_tokens.py -v`
Expected: FAIL. ImportError for `schemas` / `tokens`.

- [ ] **Step 3: Implement `Message`, `TokenCounter`, `HeuristicCounter`, `count_tokens`**

Use `math.ceil(len(content) / 4) + 4`.

- [ ] **Step 4: Run them and see them pass**

Run: `uv run pytest -v`
Expected: all pass. Also `uv run mypy src tests` is clean.

- [ ] **Step 5: Commit (ask the owner first)**: `feat(context-budget-api): message schema and heuristic token counter`

---

### Task 3: Model registry and fit check

**Files:**
- Create: `src/context_budget_api/models.py`, `src/context_budget_api/budget.py`, `tests/test_budget.py`, `tests/test_models.py`
- Modify: `tests/helpers.py`

**Interfaces:**
- Consumes: `Message`, `TokenCounter`, `count_tokens` (Task 2)
- Produces (`models.py`):
  - `DEFAULT_MODELS: dict[str, int]` (model name → context window)
  - `class UnknownModelError(ValueError)`. Message lists known model names, sorted.
  - `def context_window(registry: Mapping[str, int], model: str) -> int`
- Produces (`budget.py`):
  - `class InvalidReserveError(ValueError)`
  - `@dataclass(frozen=True) class FitResult: fits: bool; tokens: int; budget: int; remaining: int`
  - `def check_fit(messages: Sequence[Message], counter: TokenCounter, context_window: int, reserve: int) -> FitResult`. Raises `InvalidReserveError` if `reserve >= context_window`.
- Produces (`tests/helpers.py`): `class CharCounter` (counts `len(content)` per message, no overhead). Tests use it to keep the numbers easy to follow.

- [ ] **Step 1: Look up context windows**

From Anthropic's models documentation, fill `DEFAULT_MODELS` with 3–4 current Claude models (e.g. `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`). Put the source URL and date in a comment.

- [ ] **Step 2: Write the failing tests**

`tests/test_models.py`:
- `test_context_window_known_model`: `context_window({"tiny": 20}, "tiny") == 20`
- `test_unknown_model_lists_known_models`: `pytest.raises(UnknownModelError, match="alpha, beta")` for `context_window({"beta": 1, "alpha": 2}, "nope")`
- `test_default_reserve_valid_for_every_builtin_model`: every value in `DEFAULT_MODELS` is `> 1024`

`tests/test_budget.py` (with `CharCounter`):
- `test_fits_exactly_at_budget`: messages totalling 10 chars, window 20, reserve 10 → `FitResult(fits=True, tokens=10, budget=10, remaining=0)`
- `test_one_over_budget_does_not_fit`: 11 chars, same window/reserve → `fits=False, remaining=-1`
- `test_empty_conversation_fits`: `[]` → `fits=True, tokens=0`
- `test_reserve_equal_to_window_is_invalid`: `pytest.raises(InvalidReserveError)` with window 20, reserve 20

- [ ] **Step 3: Run them and see them fail**

Run: `uv run pytest tests/test_models.py tests/test_budget.py -v`
Expected: FAIL with ImportError.

- [ ] **Step 4: Implement `models.py` and `check_fit` in `budget.py`**

- [ ] **Step 5: Run them and see them pass**

Run: `uv run pytest -v && uv run mypy src tests`
Expected: all pass, mypy clean.

- [ ] **Step 6: Commit (ask the owner first)**: `feat(context-budget-api): model registry and fit check`

---

### Task 4: Trim to fit

**Files:**
- Modify: `src/context_budget_api/budget.py`
- Modify: `tests/test_budget.py`

**Interfaces:**
- Consumes: `check_fit`, `InvalidReserveError`, `CharCounter`, `msg` (Task 3)
- Produces:
  - `class CannotFitError(ValueError)`. Message contains the word `"protected"`.
  - `@dataclass(frozen=True) class TrimResult: messages: list[Message]; tokens: int; budget: int; dropped: int`
  - `def trim_to_fit(messages: Sequence[Message], counter: TokenCounter, context_window: int, reserve: int) -> TrimResult`

- [ ] **Step 1: Write the failing tests** (all with `CharCounter`, `budget = window - reserve`)

- `test_already_fits_returns_unchanged`: result messages equal input, `dropped == 0`
- `test_empty_conversation`: `[]` → `messages == []`, `dropped == 0`
- `test_drops_oldest_first`: `[sys "S", user "aaaa", asst "bbbb", user "cc"]`, budget 7 → messages `[S, bbbb, cc]`, `tokens == 7`, `dropped == 1`
- `test_system_message_in_middle_is_kept`: `[user "aaaa", sys "SS", user "bb"]`, budget 4 → `[SS, bb]`, `dropped == 1`
- `test_last_message_never_dropped`: `[user "a", user "bbbbbbbb"]`, budget 8 → `[bbbbbbbb]`; same input with budget 7 → `pytest.raises(CannotFitError, match="protected")`
- `test_last_message_is_system`: `[user "aaaa", sys "SS"]`, budget 2 → `[SS]`, `dropped == 1`
- `test_does_not_modify_input`: keep a copy of the input list, call `trim_to_fit`, assert the input still equals the copy
- `test_invalid_reserve_raises`: window 20, reserve 25 → `InvalidReserveError`

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_budget.py -v`
Expected: FAIL with ImportError for `trim_to_fit`.

- [ ] **Step 3: Implement `trim_to_fit`**

Approach: validate the reserve the same way `check_fit` does. Protected indices are every system message plus the last index. Walk the other indices oldest-first, dropping each until the total is `<= budget`. Build a new list that keeps the original order. If every droppable message is gone and the total is still over budget, raise `CannotFitError` saying the protected messages alone need N tokens but the budget is M.

- [ ] **Step 4: Run them and see them pass**

Run: `uv run pytest -v && uv run mypy src tests`
Expected: all pass, mypy clean.

- [ ] **Step 5: Commit (ask the owner first)**: `feat(context-budget-api): trim conversations to fit`

---

### Task 5: HTTP endpoints

**Files:**
- Modify: `src/context_budget_api/schemas.py`, `src/context_budget_api/main.py`
- Create: `tests/conftest.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: everything from Tasks 2–4
- Produces (`schemas.py`): `CountRequest{messages: list[Message]}`, `CountResponse{tokens: int}`, `BudgetRequest{messages: list[Message], model: str, reserve_output_tokens: int = Field(1024, ge=0)}`, `FitResponse{fits, tokens, budget, remaining}`, `TrimResponse{messages, tokens, budget, dropped}`, `ModelInfo{name: str, context_window: int}`
- Produces (`main.py`): dependencies `get_counter() -> TokenCounter` (returns `HeuristicCounter()`) and `get_registry() -> Mapping[str, int]` (returns `DEFAULT_MODELS`); routes `GET /models`, `POST /count`, `POST /fit`, `POST /trim`; one exception handler mapping `UnknownModelError`, `InvalidReserveError`, `CannotFitError` → `422` with `{"detail": str(exc)}`
- Produces (`tests/conftest.py`): fixture `client` with `app.dependency_overrides` → `CharCounter()` and registry `{"tiny": 20, "big": 2000}`, cleared after each test

- [ ] **Step 1: Write the failing tests** in `tests/test_api.py` (all use `client` unless noted)

- `test_models_lists_registry_sorted`: `[{"name": "big", "context_window": 2000}, {"name": "tiny", "context_window": 20}]`
- `test_count`: `[{"role": "user", "content": "abc"}]` → `{"tokens": 3}`
- `test_fit_exactly_at_budget`: model `tiny`, reserve 10, 10 chars → `fits` true, `remaining` 0
- `test_fit_uses_default_reserve`: model `big`, no reserve → `budget == 976`
- `test_trim_drops_oldest`: model `tiny`, reserve 13 (budget 7), the four messages from Task 4 → `dropped == 1`, contents `["S", "bbbb", "cc"]`
- `test_unknown_model_is_422`: model `nope` → 422, `"tiny"` in `detail`
- `test_reserve_not_below_window_is_422`: model `tiny`, reserve 20 → 422
- `test_negative_reserve_is_422`: reserve -1 → 422
- `test_bad_role_is_422`: role `"robot"` → 422
- `test_trim_impossible_is_422`: model `tiny`, reserve 19, one 5-char user message → 422, `"protected"` in `detail`
- `test_real_counter_is_wired_by_default` (plain `TestClient(app)`, no overrides): `/count` with `"abcd"` → `{"tokens": 5}`

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_api.py -v`
Expected: the new tests FAIL (404s / import errors). `test_health_returns_ok` still passes.

- [ ] **Step 3: Implement the schemas, dependencies, routes and exception handler**

- [ ] **Step 4: Run everything and see it pass**

Run: `uv run ruff format --check . && uv run ruff check . && uv run mypy src tests && uv run pytest -v`
Expected: all clean, all pass.

- [ ] **Step 5: Try it for real**

Run: `uv run fastapi dev src/context_budget_api/main.py`, open `http://127.0.0.1:8000/docs`, try `/trim` from the browser. Stop the server afterwards.

- [ ] **Step 6: Commit (ask the owner first)**: `feat(context-budget-api): HTTP endpoints`

---

### Task 6: Stop hook that runs the tests

**Files:**
- Create: `.claude/hooks/run_tests.py`
- Modify: `.claude/settings.json`, `CLAUDE.md` (remove "added in Task 6")

**Interfaces:**
- Consumes: the `PostToolUse` entry from Task 1 (keep it)

- [ ] **Step 1: Write `run_tests.py`**

Read the hook JSON from stdin. If `stop_hook_active` is true, exit 0 (never loop). Otherwise run `uv run pytest -q` in `$CLAUDE_PROJECT_DIR`. If it fails, write the last ~40 lines of output plus "Tests are failing. Fix them before stopping." to stderr and exit 2. If it passes, exit 0.

- [ ] **Step 2: Register it** under `"Stop"` in `.claude/settings.json` (no matcher), using the same `uv run --project "$CLAUDE_PROJECT_DIR" python ...` form as Task 1.

- [ ] **Step 3: Test it by hand**

Run: `echo '{"stop_hook_active": true}' | CLAUDE_PROJECT_DIR="$PWD" uv run python .claude/hooks/run_tests.py; echo "exit=$?"` → `exit=0`.
Run: `echo '{"stop_hook_active": false}' | ...` → `exit=0` (tests pass).
Temporarily change one assertion in `test_tokens.py` so it fails, run again → failure output, `exit=2`. Undo the change.

- [ ] **Step 4: See it block for real**

In a fresh Claude Code session in `context-budget-api/`, ask Claude to break one test and stop. Expected: the hook blocks the stop and Claude fixes it. Then run `git diff` and confirm the test file is back to normal.

- [ ] **Step 5: Commit (ask the owner first)**: `feat(context-budget-api): stop hook runs tests`

---

### Task 7: CI and README

**Files:**
- Create: `ai-eng-portfolio/.github/workflows/context-budget-api.yml` (repo root)
- Modify: `README.md`

- [ ] **Step 1: Write the workflow**

`on: push` and `pull_request`, both with `paths: ["context-budget-api/**", ".github/workflows/context-budget-api.yml"]`. One job on `ubuntu-latest`, `defaults.run.working-directory: context-budget-api`. Steps: `actions/checkout`, `astral-sh/setup-uv` (with `enable-cache: true`), `uv python install 3.14`, `uv sync --locked`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src tests`, `uv run pytest -v`. Pin each action to a version tag that's at least two weeks old.

- [ ] **Step 2: Write `README.md`**

What it does (one paragraph), endpoints table, `curl` example for `/trim`, how to run tests, a "How this was built" section (TDD, AGENTS.md/CLAUDE.md, hooks, CI) with links to the spec and this plan, and a CI badge.

- [ ] **Step 3: Run every check locally**

Same command as Task 5 Step 4. Expected: all clean.

- [ ] **Step 4: Commit and push (ask the owner first; pushing is public)**

Commit `ci(context-budget-api): GitHub Actions workflow and README`, then `git push origin main`.

- [ ] **Step 5: Watch CI**

Run: `gh run list --workflow context-budget-api.yml --limit 1` then `gh run watch <id>`.
Expected: green. If it fails, read the log with `gh run view <id> --log-failed`, fix it test-first, and push again.
