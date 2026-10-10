#!/usr/bin/env python3
"""Install the evergreen-wiki skills into an agent's user-level skills folder.

Usage:
  python3 install.py --target agents          ~/.agents/skills (read by several agents)
  python3 install.py --target claude-code     ~/.claude/skills
  python3 install.py --target gemini          ~/.gemini/skills
  python3 install.py --target opencode        ~/.config/opencode/skills
  python3 install.py --target codex           ~/.codex/skills
  python3 install.py --dest /some/skills/dir  any folder
Options: --locale zh (Chinese descriptions), --link (symlink instead of copy, for development),
--force (replace an existing install), --dry-run.

Claude Code users can also install as a plugin:  /plugin marketplace add walkwithedi/evergreen-wiki
claude.ai users upload the zips from the Releases page in Settings > Capabilities > Skills.
Folder locations change between agent versions; check your agent's documentation if a
skill does not show up, and use --dest.
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys

log = logging.getLogger("install")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS = ["kb-note", "kb-query", "kb-incremental"]
HOME = os.path.expanduser("~")
TARGETS = {
    # target: (path, verified against the agent's own documentation)
    "agents": (os.path.join(HOME, ".agents", "skills"), True),
    "claude-code": (os.path.join(HOME, ".claude", "skills"), True),
    "gemini": (os.path.join(HOME, ".gemini", "skills"), True),
    "opencode": (os.path.join(HOME, ".config", "opencode", "skills"), True),
    "codex": (os.path.join(HOME, ".codex", "skills"), False),
}


def install_one(name, dest_root, a, desc):
    src = os.path.join(ROOT, "skills", name)
    dest = os.path.join(dest_root, name)
    if os.path.lexists(dest):
        if not a.force:
            print(f"skip: {dest} exists (use --force to replace)")
            return False
        if not a.dry_run:
            if os.path.islink(dest) or os.path.isfile(dest):
                os.remove(dest)
            else:
                shutil.rmtree(dest)
    action = "link" if a.link else "copy"
    print(f"{action}: skills/{name} -> {dest}")
    if a.dry_run:
        return True
    os.makedirs(dest_root, exist_ok=True)
    if a.link:
        os.symlink(src, dest, target_is_directory=True)
        return True
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    if desc:
        p = os.path.join(dest, "SKILL.md")
        with open(p, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"^description: .*$", lambda m: "description: " + desc[name], text, count=1, flags=re.M)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    return True


def main():
    ap = argparse.ArgumentParser(description="Install evergreen-wiki skills")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--target", choices=sorted(TARGETS))
    g.add_argument("--dest")
    ap.add_argument("--locale")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    if a.link and a.locale:
        ap.error("--locale rewrites SKILL.md and cannot be combined with --link")
    if a.dest:
        dest_root = os.path.abspath(os.path.expanduser(a.dest))
    else:
        dest_root, verified = TARGETS[a.target]
        if not verified:
            print(f"note: the {a.target} skills folder ({dest_root}) is not confirmed by its official "
                  "documentation; if the skills do not show up, try --target agents or --dest.")
    desc = None
    if a.locale:
        with open(os.path.join(ROOT, "locales", a.locale, "descriptions.json"), encoding="utf-8") as f:
            desc = json.load(f)
    done = sum(install_one(n, dest_root, a, desc) for n in SKILLS)
    print(f"{'would install' if a.dry_run else 'installed'} {done} of {len(SKILLS)} skills in {dest_root}")
    if done:
        print("next: register a library (see README, 'Register your libraries'), then restart your agent.")


if __name__ == "__main__":
    main()
