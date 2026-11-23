"""PostToolUse hook: format and lint a Python file right after Claude edits it.

Claude Code sends JSON on stdin describing the tool call. Exit codes:
  0 -> all good (Claude carries on)
  2 -> lint errors remain; stderr is shown to Claude so it can fix them
"""

import json
import subprocess
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    path = payload.get("tool_input", {}).get("file_path", "")
    if not path.endswith(".py"):
        return 0

    ruff = [sys.executable, "-m", "ruff"]
    # Lint (and auto-fix) first, then format, so fixes like removed imports get tidied too.
    check = subprocess.run([*ruff, "check", "--fix", path], capture_output=True, text=True)
    subprocess.run([*ruff, "format", path], capture_output=True)
    if check.returncode != 0:
        print(f"ruff found problems in {path}:\n{check.stdout}{check.stderr}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
