#!/usr/bin/env python3
"""Claude Code PreToolUse hook: run scripts/run_checks.py before Claude runs git commit.

Reads the hook JSON from stdin. Any Bash command other than a git commit passes at once.
For a git commit, a failing check stops the command (exit code 2) and the failures go to
stderr, where Claude reads them. Commits by hand are covered by .githooks/pre-commit.
"""
import json
import os
import re
import subprocess
import sys

# git, then any global options (-C dir, -c key=value, --flag), then commit
COMMIT_RE = re.compile(r"\bgit(?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+commit(?![\w-])")


def is_commit(command):
    return bool(COMMIT_RE.search(command or ""))


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash" or not is_commit((data.get("tool_input") or {}).get("command")):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    p = subprocess.run([sys.executable, os.path.join(root, "scripts", "run_checks.py")], cwd=root,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode == 0:
        return 0
    sys.stderr.write("Commit blocked: a check failed. Fix it, then commit again.\n" + p.stdout + p.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
