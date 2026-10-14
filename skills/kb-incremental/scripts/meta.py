#!/usr/bin/env python3
"""The mechanical parts of placing one item (step 1, 2.3 and the front matter), so that the assistant
only judges and confirms.

  name --partition 05 --topic T --type T --title T (--max-len N | --language L)
      The topic file name <partition>_<topic>_<type>_<short title>.md: spaces and underscores inside a
      part become hyphens, characters not allowed in file names become hyphens too. Exit 3 when it is longer
      than the Table D limit (the result says by how much), so the short title can be shortened.
  date FILE [FILE ...] [--timezone TZ | --library ROOT]
      The document date to the minute in the library's time zone: the document's own metadata
      (Office core properties, mail Date, PDF dates) when it has one, which copying does not change;
      else the file system time, marked unreliable.
  entities SPEC --field NAME=WORDING [--field ...] [--keywords WORDING]
      Splits each field's wording (commas, semicolons, enumeration marks, not inside brackets) and
      looks every part up among the Table E names and aliases (exact match). A hit becomes [[Name]];
      an empty-value form of Table F, or a value Table F quotes as noise, is dropped with a note line;
      anything else is left to the assistant, with the names that differ only in case, spaces,
      hyphens or underscores, or where one holds the other and is at least half its length, listed as
      possible aliases. Keywords are never dropped and never registered. Exit 3 when Table E cannot
      be read: map by hand.
  terms SPEC BODY
      Every place in BODY where a Table B original wording occurs, with the line and its text, for
      the assistant to confirm one at a time. Exit 3 when Table B cannot be read.
  yaml FIELDS.json
      Front matter from a JSON object, keys in the order given: strings quoted and escaped, numbers,
      true and false, and ISO dates (2026-09-20, 2026-09-20T14:09) unquoted, lists as quoted lists;
      a key with null is left out. Partition and other zero-padded codes stay quoted when given as
      strings.

Read-only: results on stdout, nothing is written. stderr: log. Exit codes: 0 ok; 2 bad arguments or
unreadable file; 3 refused or not found (see above).
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("meta")
BAD_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
TABLE_LABEL = re.compile(r"(?:Table|表)\s*([A-F])\b")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?$")
OPEN, CLOSE = "([（【「《\"“", ")]）】」》\"”"
QUOTED = re.compile(r"[\"“「]([^\"”」]+)[\"”」]")


# ---------- name ----------

def part(text):
    s = BAD_CHARS.sub(" ", str(text)).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def file_name(partition, topic, typ, title):
    return "_".join([part(partition), part(topic), part(typ), part(title)]) + ".md"


# ---------- tables in the spec ----------

def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")
    except OSError as e:
        log.error("cannot read: %s", e)
        sys.exit(2)


def cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_row(line):
    return "|" in line and line.strip() != ""


def is_separator(line):
    return all(re.fullmatch(r":?-{3,}:?", c) for c in cells(line) if c) and "-" in line


def table(spec, letter):
    """(header cells, rows of cells) of the spec's Table <letter>, or None when no such table is
    found. The table is the run of pipe rows that follows the line naming it."""
    lines = spec.split("\n")
    for i, line in enumerate(lines):
        m = TABLE_LABEL.search(line)
        if not m or m.group(1) != letter or is_row(line):
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        rows = []
        while j < len(lines) and is_row(lines[j]):
            if not is_separator(lines[j]):
                rows.append(cells(lines[j]))
            j += 1
        if rows:
            return rows[0], rows[1:]
    return None


def column(header, words, default):
    for k, h in enumerate(header):
        if h.casefold() in words:
            return k
    return default


def listed(cell):
    """The parts of a semicolon list, without surrounding brackets."""
    return [x.strip().strip(OPEN + CLOSE).strip() for x in re.split(r"[;；]", cell or "") if x.strip()]


def entity_table(spec):
    t = table(spec, "E")
    if t is None:
        return None
    header, rows = t
    alias_col = column(header, ("aliases", "alias", "别名", "别称"), 2)
    out = []
    for r in rows:
        if r and r[0]:
            out.append((r[0], listed(r[alias_col]) if alias_col < len(r) else []))
    return out


def filter_table(spec):
    """(empty-value forms, quoted noise values) from Table F; empty sets when there is none."""
    t = table(spec, "F")
    if t is None:
        return set(), set()
    empty, noise = set(), set()
    for r in t[1]:
        if r:
            empty.update(x.casefold() for x in listed(r[0]))
        if len(r) > 1:
            noise.update(x.strip().casefold() for x in QUOTED.findall(r[1]))
    return empty, noise


def split_wording(text):
    """Split on commas, semicolons and enumeration marks that are not inside brackets."""
    out, buf, depth = [], [], 0
    for c in text:
        if c in "([（【《":
            depth += 1
        elif c in ")]）】》" and depth:
            depth -= 1
        if depth == 0 and c in ",，;；、":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def squash(s):
    return re.sub(r"[\s\-_.·]+", "", s.casefold())


def lookup(word, entities):
    """(names hit exactly, possible aliases)."""
    w = word.strip().strip(OPEN + CLOSE).strip()
    hit = [n for n, aliases in entities if w == n or w in aliases]
    if hit:
        return list(dict.fromkeys(hit)), []
    near = []
    sw = squash(w)
    for n, aliases in entities:
        for x in [n] + aliases:
            sx = squash(x)
            short, long_ = sorted((sw, sx), key=len)
            if short and (short == long_ or (len(short) >= 2 and len(short) * 2 >= len(long_) and short in long_)):
                near.append(n)
                break
    return [], list(dict.fromkeys(near))


def quote(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def entities_report(spec, fields, keywords):
    ents = entity_table(spec)
    if ents is None:
        return None
    empty, noise = filter_table(spec)
    out = [f"Table E: {len(ents)} entities; Table F: {len(empty)} empty-value forms, {len(noise)} quoted noise values"]
    yaml = []
    for name, wording, is_kw in [(n, w, False) for n, w in fields] + ([("keywords", keywords, True)] if keywords else []):
        out.append(f"{name}: {wording}")
        values, dropped = [], []
        for w in split_wording(wording):
            key = w.casefold()
            if not is_kw and (key in empty or key in noise):
                dropped.append(w)
                out.append(f"  {w} -> dropped ({'empty-value form' if key in empty else 'noise value'} in Table F)")
                continue
            hit, near = lookup(w, ents)
            if hit:
                values += [f"[[{h}]]" for h in hit]
                out.append(f"  {w} -> " + ", ".join(f"[[{h}]]" for h in hit))
            elif is_kw:
                values.append(w)
                out.append(f"  {w} -> plain text (keyword)" + (f"; possible alias of: {', '.join(near)}" if near else ""))
            else:
                values.append(w)
                out.append(f"  {w} -> no match: decide (entity to register, plain text, or alias)"
                           + (f"; possible alias of: {', '.join(near)}" if near else ""))
        values = list(dict.fromkeys(values))
        yaml.append(f"{name}: [" + ", ".join(quote(v) for v in values) + "]")
        if not is_kw and (dropped or not values):
            yaml.append(f"{name}_note: {quote(wording)}")
    out.append("draft front matter lines (unmatched wording still to be decided):")
    out += ["  " + y for y in yaml]
    return "\n".join(out) + "\n"


def terms_report(spec, body):
    t = table(spec, "B")
    if t is None:
        return None
    pairs = [(r[0], r[1] if len(r) > 1 else "") for r in t[1] if r and r[0]]
    lines = body.split("\n")
    out = [f"Table B: {len(pairs)} entries"]
    total = 0
    for orig, fixed in pairs:
        hits = [(i, ln) for i, ln in enumerate(lines, 1) if orig in ln]
        if not hits:
            continue
        out.append(f"{orig} -> {fixed}: {len(hits)} lines")
        for i, ln in hits[:20]:
            out.append(f"  line {i}: {ln.strip()[:200]}")
        if len(hits) > 20:
            out.append(f"  ({len(hits) - 20} more lines)")
        total += len(hits)
    if not total:
        out.append("no Table B wording in the body: Term fixes: none")
    else:
        out.append("check each line's context before changing it; the same letters may be another word")
    return "\n".join(out) + "\n"


# ---------- yaml ----------

def scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str) and DATE_RE.match(v):
        return v.replace(" ", "T")
    return quote(v)


def front_matter(fields):
    out = ["---"]
    for k, v in fields.items():
        if v is None:
            continue
        if isinstance(v, list):
            out.append(f"{k}: [" + ", ".join(quote(x) for x in v) + "]")
        elif isinstance(v, dict):
            raise ValueError(f"{k}: nested objects are not front matter values")
        else:
            out.append(f"{k}: {scalar(v)}")
    out.append("---")
    return "\n".join(out) + "\n"


# ---------- date ----------

def doc_date(path, tz):
    import doc2kb_core as core
    val, how = core.read_doc_modified(path)
    if not val:
        return "", "unknown"
    try:
        t = datetime.strptime(val, "%Y-%m-%d %H:%M").astimezone(kbconf.tzinfo(tz))
        val = t.strftime("%Y-%m-%d %H:%M")
    except (ValueError, kbconf.ConfigError):
        log.warning("time zone %s not applied", tz)
    return val, how


# ---------- main ----------

def main():
    kbconf.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("name")
    for k in ("--partition", "--topic", "--type", "--title"):
        p.add_argument(k, required=True)
    p.add_argument("--max-len", type=int, default=0, help="Table D file name limit")
    p.add_argument("--language", help="default limit for this language when the spec has no Table D")
    p = sub.add_parser("date")
    p.add_argument("files", nargs="+")
    p.add_argument("--timezone", help="IANA name or offset; default the library's, else UTC")
    p.add_argument("--library", help="library root, for its time zone")
    p = sub.add_parser("entities")
    p.add_argument("spec")
    p.add_argument("--field", action="append", default=[], metavar="NAME=WORDING")
    p.add_argument("--keywords", default="")
    p = sub.add_parser("terms")
    p.add_argument("spec")
    p.add_argument("body")
    p = sub.add_parser("yaml")
    p.add_argument("fields", help="JSON file with one object")
    kbconf.add_log_args(ap)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)

    if a.cmd == "name":
        limit = a.max_len or (kbconf.default_limits(a.language)[1] if a.language else 0)
        name = file_name(a.partition, a.topic, a.type, a.title)
        if not all(part(x) for x in (a.partition, a.topic, a.type, a.title)):
            print("refused: a part is empty once characters not allowed in file names are removed")
            return 3
        if limit and len(name) > limit:
            print(f"too long: {name} | {len(name)} characters, limit {limit}: shorten the short title by "
                  f"{len(name) - limit}")
            return 3
        print(name + (f" | {len(name)} of {limit} characters" if limit else ""))
        return 0
    if a.cmd == "date":
        tz = a.timezone
        if not tz and a.library:
            try:
                tz = kbconf.load_library(a.library)["timezone"]
            except (OSError, ValueError, kbconf.ConfigError) as e:
                log.warning("library time zone not read: %s", e)
        tz = tz or "UTC"
        for f in a.files:
            val, how = doc_date(f, tz)
            note = {"doc": "document metadata", "mail": "mail Date header",
                    "fs": "file system time, unreliable (copying changes it)"}.get(how, "not found")
            print(f"{os.path.basename(f)} | {val or 'date not in material'} | {note} | {tz}")
        return 0
    if a.cmd == "entities":
        fields = []
        for f in a.field:
            if "=" not in f:
                ap.error("--field takes NAME=WORDING")
            fields.append(tuple(f.split("=", 1)))
        out = entities_report(read_text(a.spec), fields, a.keywords)
        if out is None:
            print("Table E not found in the spec: map the entities by hand (entity-yaml.md)")
            return 3
        sys.stdout.write(out)
        return 0
    if a.cmd == "terms":
        out = terms_report(read_text(a.spec), read_text(a.body))
        if out is None:
            print("Table B not found in the spec: search the body for each entry by hand")
            return 3
        sys.stdout.write(out)
        return 0
    try:
        fields = json.loads(read_text(a.fields))
        if not isinstance(fields, dict):
            raise ValueError("the JSON must be one object")
        sys.stdout.write(front_matter(fields))
    except ValueError as e:
        print(f"refused: {e}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
