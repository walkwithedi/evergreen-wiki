#!/usr/bin/env python3
"""Keep shared/scripts/doc2kb_core.py a copy of a doc2kb release.

The converter is maintained in its own repository, walkwithedi/doc2kb; this one carries a copy,
and DOC2KB_VERSION records which release it is.

  sync_doc2kb.py --from DIR     copy DIR/doc2kb_core.py into shared/scripts/ and DIR/VERSION into
                                DOC2KB_VERSION (DIR: a doc2kb checkout or unpacked release); then
                                run scripts/sync_shared.py to refresh the skill copies
  sync_doc2kb.py --check DIR    exit 1 unless shared/scripts/doc2kb_core.py and DOC2KB_VERSION match
                                DIR (CI checks out the release named in DOC2KB_VERSION into DIR)

stdout: one result line. stderr: log. Exit codes: 0 ok; 1 copy differs; 2 bad arguments or files.
"""
import argparse
import logging
import os
import re
import shutil
import sys

log = logging.getLogger("sync_doc2kb")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = os.path.join(ROOT, "shared", "scripts", "doc2kb_core.py")
RECORD = os.path.join(ROOT, "DOC2KB_VERSION")


def read_version(path):
    try:
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
    except OSError as e:
        log.error("cannot read %s: %s", path, e)
        sys.exit(2)
    if not re.fullmatch(r"\d+\.\d+\.\d+", v):
        log.error("%s: %r is not a version X.Y.Z", path, v)
        sys.exit(2)
    return v


def read_bytes(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        log.error("cannot read %s: %s", path, e)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from", dest="source", metavar="DIR", help="doc2kb checkout to copy from")
    g.add_argument("--check", metavar="DIR", help="doc2kb checkout to compare with")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="default: LOG_LEVEL, else INFO")
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    src = a.source or a.check
    core = os.path.join(src, "doc2kb_core.py")
    version = read_version(os.path.join(src, "VERSION"))
    if a.source:
        read_bytes(core)
        shutil.copyfile(core, COPY)
        with open(RECORD, "w", encoding="utf-8", newline="\n") as f:
            f.write(version + "\n")
        log.info("copied %s (doc2kb %s) to %s", core, version, COPY)
        print("result: doc2kb %s copied; now run python3 scripts/sync_shared.py" % version)
        return 0
    recorded = read_version(RECORD)
    problems = []
    if recorded != version:
        problems.append("DOC2KB_VERSION says %s, the checkout is %s" % (recorded, version))
    if read_bytes(COPY) != read_bytes(core):
        problems.append("shared/scripts/doc2kb_core.py differs from doc2kb %s" % version)
    for p in problems:
        print("problem: " + p)
    print("result: " + ("copy differs; edit the converter in doc2kb, then run sync_doc2kb.py --from"
                        if problems else "doc2kb %s, copy current" % version))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
