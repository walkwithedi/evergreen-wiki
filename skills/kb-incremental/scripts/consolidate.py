#!/usr/bin/env python3
"""The mechanical parts of consolidation (references/consolidate.md): which files are due, writing key
conclusions into a filed topic file without touching its body, and clearing the queue.

  list QUEUE [--limit N]
      The rows of the consolidation queue (names.consolidation_queue), oldest first: file name,
      source file, filed time, close-read. --limit gives the next round only.
  fill TOPIC HEAD OUT
      TOPIC is a filed topic file that carries the pending mark (prep.py file --close-read). Writes
      OUT = HEAD, one blank line, then TOPIC's body exactly as it is (everything after the mark).
      Refused: no mark in TOPIC, an existing OUT, an empty HEAD or one that still carries the mark,
      front matter that is not closed, and a HEAD that drops the original line TOPIC's head has.
      The written body is compared with the old one byte for byte before the result is reported.
  done QUEUE --name FILE [--name FILE ...]
      Removes those rows from a work-folder copy of the queue. Refuses a queue that sits in a library
      root (next to _kb.json): delivery puts the copy back.

stdout: the result. stderr: log. Exit codes: 0 ok; 2 bad arguments or unreadable file; 3 refused.
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("consolidate")
PENDING_MARK = "<!-- kb:conclusions-pending -->"
YES = ("yes", "是", "y", "true")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except OSError as e:
        log.error("cannot read %s: %s", path, e)
        sys.exit(2)


def cells(line):
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def rows(lines):
    """[(line index, [file, source, filed, close-read])] for every queue row."""
    out = []
    for i, ln in enumerate(lines):
        c = cells(ln)
        if c and len(c) >= 4 and c[0].lower().endswith(".md"):
            out.append((i, c[:4]))
    return out


def cmd_list(a):
    lines = read(a.queue).split("\n")
    rs = sorted(rows(lines), key=lambda r: r[1][2])
    print(f"queue: {len(rs)} files" + (f", oldest filed {rs[0][1][2]}" if rs else ""))
    for _, c in rs[:a.limit or None]:
        print(f"{c[0]} | {c[1]} | {c[2]} | {'close-read' if c[3].lower() in YES else 'check only'}")
    if a.limit and len(rs) > a.limit:
        print(f"next round: {a.limit}; {len(rs) - a.limit} wait for later rounds")
    return 0


def head_closed(head):
    lines = head.split("\n")
    if not lines or lines[0].strip() != "---":
        return True
    return any(ln.strip() == "---" for ln in lines[1:])


def front_value(head, key):
    lines = head.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for ln in lines[1:]:
        if ln.strip() == "---":
            return None
        if ln.startswith(key + ":"):
            return ln
    return None


def cmd_fill(a):
    old, head = read(a.topic), read(a.head)
    problems = []
    if os.path.exists(a.out):
        problems.append("output file exists")
    if PENDING_MARK not in old:
        problems.append("the topic file has no pending mark; it was consolidated already or filed in full mode")
    if not head.strip():
        problems.append("head is empty")
    elif PENDING_MARK in head:
        problems.append("the new head still carries the pending mark")
    elif not head_closed(head):
        problems.append("front matter opened with --- is not closed")
    if PENDING_MARK in old:
        old_head = old.split(PENDING_MARK, 1)[0]
        orig = front_value(old_head, "original")
        if orig and front_value(head, "original") != orig:
            problems.append("the new head drops or changes the original line: " + orig)
    if problems:
        for p in problems:
            print(f"refused: {p}")
        return 3
    body = old.split(PENDING_MARK, 1)[1].lstrip("\n")
    text = head.rstrip("\n") + "\n\n" + body
    with open(a.out, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    written = read(a.out)
    if not written.endswith(body) or PENDING_MARK in written:
        os.remove(a.out)
        print("refused: the body did not come through unchanged; nothing written")
        return 3
    print(f"filled: {os.path.basename(a.out)} | head {len(head.rstrip(chr(10)).split(chr(10)))} lines"
          f" | body unchanged, {len(body)} characters")
    return 0


def cmd_done(a):
    if os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(a.queue)), kbconf.KB_JSON)):
        print("refused: the queue sits in a library root; work on the copy in the work folder")
        return 3
    lines = read(a.queue).rstrip("\n").split("\n")
    want = set(a.name)
    hits = [(i, c[0]) for i, c in rows(lines) if c[0] in want]
    drop, found = {i for i, _ in hits}, {n for _, n in hits}
    for n in sorted(want - found):
        print(f"not in the queue: {n}")
    kept = [ln for i, ln in enumerate(lines) if i not in drop]
    with open(a.queue, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(kept) + "\n")
    print(f"removed {len(drop)} rows; {len(rows(kept))} files still wait")
    return 0


def main():
    kbconf.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("queue"); p.add_argument("--limit", type=int, default=0)
    p = sub.add_parser("fill"); p.add_argument("topic"); p.add_argument("head"); p.add_argument("out")
    p = sub.add_parser("done"); p.add_argument("queue"); p.add_argument("--name", action="append", required=True)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    return {"list": cmd_list, "fill": cmd_fill, "done": cmd_done}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
