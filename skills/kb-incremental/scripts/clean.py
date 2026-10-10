#!/usr/bin/env python3
"""Structural cleanup (step 2.1). Formatting only: body information is never reduced.

Five actions:
  1. drop the extraction header a converter put at the top (path lines, tool credits, empty headings)
  2. parse tables, drop columns whose cells are all empty, rebuild the separator row
  3. demote headings longer than the limit to body text
  4. demote headings ending in a full stop, semicolon or colon
  5. squeeze runs of blank lines to one

stdout: one result line. stderr: a log line per change (line number, action, snippet).
Usage: python3 clean.py SRC DST [--max-heading-len 90] [--header-scan 12]
Take --max-heading-len from Table D of the library spec.
"""
import argparse
import logging
import os
import re
import sys

log = logging.getLogger("clean")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"

HEADING_RE = re.compile(r"^(#{1,6})\s*(.*?)\s*$")
EMPTY_HEADING_RE = re.compile(r"^#{1,6}\s*$")
# Extraction header patterns: applied only before the first body line; prefer missing one over deleting body
HEADER_PATTERNS = [
    re.compile(r"^\s*(原始)?(文件)?路径\s*[：:]"),
    re.compile(r"^\s*(source|path|file|filepath|源文件)\s*[：:]", re.I),
    re.compile(r"(converted|generated|extracted)\s+(by|with|from)", re.I),
    re.compile(r"(markitdown|pandoc|doc2kb|docling|mammoth|pdftotext)", re.I),
    re.compile(r"^\s*(转换工具|提取工具|由.{1,20}(转换|生成|提取))"),
    re.compile(r"^\s*[A-Za-z]:\\"),
    re.compile(r"^\s*/(home|mnt|tmp|Users|data)/"),
]
HEADER_CONTENT = 0
HEADING_END_PUNCT = ("。", "；", "：", ";", ":", ".")


def snippet(text, n=40):
    text = text.replace("\n", " ")
    return text if len(text) <= n else text[:n] + "…"


def content_len(text):
    """Count substantive characters only: no whitespace, table or heading markup."""
    return len(re.sub(r"[\s|#:\-]", "", text))


def strip_extraction_header(lines, scan):
    """Only look at the first `scan` lines, before the first substantive body line."""
    global HEADER_CONTENT
    removed = 0
    out_start = 0
    for i, line in enumerate(lines[:scan]):
        s = line.strip()
        if s == "":
            continue
        if EMPTY_HEADING_RE.match(s):
            log.info("header line %d: drop empty heading: %r", i + 1, s)
            lines[i] = None
            removed += 1
            continue
        if any(p.search(s) for p in HEADER_PATTERNS):
            log.info("header line %d: drop tool-generated line: %s", i + 1, snippet(s))
            HEADER_CONTENT += content_len(s)
            lines[i] = None
            removed += 1
            continue
        log.debug("header scan stopped at line %d (body text): %s", i + 1, snippet(s))
        out_start = i
        break
    else:
        log.debug("no body text within the first %d lines", scan)
    kept = [l for l in lines if l is not None]
    log.info("header done: dropped %d lines (scanned to line %d)", removed, out_start + 1)
    return kept, removed


def is_table_line(line):
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_sep_row(cells):
    return all(re.fullmatch(r"\s*:?-{1,}:?\s*", c) for c in cells if c is not None) and len(cells) > 0


UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def split_row(line):
    """Split on unescaped pipes; an escaped \\| inside a cell is kept as is."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip() for c in UNESCAPED_PIPE.split(s)]


def clean_table(block, start_lineno, table_no):
    rows = [split_row(l) for l in block]
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    sep_idx = [i for i, r in enumerate(rows) if is_sep_row(r)]
    data_rows = [r for i, r in enumerate(rows) if i not in sep_idx]
    if not data_rows:
        log.warning("table %d (line %d) has only separator rows, kept as is", table_no, start_lineno)
        return block, 0
    empty_cols = [c for c in range(width) if all(r[c] == "" for r in data_rows)]
    if len(empty_cols) == width:
        log.warning("table %d (line %d) is entirely empty, kept as is", table_no, start_lineno)
        return block, 0
    keep = [c for c in range(width) if c not in empty_cols]
    if empty_cols:
        log.info("table %d (line %d): drop empty columns %s (%d -> %d columns)",
                 table_no, start_lineno, [c + 1 for c in empty_cols], width, len(keep))
    else:
        log.debug("table %d (line %d): no empty columns", table_no, start_lineno)
    out = []
    header_done = False
    for i, r in enumerate(rows):
        if i in sep_idx:
            continue
        out.append("| " + " | ".join(r[c] for c in keep) + " |")
        if not header_done:
            out.append("| " + " | ".join("---" for _ in keep) + " |")
            header_done = True
    if not sep_idx:
        log.info("table %d (line %d) had no separator row; added one after the first row", table_no, start_lineno)
    return out, len(empty_cols)


def process_tables(lines):
    out, i, total, table_no = [], 0, 0, 0
    while i < len(lines):
        if is_table_line(lines[i]):
            j = i
            while j < len(lines) and is_table_line(lines[j]):
                j += 1
            table_no += 1
            new_block, n = clean_table(lines[i:j], i + 1, table_no)
            out.extend(new_block)
            total += n
            i = j
        else:
            out.append(lines[i])
            i += 1
    log.info("tables done: %d tables, %d empty columns dropped", table_no, total)
    return out, total


def demote_headings(lines, max_len):
    count = 0
    out = []
    for n, line in enumerate(lines, 1):
        m = HEADING_RE.match(line)
        if m and m.group(2):
            text = m.group(2)
            if len(text) > max_len:
                log.info("demote heading line %d: length %d > %d: %s", n, len(text), max_len, snippet(text))
                out.append(text)
                count += 1
                continue
            if text.endswith(HEADING_END_PUNCT):
                log.info("demote heading line %d: ends with %r: %s", n, text[-1], snippet(text))
                out.append(text)
                count += 1
                continue
        out.append(line)
    log.info("headings done: %d demoted (limit %d characters)", count, max_len)
    return out, count


def compress_blank(lines):
    out, count, run = [], 0, 0
    for n, line in enumerate(lines, 1):
        if line.strip() == "":
            run += 1
            if run == 1:
                out.append("")
            elif run == 2:
                count += 1
                log.debug("squeezed blank lines near line %d", n - 1)
        else:
            run = 0
            out.append(line)
    log.info("blank lines done: %d runs squeezed", count)
    return out, count



def utf8_stdio():
    """Windows consoles default to a legacy code page; library names may be CJK."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

def main():
    utf8_stdio()
    ap = argparse.ArgumentParser(description="Structural cleanup of a converted document")
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--max-heading-len", type=int, default=90)
    ap.add_argument("--header-scan", type=int, default=12)
    ap.add_argument("-v", "--verbose", action="store_true", help="same as --log-level DEBUG")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="default: LOG_LEVEL, else INFO")
    a = ap.parse_args()
    logging.basicConfig(level="DEBUG" if a.verbose else a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    log.info("cleaning %s -> %s", a.src, a.dst)
    try:
        with open(a.src, encoding="utf-8") as f:
            raw = f.read()
    except UnicodeDecodeError:
        log.error("not UTF-8: %s", a.src)
        sys.exit(2)
    except OSError as e:
        log.error("cannot read input: %s", e)
        sys.exit(2)
    before_chars = len(raw)
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    log.info("read %d lines, %d characters", len(lines), before_chars)

    lines, n_head = strip_extraction_header(lines, a.header_scan)
    lines, n_col = process_tables(lines)
    lines, n_demote = demote_headings(lines, a.max_heading_len)
    lines, n_blank = compress_blank(lines)

    text = "\n".join(lines).strip("\n") + "\n"
    try:
        with open(a.dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except OSError as e:
        log.error("cannot write output: %s", e)
        sys.exit(3)
    after_chars = len(text)
    log.info("wrote %d lines, %d characters (%+d)", len(lines), after_chars, after_chars - before_chars)
    lost = content_len(raw) - HEADER_CONTENT - content_len(text)
    log.info("substantive characters: source %d, header %d, cleaned %d, difference %d",
             content_len(raw), HEADER_CONTENT, content_len(text), lost)
    if lost != 0:
        log.warning("substantive character difference is %d, body text may have been changed; revert and check", lost)
    print(f"Structural cleanup: header lines dropped {n_head}, empty columns dropped {n_col}, "
          f"headings demoted {n_demote}, blank runs squeezed {n_blank}")


if __name__ == "__main__":
    main()
