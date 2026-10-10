#!/usr/bin/env python3
"""Copy shared files into every skill, or check that the copies are current.

Each skill must work on its own (a claude.ai upload or a copied folder cannot reach a
sibling directory), so shared references and scripts are copied into each skill.
Edit only the files under shared/; run this script; commit the copies.

Usage:
  python3 scripts/sync_shared.py          copy
  python3 scripts/sync_shared.py --check  exit 1 if any copy differs (used in CI)
"""
import argparse
import filecmp
import logging
import os
import shutil
import sys

log = logging.getLogger("sync_shared")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REFS = ["config.md", "environment.md", "backend-gdrive.md", "backend-local.md"]
# (shared file, skills that receive it, target folder inside the skill)
PLAN = [(f"references/{r}", ["kb-note", "kb-query", "kb-incremental"], "references") for r in REFS]
PLAN.append(("scripts/kbconf.py", ["kb-incremental"], "scripts"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    stale = 0
    for rel, skills, folder in PLAN:
        src = os.path.join(ROOT, "shared", rel)
        for skill in skills:
            dst = os.path.join(ROOT, "skills", skill, folder, os.path.basename(rel))
            same = os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False)
            if same:
                log.debug("current: %s", dst)
                continue
            if a.check:
                stale += 1
                print(f"stale: skills/{skill}/{folder}/{os.path.basename(rel)} (edit shared/{rel} and run scripts/sync_shared.py)")
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                print(f"copied: shared/{rel} -> skills/{skill}/{folder}/")
    if a.check:
        print("result: " + ("stale copies found" if stale else "all copies current"))
        sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
