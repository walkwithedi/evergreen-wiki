#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kb_batch.py - knowledge-base batch files: write them from converted documents, split them back.

A batch file holds several converted source documents for one ingest run:

    <header: batch name, tier, character limit, note for the reader, source table>

    ---

    # S01 minutes.docx
    > Original path: ...
    > Document last modified: ...
    > Extracted: ...

    ## A heading of the document

    A paragraph. ^s01-p1

    - a list item ^s01-p2

    | a | table |
    | --- | --- |
    | 1 | 2 |

    ^s01-p3

    # S02 schedule.xlsx · 1/2
    ...

- Sources are numbered S01, S02, ... over one run; a source too long for one batch is cut
  into parts at headings (the highest level that helps first), else between blocks, and its
  parts keep the source number and are marked "· k/n" in the section heading.
- Paragraphs and list items carry an anchor at their end, a whole table one anchor on the line
  below it (Obsidian block references). Headings, quoted lines (notes added by the converter),
  rules, picture placeholders and comments carry none. Anchors are numbered over the whole
  source, across parts.
- Headings of the document are demoted by one level so the source sections stay level 1.

Splitting back joins the parts of each source, restores the heading levels and rewrites the
anchors from ^s01-p3 to ^p3, so a link [[source file#^p3]] reaches the paragraph.

Python 3 standard library only.

Usage:
  kb_batch.py split BATCH.md [BATCH.md ...] -o OUTDIR [--names NAMES.json]
      NAMES.json maps a source number or original file name to the output file name;
      the default is the original file name with .md in place of its extension.
"""
import argparse
import json
import logging
import os
import re
import sys

log = logging.getLogger('kb_batch')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'

# Characters per batch for each tier; a library may set its own (_kb.json "batch_chars").
TIER_CHARS = {'weak': 20000, 'strong': 100000}
DEFAULT_TIER = 'weak'
SETTINGS_FILE = '_kb.json'

SECTION_RE = re.compile(r'^# (S\d{2,}) (.+?)(?: · (\d+)/(\d+))?$')
HEADING_RE = re.compile(r'^(#{1,6}) ')
LIST_RE = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+')
NO_ANCHOR_RE = re.compile(r'^(?:>|---\s*$|<!--|\[(?:Image|图)[ :：])')

# Labels of the batch header; doc2kb passes its own in the chosen language.
LABELS = {
    'title': 'Batch file %s (%d of %d)',
    'limit': 'Tier: %s  Character limit: %d',
    'note': ('Each source is a section headed "# Snn"; a source cut into parts is marked "· k/n". '
             'Paragraphs and list items end with an anchor such as ^s01-p2, a table has one on the '
             'line below it. Quote sentences exactly as written and cite the anchor.'),
    'table_head': '| Source | File | Original path | Modified | Characters | Part |',
}


def source_id(n):
    return 'S%02d' % n


def anchor_prefix(sid):
    return sid.lower() + '-p'


# ---------------------------------------------------------------- limits

def read_settings(library):
    """tier and batch_chars from a library's settings file; {} when it has none."""
    path = library
    if os.path.isdir(path):
        path = os.path.join(path, SETTINGS_FILE)
    try:
        with open(path, encoding='utf-8') as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError('cannot read %s: %s' % (path, e))
    if not isinstance(raw, dict):
        raise ValueError('%s is not a JSON object' % path)
    return {k: raw[k] for k in ('tier', 'batch_chars') if k in raw}


def batch_limit(tier=None, chars=None, library=None):
    """(characters per batch, tier). Explicit values win over the library's settings,
    batch_chars over tier; without any the weak tier applies."""
    lib = read_settings(library) if library else {}
    tier = tier or lib.get('tier') or DEFAULT_TIER
    if tier not in TIER_CHARS:
        raise ValueError('tier must be one of %s, got %r' % (', '.join(sorted(TIER_CHARS)), tier))
    chars = chars or lib.get('batch_chars') or TIER_CHARS[tier]
    if not isinstance(chars, int) or isinstance(chars, bool) or chars < 1000:
        raise ValueError('batch_chars must be a whole number of 1000 or more, got %r' % (chars,))
    return chars, tier


# ---------------------------------------------------------------- anchors

def _kind(line):
    s = line.strip()
    if HEADING_RE.match(s):
        return 'heading'
    if NO_ANCHOR_RE.match(s):
        return 'plain'
    if s.startswith('|'):
        return 'table'
    if LIST_RE.match(line):
        return 'item'
    return 'text'


def anchor_blocks(sid, body):
    """The body as a list of chunks (joined with blank lines), anchors added.
    A chunk is a heading, a paragraph, a list (items anchored one by one), a table with its
    anchor, or text that carries no anchor."""
    prefix = anchor_prefix(sid)
    n = 0
    chunks = []
    for block in re.split(r'\n(?:[ \t]*\n)+', body.strip('\n')):
        lines = [ln for ln in block.split('\n') if ln.strip()]
        if not lines:
            continue
        # runs of lines of one kind; plain text right below an item continues that item
        runs = []
        for ln in lines:
            k = _kind(ln)
            if k == 'text' and runs and runs[-1][0] == 'item':
                k = 'item'
            if k != 'heading' and runs and runs[-1][0] == k:
                runs[-1][1].append(ln)
            else:
                runs.append([k, [ln]])
        for kind, rl in runs:
            if kind == 'text':
                n += 1
                rl[-1] = '%s ^%s%d' % (rl[-1].rstrip(), prefix, n)
                chunks.append('\n'.join(rl))
            elif kind == 'item':
                out = []
                for i, ln in enumerate(rl):
                    out.append(ln)
                    nxt = rl[i + 1] if i + 1 < len(rl) else None
                    if nxt is None or LIST_RE.match(nxt):
                        n += 1
                        out[-1] = '%s ^%s%d' % (out[-1].rstrip(), prefix, n)
                chunks.append('\n'.join(out))
            elif kind == 'table':
                n += 1
                chunks.append('\n'.join(rl) + '\n\n^%s%d' % (prefix, n))
            else:
                chunks.append('\n'.join(rl))
    return chunks


def demote(body):
    return re.sub(r'^(#{1,5}) ', r'#\1 ', body, flags=re.M)


def promote(body):
    return re.sub(r'^#(#{1,5}) ', r'\1 ', body, flags=re.M)


# ---------------------------------------------------------------- cutting and packing

def _size(chunks):
    return sum(len(c) + 2 for c in chunks)


def _heading_level(chunk):
    m = HEADING_RE.match(chunk)
    return len(m.group(1)) if m and '\n' not in chunk else 0


def cut(chunks, limit):
    """Cut a source's chunks into parts of at most limit characters, at the highest heading
    level that divides it, else between chunks. A chunk longer than the limit is a part of
    its own (the only way a part exceeds the limit)."""
    if _size(chunks) <= limit or len(chunks) <= 1:
        return [chunks]
    segments = None
    for level in sorted({_heading_level(c) for c in chunks} - {0}):
        segs, cur = [], []
        for c in chunks:
            if _heading_level(c) == level and cur:
                segs.append(cur)
                cur = []
            cur.append(c)
        segs.append(cur)
        if len(segs) > 1:
            segments = segs
            break
    if segments is None:
        segments = [[c] for c in chunks]
    pieces = []
    for seg in segments:
        pieces.extend(cut(seg, limit) if _size(seg) > limit else [seg])
    parts, cur = [], []
    for p in pieces:
        if cur and _size(cur) + _size(p) > limit:
            parts.append(cur)
            cur = []
        cur = cur + p
    if cur:
        parts.append(cur)
    return parts


def pack(units, limit):
    """Group units (dicts with 'text') into batches in order: a batch is closed when the next
    unit would take it over the limit. A unit longer than the limit gets a batch of its own."""
    batches, cur, size = [], [], 0
    for u in units:
        n = len(u['text']) + 2
        if cur and (size + n > limit or n > limit):
            batches.append(cur)
            cur, size = [], 0
        cur.append(u)
        size += n
    if cur:
        batches.append(cur)
    return batches


# ---------------------------------------------------------------- building

def build_units(sources, limit):
    """sources: dicts with name, path, modified, meta (quoted lines) and body (converted
    Markdown without its header), in batch order. Returns the units (one per source part)
    and the source numbers whose parts exceed the limit."""
    units, oversized = [], []
    for i, s in enumerate(sources, 1):
        sid = source_id(i)
        chunks = anchor_blocks(sid, demote(s['body']))
        head = '# %s %s · 0/0\n%s\n' % (sid, s['name'], s['meta'].rstrip('\n'))
        parts = cut(chunks, max(limit - len(head) - 2, limit // 2))
        for k, part in enumerate(parts, 1):
            title = '# %s %s' % (sid, s['name'])
            if len(parts) > 1:
                title += ' · %d/%d' % (k, len(parts))
            text = title + '\n' + s['meta'].rstrip('\n') + '\n\n' + '\n\n'.join(part) + '\n'
            u = {'sid': sid, 'name': s['name'], 'path': s.get('path', ''),
                 'modified': s.get('modified', ''), 'part': (k, len(parts)),
                 'chars': len(text), 'text': text}
            if len(text) > limit:
                oversized.append(u)
            units.append(u)
    return units, oversized


def render(batch, number, total, name, tier, limit, labels=None):
    lb = dict(LABELS, **(labels or {}))
    w = [lb['title'] % (name, number, total), '', lb['limit'] % (tier, limit), '',
         lb['note'], '', lb['table_head'], '| --- | --- | --- | --- | --- | --- |']
    for u in batch:
        k, n = u['part']
        w.append('| %s | %s | %s | %s | %d | %s |' % (
            u['sid'], _cell(u['name']), _cell(u['path']), u['modified'] or '-',
            u['chars'], '%d/%d' % (k, n) if n > 1 else '-'))
    w += ['', '---', '']
    return '\n'.join(w) + '\n' + '\n'.join(u['text'] for u in batch)


def _cell(s):
    return s.replace('|', '\\|')


# ---------------------------------------------------------------- reading and splitting back

def parse(text):
    """The source sections of a batch file: dicts with sid, name, part, of, text (the section
    without its heading line)."""
    out, cur = [], None
    for ln in text.split('\n'):
        m = SECTION_RE.match(ln)
        if m:
            cur = {'sid': m.group(1), 'name': m.group(2),
                   'part': int(m.group(3) or 1), 'of': int(m.group(4) or 1), 'lines': []}
            out.append(cur)
        elif cur is not None:
            cur['lines'].append(ln)
    for s in out:
        s['text'] = '\n'.join(s.pop('lines')).strip('\n')
    return out


def sources_table(text):
    """The header table of a batch file: {sid: {'name', 'path', 'modified'}}. Read by
    position, so either language's labels work."""
    out = {}
    for ln in text.split('\n'):
        if SECTION_RE.match(ln):
            break
        if not re.match(r'^\| S\d{2,} \|', ln):
            continue
        cells = [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', ln.strip())[1:-1]]
        if len(cells) >= 4:
            out[cells[0]] = {'name': cells[1], 'path': cells[2],
                             'modified': '' if cells[3] == '-' else cells[3]}
    return out


def split_back(texts):
    """Join the sections of one run's batch files back into one text per source.
    Returns {sid: {'name', 'text', 'missing'}} in source order; missing lists part numbers
    not found among the batch files given."""
    by_sid = {}
    for t in texts:
        for s in parse(t):
            by_sid.setdefault(s['sid'], {'name': s['name'], 'of': s['of'], 'parts': {}})
            by_sid[s['sid']]['parts'][s['part']] = s['text']
    out = {}
    for sid in sorted(by_sid, key=lambda x: int(x[1:])):
        e = by_sid[sid]
        missing = [k for k in range(1, e['of'] + 1) if k not in e['parts']]
        bodies = []
        for k in sorted(e['parts']):
            body = e['parts'][k]
            if k > 1:  # the quoted lines repeat in every part; keep them once
                body = re.sub(r'^(?:>[^\n]*\n)+\n?', '', body + '\n').strip('\n')
            bodies.append(body)
        body = promote('\n\n'.join(bodies))
        body = re.sub(r'\^' + re.escape(anchor_prefix(sid)) + r'(\d+)$', r'^p\1', body, flags=re.M)
        out[sid] = {'name': e['name'], 'text': body.strip('\n') + '\n', 'missing': missing}
    return out


def strip_anchors(text):
    """The text without anchors, for comparing a source with its original conversion."""
    text = re.sub(r'\n\n\^(?:s\d{2,}-)?p\d+$', '', text, flags=re.M)
    return re.sub(r' \^(?:s\d{2,}-)?p\d+$', '', text, flags=re.M)


def output_name(sid, name, names):
    if sid in names:
        return names[sid]
    if name in names:
        return names[name]
    return os.path.splitext(name)[0] + '.md'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Split knowledge-base batch files back into one file per source.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sp = sub.add_parser('split', help='write one Markdown file per source')
    sp.add_argument('batches', nargs='+', help='batch files of one run')
    sp.add_argument('-o', '--outdir', required=True, help='output folder')
    sp.add_argument('--names', default=None,
                    help='JSON file mapping a source number or original file name to an output file name')
    ap.add_argument('--log-level', default=os.environ.get('LOG_LEVEL', 'WARNING').upper(),
                    type=str.upper, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                    help='default: environment variable LOG_LEVEL, else WARNING')
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)

    names = {}
    if a.names:
        with open(a.names, encoding='utf-8') as f:
            names = json.load(f)
    texts = []
    for p in a.batches:
        with open(p, encoding='utf-8') as f:
            texts.append(f.read())
    os.makedirs(a.outdir, exist_ok=True)
    status = 0
    for sid, e in split_back(texts).items():
        if e['missing']:
            log.error('%s %s: parts %s missing; not written', sid, e['name'],
                      ', '.join(map(str, e['missing'])))
            status = 3
            continue
        path = os.path.join(a.outdir, output_name(sid, e['name'], names))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(e['text'])
        print('%s\t%s' % (sid, path))
    return status


if __name__ == '__main__':
    sys.exit(main())
