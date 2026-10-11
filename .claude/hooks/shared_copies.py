#!/usr/bin/env python3
"""Claude Code hooks that keep the copies of shared/ files in the skills current.

Each skill carries a copy of the files under shared/ (scripts/sync_shared.py lists them),
and CI fails when a copy differs from its source.
  PreToolUse  (Edit, Write, MultiEdit): editing a copy is blocked (exit 2) with a pointer to
              the file under shared/ that must be edited instead.
  PostToolUse (Edit, Write, MultiEdit): after a file under shared/ changes, the copies are
              refreshed with scripts/sync_shared.py and Claude is told which ones changed.
Reads the hook JSON from stdin; anything else passes.
"""
import json
import os
import subprocess
import sys

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sync_shared  # noqa: E402


def copies():
    """{copy path relative to ROOT: shared source relative to ROOT}"""
    out = {}
    for rel, skills, folder in sync_shared.PLAN:
        for skill in skills:
            out[f"skills/{skill}/{folder}/{os.path.basename(rel)}"] = f"shared/{rel}"
    return out


def relpath(path):
    if not path:
        return ""
    full = os.path.abspath(os.path.join(ROOT, path))
    rel = os.path.relpath(full, ROOT)
    return "" if rel.startswith("..") else rel.replace(os.sep, "/")


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    rel = relpath((data.get("tool_input") or {}).get("file_path"))
    event = data.get("hook_event_name")
    if event == "PreToolUse":
        src = copies().get(rel)
        if src:
            sys.stderr.write(f"{rel} is a copy of {src}, made by scripts/sync_shared.py. "
                             f"Edit {src} instead; the copies are refreshed after the edit.\n")
            return 2
    elif event == "PostToolUse" and rel.startswith("shared/"):
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sync_shared.py")], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        copied = [line for line in p.stdout.splitlines() if line.startswith("copied:")]
        if p.returncode != 0 or copied:
            msg = "\n".join(copied) or (p.stdout + p.stderr)
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext":
                  f"scripts/sync_shared.py refreshed the skill copies of {rel}:\n{msg}\nCommit them too."}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
