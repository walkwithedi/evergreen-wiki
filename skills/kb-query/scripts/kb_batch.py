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

Python 3 standard library only. Making batch files needs doc2kb_core.py (the converter, a copy of
doc2kb's) next to this file; splitting them back does not.

Usage:
  kb_batch.py make (--batch FOLDER | FILE | --files LIST) -o OUTDIR [--library LIB | --batch-chars N]
                   [any doc2kb_core.py option: --only, --since, --fp-db, --lang, ...]
      converts the documents with doc2kb_core.py and writes the run's batch files,
      <name>_YYYYMMDD_b01.md, _b02.md, ... (a second run that day adds the time). The limit is
      --batch-chars, else --tier (kept for older command lines), else batch_chars in LIB/_kb.json,
      else 20,000 characters. No picture files are exported.
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

# Characters per batch (weak is the default; strong is kept for older command lines); a library may
# set its own (_kb.json "batch_chars").
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
    """(characters per batch, tier). Explicit values win over the library's batch_chars; an explicit
    tier (kept for older command lines) picks its limit; otherwise the default applies. A library's
    tier setting is ignored."""
    lib = read_settings(library) if library else {}
    tier = tier or DEFAULT_TIER
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


LIB_ANCHOR_RE = re.compile(r'(^| )\^p(\d+)$', re.M)


def from_library(sources):
    """Units (one per source, never cut) made from sources already in a library, keeping their anchors:
    sources are dicts with name (file name), path (folder/name), modified and text (the library file).
    The notes at the top stay notes, headings are demoted and ^pN becomes ^sNN-pN, so that split_back
    gives the library text again."""
    units = []
    for i, s in enumerate(sources, 1):
        sid = source_id(i)
        lines = s['text'].replace('\r\n', '\n').strip('\n').split('\n')
        k = 0
        while k < len(lines) and lines[k].startswith('>'):
            k += 1
        meta, body = '\n'.join(lines[:k]), '\n'.join(lines[k:]).strip('\n')
        prefix = anchor_prefix(sid)
        body = LIB_ANCHOR_RE.sub(lambda m: '%s^%s%s' % (m.group(1), prefix, m.group(2)), demote(body))
        text = '# %s %s\n%s\n\n%s\n' % (sid, s['name'], meta, body) if meta else '# %s %s\n\n%s\n' % (sid, s['name'], body)
        units.append({'sid': sid, 'name': s['name'], 'path': s.get('path', ''), 'modified': s.get('modified', ''),
                      'part': (1, 1), 'chars': len(text), 'text': text})
    return units


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


# ---------------------------------------------------------------- make: convert, then write batch files

# Run messages and header labels in English and Chinese, chosen with the converter's --lang.
MAKE_LABELS = {
    'at': ('  batch file %d of %d: %s, sources: %d', '  批文件 %d/%d: %s，来源 %d 个'),
    'oversize': ('  ⚠ %s %s: %d characters in one block, more than the limit of %d; '
                 'it is a batch of its own',
                 '  ⚠ %s %s：单个段落或表格 %d 字符，超过上限 %d，单独成批'),
    'title': ('Batch file %s (%d of %d)', '批文件 %s（第 %d 批，共 %d 批）'),
    'limit': ('Tier: %s  Character limit: %d', '档位：%s　字数上限：%d'),
    'note': ('Each source is a section headed "# Snn"; a source cut into parts is marked "· k/n". '
             'Paragraphs and list items end with an anchor such as ^s01-p2, a table has one on the '
             'line below it. Quote sentences exactly as written and cite the anchor.',
             '每个来源一节，标题为「# Snn」；切成几部分的来源在标题末尾标「· 1/3」这样的序号。'
             '段落和列表项末尾带锚点（如 ^s01-p2），表格的锚点在表格下一行。'
             '引用时一字不改地照抄原句，并注明锚点。'),
    'table_head': ('| Source | File | Original path | Modified | Characters | Part |',
                   '| 来源 | 文件 | 原始路径 | 修改时间 | 字符数 | 部分 |'),
    'rep': ('Batch files: %d, tier %s, at most %d characters each\n',
            '批文件：%d 个，档位 %s，每个至多 %d 字符\n'),
    'rep_item': ('  %s  sources: %d\n', '  %s  来源 %d 个\n'),
}


def _label(core, key, *args):
    text = MAKE_LABELS[key][core.LANGS.index(core.LANG)]
    return text % args if args else text


def batch_name(md_dir, out_name, now=None):
    """<name>_YYYYMMDD, or <name>_YYYYMMDD-HHMM when that day already has batch files."""
    import datetime
    now = now or datetime.datetime.now()
    stem = '%s_%s' % (out_name, now.strftime('%Y%m%d'))
    try:
        taken = any(n.startswith(stem + '_b') for n in os.listdir(md_dir))
    except OSError:
        taken = False
    return '%s_%s' % (out_name, now.strftime('%Y%m%d-%H%M')) if taken else stem


def batch_writer(core, limit, tier):
    """A writer for doc2kb_core.run_batch() / run_files(): documents oldest first, cut and packed
    into batch files of at most limit characters."""
    def write(entries, md_dir, ts, src_root, out_name):
        ok = [e for e in entries if e['stat']['status'] in (core.OK, core.SKIPPED)]
        ok.sort(key=lambda e: (e['stat'].get('doc_mtime') or '9999', e['rel']))
        sources = []
        for e in ok:
            st = e['stat']
            body = re.sub(r'^(> [^\n]*\n)+\n', '', e.get('body', ''))
            meta = (core.T('section_path', e['rel'])
                    + core.T('section_modified', st.get('doc_mtime') or core.T('unknown'),
                             core.src_label(st.get('mtime_src') or 'unknown'))
                    + core.T('section_extracted', ts))
            sources.append({'name': core.fs_text(os.path.basename(e['rel'])), 'path': core.fs_text(e['rel']),
                            'modified': st.get('doc_mtime') or '', 'meta': meta, 'body': body,
                            'rel': e['rel']})
        units, oversized = build_units(sources, limit)
        batches = pack(units, limit)
        stem = batch_name(md_dir, out_name)
        labels = {k: _label(core, k) for k in ('title', 'limit', 'note', 'table_head')}
        written, file_of = [], {}
        rel_of = {source_id(i): s['rel'] for i, s in enumerate(sources, 1)}
        for n, batch in enumerate(batches, 1):
            name = '%s_b%02d' % (stem, n)
            path = os.path.join(md_dir, name + '.md')
            with open(path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(render(batch, n, len(batches), name, tier, limit, labels))
            written.append((path, len(batch)))
            for u in batch:
                file_of.setdefault(rel_of[u['sid']], os.path.basename(path))

        def finish(rp):
            """Print the batch files and add them to the converter's batch report."""
            lines = [_label(core, 'rep', len(written), tier, limit)]
            for i, (p, k) in enumerate(written, 1):
                print(_label(core, 'at', i, len(written), os.path.basename(p), k))
                lines.append(_label(core, 'rep_item', os.path.basename(p), k))
            for u in oversized:
                msg = _label(core, 'oversize', u['sid'], u['name'], u['chars'], limit)
                print(msg)
                lines.append(msg + '\n')
            try:
                with open(rp, encoding='utf-8') as f:
                    old = f.read()
                head, sep, rest = old.partition('\n\n')
                with open(rp, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(head + sep + ''.join(lines) + '\n' + rest)
            except OSError as e:
                log.warning('batch report not updated: %s', e)

        return (written[0][0] if written else None), file_of, finish
    return write


def make_main(argv):
    """kb_batch.py make: the converter's options plus the batch limit; see the module docstring."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import doc2kb_core as core
    ap = core.build_parser()
    ap.prog = 'kb_batch.py make'
    ap.description = 'Convert documents with doc2kb_core.py and write knowledge-base batch files.'
    ap.add_argument('--tier', choices=sorted(TIER_CHARS), default=None,
                    help='kept for older command lines: weak (%d characters per batch) or strong (%d); '
                         '--batch-chars or the library\'s batch_chars is preferred'
                         % (TIER_CHARS['weak'], TIER_CHARS['strong']))
    ap.add_argument('--batch-chars', type=int, default=None, metavar='N',
                    help='characters per batch (default: the library\'s batch_chars, else %d)' % TIER_CHARS['weak'])
    ap.add_argument('--library', metavar='DIR', default=None,
                    help='local library whose _kb.json sets batch_chars')
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format=LOG_FORMAT, stream=sys.stderr)
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass  # a stream that cannot be reconfigured keeps its encoding
    core.set_lang(args.lang)
    try:
        limit, tier = batch_limit(args.tier, args.batch_chars, args.library)
    except ValueError as e:
        ap.error(str(e))
    args.merge = True
    args.no_images = True
    writer = batch_writer(core, limit, tier)
    if args.batch:
        return core.run_batch(args, writer=writer)
    if not args.input and not args.files:
        ap.error('give an input file, a list with --files, or a folder with --batch')
    return core.run_files(args, writer=writer)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['make']:
        return make_main(argv[1:])
    ap = argparse.ArgumentParser(description='Make knowledge-base batch files, or split them back into one file per source.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('make', help='convert documents and write batch files (kb_batch.py make -h for options)')
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
