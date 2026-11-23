@AGENTS.md

## Hooks (Claude Code only)

- After every edit to a `.py` file, a hook formats and lints it. If lint errors
  remain, they are shown to you: fix them before moving on.
- When you try to stop, a hook runs the tests. If they fail, you're blocked from
  stopping and shown the failures: fix them, never by weakening a test.
