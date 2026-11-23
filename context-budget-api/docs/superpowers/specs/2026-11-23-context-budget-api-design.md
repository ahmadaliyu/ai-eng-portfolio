# Context Budget API — Design

Date: 2026-11-23
Status: approved 2026-11-23

## Intent and the why

This is a learning and portfolio project. The goal is to practise the **workflow**
of building a service with a coding agent (Claude Code), with the guard rails a
professional team would use:

- tests written **before** the code they check (TDD: red → green → refactor)
- `AGENTS.md` / `CLAUDE.md` telling the agent how to work in the project
- Claude Code **hooks** that check the agent's work automatically
- **CI** on GitHub that runs the same checks on every push

The service itself is deliberately small. It ties in with the owner's study of
the "context tax" and compaction: it answers *"does this conversation fit in a
model's context window, and if not, what should be dropped?"*

Success: every endpoint is covered by tests that were written first, the hooks
fire during the build, CI is green on GitHub, and the owner can explain each
piece of the setup.

## Goals

- A FastAPI service with endpoints to count tokens in a conversation, check whether it fits a model's
  budget, and trim it to fit.
- Deterministic behaviour: same input, same output, no network, no API keys.
- A test suite that drives the design, run locally, by hooks, and in CI.
- Agent instructions and hooks that live inside the project folder.

## Non-goals

- Exact token counts for any specific model. The estimate is a heuristic.
- Summarising or rewriting messages (real compaction). Trim only drops messages.
- Auth, persistence, deployment, rate limiting.
- Calling any LLM.

## Anti-goals (would count as failure even if it "works")

- Code written before its test, or tests written to match code after the fact.
- Tests that need network access or secrets.
- Hooks so slow or noisy that they get in the way of the agent.
- Setup the owner can't explain afterwards.

## Constraints

- Lives at `ai-eng-portfolio/context-budget-api/`. The repo holds many projects.
- Follows the repo's existing setup: **uv**, **Python 3.14**, dev group with
  **pytest, ruff, mypy** (same as `async-api-fanout`).
- GitHub only reads workflows from the repo root, so CI goes in
  `ai-eng-portfolio/.github/workflows/` and is filtered to this folder.
- Claude Code loads project hooks from the folder a session starts in, so the
  build phase runs in a Claude Code session opened in `context-budget-api/`.
- Windows dev machine; CI runs on Ubuntu. Hook commands must work on both, or at least
  on the dev machine. CI does not run hooks.

## Approaches considered

