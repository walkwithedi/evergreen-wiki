#!/usr/bin/env python3
"""Claude Code PreToolUse hook: run scripts/run_checks.py before Claude runs git commit.

Reads the hook JSON from stdin. Any Bash command other than a git commit passes at once.
For a git commit, a failing check stops the command (exit code 2) and the failures go to
stderr, where Claude reads them. Commits by hand are covered by .githooks/pre-commit.
"""
import json
import os
import subprocess
import sys

# Global options of git that take the next word as their value.
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def is_commit(command):
    """True when some git invocation in the command runs the commit subcommand:
    git, then any global options (-C dir, -c key=value, --flag), then the word commit.
    Word by word rather than a regular expression, so no input can make it slow."""
    words = (command or "").replace(";", " ; ").replace("&&", " && ").replace("||", " || ").split()
    for i, w in enumerate(words):
        if w != "git" and not w.endswith("/git"):
            continue
        j = i + 1
        while j < len(words) and words[j].startswith("-"):
            j += 2 if words[j] in OPTIONS_WITH_VALUE else 1
        if j < len(words) and words[j] == "commit":
            return True
    return False


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
