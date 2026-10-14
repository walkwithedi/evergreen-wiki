#!/usr/bin/env python3
"""Find the passages of a local library that answer a question, so that only those are read.

  find ROOT KEYWORD [KEYWORD ...] [--file PART] [--in FOLDER] [--all]
      Searches the Markdown files directly in ROOT (or in its subfolder FOLDER, such as the entities
      or notes folder), skipping what the skills never use as a source: other subfolders, names
      starting with an underscore or the snapshot prefix, and old versions (old suffix plus a time
      stamp). Keywords match without regard to case; a block matches when it holds any keyword (all
      of them with --all). For each match it prints the smallest block holding it (a numbered or
      bulleted item, a table row with its header row, a paragraph, the front matter), the headings
      above it and its line numbers, so the rest of that section can be read by line number.
  toc FILE
      The headings of FILE with the line range, size and number of list items or table rows of
      each section, for choosing sections by heading.

Read-only. Names come from the library's _kb.json (defaults when it has none). Output is capped
(--max-blocks, --max-per-file, --max-chars); the last line says what was left out.
stdout: the result. stderr: log. Exit code: 0 (also when nothing matched); 2 bad arguments.
"""
import argparse
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("kbfind")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
ITEM_RE = re.compile(r"^ {0,3}(?:\d{1,4}[.)]|[-*+])\s+")
STAMP_RE = re.compile(r"\d{8}")
BLOCK_CHARS = 700  # characters of one block printed; the rest is left to a read by line number


def ignored(name, names):
    """True for files the skills never use as a source (references/config.md, Ignored files)."""
    if not name.lower().endswith(".md") or name.startswith(("_", ".", names["snapshot_prefix"])):
        return True
    stem = name[:-3]
    old = names["old_suffix"]
    return bool(old) and old in stem and bool(STAMP_RE.search(stem.split(old)[-1]))


def read_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().replace("\r\n", "\n").split("\n")


def is_table_row(line):
    s = line.strip()
    return s.startswith("|") or (s.count(" | ") >= 1 and not ITEM_RE.match(line))


def is_separator(line):
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", line))


def blocks(lines):
    """[(first line, last line, heading path, kind, table header line or None)], line numbers from 1.
    Headings start sections; within one, a block is a list item with its continuation lines, a table
    row, a paragraph or the front matter."""
    out, path, i, n = [], [], 0, len(lines)
    if n and lines[0].strip() == "---":
        end = next((j for j in range(1, n) if lines[j].strip() == "---"), None)
        if end is not None:
            out.append((1, end + 1, (), "front matter", None))
            i = end + 1
    header = None  # the header row of the table being read
    while i < n:
        line = lines[i]
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            path = [p for p in path if p[0] < level] + [(level, m.group(2))]
            out.append((i + 1, i + 1, tuple(t for _, t in path[:-1]), "heading", None))
            header, i = None, i + 1
            continue
        if not line.strip():
            header, i = None, i + 1
            continue
        heads = tuple(t for _, t in path)
        if is_table_row(line):
            if header is None:
                header = i + 1
                out.append((i + 1, i + 1, heads, "table header", None))
            elif not is_separator(line):
                out.append((i + 1, i + 1, heads, "table row", header))
            i += 1
            continue
        header = None
        start, kind = i, "item" if ITEM_RE.match(line) else "paragraph"
        i += 1
        while i < n and lines[i].strip() and not HEADING_RE.match(lines[i]) and not ITEM_RE.match(lines[i]) \
                and not is_table_row(lines[i]):
            i += 1
        out.append((start + 1, i, heads, kind, None))
    return out


def library_names(root):
    """The library's names; root may be the library or one of its folders."""
    for path in (root, os.path.dirname(os.path.normpath(root))):
        if os.path.isfile(os.path.join(path, kbconf.KB_JSON)):
            try:
                return kbconf.load_library(path)["names"]
            except (OSError, ValueError, kbconf.ConfigError) as e:
                log.warning("cannot read %s: %s; using the default names", kbconf.KB_JSON, e)
    return kbconf.resolve_names()


def shown(lines, b):
    text = "\n".join(lines[b[0] - 1:b[1]])
    if b[4]:
        text = lines[b[4] - 1] + "\n" + text
    if len(text) > BLOCK_CHARS:
        text = text[:BLOCK_CHARS].rstrip() + f" ... (block continues to line {b[1]})"
    return text


