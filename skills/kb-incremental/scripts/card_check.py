#!/usr/bin/env python3
"""Rewrite check for summary files (after a "trigger" in step 5, before delivery).

For every summary file rewritten in full: status card, change log, open items, glossary,
entity pages (with overview) and the spec itself. Compares the old and new versions so
that a rewrite never silently drops existing content:

  1. Items kept: every item of the old version (numbered item, list item or paragraph,
     compared without its number or bullet) must appear unchanged in the new version, or
     its old wording must appear in the change list. Change list lines:
       Item X: [old wording] -> [new wording]
       Delete item X: [old wording] (reason)
     (the Chinese forms 第X条：… → … and 删除第X条：… are accepted too).
     Anything else is reported as an unexplained loss.
  2. Length: new body shorter than --min-ratio (default 0.7) of the old one = suspected trimming.
  3. Locked fields: front-matter "type"/"entity_type" (类型/实体类型) must not change,
     aliases may only grow, and the first level-1 heading (entity name) must not change.
Header field lines (last updated, entries, version) change on every rewrite and are ignored.

stdout: self-check lines and problems. stderr: log.
Exit code: 0 passed; 3 failed (do not deliver); 2 bad arguments or unreadable file.
Usage: python3 card_check.py OLD NEW [--changes CHANGES.txt] [--min-ratio 0.7]
"""
import argparse
import logging
import os
import re
import sys

log = logging.getLogger("card_check")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"

LOCKED_FIELDS = ("type", "entity_type", "类型", "实体类型")
UNION_FIELDS = ("aliases",)
# Number or bullet prefixes: 1. 1、 1) (1) （1） 第1条： Item 1: - * ·
PREFIX_RE = re.compile(r"^\s*(?:第\s*\d+\s*条\s*[：:、.]?|item\s*\d+\s*[:.]?|[（(]\s*\d+\s*[)）]|\d+\s*[.、．)）]|[-*·•])\s*", re.I)
NUMBER_RE = re.compile(r"^\s*(?:第\s*(\d+)\s*条|item\s*(\d+)|[（(]\s*(\d+)\s*[)）]|(\d+)\s*[.、．)）])", re.I)
SPACE_RE = re.compile(r"[\s\u3000]+")
HEAD_FIELD_RE = re.compile(r"^(最后更新|更新日期|条目数|版本|last updated|updated|entries|version)[^：:]{0,6}[：:]", re.I)
CHANGE_NUM_RE = re.compile(r"第\s*(\d+)\s*条|item\s*(\d+)", re.I)


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except OSError as e:
        log.error("cannot read: %s", e)
        sys.exit(2)


def split_frontmatter(text):
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], lines[i + 1:]
        log.warning("front matter has no closing ---; treated as no front matter")
    return [], lines


def parse_frontmatter(fm_lines):
    fields = {}
    for line in fm_lines:
        m = re.match(r"^([^\s:#][^:]*?)\s*:\s*(.*)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()
    return fields


def list_items(value):
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return {x.strip().strip("\"'") for x in v.split(",") if x.strip()}


def norm(text):
    return SPACE_RE.sub("", PREFIX_RE.sub("", text, count=1))


def units(body_lines):
    """Split the body into items: headings and code blocks excluded; each non-empty line is one item, compared without its number or bullet."""
    out = []
    section = ""
    in_code = False
    for i, line in enumerate(body_lines):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        if s.startswith("#"):
            section = s.lstrip("#").strip()
            continue
        if re.fullmatch(r"\|?[\s:\-|｜]+\|?", s) or HEAD_FIELD_RE.match(s):
            continue
        key = norm(s)
        if not key:
            continue
        m = NUMBER_RE.match(s)
        num = next((g for g in m.groups() if g), None) if m else None
        out.append({"line": i + 1, "text": s, "key": key, "num": num, "section": section})
    return out


def first_h1(body_lines):
    for line in body_lines:
        if re.match(r"^#\s+\S", line):
            return line[1:].strip()
    return None


def snippet(text, n=50):
    return text if len(text) <= n else text[:n] + "…"



def utf8_stdio():
    """Windows consoles default to a legacy code page; library names may be CJK."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Rewrite check for summary files")
    ap.add_argument("old", help="version before the rewrite, read in full from the library")
    ap.add_argument("new", help="rewritten version about to be delivered")
    ap.add_argument("--changes", help="change list, one line each: Item X: [old] -> [new]")
    ap.add_argument("--min-ratio", type=float, default=0.7, help="minimum new/old body length ratio, default 0.7")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="default: LOG_LEVEL, else INFO")
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    log.info("old: %s; new: %s; changes: %s", a.old, a.new, a.changes or "none")

    old_fm, old_body = split_frontmatter(read(a.old))
    new_fm, new_body = split_frontmatter(read(a.new))
    changes_raw = read(a.changes) if a.changes else ""
    changes_key = SPACE_RE.sub("", changes_raw)
    changed_nums = {x or y for x, y in CHANGE_NUM_RE.findall(changes_raw)}
    log.info("change list: %d characters, items referenced %s", len(changes_raw), sorted(changed_nums, key=int) or "none")

    problems = []

    # Locked fields and title
    of, nf = parse_frontmatter(old_fm), parse_frontmatter(new_fm)
    for k in LOCKED_FIELDS:
        if k in of and of.get(k) != nf.get(k):
            problems.append(f"locked field changed: {k} {of[k]!r} -> {nf.get(k)!r}")
    for k in UNION_FIELDS:
        if k in of:
            lost = list_items(of[k]) - list_items(nf.get(k, ""))
            if lost:
                problems.append(f"{k} lost entries: {sorted(lost)}")
    oh, nh = first_h1(old_body), first_h1(new_body)
    if oh and oh != nh:
        problems.append(f"level-1 heading changed: {oh!r} -> {nh!r}")

    # Items kept
    ou, nu = units(old_body), units(new_body)
    new_keys = {u["key"] for u in nu}
    old_keys = {u["key"] for u in ou}
    kept = by_changes = 0
    missing = []
    for u in ou:
        if u["key"] in new_keys:
            kept += 1
        elif u["key"] in changes_key or (u["num"] and u["num"] in changed_nums):
            by_changes += 1
            log.debug("explained by change list: line %d %s", u["line"], snippet(u["text"]))
        else:
            missing.append(u)
            log.info("unexplained loss: line %d [%s] %s", u["line"], u["section"] or "no section", snippet(u["text"]))
    added = sum(1 for u in nu if u["key"] not in old_keys)

    # Length
    old_len = sum(len(u["key"]) for u in ou)
    new_len = sum(len(u["key"]) for u in nu)
    ratio = new_len / old_len if old_len else 1.0
    log.info("body characters: old %d, new %d, ratio %.2f", old_len, new_len, ratio)
    if old_len and ratio < a.min_ratio:
        problems.append(f"shrunk: new body is {ratio:.0%} of the old, below {a.min_ratio:.0%}")

    print(f"Self-check: {len(ou)} existing items, {kept} kept, {by_changes} explained by the change list, "
          f"{added} added, {len(missing)} unexplained losses; body characters {old_len} -> {new_len}")
    for u in missing[:30]:
        print(f"  missing: old line {u['line']} [{u['section'] or 'no section'}] {snippet(u['text'])}")
    if len(missing) > 30:
        print(f"  ... {len(missing)} in total, first 30 shown")
    if missing:
        problems.append(f"{len(missing)} unexplained losses")
    for p in problems:
        print(f"Problem: {p}")
    if problems:
        print("Result: FAILED, do not deliver")
        sys.exit(3)
    print("Result: passed")


if __name__ == "__main__":
    main()
