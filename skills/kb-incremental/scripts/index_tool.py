#!/usr/bin/env python3
"""Maintain the file index (names.index in _kb.json, default 01_File-Index.md).

Columns: file name | source file name | source hash (the third column may be missing on
older rows). Three row styles are accepted and kept:
  a.md ｜ b.docx ｜ 3f2a…        (full-width bar, common in CJK libraries)
  a.md | b.docx | 3f2a…          (half-width bar)
  | a.md | b.docx | 3f2a… |      (Markdown table row)
A row is an entry when its first cell ends with .md. Every other line (title, header
fields, table header, separator) is kept as is.
Source hash: SHA-256 of every byte of the uploaded source file, first 16 hex digits.

Subcommands:
  hash   SOURCE                                           print the source hash
  check  INDEX --orig SOURCE_NAME [--name PROPOSED] [--file SOURCE]
                                                          duplicate-upload, content-hash and same-name checks
  add    INDEX --name FILE --orig SOURCE_NAME [--file SOURCE]      append a row (in place)
  update INDEX --name FILE --orig NEW_SOURCE_NAME [--file SOURCE]  update source name and hash (in place)
  write  INDEX --out PATH --date YYYY-MM-DD               sort rows, update entry count and date
Results go to stdout, logs to stderr. The header fields recognised are
"Entries:" / "条目数：" and "Last updated:" / "最后更新：".
"""
import argparse
import hashlib
import logging
import os
import re
import sys

log = logging.getLogger("index")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
BRACKET_NUM = re.compile(r"\s*[（(]\s*\d+\s*[)）]\s*$")
HASH_RE = re.compile(r"^[0-9a-f]{16}$")
SEP_RE = re.compile(r"\|?[\s:\-|｜]+\|?")
NAME_HEADERS = {"file name", "file", "name", "文件名"}
ORIG_HEADER_WORDS = ("source", "original", "原始文件名")
HASH_HEADERS = {"en": "Source hash", "zh": "原文哈希"}
COUNT_RE = re.compile(r"^(\s*(?:条目数|Entries)\s*[：:]\s*)\d+(.*)$", re.I)
DATE_RE = re.compile(r"^(\s*(?:最后更新|Last updated)[^：:]*[：:]\s*)\S+(.*)$", re.I)


def split_cells(line):
    s = line.strip()
    if "｜" in s:
        return [p.strip() for p in s.split("｜")], "full"
    if "|" in s:
        style = "half"
        if s.startswith("|"):
            s = s[1:]
            style = "md"
        if s.endswith("|"):
            s = s[:-1]
        return [p.strip() for p in s.split("|")], style
    return None, None


def parse(path):
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().replace("\r\n", "\n").split("\n")
    except OSError as e:
        log.error("cannot read index: %s", e)
        sys.exit(2)
    rows = []  # [line_idx, name, orig, style, hash]
    for i, line in enumerate(lines):
        cells, style = split_cells(line)
        if cells and len(cells) >= 2 and cells[0].lower().endswith(".md"):
            h = ""
            if len(cells) >= 3:
                h = cells[2].lower()
                if h and not HASH_RE.match(h):
                    log.warning("line %d: third column is not a source hash, treated as none: %r", i + 1, cells[2][:40])
                    h = ""
            if len(cells) > 3:
                log.warning("line %d has %d columns, only the first three are used: %s", i + 1, len(cells), line.strip()[:60])
            rows.append([i, cells[0], cells[1], style, h])
    log.info("read index %s: %d lines, %d entries (%d with source hash)",
             path, len(lines), len(rows), sum(1 for r in rows if r[4]))
    if len({r[3] for r in rows}) > 1:
        log.warning("index mixes row styles %s; new rows use the most common one", {r[3] for r in rows})
    return lines, rows


def main_style(rows):
    if not rows:
        return "md"
    counts = {}
    for r in rows:
        counts[r[3]] = counts.get(r[3], 0) + 1
    return max(counts, key=counts.get)