def find(root, keywords, part="", folder="", need_all=False, max_blocks=30, max_per_file=10, max_chars=12000):
    names = library_names(root)
    where = os.path.join(root, folder) if folder else root
    keys = [k.casefold() for k in keywords if k.strip()]
    files = sorted(f for f in os.listdir(where)
                   if os.path.isfile(os.path.join(where, f)) and not ignored(f, names)
                   and (not part or part.casefold() in f.casefold()))
    found = []
    for f in files:
        lines = read_lines(os.path.join(where, f))
        hits = []
        for b in blocks(lines):
            text = "\n".join(lines[b[0] - 1:b[1]]).casefold()
            got = [k for k in keys if k in text]
            if got and (not need_all or len(got) == len(keys)):
                hits.append(b)
        if hits:
            found.append((f, lines, hits))
    found.sort(key=lambda x: (-len(x[2]), x[0]))
    total = sum(len(h) for _, _, h in found)
    out = [f"keywords: {', '.join(keywords)}{' (all)' if need_all else ''} | folder: {folder or '(library root)'}"
           f" | files searched: {len(files)} | files with hits: {len(found)} | blocks: {total}"]
    used, printed, left_files = len(out[0]), 0, []
    for f, lines, hits in found:
        if printed >= max_blocks or used >= max_chars:
            left_files.append(f"{f} ({len(hits)})")
            continue
        size = sum(len(x) + 1 for x in lines)
        head = f"\n== {f} | {len(hits)} blocks | {size} characters, {len(lines)} lines"
        out.append(head)
        used += len(head)
        for k, b in enumerate(hits):
            if k >= max_per_file or printed >= max_blocks or used >= max_chars:
                out.append(f"({len(hits) - k} more blocks in this file; narrow the keywords or read by line number)")
                break
            where_in = " > ".join(b[2]) or "(no heading)"
            lines_txt = f"line {b[0]}" if b[0] == b[1] else f"lines {b[0]}-{b[1]}"
            text = f"-- {lines_txt} | {where_in}" + ("" if b[3] in ("item", "paragraph", "table row") else
                                                     f" | {b[3]}") + "\n" + shown(lines, b)
            out.append(text)
            used += len(text)
            printed += 1
    if left_files:
        out.append(f"\nnot shown (cap reached): {', '.join(left_files)}")
    if not found:
        out.append("no match")
    return "\n".join(out) + "\n"


def toc(path):
    lines = read_lines(path)
    size = sum(len(x) + 1 for x in lines)
    heads = [(i + 1, len(m.group(1)), m.group(2)) for i, ln in enumerate(lines)
             for m in [HEADING_RE.match(ln)] if m]
    out = [f"{os.path.basename(path)} | {size} characters, {len(lines)} lines | headings: {len(heads)}"]
    starts = [1] + [h[0] for h in heads]
    ends = [h[0] - 1 for h in heads] + [len(lines)]
    titles = [(0, "(before the first heading)")] + [(lv, t) for _, lv, t in heads]
    for start, end, (level, title) in zip(starts, ends, titles):
        body = lines[start - 1:end] if level == 0 else lines[start:end]
        if level == 0 and not any(x.strip() for x in body):
            continue
        chars = sum(len(x) + 1 for x in body)
        items = sum(1 for x in body if ITEM_RE.match(x))
        rows = sum(1 for x in body if is_table_row(x) and not is_separator(x))
        extra = (f" | {items} items" if items else "") + (f" | {rows} table rows" if rows else "")
        out.append(f"{start}-{end} | {'#' * level + ' ' if level else ''}{title} | {chars} characters{extra}")
    return "\n".join(out) + "\n"


def main():
    kbconf.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find", help="matching blocks of the library's files")
    p.add_argument("root", help="library root folder")
    p.add_argument("keywords", nargs="+")
    p.add_argument("--file", default="", help="only files whose name contains this")
    p.add_argument("--in", dest="folder", default="", help="a subfolder of the library instead of its root")
    p.add_argument("--all", action="store_true", help="a block must hold every keyword")
    p.add_argument("--max-blocks", type=int, default=30)
    p.add_argument("--max-per-file", type=int, default=10)
    p.add_argument("--max-chars", type=int, default=12000)
    p = sub.add_parser("toc", help="sections of one file with line ranges")
    p.add_argument("file")
    kbconf.add_log_args(ap)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    if a.cmd == "toc":
        if not os.path.isfile(a.file):
            print(f"not a file: {a.file}", file=sys.stderr)
            return 2
        sys.stdout.write(toc(a.file))
        return 0
    where = os.path.join(a.root, a.folder) if a.folder else a.root
    if not os.path.isdir(where) or (a.folder and (os.path.isabs(a.folder) or ".." in a.folder.replace("\\", "/").split("/"))):
        print(f"not a library folder: {where}", file=sys.stderr)
        return 2
    sys.stdout.write(find(a.root, a.keywords, a.file, a.folder, a.all, a.max_blocks, a.max_per_file, a.max_chars))
    return 0


if __name__ == "__main__":
    sys.exit(main())
