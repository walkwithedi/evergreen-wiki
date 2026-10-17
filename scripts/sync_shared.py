#!/usr/bin/env python3
"""Copy shared files into every skill and tool, or check that the copies are current.

Each skill must work on its own (a claude.ai upload or a copied folder cannot reach a
sibling directory), so shared references and scripts are copied into each skill; the
stand-alone tools under tools/ get their copy the same way.
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
# (file under shared/, folders that receive a copy, relative to the repository root)
PLAN = [(f"references/{r}", [f"skills/{s}/references" for s in ("kb-note", "kb-query", "kb-incremental")])
        for r in REFS]
PLAN.append(("scripts/kbconf.py", ["skills/kb-incremental/scripts", "skills/kb-query/scripts"]))
# the converter: used by kb-incremental (scripts/convert.py) and by the stand-alone tool
PLAN.append(("scripts/doc2kb_core.py", ["skills/kb-incremental/scripts", "tools/doc2kb"]))
# knowledge-base batch files: written by doc2kb_core, split back by the skills
PLAN.append(("scripts/kb_batch.py", ["skills/kb-incremental/scripts", "tools/doc2kb"]))


def copies():
    """{copy path relative to the root: source path relative to the root}, "/" separated."""
    return {f"{folder}/{os.path.basename(rel)}": f"shared/{rel}" for rel, folders in PLAN for folder in folders}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    stale = 0
    for copy, source in copies().items():
        src = os.path.join(ROOT, *source.split("/"))
        dst = os.path.join(ROOT, *copy.split("/"))
        same = os.path.isfile(dst) and filecmp.cmp(src, dst, shallow=False)
        if same:
            log.debug("current: %s", dst)
            continue
        if a.check:
            stale += 1
            print(f"stale: {copy} (edit {source} and run scripts/sync_shared.py)")
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            print(f"copied: {source} -> {os.path.dirname(copy)}/")
    if a.check:
        print("result: " + ("stale copies found" if stale else "all copies current"))
        sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