**Token counting**
- *Character heuristic behind a `TokenCounter` interface* — **chosen** (Claude's call).
  Deterministic and offline. Easy to swap in a fake counter in tests.
- *tiktoken* — downloads its data files on first use, which is fragile in CI. It's also only an
  approximation for Claude models.
- *Anthropic `count_tokens` API* — exact, but needs a key and network access in every test run.

**Where the agent setup lives**
- *Inside the project folder* — **chosen by the owner.** Self-contained and portable. Needs a
  Claude Code session opened in that folder for hooks to load.
- *At the repo root* — works from any session, but every hook needs extra logic to work out which
  project a file belongs to, and every other project in the repo shares it.

## The design

### Project layout

```
context-budget-api/
  AGENTS.md                 # the real agent instructions (works for any agent)
  CLAUDE.md                 # imports AGENTS.md + Claude-specific notes
  README.md
  pyproject.toml            # uv project, Python >=3.14
  .claude/
    settings.json           # hooks
    hooks/                  # hook scripts (Python, run via uv)
  src/context_budget_api/
    __init__.py
    main.py                 # FastAPI app + routes
    schemas.py              # Pydantic request/response models
    tokens.py               # TokenCounter protocol + HeuristicCounter
    models.py               # model registry (name -> context window)
    budget.py               # fit / trim logic, pure functions
  tests/
    conftest.py             # TestClient, fake counter, fake registry
    test_tokens.py
    test_budget.py
    test_api.py
  docs/superpowers/specs/   # this document
```

Pure logic (`tokens.py`, `budget.py`) is kept separate from HTTP (`main.py`), so
most tests are plain function tests and only a few go through the API.

### Data shapes

A message: `{"role": "system" | "user" | "assistant", "content": str}`.

### Token estimate (HeuristicCounter)

- per message: `ceil(len(content) / 4) + 4` (the `+4` is a fixed overhead for role and formatting)
- per conversation: sum over messages; empty list → `0`

### Model registry

A small built-in dict of model name → context window (tokens), for a few current
Claude models. The app reads it through a dependency, so tests use their own
fake registry and never depend on real numbers.

### Endpoints

| Method & path | Input | Output |
|---|---|---|
| `GET /health` | — | `{"status": "ok"}` |
| `GET /models` | — | list of `{name, context_window}` |
| `POST /count` | `{messages}` | `{tokens}` |
| `POST /fit` | `{messages, model, reserve_output_tokens}` | `{fits, tokens, budget, remaining}` |
| `POST /trim` | `{messages, model, reserve_output_tokens}` | `{messages, tokens, budget, dropped}` |

- `budget = context_window - reserve_output_tokens`
- `remaining = budget - tokens` (negative when it doesn't fit)
- `reserve_output_tokens` defaults to `1024`, must be `>= 0` and less than the context window.

### Trim rules

1. System messages are never dropped.
2. The last message is never dropped (it's the turn being answered).
3. Otherwise drop the **oldest** non-system message, one at a time, until it fits.
4. Order of the kept messages is unchanged.
5. If it already fits (including an empty list), return the input unchanged with `dropped: 0`.
   System messages are kept wherever they appear, not only at the start.
6. If it can't fit even after dropping everything allowed → `422` with a clear
   message saying the protected messages alone exceed the budget.

### Errors

- Unknown model → `422` with a message listing the known models.
- Malformed input (bad role, missing content, negative reserve) → FastAPI/Pydantic's
  standard `422`.

### Agent instructions

- `AGENTS.md` (the cross-agent standard) holds the real rules: how to run
  tests/lint/types with uv, the TDD rule (write a failing test, run it, see it
  fail, then implement), project layout, "no network in tests".
- `CLAUDE.md` is short: `@AGENTS.md` to import it, plus notes about the hooks.

### Claude Code hooks (`.claude/settings.json`)

- **PostToolUse** on `Edit|Write|MultiEdit` for `.py` files: run `ruff format`
  and `ruff check --fix` on the edited file. Fast, keeps code tidy.
- **Stop**: run `pytest -q`. If tests fail, the hook exits with code 2, so the
  failure is fed back to Claude and it keeps working instead of
  stopping. It checks `stop_hook_active` in its input so it can never loop.
- **Order (Claude's call):** the formatting hook goes in early, right after
  scaffolding, so it fires throughout the build. The Stop hook goes in **after**
  the features are built. During the walkthrough we deliberately stop on a
  failing ("red") test so the owner can see it, and a blocking Stop hook would
  stop us pausing there. From then on it guards every later change.

### CI (`.github/workflows/context-budget-api.yml`)

- Triggers on push and pull request, filtered to `context-budget-api/**` and the
  workflow file itself.
- Ubuntu, `astral-sh/setup-uv`, Python 3.14, working directory `context-budget-api`.
- Steps: `uv sync`, `ruff format --check`, `ruff check`, `mypy`, `pytest`.
- mypy runs in `strict` mode (Claude's call). It's stricter, but catches more, and
  it suits typed Pydantic/FastAPI code.

### How we work

- We build directly on `main` (owner's choice).
- We go one step at a time, and each step is explained as we go. Commits happen at milestones,
  each with the owner's OK.

## Left to the builder

- Exact context-window numbers for the registry. Take them from Anthropic's
  models documentation at build time. Tests don't depend on them.
- Exact hook script code and how the Stop hook avoids blocking a deliberate red step.
- Pinned dependency versions (whatever `uv add` picks).
