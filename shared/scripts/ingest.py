#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ingest.py - file one intake run into a 2.0 library and rebuild its topic pages.

The library (or a staging folder laid out like it, for a library in Google Drive) has three
folders, named by kbconf names: sources_dir (default Sources), cards_dir (Cards) and topics_dir
(Topics), plus archive_dir for older versions.

file: the run's batch files are split back into one file per source, Sources/<original name>.md
  (two sources of the run with the same name get their parent folder's name in front). The
  accepted cards (quote_check.py check) go to Cards/<same name>.md. A source whose name is
  already in the library is a new version: the old source file and its cards file move to
  Archive/Sources and Archive/Cards as <name><old_suffix><YYYYMMDDHHMMSS>.md; nothing is deleted.
  A run with a part missing from the batch files writes nothing. Prints a JSON record: sources
  written, files archived, topics touched (of the new cards and of the archived ones).

pages: Topics/<topic>.md is rebuilt from every cards file: the topic's cards, newest first by
  event date or else the source's date, each with its conclusion, quote, source link and cards
  link. Pages are generated; edits to them are overwritten.

topics: prints the topics of the spec's Table A, one per line, and with --out writes them to a file
  (for quote_check.py --topics).

add-topic: appends topics the owner confirmed to a partition of Table A (partitions.fallback
  unless --partition), raises the spec's version by one minor step (v1 -> v1.1, v5.2 -> v5.3) for
  the lot, sets the last-updated date and adds one revision line per topic. Known topics are
  skipped; with nothing new the spec is left as it is.

retopic: changes the topic of accepted cards, for a new topic the owner put under a known one.

check-page: a topic page the model wrote (strong tier) must cite every current card of the topic
  and nothing else ([[Sources/<source>#^pN]] links); exit 3 with the unknown and missing links
  otherwise. --write puts a page that passes into the topics folder.

Python 3 standard library only.

Exit codes: 0 done; 3 check-page found problems; 2 bad arguments, unreadable input or a part missing.
Usage:
  ingest.py file BATCH.md [BATCH.md ...] --cards ACCEPTED.jsonl --library DIR [--target DIR]
                 [--names NAMES.json]
  ingest.py pages --library DIR [--target DIR] (--topic NAME ... | --all)
  ingest.py topics --library DIR [--out FILE]
  ingest.py add-topic --library DIR --topic NAME [--topic NAME ...] [--partition NN]
  ingest.py retopic ACCEPTED.jsonl --from TOPIC --to TOPIC
  ingest.py check-page --library DIR [--target DIR] --topic NAME --page FILE [--write]
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import timedelta

import kb_batch
import kbconf
import quote_check

log = logging.getLogger('ingest')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'

FOLDER_UNSAFE_RE = re.compile(r'[\\/:*?"<>|#^\[\]\s]+')


def lang_of(cfg):
    return 'zh' if str(cfg.get('language', 'en')).lower().startswith('zh') else 'en'


def source_names(table, names=None):
    """{sid: file name} for the run's sources; the same name twice gets the parent folder's name."""
    out = {sid: kb_batch.output_name(sid, v['name'], names or {}) for sid, v in table.items()}
    counts = {}
    for f in out.values():
        counts[f] = counts.get(f, 0) + 1
    for sid, f in out.items():
        if counts[f] > 1 and not (names and (sid in names or table[sid]['name'] in names)):
            parent = os.path.basename(os.path.dirname(table[sid].get('path', '').replace('\\', '/')))
            out[sid] = '%s_%s' % (FOLDER_UNSAFE_RE.sub('-', parent) or sid, f)
    return out


def _archive_path(folder, fname, old_suffix, stamp0):
    stem, ext = os.path.splitext(fname)
    k = 0
    while True:
        p = os.path.join(folder, '%s%s%s%s' % (stem, old_suffix, (stamp0 + timedelta(seconds=k)).strftime('%Y%m%d%H%M%S'), ext))
        if not os.path.exists(p):
            return p
        k += 1


def file_run(batches, cards, target, cfg, names=None):
    """File one run into target (a library or a staging folder); returns the run record."""
    texts = []
    for p in batches:
        with open(p, encoding='utf-8') as f:
            texts.append(f.read().replace('\r\n', '\n'))
    table = {}
    for t in texts:
        table.update(kb_batch.sources_table(t))
    split = kb_batch.split_back(texts)
    missing = ['%s %s (parts %s)' % (sid, e['name'], ', '.join(map(str, e['missing'])))
               for sid, e in split.items() if e['missing']]
    if missing:
        raise ValueError('parts missing from the batch files, nothing written: ' + '; '.join(missing))
    for sid, e in split.items():
        table.setdefault(sid, {'name': e['name'], 'path': '', 'modified': ''})
    fnames = source_names({sid: table[sid] for sid in split}, names)

    n = cfg['names']
    src_dir, card_dir = os.path.join(target, n['sources_dir']), os.path.join(target, n['cards_dir'])
    stamp0 = kbconf.now(cfg['timezone']).replace(microsecond=0)
    topics, archived = set(), []
    for sid in split:
        fname = fnames[sid]
        for folder, sub in ((src_dir, n['sources_dir']), (card_dir, n['cards_dir'])):
            old = os.path.join(folder, fname)
            if not os.path.isfile(old):
                continue
            if folder == card_dir:
                with open(old, encoding='utf-8') as f:
                    topics.update(c['topic'] for c in quote_check.read_cards(f.read())['cards'] if c['topic'])
            dest_dir = os.path.join(target, n['archive_dir'], sub)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(old, _archive_path(dest_dir, fname, n['old_suffix'], stamp0))
            archived.append('%s/%s' % (sub, fname))

    os.makedirs(src_dir, exist_ok=True)
    for sid, e in split.items():
        with open(os.path.join(src_dir, fnames[sid]), 'w', encoding='utf-8') as f:
            f.write(e['text'])
    quote_check.write([c for c in cards if c['source'] in split], table, card_dir, fnames, lang_of(cfg),
                      n['sources_dir'], n['topics_dir'])
    topics.update(c['topic'] for c in cards if c['source'] in split)
    return {'sources': [fnames[sid] for sid in split], 'archived': archived, 'topics': sorted(topics)}


PAGE_LABELS = {
    'en': {'note': '> This page is generated from the cards by a script; edits here are overwritten.',
           'empty': 'No current cards.', 'card': 'card', 'undated': 'undated'},
    'zh': {'note': '> 本页由脚本根据卡片生成，在此修改会被覆盖。',
           'empty': '暂无现行卡片。', 'card': '卡片', 'undated': '无日期'},
}


def _all_cards(target, cfg):
    """[(cards file stem, source link, card)] over every cards file of the library."""
    folder = os.path.join(target, cfg['names']['cards_dir'])
    out = []
    for fname in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not fname.endswith('.md'):
            continue
        with open(os.path.join(folder, fname), encoding='utf-8') as f:
            got = quote_check.read_cards(f.read())
        out.extend((fname[:-3], got['source'], c) for c in got['cards'])
    return out


def render_page(topic, entries, cfg):
    lb = PAGE_LABELS[lang_of(cfg)]
    cards_dir = cfg['names']['cards_dir']
    w = ['# ' + topic, '', lb['note'], '']
    if not entries:
        w += [lb['empty'], '']
    for day, stem, src, c in entries:
        w.append('- %s · %s' % (day or lb['undated'], c['conclusion']))
        w.append('  > %s [[%s#^%s]] · [[%s/%s|%s]]' % (c['quote'], src, c['anchor'], cards_dir, stem, lb['card']))
    return '\n'.join(w) + '\n'


def pages_run(target, cfg, topics=None):
    """Rebuild the pages of the topics named (every topic with cards when None); returns their paths."""
    by_key, shown = {}, {}
    for stem, src, c in _all_cards(target, cfg):
        k = kbconf.topic_key(c['topic'])
        shown.setdefault(k, c['topic'])
        day = c.get('event_date') or c['date'][:10]
        by_key.setdefault(k, []).append((day, stem, src, c))
    wanted = [kbconf.topic_key(t) for t in topics] if topics is not None else sorted(by_key)
    names = dict(shown, **{kbconf.topic_key(t): t for t in topics or ()})
    folder = os.path.join(target, cfg['names']['topics_dir'])
    os.makedirs(folder, exist_ok=True)
    paths = []
    for k in dict.fromkeys(wanted):
        entries = sorted(by_key.get(k, []), key=lambda e: (e[0] or '', e[1], int(e[3]['anchor'][1:] or 0)),
                         reverse=True)
        path = os.path.join(folder, quote_check.page_name(names[k]) + '.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(render_page(names[k], entries, cfg))
        paths.append(path)
    return paths


SPEC_LABELS = {
    'en': {'revision': 'Revision: v%s (%s) partition %s gets topic "%s"; no partition number added.'},
    'zh': {'revision': '修订：v%s（%s）分区 %s 增加主题「%s」，未新增分区号。'},
}
VERSION_RE = re.compile(r'^((?:Version|版本)\s*[:：]\s*v)(\d+)(?:\.(\d+))?\s*$')
UPDATED_RE = re.compile(r'^((?:Last updated|最后更新)\s*[:：]\s*).*$')
REVISION_RE = re.compile(r'^(?:Revision|修订)\s*[:：]')
LINK_ANCHOR_RE = re.compile(r'\[\[([^\]#|]+)#\^(p\d+)(?:\|[^\]]*)?\]\]')


def spec_path(library, cfg):
    return os.path.join(library, cfg['names']['spec'])


def read_spec(library, cfg):
    with open(spec_path(library, cfg), encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n')


def add_topics(library, cfg, new_topics, partition=None):
    """Append confirmed topics to a partition of Table A (the fallback partition by default), raise the
    spec's version by one minor step for the lot and add one revision line per topic.
    Returns (added, known): topics already in Table A are not added again."""
    spec = read_spec(library, cfg)
    known_topics = kbconf.topics(spec, cfg)
    added, known = [], []
    for t in new_topics:
        t = ' '.join(t.split())
        hit = kbconf.match_topic(t, known_topics + added)
        (known if hit else added).append(hit or t)
    if not added:
        return added, known
    part = partition or cfg['partitions'].get('fallback') or ''
    lines = spec.split('\n')
    inside, row = False, None
    for i, line in enumerate(lines):
        m = kbconf.TABLE_LABEL.search(line)
        if m:
            inside = m.group(1) == 'A'
            continue
        pm = kbconf.PARTITION_LINE.match(line) if inside else None
        if pm and int(pm.group(1)) >= cfg['partitions']['topic_start'] and (not part or pm.group(1) == part):
            row = i
            if part:
                break
    if row is None:
        raise ValueError('partition %s is not a topic partition of Table A' % (part or '(none)'))
    part = kbconf.PARTITION_LINE.match(lines[row]).group(1)
    zh = '；' in lines[row] or '：' in lines[row]
    body = lines[row].rstrip()
    end = body[-1] if body[-1] in '.。' else ''
    body = body[:-1] if end else body
    lines[row] = body + ''.join(('；' if zh else '; ') + t for t in added) + end
    today = kbconf.now(cfg['timezone']).strftime('%Y-%m-%d')
    lang = 'zh' if zh else 'en'
    version, vline = None, None
    for i, line in enumerate(lines):
        m = VERSION_RE.match(line)
        if m and version is None:
            version = '%s.%d' % (m.group(2), int(m.group(3) or 0) + 1)
            lines[i] = m.group(1) + version
            vline = i
        elif UPDATED_RE.match(line):
            lines[i] = UPDATED_RE.match(line).group(1) + today
    if vline is not None:
        at = vline + 1                      # after the version line, or the header's last revision line
        for i in range(vline + 1, len(lines)):
            if not lines[i].strip():
                break
            if REVISION_RE.match(lines[i]):
                at = i + 1
        notes = [SPEC_LABELS[lang]['revision'] % (version, today, part, t) for t in added]
        lines[at:at] = notes
    with open(spec_path(library, cfg), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return added, known


def retopic(path, old, new):
    """Rewrite the topic of the cards in a JSON lines file from old to new; returns the count."""
    with open(path, encoding='utf-8') as f:
        cards = [json.loads(ln) for ln in f if ln.strip()]
    n = 0
    for c in cards:
        if kbconf.topic_key(str(c.get('topic', ''))) == kbconf.topic_key(old):
            c['topic'] = new
            n += 1
    with open(path, 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    return n


def check_page(target, cfg, topic, page):
    """Links of a topic page written by the model against the topic's current cards:
    unknown = cited passages no card holds; missing = cards the page does not cite."""
    key = kbconf.topic_key(topic)
    have = {'%s#^%s' % (src, c['anchor']) for _, src, c in _all_cards(target, cfg)
            if kbconf.topic_key(c['topic']) == key}
    cited = {'%s#^%s' % m for m in LINK_ANCHOR_RE.findall(page)}
    return {'unknown': sorted(cited - have), 'missing': sorted(have - cited)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='File an intake run into a 2.0 library and rebuild its topic pages.')
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('file', help='split the batch files back, archive old versions, write the cards')
    f.add_argument('batches', nargs='+', help='batch files of the run')
    f.add_argument('--cards', required=True, help='accepted cards (quote_check.py check --accepted)')
    f.add_argument('--names', default=None,
                   help='JSON file mapping a source number or original file name to a file name')
    pg = sub.add_parser('pages', help='rebuild topic pages from the cards')
    group = pg.add_mutually_exclusive_group(required=True)
    group.add_argument('--topic', action='append', help='a topic to rebuild (repeatable)')
    group.add_argument('--all', action='store_true', help='every topic with cards')
    tp = sub.add_parser('topics', help="print the topics of the spec's Table A, one per line")
    tp.add_argument('--out', default=None, help='write them to this file as well')
    at = sub.add_parser('add-topic', help='add confirmed topics to Table A (one version step, a revision line each)')
    at.add_argument('--topic', action='append', required=True, help='a topic to add (repeatable)')
    at.add_argument('--partition', default=None, help='two-digit partition (default: partitions.fallback)')
    cp = sub.add_parser('check-page', help="check a model-written topic page against the topic's cards")
    cp.add_argument('--topic', required=True)
    cp.add_argument('--page', required=True, help='the page as written')
    cp.add_argument('--write', action='store_true', help='when it passes, write it to the topics folder')
    for p in (f, pg, tp, at, cp):
        p.add_argument('--library', required=True, help='library root (its _kb.json gives the names)')
    for p in (f, pg, cp):
        p.add_argument('--target', default=None, help='write here instead of the library (a staging folder)')
    rt = sub.add_parser('retopic', help="change accepted cards' topic")
    rt.add_argument('cards', help='accepted cards (JSON lines), rewritten in place')
    rt.add_argument('--from', dest='old', required=True)
    rt.add_argument('--to', dest='new', required=True)
    a = ap.parse_args(argv)
    kbconf.setup_logging(a.log_level)

    try:
        if a.cmd == 'retopic':
            n = retopic(a.cards, a.old, a.new)
            print('%d card%s now under %s' % (n, '' if n == 1 else 's', a.new))
            return 0
        cfg = kbconf.load_library(a.library)
        if a.cmd == 'topics':
            found = kbconf.topics(read_spec(a.library, cfg), cfg)
            for t in found:
                print(t)
            if a.out:
                with open(a.out, 'w', encoding='utf-8') as fh:
                    fh.write(''.join(t + '\n' for t in found))
            return 0
        if a.cmd == 'add-topic':
            added, known = add_topics(a.library, cfg, a.topic, a.partition)
            for t in added:
                print('added: ' + t)
            for t in known:
                print('known: ' + t)
            return 0
        target = a.target or a.library
        if a.cmd == 'check-page':
            with open(a.page, encoding='utf-8') as fh:
                page = fh.read()
            res = check_page(target, cfg, a.topic, page)
            print(json.dumps(res, ensure_ascii=False))
            if res['unknown'] or res['missing']:
                return 3
            if a.write:
                folder = os.path.join(target, cfg['names']['topics_dir'])
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, quote_check.page_name(a.topic) + '.md'), 'w', encoding='utf-8') as fh:
                    fh.write(page)
            return 0
        if a.cmd == 'pages':
            for p in pages_run(target, cfg, None if a.all else a.topic):
                print(p)
            return 0
        names = None
        if a.names:
            with open(a.names, encoding='utf-8') as fh:
                names = json.load(fh)
        with open(a.cards, encoding='utf-8') as fh:
            cards = [json.loads(ln) for ln in fh if ln.strip()]
        print(json.dumps(file_run(a.batches, cards, target, cfg, names), ensure_ascii=False))
        return 0
    except (kbconf.ConfigError, OSError, ValueError) as e:
        log.error('%s', e)
        return 2


if __name__ == '__main__':
    sys.exit(main())
