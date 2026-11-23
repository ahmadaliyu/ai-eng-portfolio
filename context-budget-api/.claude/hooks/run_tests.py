"""Stop hook: run the test suite before Claude is allowed to stop.

Claude Code sends JSON on stdin. Exit codes:
  0 -> tests pass (or we're already continuing because of this hook), Claude may stop
  2 -> tests fail; stderr is shown to Claude, which keeps working to fix them
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TAIL_LINES = 40


def main() -> int:
    payload = json.load(sys.stdin)
    # True when Claude is already continuing because this hook blocked it once.
    # Letting it stop then means the hook can never trap Claude in a loop.
    if payload.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or str(Path(__file__).resolve().parents[2])
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).splitlines()
        tail = "\n".join(output[-TAIL_LINES:])
        print(f"{tail}\n\nTests are failing. Fix them before stopping.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
