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

Python 3 standard library only.

Exit codes: 0 done; 2 bad arguments, unreadable input or a part missing.
Usage:
  ingest.py file BATCH.md [BATCH.md ...] --cards ACCEPTED.jsonl --library DIR [--target DIR]
                 [--names NAMES.json]
  ingest.py pages --library DIR [--target DIR] (--topic NAME ... | --all)
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
    for p in (f, pg):
        p.add_argument('--library', required=True, help='library root (its _kb.json gives the names)')
        p.add_argument('--target', default=None, help='write here instead of the library (a staging folder)')
    a = ap.parse_args(argv)
    kbconf.setup_logging(a.log_level)

    try:
        cfg = kbconf.load_library(a.library)
        target = a.target or a.library
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
