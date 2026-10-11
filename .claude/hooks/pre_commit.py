#!/usr/bin/env python3
"""Claude Code PreToolUse hook: checks before Claude runs git commit or git push.

Reads the hook JSON from stdin. Any Bash command other than a git commit or push passes at once.
  git commit  runs scripts/run_checks.py (tests, repository checks, shared copies, data scan)
  git push    runs scripts/sensitive_scan.py --unpushed: messages, identities, added lines and
              binary files of every commit on a local branch that no remote has yet
A failing check stops the command (exit code 2) and the failures go to stderr, where Claude
reads them. Commits and pushes by hand are covered by .githooks/.
"""
import json
import os
import subprocess
import sys

# Global options of git that take the next word as their value.
OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def git_subcommands(command):
    """The subcommands of every git invocation in the command: git, then any global options
    (-C dir, -c key=value, --flag), then the subcommand word.
    Word by word rather than a regular expression, so no input can make it slow."""
    words = (command or "").replace(";", " ; ").replace("&&", " && ").replace("||", " || ").split()
    found = set()
    for i, w in enumerate(words):
        if w != "git" and not w.endswith("/git"):
            continue
        j = i + 1
        while j < len(words) and words[j].startswith("-"):
            j += 2 if words[j] in OPTIONS_WITH_VALUE else 1
        if j < len(words):
            found.add(words[j])
    return found


def is_commit(command):
    return "commit" in git_subcommands(command)


def run(root, args):
    return subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    subs = git_subcommands((data.get("tool_input") or {}).get("command"))
    if not subs & {"commit", "push"}:
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if "commit" in subs:
        p = run(root, [os.path.join(root, "scripts", "run_checks.py")])
        if p.returncode:
            sys.stderr.write("Commit blocked: a check failed. Fix it, then commit again.\n" + p.stdout + p.stderr)
            return 2
    if "push" in subs:
        p = run(root, [os.path.join(root, "scripts", "sensitive_scan.py"), "--unpushed"])
        if p.returncode:
            sys.stderr.write("Push blocked: the commits to push hold possible personal data, work details or "
                             "credentials. Rewrite the commits that hold them before pushing.\n" + p.stdout + p.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
