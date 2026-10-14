#!/usr/bin/env python3
"""Assemble a topic file (output and delivery): the head, one blank line, then the body as it is.

The head is what the assistant writes: the metadata (YAML front matter or the text header) and the
key conclusions. The body is the cleaned source text that clean.py wrote, with term fixes and masking
made in place. The body is copied as it is (Windows line endings become \n, leading blank lines are
dropped), so the assistant never types it out again.

Refused: an output file that already exists (nothing is overwritten), an empty body, and a head that
opens front matter with --- without closing it.

stdout: one result line. stderr: log.
Exit code: 0 written; 3 refused; 2 bad arguments or unreadable file.
Usage: python3 assemble.py HEAD BODY OUT
"""
import argparse
import logging
import os
import sys

log = logging.getLogger("assemble")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except OSError as e:
        log.error("cannot read: %s", e)
        sys.exit(2)


def front_matter_closed(head):
    """True when the head has no front matter, or its opening --- line has a closing --- line."""
    lines = head.split("\n")
    if not lines or lines[0].strip() != "---":
        return True
    return any(line.strip() == "---" for line in lines[1:])


def assemble(head, body):
    return head.rstrip("\n") + "\n\n" + body.lstrip("\n")


def utf8_stdio():
    """Windows consoles default to a legacy code page; library names may be CJK."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Assemble a topic file from its head and its cleaned body")
    ap.add_argument("head", help="metadata and key conclusions, written by the assistant")
    ap.add_argument("body", help="cleaned body (clean.py output, term fixes made in place)")
    ap.add_argument("out", help="topic file to write, in <work>/out/")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="default: LOG_LEVEL, else INFO")
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    head, body = read(a.head), read(a.body)
    problems = []
    if os.path.exists(a.out):
        problems.append("output file exists; choose another name or remove the old copy from the work folder")
    if not body.strip():
        problems.append("body is empty")
    if not head.strip():
        problems.append("head is empty")
    elif not front_matter_closed(head):
        problems.append("front matter opened with --- is not closed")
    if problems:
        for p in problems:
            print(f"refused: {p}")
        return 3
    text = assemble(head, body)
    try:
        with open(a.out, "x", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except OSError as e:
        log.error("cannot write: %s", e)
        return 2
    log.info("written: %s", a.out)
    print(f"assembled: {os.path.basename(a.out)} | head {len(head.rstrip(chr(10)).split(chr(10)))} lines"
          f" | body {len(body.strip())} characters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