def fmt(name, orig, style, h=""):
    cells = [name, orig] + ([h] if h else [])
    if style == "md":
        return "| " + " | ".join(cells) + " |"
    if style == "half":
        return " | ".join(cells)
    return " ｜ ".join(cells)


def file_hash(path):
    d = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                d.update(chunk)
    except OSError as e:
        log.error("cannot read source file for hashing: %s", e)
        sys.exit(2)
    h = d.hexdigest()[:16]
    log.info("source hash %s <- %s (%d bytes)", h, path, os.path.getsize(path))
    return h


def norm_orig(s):
    """Base name, '(2)' style copy numbers removed, extension lower-cased."""
    base = os.path.basename(s.replace("\\", "/")).strip()
    stem, ext = os.path.splitext(base)
    stem2 = BRACKET_NUM.sub("", stem)
    if stem2 != stem:
        log.debug("normalised %r -> %r", stem, stem2)
    return (stem2 + ext.lower()).strip()


def save(path, lines):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
        log.info("created directory %s", d)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")
    log.info("wrote %s", path)


def cmd_hash(a):
    print(file_hash(a.file))


def cmd_check(a):
    lines, rows = parse(a.index)
    h = None
    if a.file:
        h = file_hash(a.file)
        same = [r for r in rows if r[4] == h]
        if same:
            for r in same:
                print(f"Content hash: HIT  line {r[0]+1}  {lines[r[0]].strip()}")
        else:
            print(f"Content hash: no hit (source hash {h}; {sum(1 for r in rows if r[4])} rows have a hash)")
    else:
        print("Content hash: skipped, no source file given")
    target = norm_orig(a.orig)
    log.info("duplicate check: source name %r normalised to %r", a.orig, target)
    dup = [r for r in rows if norm_orig(r[2]) == target]
    if dup:
        for r in dup:
            if not r[4]:
                note = " (row has no hash)"
            elif h is None:
                note = ""
            else:
                note = " (hash matches)" if r[4] == h else " (hash differs)"
            print(f"Source name: HIT{note}  line {r[0]+1}  {lines[r[0]].strip()}")
    else:
        print("Source name: no hit")
    if a.name:
        hit = [r for r in rows if r[1] == a.name]
        if hit:
            for r in hit:
                print(f"File name: HIT  line {r[0]+1}  {lines[r[0]].strip()}")
        else:
            print("File name: no hit")
        near = [r[1] for r in rows if r[1] != a.name and r[1].rsplit("_", 1)[0] == a.name.rsplit("_", 1)[0]]
        if near:
            log.info("same partition/topic/type already holds %d files: %s", len(near), near[:10])


def cmd_add(a):
    lines, rows = parse(a.index)
    if any(r[1] == a.name for r in rows):
        log.error("file name already indexed; use update for a new version: %s", a.name)
        sys.exit(4)
    new_line = fmt(a.name, a.orig, main_style(rows), file_hash(a.file) if a.file else "")
    insert_at = rows[-1][0] + 1 if rows else last_table_line(lines) + 1
    lines.insert(insert_at, new_line)
    log.info("inserted line %d: %s", insert_at + 1, new_line)
    save(a.index, lines)
    print(f"Added: {new_line}")


def last_table_line(lines):
    """Empty index: insert after the header/separator rows, else at the end."""
    idx = -1
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("|") or "｜" in s:
            idx = i
    return idx if idx >= 0 else len(lines) - 1


def cmd_update(a):
    lines, rows = parse(a.index)
    hit = [r for r in rows if r[1] == a.name]
    if not hit:
        log.error("file name not in index: %s", a.name)
        sys.exit(4)
    if len(hit) > 1:
        log.error("file name appears %d times; check by hand: %s", len(hit), a.name)
        sys.exit(4)
    i, name, old, style, old_h = hit[0]
    h = file_hash(a.file) if a.file else ""
    if not h and old_h:
        log.warning("no source file given; old hash %s on line %d no longer matches, cleared", old_h, i + 1)
    lines[i] = fmt(name, a.orig, style, h)
    log.info("line %d source name %r -> %r, hash %r -> %r", i + 1, old, a.orig, old_h, h)
    save(a.index, lines)
    print(f"Updated: {lines[i]}")


def is_header_row(cells):
    return (cells and len(cells) == 2 and cells[0].strip().lower() in NAME_HEADERS
            and any(w in cells[1].lower() for w in ORIG_HEADER_WORDS))


def extend_header(head):
    """When any entry has a hash, give a two-column header a third column."""
    out = list(head)
    for i, line in enumerate(out):
        cells, style = split_cells(line)
        if not is_header_row(cells):
            continue
        label = HASH_HEADERS["zh"] if cells[0] == "文件名" else HASH_HEADERS["en"]
        out[i] = fmt(cells[0], cells[1], style, label)
        log.info("header gains a third column: %s", out[i])
        if style == "md" and i + 1 < len(out) and SEP_RE.fullmatch(out[i + 1].strip()):
            out[i + 1] = "| --- | --- | --- |"
        break
    return out


def cmd_write(a):
    lines, rows = parse(a.index)
    if not rows and not a.allow_empty:
        log.error("index has no entries; refusing to write (use --allow-empty for a new library)")
        sys.exit(4)
    if rows:
        first, last = rows[0][0], rows[-1][0]
        row_idx = {r[0] for r in rows}
        between = [i for i in range(first, last + 1)
                   if i not in row_idx and lines[i].strip() and not SEP_RE.fullmatch(lines[i].strip())]
        names = [r[1] for r in rows]
        dups = sorted({n for n in names if names.count(n) > 1})
        if dups:
            log.warning("file names appear more than once: %s; check by hand", dups)
        head, tail = lines[:first], lines[last + 1:]
        if between:
            log.warning("%d non-entry lines sit between entries (group titles?); not sorting, header only", len(between))
            body = lines[first:last + 1]
        else:
            sorted_rows = sorted(rows, key=lambda r: r[1])
            body = [lines[r[0]].strip() for r in sorted_rows]
            moved = sum(1 for k, r in enumerate(sorted_rows) if r is not rows[k])
            log.info("sorted by file name: %d of %d rows moved", moved, len(rows))
        if any(r[4] for r in rows):
            head = extend_header(head)
    else:
        head, body, tail = lines, [], []
    n = len(rows)
    new_head, hit_count, hit_date = [], False, False
    for line in head:
        m = COUNT_RE.match(line)
        if m:
            line = f"{m.group(1)}{n}{m.group(2)}"
            hit_count = True
        m = DATE_RE.match(line)
        if m:
            line = f"{m.group(1)}{a.date}{m.group(2)}"
            hit_date = True
        new_head.append(line)
    if not hit_count:
        log.warning("no 'Entries:' field in the header; not updated")
    if not hit_date:
        log.warning("no 'Last updated:' field in the header; not updated")
    save(a.out, new_head + body + tail)
    print(f"Index written: {a.out}, {n} entries")



def utf8_stdio():
    """Windows consoles default to a legacy code page; library names may be CJK."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Maintain the file index")
    ap.add_argument("-v", "--verbose", action="store_true", help="same as --log-level DEBUG")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="default: LOG_LEVEL, else INFO")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("hash"); p.add_argument("file")
    p = sub.add_parser("check"); p.add_argument("index"); p.add_argument("--orig", required=True)
    p.add_argument("--name"); p.add_argument("--file")
    for c in ("add", "update"):
        p = sub.add_parser(c); p.add_argument("index"); p.add_argument("--name", required=True)
        p.add_argument("--orig", required=True); p.add_argument("--file")
    p = sub.add_parser("write"); p.add_argument("index"); p.add_argument("--out", required=True)
    p.add_argument("--date", required=True); p.add_argument("--allow-empty", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level="DEBUG" if a.verbose else a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    log.info("subcommand: %s", a.cmd)
    {"hash": cmd_hash, "check": cmd_check, "add": cmd_add, "update": cmd_update, "write": cmd_write}[a.cmd](a)


if __name__ == "__main__":
    main()
