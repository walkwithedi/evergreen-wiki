#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ingest.py - file one intake run into a library and rebuild its topic pages.

The library (or, with --target, another folder laid out like it) has three
folders, named by kbconf names: sources_dir (default Sources), cards_dir (Cards) and topics_dir
(Topics), plus archive_dir for older versions.

file: the run's batch files are split back into one file per source, Sources/<folder>/<original
  name>.md, where folder is the one the document came from below the material root (kbconf
  rel_folder). The accepted cards (quote_check.py verify) go to Cards/<folder>/<same name>.md; a run
  filed without --cards writes the sources only, to be searched until their cards are written. A
  name is one document wherever its folder is: a source whose name is already in the library is a
  new version, and the old source file and its cards file move to Archive/Sources/<old folder> and
  Archive/Cards/<old folder> as <name><old_suffix><YYYYMMDDHHMMSS>.md; nothing is deleted. A source
  with the same content (fingerprint) as one in the library, or as an earlier one of the run, is not
  written and is listed as a duplicate. Several sources of the run with one name and different
  content form a group: the newest is filed as current and the others go straight to the archive as
  its older versions, unless --groups FILE ({name: {"current": path, "separate": [paths]}}) says
  otherwise; a separate one is another document and gets its folder's last part in front of its name.
  --replaces NEW=OLD (repeatable) archives OLD the same way: the owner confirmed that the run's
  source NEW is a new version of the library's source OLD under another name. A run with a part
  missing from the batch files, or naming an OLD that is not in the library, writes nothing.
  --restore FILE keeps conflicts (from the conflicts command) the owner chose to restore: a quote
  still in the new version becomes a current card of it again; any other old card is kept in the
  new version's cards file, citing the archived old source and marked as from an earlier version.
  Items of the status card that cite a source being archived get a review mark, once.
  Prints a JSON record: sources written, files archived, older versions filed straight to the
  archive, duplicates, topics touched (of the new cards and of the archived ones), sources written
  without cards, conflicts restored, status-card items marked for review. The library's index
  (kbindex.py) is brought up to date.

conflicts: for each library source the run replaces (same name, or --replaces), its current cards
  against the new version and the run's cards. An old card whose quote is in the new version and
  quoted by a new card is unchanged and not listed; "not_carried": the quote is in the new version
  but no new card quotes it; "changed": the quote is gone and a new card's conclusion is close to
  the old one (SIMILAR_MIN); "removed": the quote is gone and no new card is close. Prints JSON.

note: a quick note (the user's words, in a text file) as the batch file of a run with one source,
  "Note <YYYYMMDD-HHMM> <title>.md" ("随手记 ..." in a Chinese library). The words are the source
  text, one anchor per paragraph; where it came from, when it was recorded and --context go into
  note lines (">"), which cards cannot quote. Prints the batch file paths; the run then goes on as
  any other (quote_check.py verify, file, pages).

pending: the owner's decisions of a run of a local library through a file, so that the knowledge base
  client can show them as a form. "write" puts the run's new topics (--report, quote_check.py's
  report), new entities (--entities, the entities report), version candidates (--versions) and
  conflicts (--conflicts) into <library>/_pending/<run>.json, with the spec's topics and entity names
  to choose from; it prints the file's path. The decisions come back as <run>.decisions.json:
  {"topics": {name: {"add": true} | {"under": topic}}, "entities": {name: {"add": true, "type": T} |
  {"alias": table name}}, "versions": ["new=old", ...], "conflicts": {id: "accept" | "restore"},
  "groups": {name: {"current": path, "separate": [paths]}}}; what is left out takes the default
  (topics and entities added, pairs not new versions, conflicts accepted, the newest of a group
  current). "read" checks them and turns them into what the next commands take: topics to add,
  topics to put under others, --replaces pairs, an entity map (--map), a restore file (--restore) and
  a groups file (--groups) in --work. "done" removes both files once the run is filed.

status-check: the numbered items of a rewritten status card against the current one. Items pair
  by their text (review marks left out), else by a source link they share. Lists removed and
  changed items, source links no longer cited and added items; exit 3 when anything was removed,
  changed or lost. --write puts a rewrite with none of these in the library; with --confirmed (the
  owner has seen the list and accepted it) it is written anyway.

versions: for each source of the run whose name is not in the library yet, the library's sources
  that may be its older version. A pair is a candidate when the names are close once dates,
  version marks (v2, rev, final, draft, copy, (1), 副本, 终稿, 定稿, 修订版) and punctuation are
  dropped (equal, or a similarity of NAME_MIN or more) and at least OVERLAP_MIN of the shorter
  source's paragraphs (PARA_MIN characters or more, compared as quote_check does) are in the other.
  Names are compared only with library names sharing enough letter pairs, through the index.
  Same-named sources (in any folder) are new versions anyway and are listed apart, with the run's
  groups of same-named sources and its duplicates. Prints JSON.

entities: the cards' entity names against the spec's Table E. Names or aliases of the table
  (compared without regard to case and spacing) are merged into the table's name; the other names
  are listed with the type the assistant suggested (entity_types on the card, else other), the
  number of cards naming them and the closest names of the table. --apply writes the owner's
  decisions (--map FILE: {"name": "table name"} records it as an alias, {"name": {"type": T}}
  adds it with that type; names left out are added with the suggested type): the cards file is
  rewritten with the table's names, and Table E gets the new rows and aliases, with one version
  step for the lot and a revision line each.

pages: Topics/<topic>.md is rebuilt from the cards (through the index): the topic's cards, newest
  first by event date or else the source's date, each with its conclusion, quote, source link and
  cards link. A topic with more than YEAR_SPLIT cards keeps its newest year and undated cards on that
  page and each earlier year on Topics/<topic> (YYYY).md. Pages are generated; edits to them are
  overwritten.

topics: prints the topics of the spec's Table A, one per line, and with --out writes them to a file
  (for quote_check.py --topics).

add-topic: appends topics the owner confirmed to a partition of Table A (partitions.fallback
  unless --partition), raises the spec's version by one minor step (v1 -> v1.1, v5.2 -> v5.3) for
  the lot, sets the last-updated date and adds one revision line per topic. Known topics are
  skipped; with nothing new the spec is left as it is.

retopic: changes the topic of accepted cards, for a new topic the owner put under a known one.

file --sources S01,S03 files only those sources of the batch files (the others are left for another call).

backfill: batch files for sources already in the library without cards (the newest first, or --source
  paths), one source per file, kept whole, with the library's anchors; the run then goes on with
  quote_check.py verify and add-cards.

add-cards: writes the cards of such sources. A source must be in the library at its path, with the same
  content and no cards file; nothing is archived. Prints the sources that got cards, their topics and the
  sources refused with the reason.

progress --work DIR: how far the run in a work folder got, judged only from the files its steps leave
  there: batch files (*_bNN.md), one cards file per source (cards/S01.jsonl, ...), accepted.jsonl and
  report.json newer than the cards (report2.json once rejected cards were rewritten), entities.json,
  versions.json and conflicts.json (not for notes and backfill runs), and filed.json and pages.json,
  which file, add-cards and pages append their records to when given --work. A run is finished when it
  was filed and every topic it touched has its page rebuilt. Prints the step reached and the next one.

work: run folders, <library>/.kb-work/<chat|client>-<YYYYMMDD-HHMMSS>/. "new" makes one and prints its
  path; "list" lists them, finished or not; "done --work DIR" removes a run folder once progress says it
  is finished; "drop --run NAME" removes an unfinished one the owner gave up. Nothing outside .kb-work
  is ever removed.

check: a read-only health check (health_check): quotes no longer in their paragraph, links to files that do
  not exist, topic pages missing, out of date or no longer built, cards files without their source,
  status-card items marked for review or citing a source that is not current, runs waiting for decisions
  for more than PENDING_DAYS days, run folders left unfinished for more than WORK_DAYS days, and the number
  of sources without cards. Writes nothing; exit 3 when
  it finds problems.

Python 3 standard library only.

Exit codes: 0 done; 3 status-check or check found problems; 2 bad arguments, unreadable input or a part missing.
Usage:
  ingest.py file BATCH.md [BATCH.md ...] [--cards ACCEPTED.jsonl] --library DIR [--target DIR] [--work DIR]
                 [--names NAMES.json] [--replaces NEW.md=OLD.md ...] [--restore RESTORE.json] [--groups GROUPS.json]
  ingest.py conflicts BATCH.md [BATCH.md ...] --cards ACCEPTED.jsonl --library DIR [--target DIR]
                 [--replaces NEW.md=OLD.md ...] [--groups GROUPS.json]
  ingest.py status-check --old CURRENT.md --new REWRITE.md [--write [--confirmed] --library DIR]
  ingest.py note --library DIR --title TITLE --text WORDS.txt [--context TEXT] -o DIR
  ingest.py pending write --library DIR [--run NAME] [--report F] [--entities F] [--versions F] [--conflicts F]
  ingest.py pending read --library DIR --run NAME --work DIR
  ingest.py pending done --library DIR --run NAME
  ingest.py versions BATCH.md [BATCH.md ...] --library DIR [--target DIR] [--groups GROUPS.json]
  ingest.py entities ACCEPTED.jsonl --library DIR [--apply [--map MAP.json]]
  ingest.py pages --library DIR [--target DIR] (--topic NAME ... | --all) [--work DIR]
  ingest.py topics --library DIR [--out FILE]
  ingest.py add-topic --library DIR --topic NAME [--topic NAME ...] [--partition NN]
  ingest.py retopic ACCEPTED.jsonl --from TOPIC --to TOPIC
  ingest.py check --library DIR [--json]
  ingest.py backfill --library DIR -o DIR [--source PATH ...] [--limit N]
  ingest.py add-cards BATCH.md [BATCH.md ...] --cards ACCEPTED.jsonl --library DIR [--work DIR]
  ingest.py progress --work DIR [--json]
  ingest.py work new --library DIR [--prefix chat|client]
  ingest.py work list --library DIR
  ingest.py work done --work DIR
  ingest.py work drop --library DIR --run NAME
"""
import argparse
import difflib
import json
import logging
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta

import kb_batch
import kbconf
import kbindex
import quote_check

log = logging.getLogger('ingest')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'

FOLDER_UNSAFE_RE = re.compile(r'[\\/:*?"<>|#^\[\]\s]+')


def lang_of(cfg):
    return 'zh' if str(cfg.get('language', 'en')).lower().startswith('zh') else 'en'


def run_sources(table, split, names=None):
    """{sid: {name, folder, path, fp, modified}} of a run's sources: the file name (kb_batch.output_name),
    the library folder its original path gives (kbconf.rel_folder), the path below the sources folder,
    the content fingerprint and the last-modified time."""
    out = {}
    for sid, e in split.items():
        t = table.get(sid, {})
        name = os.path.basename(kb_batch.output_name(sid, e['name'], names or {}))
        folder = kbconf.rel_folder(t.get('path', ''))
        out[sid] = {'name': name, 'folder': folder, 'path': _join(folder, name),
                    'fp': kbindex.fingerprint(e['text']), 'modified': t.get('modified', '')}
    return out


def _join(folder, name):
    return '%s/%s' % (folder, name) if folder else name


def _sid_n(sid):
    return int(sid[1:])


def plan_run(srcs, ix, groups=None):
    """What filing does with each source of a run, before anything is written:
      duplicates  [{source, existing}]: the same content (fingerprint) is in the library already, or an
                  earlier source of the run has it; not written.
      groups      [{name, members: [{path, modified}], current}]: several sources of the run with one
                  name and different content. By default the newest (last-modified) is the current
                  version and the others are filed as its older versions, straight into the archive;
                  groups ({name: {"current": path, "separate": [paths]}}) changes that: a separate one
                  is another document and gets its folder's last part in front of its name.
      current     {sid: path below the sources folder} of the sources filed as current.
      older       {sid: path} of the sources filed as older versions.
    """
    groups = groups or {}
    lib_fp = ix.by_fingerprint(e['fp'] for e in srcs.values())
    dups, seen, keep = [], {}, []
    for sid in sorted(srcs, key=_sid_n):
        e = srcs[sid]
        if e['fp'] in lib_fp:
            dups.append({'source': e['path'], 'existing': lib_fp[e['fp']]})
        elif e['fp'] in seen:
            dups.append({'source': e['path'], 'existing': srcs[seen[e['fp']]]['path'], 'in_run': True})
        else:
            seen[e['fp']] = sid
            keep.append(sid)
    by_name = {}
    for sid in keep:
        by_name.setdefault(srcs[sid]['name'], []).append(sid)
    current, older, out_groups = {}, {}, []
    taken = set()
    for name, sids in by_name.items():
        if len(sids) == 1:
            current[sids[0]] = srcs[sids[0]]['path']
            taken.add(name)
            continue
        default = max(sids, key=lambda x: (srcs[x]['modified'] or '', _sid_n(x)))
        d = groups.get(name) or {}
        paths = {srcs[x]['path']: x for x in sids}
        cur = paths.get(d.get('current')) or default
        separate = [paths[x] for x in d.get('separate') or [] if x in paths and paths[x] != cur]
        out_groups.append({'name': name, 'current': srcs[default]['path'],
                           'members': [{'path': srcs[x]['path'], 'modified': srcs[x]['modified']} for x in sids]})
        current[cur] = srcs[cur]['path']
        taken.add(name)
        for x in sids:
            if x == cur:
                continue
            if x in separate:
                e = srcs[x]
                part = e['folder'].rsplit('/', 1)[-1] if e['folder'] else ''
                new = '%s_%s' % (FOLDER_UNSAFE_RE.sub('-', part) or x, name)
                while new in taken:
                    new = '%s_%s' % (x, new)
                taken.add(new)
                e['name'], e['path'] = new, _join(e['folder'], new)
                current[x] = e['path']
            else:
                older[x] = srcs[x]['path']
    return {'duplicates': dups, 'groups': out_groups, 'current': current, 'older': older}


NAME_MIN = 0.8      # name similarity for a version candidate (difflib ratio of the name keys)
OVERLAP_MIN = 0.5   # share of the shorter source's paragraphs found in the other
PARA_MIN = 20       # shorter paragraphs (headings, dates, signatures) are not compared
PARA_ANCHOR_RE = re.compile(r'\s*\^(?:s\d{2,}-)?p\d+\s*$')
name_key = kbindex.name_key


def paragraphs(text):
    """The comparable paragraphs of a source: normalised, without anchors, notes and short lines."""
    out = set()
    for block in re.split(r'\n\s*\n', text):
        block = block.strip()
        if not block or block.startswith(('>', '#')):
            continue
        p = quote_check.norm(PARA_ANCHOR_RE.sub('', block))
        if len(p) >= PARA_MIN:
            out.add(p)
    return out


SIMILAR_MIN = 0.6   # conclusion similarity for a changed card
ANCHORED_RE = re.compile(r'^(.*?)\s*\^(p\d+)\s*$', re.S)
MARK_RE = re.compile(r'\s*⏳[^⏳\n]*')
ITEM_RE = re.compile(r'^\s*\d+[.、．]\s+\S')
CITE_RE = re.compile(r'\[\[([^\]|#]+#\^p\d+)(?:\|[^\]]*)?\]\]')


anchored = kbindex.anchored


def _find_anchor(quote, paras):
    q = quote_check.norm(quote)
    return next((a for a, t in paras.items() if q in quote_check.norm(t)), None)


def _replaced(srcs, plan, lib, replaces):
    """{new name: [library paths it replaces]} for a run: the same name anywhere in the library, and the
    pairs the owner confirmed (replaces: {new name: library name})."""
    out = {}
    for sid in plan['current']:
        name = srcs[sid]['name']
        if lib.get(name):
            out[name] = list(lib[name])
    for new, old in (replaces or {}).items():
        out.setdefault(new, []).extend(p for p in lib.get(old, []) if p not in out.get(new, []))
    return out


def _read_cards_file(path):
    with open(path, encoding='utf-8') as f:
        return quote_check.read_cards(f.read())['cards']


def conflicts(batches, cards, target, cfg, names=None, replaces=None, groups=None, only=None):
    """Old cards of the sources the run replaces that the new version changes, drops or does not
    carry over: [{id, kind, source, old_source, old, new, new_anchor}]; source is the new name,
    old_source the old version's path below the sources folder."""
    table, split = _read_run(batches, only)
    srcs = run_sources(table, split, names)
    ix = kbindex.open_index(target, cfg)
    try:
        plan = plan_run(srcs, ix, groups)
        lib = ix.source_paths()
    finally:
        ix.close()
    sid_of = {srcs[sid]['name']: sid for sid in plan['current']}
    card_dir = os.path.join(target, cfg['names']['cards_dir'])
    out = []
    for new, olds in _replaced(srcs, plan, lib, replaces).items():
        for old in olds:
            path = os.path.join(card_dir, *old.split('/'))
            if new not in sid_of or not os.path.isfile(path):
                continue
            old_cards = _read_cards_file(path)
            sid = sid_of[new]
            paras = anchored(split[sid]['text'])
            mine = [c for c in cards if c['source'] == sid]
            for oc in old_cards:
                q = quote_check.norm(oc['quote'])
                at = _find_anchor(oc['quote'], paras)
                if at and any(quote_check.norm(c['quote']) == q for c in mine):
                    continue
                entry = {'kind': 'not_carried', 'source': new, 'old_source': old, 'old': oc, 'new': None}
                if at:
                    entry['new_anchor'] = at
                else:
                    key = quote_check.norm(oc['conclusion'])
                    best = max(mine, default=None, key=lambda c: difflib.SequenceMatcher(
                        None, key, quote_check.norm(c['conclusion'])).ratio())
                    close = best is not None and difflib.SequenceMatcher(
                        None, key, quote_check.norm(best['conclusion'])).ratio() >= SIMILAR_MIN
                    entry['kind'], entry['new'] = ('changed', best) if close else ('removed', None)
                out.append(entry)
    return [dict(id='c%d' % i, **e) for i, e in enumerate(out, 1)]


def _read_run(batches, only=None):
    """(source table, split sources) of a run's batch files; only: the source numbers to keep (all when None)."""
    texts = []
    for p in batches:
        with open(p, encoding='utf-8') as f:
            texts.append(f.read().replace('\r\n', '\n'))
    table = {}
    for t in texts:
        table.update(kb_batch.sources_table(t))
    split = kb_batch.split_back(texts)
    if only is not None:
        unknown = sorted(set(only) - set(split))
        if unknown:
            raise ValueError('--sources names %s, not in the batch files; nothing written' % ', '.join(unknown))
        split = {sid: e for sid, e in split.items() if sid in only}
    for sid, e in split.items():
        table.setdefault(sid, {'name': e['name'], 'path': '', 'modified': ''})
    return table, split


def _bigrams(key):
    return {key[i:i + 2] for i in range(len(key) - 1)} or ({key} if key else set())


def version_candidates(batches, target, cfg, names=None, groups=None):
    """{"same_name": [names], "candidates": [{new, old, name_score, overlap}], "groups": [...],
    "duplicates": [...]} for a run. same_name: the run's names already in the library (in any folder),
    which are new versions anyway. Candidates: library sources under another name whose name key shares
    enough letter pairs with the new one (Dice NAME_MIN - 0.2 or more), is close (NAME_MIN) and that
    share OVERLAP_MIN of their paragraphs. new and old are file names."""
    table, split = _read_run(batches)
    srcs = run_sources(table, split, names)
    ix = kbindex.open_index(target, cfg)
    try:
        plan = plan_run(srcs, ix, groups)
        lib = ix.source_paths()
        keys = ix.keys()
    finally:
        ix.close()
    run_names = {srcs[sid]['name'] for sid in plan['current']}
    same = sorted(n for n in run_names if n in lib)
    grams = {}
    for path, key in keys:
        if path.rsplit('/', 1)[-1] in run_names or not key:
            continue
        for g in _bigrams(key):
            grams.setdefault(g, []).append((path, key))
    src_dir = os.path.join(target, cfg['names']['sources_dir'])
    found, cache = [], {}
    for sid in sorted(plan['current'], key=_sid_n):
        e = srcs[sid]
        if e['name'] in lib:
            continue
        key = name_key(e['name'])
        if not key:
            continue
        mine_g = _bigrams(key)
        shared = {}
        for g in mine_g:
            for item in grams.get(g, ()):
                shared[item] = shared.get(item, 0) + 1
        mine = None
        for (old, okey), n in shared.items():
            if 2.0 * n / (len(mine_g) + len(_bigrams(okey))) < NAME_MIN - 0.2:
                continue
            score = 1.0 if key == okey else round(difflib.SequenceMatcher(None, key, okey).ratio(), 2)
            if score < NAME_MIN:
                continue
            if old not in cache:
                with open(os.path.join(src_dir, *old.split('/')), encoding='utf-8') as f:
                    cache[old] = paragraphs(f.read())
            if mine is None:
                mine = paragraphs(split[sid]['text'])
            theirs = cache[old]
            overlap = round(len(mine & theirs) / min(len(mine), len(theirs)), 2) if mine and theirs else 0.0
            if overlap >= OVERLAP_MIN:
                found.append({'new': e['name'], 'old': old.rsplit('/', 1)[-1], 'old_path': old,
                              'name_score': score, 'overlap': overlap})
    found.sort(key=lambda c: (c['new'], -c['name_score'], c['old']))
    return {'same_name': same, 'candidates': found, 'groups': plan['groups'], 'duplicates': plan['duplicates']}


def _archive_path(folder, fname, old_suffix, stamp0):
    stem, ext = os.path.splitext(fname)
    k = 0
    while True:
        p = os.path.join(folder, '%s%s%s%s' % (stem, old_suffix, (stamp0 + timedelta(seconds=k)).strftime('%Y%m%d%H%M%S'), ext))
        if not os.path.exists(p):
            return p
        k += 1


def file_run(batches, cards, target, cfg, names=None, replaces=None, restore=None, groups=None, only=None):
    """File one run into target (a library or a staging folder); returns the run record.
    cards may be empty: the sources are then filed without cards, to be read and searched until their
    cards are written. replaces: {new file name: library file name it is a new version of};
    restore: conflicts (from conflicts()) to keep; groups: decisions on same-named sources (plan_run);
    only: the source numbers of the batch files to file (all when None)."""
    table, split = _read_run(batches, only)
    missing = ['%s %s (parts %s)' % (sid, e['name'], ', '.join(map(str, e['missing'])))
               for sid, e in split.items() if e['missing']]
    if missing:
        raise ValueError('parts missing from the batch files, nothing written: ' + '; '.join(missing))
    srcs = run_sources(table, split, names)
    ix = kbindex.open_index(target, cfg)
    try:
        plan = plan_run(srcs, ix, groups)
        lib = ix.source_paths()
        run_names = {srcs[sid]['name'] for sid in plan['current']}
        replaces = replaces or {}
        for new, old in replaces.items():
            if new not in run_names:
                raise ValueError('--replaces names %s, which is not a source of this run; nothing written' % new)
            if not lib.get(old):
                raise ValueError('--replaces names %s, which is not in the library; nothing written' % old)

        n = cfg['names']
        src_dir, card_dir = os.path.join(target, n['sources_dir']), os.path.join(target, n['cards_dir'])
        stamp0 = kbconf.now(cfg['timezone']).replace(microsecond=0)
        topics, archived, moved = set(), [], {}
        for olds in _replaced(srcs, plan, lib, replaces).values():
            for old in olds:
                for folder, sub in ((src_dir, n['sources_dir']), (card_dir, n['cards_dir'])):
                    path = os.path.join(folder, *old.split('/'))
                    if not os.path.isfile(path):
                        continue
                    if folder == card_dir:
                        topics.update(c['topic'] for c in _read_cards_file(path) if c['topic'])
                    dest = _archive_to(target, n, sub, old, stamp0)
                    shutil.move(path, dest)
                    archived.append('%s/%s' % (sub, old))
                    if folder == src_dir:
                        moved[old] = os.path.splitext(os.path.relpath(dest, target).replace(os.sep, '/'))[0]
        older = []
        for sid, path in plan['older'].items():
            dest = _archive_to(target, n, n['sources_dir'], path, stamp0)
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(split[sid]['text'])
            older.append(os.path.relpath(dest, target).replace(os.sep, '/'))
        current = plan['current']
        cards = [c for c in cards if c['source'] in current] + _restored(restore or [], srcs, current, split, table, moved)
        for sid, path in current.items():
            dest = os.path.join(src_dir, *path.split('/'))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(split[sid]['text'])
        quote_check.write(cards, table, card_dir, {sid: current[sid] for sid in current}, lang_of(cfg),
                          n['sources_dir'], n['topics_dir'])
        topics.update(c['topic'] for c in cards)
        review = mark_review(target, cfg, [os.path.splitext(p)[0] for p in moved], stamp0.strftime('%Y-%m-%d'))
        ix.refresh()
    finally:
        ix.close()
    with_cards = {c['source'] for c in cards}
    return {'sources': [current[sid] for sid in sorted(current, key=_sid_n)], 'archived': archived,
            'older': older, 'duplicates': plan['duplicates'], 'topics': sorted(topics),
            'without_cards': [current[sid] for sid in sorted(current, key=_sid_n) if sid not in with_cards],
            'restored': [e['id'] for e in restore or []], 'review': review}


def _archive_to(target, n, sub, path, stamp0):
    """A free path in the archive for an older version of path (below the sources or cards folder)."""
    folder, _, name = path.rpartition('/')
    dest_dir = os.path.join(target, n['archive_dir'], sub, *([x for x in folder.split('/') if x]))
    os.makedirs(dest_dir, exist_ok=True)
    return _archive_path(dest_dir, name, n['old_suffix'], stamp0)


def _restored(restore, srcs, current, split, table, moved):
    """Cards for the conflicts the owner restores: back on the new version where its text still holds
    the quote, else citing the archived old version."""
    sid_of = {srcs[sid]['name']: sid for sid in current}
    out = []
    for e in restore:
        sid = sid_of.get(e.get('source'))
        if sid is None:
            raise ValueError('a conflict to restore names %s, which is not a source of this run' % e.get('source'))
        oc = e['old']
        c = {'source': sid, 'quote': oc['quote'], 'conclusion': oc['conclusion'], 'topic': oc['topic'],
             'entities': oc.get('entities', [])}
        if oc.get('event_date'):
            c['event_date'] = oc['event_date']
        at = _find_anchor(oc['quote'], anchored(split[sid]['text']))
        if at:
            c.update(anchor=at, date=table.get(sid, {}).get('modified', ''))
        else:
            link = oc.get('link') or moved.get(e['old_source'])
            if not link:
                raise ValueError('the old version of %s is not being archived; cannot restore %s'
                                 % (e['old_source'], e.get('id')))
            c.update(anchor=oc['anchor'], date=oc.get('date', ''), link=link)
        out.append(c)
    return out


def add_cards(batches, cards, target, cfg):
    """Write the cards of sources already in the library that have none yet (batch files made by
    backfill_batch). Each source must be in the library at its path, with the same content and no cards
    file; nothing is archived. Returns {"sources", "topics", "refused": [{source, reason}]}."""
    table, split = _read_run(batches)
    srcs = run_sources(table, split)
    n = cfg['names']
    ix = kbindex.open_index(target, cfg)
    try:
        held = {p: fp for p, fp in ix.db.execute('SELECT path, fp FROM sources')}
        names, refused = {}, []
        for sid in sorted(split, key=_sid_n):
            e = srcs[sid]
            if e['path'] not in held:
                refused.append({'source': e['path'], 'reason': 'not in the library'})
            elif held[e['path']] != e['fp']:
                refused.append({'source': e['path'], 'reason': 'the library file changed since the batch file was made'})
            elif os.path.isfile(os.path.join(target, n['cards_dir'], *e['path'].split('/'))):
                refused.append({'source': e['path'], 'reason': 'it has cards already'})
            else:
                names[sid] = e['path']
        mine = [c for c in cards if c['source'] in names]
        quote_check.write(mine, table, os.path.join(target, n['cards_dir']), names, lang_of(cfg),
                          n['sources_dir'], n['topics_dir'])
        ix.refresh()
    finally:
        ix.close()
    with_cards = {c['source'] for c in mine}
    return {'sources': [names[sid] for sid in sorted(names, key=_sid_n) if sid in with_cards],
            'topics': sorted({c['topic'] for c in mine}), 'refused': refused}


BACKFILL_PREFIX = 'backfill_'


def backfill_batch(target, cfg, outdir, paths=None, limit=None):
    """Batch files for sources of the library without cards: the paths given (below the sources folder),
    else the newest first, at most limit sources; one source per batch file, kept whole, anchors as in
    the library (kb_batch.from_library). Returns the batch files written."""
    n = cfg['names']
    ix = kbindex.open_index(target, cfg)
    try:
        uncarded = ix.uncarded()
    finally:
        ix.close()
    dates = dict(uncarded)
    if paths is None:
        paths = [p for p, _ in uncarded]
    else:
        missing = [p for p in paths if p not in dates]
        if missing:
            raise ValueError('not sources without cards: %s' % ', '.join(missing))
    if limit:
        paths = paths[:limit]
    os.makedirs(outdir, exist_ok=True)
    stamp = kbconf.now(cfg['timezone']).strftime('%Y%m%d-%H%M%S')
    out = []
    for i, p in enumerate(paths, 1):
        with open(os.path.join(target, n['sources_dir'], *p.split('/')), encoding='utf-8') as f:
            text = f.read()
        units = kb_batch.from_library([{'name': p.rsplit('/', 1)[-1], 'path': p, 'modified': dates[p], 'text': text}])
        name = '%s%s_b%02d' % (BACKFILL_PREFIX, stamp, i)
        path = os.path.join(outdir, name + '.md')
        limit_chars, tier = kb_batch.batch_limit(None, cfg.get('batch_chars'))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(kb_batch.render(units, 1, 1, name, tier, max(limit_chars, units[0]['chars'])))
        out.append(path)
    return out


REVIEW_MARKS = {'en': '⏳ review: %s has a new version (%s)', 'zh': '⏳ 待复核：%s 有新版本（%s）'}


def mark_review(target, cfg, stems, day):
    """Mark the status card's items that cite one of the source stems; returns the items marked."""
    path = os.path.join(target, cfg['names']['status_card'])
    if not stems or not os.path.isfile(path):
        return []
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    src = cfg['names']['sources_dir']
    marked = []
    for i, line in enumerate(lines):
        for stem in stems:
            cite = re.compile(r'\[\[%s(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]' % re.escape('%s/%s' % (src, stem)))
            if cite.search(line) and not re.search(r'⏳[^⏳]*%s' % re.escape(stem), lines[i]):
                lines[i] = lines[i].rstrip() + ' ' + REVIEW_MARKS[lang_of(cfg)] % (stem, day)
        if lines[i] != line:
            marked.append(line)
    if marked:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    return marked


PAGE_LABELS = {
    'en': {'note': '> This page is generated from the cards by a script; edits here are overwritten.',
           'empty': 'No current cards.', 'card': 'card', 'undated': 'undated', 'earlier': 'earlier version',
           'years': 'Earlier years:', 'main': 'All years:'},
    'zh': {'note': '> 本页由脚本根据卡片生成，在此修改会被覆盖。',
           'empty': '暂无现行卡片。', 'card': '卡片', 'undated': '无日期', 'earlier': '旧版本',
           'years': '更早年份：', 'main': '全部年份：'},
}
YEAR_SPLIT = 60     # a topic with more cards than this gets one page per earlier year
YEAR_PAGE_RE = re.compile(r' \((\d{4})\)\.md$')


def _all_cards(target, cfg):
    """[(cards file stem, source link, card)] over every cards file of the library."""
    ix = kbindex.open_index(target, cfg)
    try:
        return [(os.path.splitext(f)[0], src, c) for f, src, c in ix.cards()]
    finally:
        ix.close()


def render_page(topic, entries, cfg, years=None, year=None, page=None):
    """A topic page; years lists the earlier years that have their own page; year and page name the
    main page of a year page."""
    lb = PAGE_LABELS[lang_of(cfg)]
    cards_dir, topics_dir = cfg['names']['cards_dir'], cfg['names']['topics_dir']
    w = ['# %s' % topic + (' (%s)' % year if year else ''), '', lb['note'], '']
    if year:
        w += ['%s [[%s/%s|%s]]' % (lb['main'], topics_dir, page, quote_check.link_text(topic)), '']
    if not entries:
        w += [lb['empty'], '']
    for day, stem, src, c in entries:
        w.append('- %s · %s' % (day or lb['undated'], c['conclusion']))
        w.append('  > %s [[%s#^%s]] · [[%s/%s|%s]]%s' % (c['quote'], c.get('link') or src, c['anchor'], cards_dir, stem,
                                                       lb['card'], ' · ' + lb['earlier'] if c.get('link') else ''))
    if years:
        w += ['', lb['years'] + ' ' + ' · '.join('[[%s/%s (%s)|%s]]' % (topics_dir, page, y, y) for y in years)]
    return '\n'.join(w) + '\n'


def _write(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def page_texts(ix, cfg, keys, names):
    """{file name in the topics folder: text} of the pages of the topics keys (topic keys), as pages_run
    writes them; names gives each key's topic as shown."""
    out = {}
    for k in dict.fromkeys(keys):
        entries = []
        for f, src, c in ix.cards([k]):
            day = c.get('event_date') or c['date'][:10]
            entries.append((day, os.path.splitext(f)[0], src, c))
        entries.sort(key=lambda e: (e[0] or '', e[1], int(e[3]['anchor'][1:] or 0)), reverse=True)
        page = quote_check.page_name(names[k])
        by_year = {}
        if len(entries) > YEAR_SPLIT:
            for e in entries:
                by_year.setdefault(e[0][:4] if e[0] else '', []).append(e)
        dated = sorted((y for y in by_year if y), reverse=True)
        earlier = dated[1:]
        main = [e for e in entries if not earlier or not e[0] or e[0][:4] == dated[0]]
        out[page + '.md'] = render_page(names[k], main, cfg, earlier, page=page)
        for y in earlier:
            out['%s (%s).md' % (page, y)] = render_page(names[k], by_year[y], cfg, year=y, page=page)
    return out


def pages_run(target, cfg, topics=None):
    """Rebuild the pages of the topics named (every topic with cards when None); returns their paths.
    A topic with more than YEAR_SPLIT cards keeps the newest year (and undated cards) on its page and
    each earlier year on a page of its own, "<topic> (YYYY)"; year pages no longer needed are removed."""
    ix = kbindex.open_index(target, cfg)
    try:
        held = ix.topics()
        if topics is None:
            wanted = sorted(held)
            names = {k: held[k][0] for k in held}
        else:
            wanted = [kbconf.topic_key(t) for t in topics]
            names = dict({k: held[k][0] for k in wanted if k in held}, **{kbconf.topic_key(t): t for t in topics})
        texts = page_texts(ix, cfg, wanted, names)
    finally:
        ix.close()
    folder = os.path.join(target, cfg['names']['topics_dir'])
    os.makedirs(folder, exist_ok=True)
    paths = []
    for fname, text in texts.items():
        path = os.path.join(folder, fname)
        _write(path, text)
        paths.append(path)
    mains = {quote_check.page_name(names[k]) for k in wanted}
    for f in os.listdir(folder):
        m = YEAR_PAGE_RE.search(f)
        if m and f[:m.start()] in mains and f not in texts:
            os.remove(os.path.join(folder, f))
    return paths


SPEC_LABELS = {
    'en': {'revision': 'Revision: v%s (%s) partition %s gets topic "%s"; no partition number added.',
           'entity': 'Revision: v%s (%s) entity "%s" added to Table E.',
           'alias': 'Revision: v%s (%s) "%s" recorded as an alias of "%s".',
           'types': {'project': 'project', 'team': 'department or team', 'organisation': 'organisation',
                     'system': 'system or product', 'other': 'other'}},
    'zh': {'revision': '修订：v%s（%s）分区 %s 增加主题「%s」，未新增分区号。',
           'entity': '修订：v%s（%s）表 E 增加实体「%s」。',
           'alias': '修订：v%s（%s）「%s」登记为「%s」的别名。',
           'types': {'project': '项目', 'team': '部门或团队', 'organisation': '单位',
                     'system': '系统或产品', 'other': '其他'}},
}
EMPTY_TABLE_RE = re.compile(r'^\s*(?:No entries yet|暂无条目)')
VERSION_RE = re.compile(r'^((?:Version|版本)\s*[:：]\s*v)(\d+)(?:\.(\d+))?\s*$')
UPDATED_RE = re.compile(r'^((?:Last updated|最后更新)\s*[:：]\s*).*$')
REVISION_RE = re.compile(r'^(?:Revision|修订)\s*[:：]')


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
    lang = 'zh' if zh else 'en'
    revise_spec(library, cfg, lines,
                lambda version, today: [SPEC_LABELS[lang]['revision'] % (version, today, part, t) for t in added])
    return added, known


def revise_spec(library, cfg, lines, notes):
    """Write the spec's lines back after a change: the version up one minor step, today's date as last
    updated, and the revision lines notes(version, today) after the header's last revision line."""
    today = kbconf.now(cfg['timezone']).strftime('%Y-%m-%d')
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
        lines[at:at] = notes(version, today)
    with open(spec_path(library, cfg), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


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


def _entity_index(table):
    """{name key: table name} for every name and alias of Table E."""
    index = {}
    for row in table:
        for name in [row['name']] + row['aliases']:
            index.setdefault(kbconf.topic_key(name), row['name'])
    return index


def entity_report(cards, spec):
    """{"merged": {name as written: table name}, "new": [{name, type, cards, closest}]} for the
    cards' entities against the spec's Table E."""
    table = kbconf.entities(spec)
    index = _entity_index(table)
    merged, new = {}, {}
    for c in cards:
        types = c.get('entity_types') or {}
        for name in c.get('entities') or []:
            hit = index.get(kbconf.topic_key(name))
            if hit:
                if name != hit:
                    merged[name] = hit
                continue
            e = new.setdefault(kbconf.topic_key(name), {'name': name, 'type': 'other', 'cards': 0, 'closest': []})
            e['cards'] += 1
            if e['type'] == 'other' and types.get(name) in quote_check.ENTITY_TYPES:
                e['type'] = types[name]
    for key, e in new.items():
        scored = sorted(((difflib.SequenceMatcher(None, key, k).ratio(), name) for k, name in index.items()),
                        reverse=True)
        e['closest'] = list(dict.fromkeys(name for r, name in scored if r >= 0.6))[:3]
    return {'merged': merged, 'new': list(new.values())}


def apply_entities(cards_path, library, cfg, decisions=None):
    """Write the owner's entity decisions: the cards file with the table's names, Table E with the new
    rows and aliases (one version step, a revision line each). Returns {merged, added, aliases}."""
    with open(cards_path, encoding='utf-8') as f:
        cards = [json.loads(ln) for ln in f if ln.strip()]
    spec = read_spec(library, cfg)
    table = kbconf.entities(spec)
    index = _entity_index(table)
    report = entity_report(cards, spec)
    decisions = decisions or {}
    added, aliases = [], {}
    for e in report['new']:
        d = decisions.get(e['name'])
        if isinstance(d, str):
            target = index.get(kbconf.topic_key(d))
            if not target:
                raise ValueError('%s is to become an alias of %s, which is not in Table E; nothing written' % (e['name'], d))
            aliases[e['name']] = target
            continue
        kind = (d or {}).get('type') or e['type']
        if kind not in quote_check.ENTITY_TYPES:
            raise ValueError('unknown entity type %s for %s (one of %s); nothing written'
                             % (kind, e['name'], ', '.join(quote_check.ENTITY_TYPES)))
        added.append((e['name'], kind))
    for name, target in aliases.items():
        index[kbconf.topic_key(name)] = target
    for name, _ in added:
        index[kbconf.topic_key(name)] = name
    for c in cards:
        c['entities'] = list(dict.fromkeys(index.get(kbconf.topic_key(x), x) for x in c.get('entities') or []))
    if added or aliases:
        _write_table_e(library, cfg, spec, added, aliases)
    with open(cards_path, 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    return {'merged': report['merged'], 'added': [n for n, _ in added], 'aliases': aliases}


def _write_table_e(library, cfg, spec, added, aliases):
    lines = spec.split('\n')
    start = None
    for i, ln in enumerate(lines):
        m = kbconf.TABLE_LABEL.search(ln)
        if m and '|' not in ln and m.group(1) == 'E':
            start = i
            break
    if start is None:
        raise ValueError('the spec has no Table E; nothing written')
    lang = 'zh' if '表' in lines[start] else 'en'
    lb = SPEC_LABELS[lang]
    header, last = None, None
    for i in range(start + 1, len(lines)):
        ln = lines[i]
        if kbconf.TABLE_LABEL.search(ln) and '|' not in ln:
            break
        if ln.count('|') >= 2:
            if header is None:
                header = i
            last = i
            cells = ln.split('|')
            name = cells[0].strip()
            for alias, target in aliases.items():
                if name == target and len(cells) > 2:
                    have = cells[2].strip()
                    cells[2] = ' %s ' % (have + ('；' if lang == 'zh' else '; ') + alias if have else alias)
            lines[i] = '|'.join(cells)
        elif header is not None and EMPTY_TABLE_RE.match(ln):
            lines[i] = None
    if header is None:
        raise ValueError('Table E has no column line; nothing written')
    rows = ['%s | %s |  |  | ' % (name, lb['types'][kind]) for name, kind in added]
    lines[last + 1:last + 1] = rows
    lines = [ln for ln in lines if ln is not None]
    revise_spec(library, cfg, lines, lambda version, today:
                [lb['alias'] % (version, today, a, t) for a, t in aliases.items()]
                + [lb['entity'] % (version, today, name) for name, _ in added])


NOTE_LABELS = {
    'en': {'name': 'Note', 'origin': 'assistant conversation', 'path': 'Original path', 'recorded': 'Recorded',
           'context': 'Context', 'colon': ': '},
    'zh': {'name': '随手记', 'origin': '助手对话', 'path': '原始路径', 'recorded': '记录时间',
           'context': '背景', 'colon': '：'},
}
TITLE_UNSAFE_RE = re.compile(r'[\\/:*?"<>|#^\[\]\n\r]+')


def note_batch(cfg, title, text, outdir, context=None):
    """Write a quick note as a run's batch files with one source (one file unless the words are very
    long); returns their paths."""
    lb = NOTE_LABELS[lang_of(cfg)]
    title = ' '.join(TITLE_UNSAFE_RE.sub(' ', title).split())
    words = text.replace('\r\n', '\n').strip()
    if not title or not words:
        raise ValueError('a note needs a title and some words')
    t = kbconf.now(cfg['timezone'])
    stamp, when = t.strftime('%Y%m%d-%H%M'), t.strftime('%Y-%m-%d %H:%M')
    meta = ''.join('> %s%s%s\n' % (k, lb['colon'], v) for k, v in (
        (lb['path'], lb['origin']), (lb['recorded'], '%s (%s)' % (when, cfg['timezone']))) + (
        ((lb['context'], ' '.join(context.split())),) if context and context.strip() else ()))
    limit, tier = kb_batch.batch_limit(None, cfg.get('batch_chars'))
    units, _ = kb_batch.build_units([{'name': '%s %s %s.md' % (lb['name'], stamp, title), 'path': lb['origin'],
                                      'modified': when, 'meta': meta, 'body': words}], limit)
    batches = kb_batch.pack(units, limit)
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for i, b in enumerate(batches, 1):
        stem = 'note_%s_b%02d' % (stamp, i)
        path = os.path.join(outdir, stem + '.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(kb_batch.render(b, i, len(batches), stem, tier, limit))
        paths.append(path)
    return paths


PENDING_DIR = '_pending'
RUN_RE = re.compile(r'^[0-9A-Za-z_-]{1,64}$')


def pending_paths(library, run):
    """(pending file, decisions file) of a run; refuses a run name that is not a plain name."""
    if not RUN_RE.match(run or ''):
        raise ValueError('a run name is letters, digits, - and _ only, got %r' % run)
    base = os.path.join(library, PENDING_DIR, run)
    return base + '.json', base + '.decisions.json'


def _load(path, default):
    if not path:
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def pending_write(library, cfg, run=None, report=None, entities=None, versions=None, conflicts_found=None):
    """Write the run's decisions to be made to <library>/_pending/<run>.json; returns its path."""
    run = run or kbconf.now(cfg['timezone']).strftime('%Y%m%d-%H%M%S')
    path, _ = pending_paths(library, run)
    spec = read_spec(library, cfg)
    pend = {'run': run, 'label': cfg.get('label', ''), 'created': kbconf.now(cfg['timezone']).strftime('%Y-%m-%d %H:%M'),
            'new_topics': (report or {}).get('new_topics', []), 'topics': kbconf.topics(spec, cfg),
            'entities': (entities or {}).get('new', []), 'entity_names': [r['name'] for r in kbconf.entities(spec)],
            'same_name': (versions or {}).get('same_name', []), 'versions': (versions or {}).get('candidates', []),
            'groups': (versions or {}).get('groups', []), 'duplicates': (versions or {}).get('duplicates', []),
            'conflicts': conflicts_found or []}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pend, f, ensure_ascii=False, indent=1)
    return path


def check_decisions(pend, decisions):
    """Problems with the owner's decisions for a pending run; [] when they can be used."""
    out = []
    d = decisions if isinstance(decisions, dict) else {}
    topics = {kbconf.topic_key(t) for t in pend['topics']}
    for name, v in (d.get('topics') or {}).items():
        if name not in pend['new_topics']:
            out.append('topic %s is not a new topic of this run' % name)
        elif not isinstance(v, dict) or not (v.get('add') or kbconf.topic_key(str(v.get('under', ''))) in topics):
            out.append('topic %s: add it or put it under a topic of the spec' % name)
    names = {kbconf.topic_key(n) for n in pend['entity_names']}
    new_names = [e['name'] for e in pend['entities']]
    for name, v in (d.get('entities') or {}).items():
        if name not in new_names:
            out.append('entity %s is not a new name of this run' % name)
        elif not isinstance(v, dict):
            out.append('entity %s: add it or record it as an alias' % name)
        elif 'alias' in v and kbconf.topic_key(str(v['alias'])) not in names:
            out.append('entity %s: %s is not in Table E' % (name, v['alias']))
        elif 'alias' not in v and v.get('type', 'other') not in quote_check.ENTITY_TYPES:
            out.append('entity %s: unknown type %s' % (name, v.get('type')))
    pairs = {'%s=%s' % (c['new'], c['old']) for c in pend['versions']}
    for pair in d.get('versions') or []:
        if pair not in pairs:
            out.append('%s is not a version candidate of this run' % pair)
    members = {g['name']: {m['path'] for m in g['members']} for g in pend.get('groups', [])}
    for name, v in (d.get('groups') or {}).items():
        if name not in members:
            out.append('%s is not a group of same-named sources of this run' % name)
        elif not isinstance(v, dict) or (v.get('current') and v['current'] not in members[name]) \
                or not set(v.get('separate') or []) <= members[name]:
            out.append('group %s: current and separate must name sources of the group' % name)
    ids = {c['id'] for c in pend['conflicts']}
    for cid, v in (d.get('conflicts') or {}).items():
        if cid not in ids:
            out.append('conflict %s is not one of this run' % cid)
        elif v not in ('accept', 'restore'):
            out.append('conflict %s: accept or restore, not %s' % (cid, v))
    return out


def pending_read(library, run, work):
    """The decisions of a run as the next commands take them; writes entity-map.json and restore.json."""
    path, dpath = pending_paths(library, run)
    pend = _load(path, None)
    if not os.path.isfile(dpath):
        raise ValueError('no decisions for run %s yet (%s)' % (run, dpath))
    d = _load(dpath, {})
    problems = check_decisions(pend, d)
    if problems:
        raise ValueError('the decisions cannot be used: ' + '; '.join(problems))
    topics = d.get('topics') or {}
    retopic_to = {n: v['under'] for n, v in topics.items() if not v.get('add')}
    emap = {}
    for name, v in (d.get('entities') or {}).items():
        emap[name] = v['alias'] if 'alias' in v else {'type': v.get('type', 'other')}
    restore = [c for c in pend['conflicts'] if (d.get('conflicts') or {}).get(c['id']) == 'restore']
    os.makedirs(work, exist_ok=True)
    out = {'add_topics': [t for t in pend['new_topics'] if t not in retopic_to], 'retopic': retopic_to,
           'replaces': list(d.get('versions') or []),
           'entity_map': os.path.join(work, 'entity-map.json'), 'restore': os.path.join(work, 'restore.json'),
           'groups': os.path.join(work, 'groups.json')}
    for key, data in (('entity_map', emap), ('restore', restore), ('groups', d.get('groups') or {})):
        with open(out[key], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return out


def pending_done(library, run):
    """Remove a filed run's pending and decisions files (and the folder when it is empty)."""
    for path in pending_paths(library, run):
        if os.path.isfile(path):
            os.remove(path)
    folder = os.path.join(library, PENDING_DIR)
    if os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)


def status_items(text):
    return [ln.strip() for ln in text.replace('\r\n', '\n').split('\n') if ITEM_RE.match(ln)]


def status_check(old_text, new_text):
    """{removed, changed: [{old, new}], lost, added} between two versions of the status card."""
    def key(item):
        return quote_check.norm(re.sub(r'^\s*\d+[.、．]\s*', '', MARK_RE.sub('', item)))

    old, new = status_items(old_text), status_items(new_text)
    free = list(new)
    removed, changed = [], []
    for item in old:
        same = next((x for x in free if key(x) == key(item)), None)
        if same is not None:
            free.remove(same)
            continue
        cites = set(CITE_RE.findall(item))
        near = next((x for x in free if cites & set(CITE_RE.findall(x))), None)
        if near is not None:
            free.remove(near)
            changed.append({'old': MARK_RE.sub('', item), 'new': near})
        else:
            removed.append(MARK_RE.sub('', item))
    kept = set(CITE_RE.findall('\n'.join(new)))
    lost = sorted(dict.fromkeys(c for item in old for c in CITE_RE.findall(item) if c not in kept))
    return {'removed': removed, 'changed': changed, 'lost': lost, 'added': free}


PENDING_DAYS = 7    # a run waiting longer than this for the owner's decisions is reported
LIB_LINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#\^(p\d+))?(?:\|[^\]]*)?\]\]')


def health_check(library, cfg, today=None):
    """A read-only check of a library; returns {"problems": n, ...} with the findings by kind:
      quotes      cards whose quote is not in the paragraph its link names (or the source or anchor is gone)
      links       links of the status card's items and the topic pages to a source, cards file, topic page or
                  archived file that does not exist
      pages       topics with cards whose page is missing or differs from what ingest.py pages builds,
                  and year pages that are no longer built
      unpaired    cards files without their source
      status      status-card items marked for review, and items citing a source that is not current
      pending     runs waiting for the owner's decisions for more than PENDING_DAYS days
      work        run folders under .kb-work left unfinished for more than WORK_DAYS days
      uncarded    sources without cards yet (counted, not a problem)
    """
    n = cfg['names']
    today = today or kbconf.now(cfg['timezone']).date()
    ix = kbindex.open_index(library, cfg)
    try:
        sources = {p for p, in ix.db.execute('SELECT path FROM sources')}
        paras = {}
        for src, anchor, text in ix.db.execute('SELECT source, anchor, text FROM paragraphs'):
            paras[(src, anchor)] = text
        quotes, archived_cache = [], {}
        for cards_file, src, c in ix.cards():
            link = c.get('link') or src
            if link.startswith(n['sources_dir'] + '/'):
                text = paras.get((link[len(n['sources_dir']) + 1:] + '.md', c['anchor']))
            else:
                if link not in archived_cache:
                    path = os.path.join(library, *link.split('/')) + '.md'
                    archived_cache[link] = None
                    if os.path.isfile(path):
                        with open(path, encoding='utf-8') as fh:
                            archived_cache[link] = anchored(fh.read())
                text = (archived_cache[link] or {}).get(c['anchor'])
            if text is None:
                quotes.append({'cards': cards_file, 'link': '%s#^%s' % (link, c['anchor']), 'reason': 'no such paragraph'})
            elif quote_check.norm(c['quote']) not in quote_check.norm(text):
                quotes.append({'cards': cards_file, 'link': '%s#^%s' % (link, c['anchor']), 'reason': 'quote not in the paragraph'})
        top = n['cards_dir'] + '/'
        unpaired = sorted(p[len(top):] for p, in ix.db.execute('SELECT path FROM files') if p.startswith(top)
                          and p[len(top):] not in sources)
        held = ix.topics()
        texts = page_texts(ix, cfg, sorted(held), {k: held[k][0] for k in held})
        uncarded = len(ix.uncarded())
    finally:
        ix.close()

    topics_dir = os.path.join(library, n['topics_dir'])
    on_disk = {f for f in os.listdir(topics_dir) if f.endswith('.md')} if os.path.isdir(topics_dir) else set()
    pages = {'missing': sorted(f for f in texts if f not in on_disk), 'stale': [], 'extra': []}
    for f in sorted(texts):
        if f in on_disk:
            with open(os.path.join(topics_dir, f), encoding='utf-8') as fh:
                if fh.read() != texts[f]:
                    pages['stale'].append(f)
    mains = {f[:-3] for f in texts if not YEAR_PAGE_RE.search(f)}
    for f in sorted(on_disk):
        m = YEAR_PAGE_RE.search(f)
        if m and f[:m.start()] in mains and f not in texts:
            pages['extra'].append(f)

    def exists(target):
        return os.path.isfile(os.path.join(library, *target.split('/')) + '.md')

    links, tops = [], tuple(n[k] + '/' for k in ('sources_dir', 'cards_dir', 'topics_dir', 'archive_dir'))
    card_path = os.path.join(library, n['status_card'])
    files = [(n['status_card'], card_path)] + [('%s/%s' % (n['topics_dir'], f), os.path.join(topics_dir, f))
                                               for f in sorted(on_disk)]
    status = {'review': [], 'not_current': []}
    for shown, path in files:
        if not os.path.isfile(path):
            continue
        with open(path, encoding='utf-8') as fh:
            text = fh.read()
        if shown == n['status_card']:   # only its numbered items cite; the text above them may show examples
            text = '\n'.join(ln for ln in text.split('\n') if ITEM_RE.match(ln))
        for target, _ in LIB_LINK_RE.findall(text):
            if target.startswith(tops) and not exists(target):
                links.append({'file': shown, 'link': target})
        if shown != n['status_card']:
            continue
        for line in text.split('\n'):
            if not ITEM_RE.match(line):
                continue
            item = MARK_RE.sub('', line).strip()
            if '⏳' in line:
                status['review'].append(item)
            cited = [t for t, _ in LIB_LINK_RE.findall(item) if t.startswith(n['sources_dir'] + '/')]
            if any(t[len(n['sources_dir']) + 1:] + '.md' not in sources for t in cited):
                status['not_current'].append(item)

    pending = []
    folder = os.path.join(library, PENDING_DIR)
    for fname in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if fname.endswith('.json') and not fname.endswith('.decisions.json'):
            age = (today - datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, fname))).date()).days
            if age > PENDING_DAYS:
                pending.append({'run': fname[:-5], 'days': age})
    work = [{'run': r['run'], 'days': r['days']} for r in work_runs(library) if not r['done'] and r['days'] > WORK_DAYS]
    problems = (len(quotes) + len(links) + sum(len(v) for v in pages.values()) + len(unpaired)
                + len(status['review']) + len(status['not_current']) + len(pending) + len(work))
    return {'problems': problems, 'quotes': quotes, 'links': links, 'pages': pages, 'unpaired': unpaired,
            'status': status, 'pending': pending, 'work': work, 'uncarded': uncarded, 'sources': len(sources)}


# ---------------------------------------------------------------- work folders

WORK_DIR = '.kb-work'
WORK_RE = re.compile(r'^(chat|client)-\d{8}-\d{6}(?:-\d+)?$')
WORK_DAYS = 7       # a run left unfinished longer than this is reported by the health check
FILED_LOG, PAGES_LOG = 'filed.json', 'pages.json'
BATCH_NAME_RE = re.compile(r'_b\d{2,}\.md$')


def work_new(library, cfg, prefix='chat'):
    """Make <library>/.kb-work/<prefix>-<YYYYMMDD-HHMMSS>/ (a -2, -3, ... suffix when taken); returns its path."""
    if prefix not in ('chat', 'client'):
        raise ValueError('a work folder prefix is chat or client, got %r' % prefix)
    base = '%s-%s' % (prefix, kbconf.now(cfg['timezone']).strftime('%Y%m%d-%H%M%S'))
    root = os.path.join(library, WORK_DIR)
    os.makedirs(root, exist_ok=True)
    name, k = base, 1
    while True:
        path = os.path.join(root, name)
        try:
            os.mkdir(path)
            return path
        except FileExistsError:
            k += 1
            name = '%s-%d' % (base, k)


def work_place(work):
    """(library root, run name) of a run's work folder; refuses any folder that is not
    <library>/.kb-work/<chat|client>-<time>."""
    real = os.path.realpath(work)
    parent, run = os.path.split(real)
    if os.path.basename(parent) != WORK_DIR or not WORK_RE.match(run) or not os.path.isdir(real):
        raise ValueError('not a run folder under %s/: %s' % (WORK_DIR, work))
    return os.path.dirname(parent), run


def log_step(work, fname, record):
    """Append a step's record to <work>/<fname> (a JSON list), for progress."""
    if not work:
        return
    path = os.path.join(work, fname)
    done = _load(path if os.path.isfile(path) else None, [])
    done.append(record)
    _write(path, json.dumps(done, ensure_ascii=False, indent=1) + '\n')


def _mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0


def work_progress(work):
    """How far the run in a work folder got, from the files the steps leave there; see progress."""
    if not os.path.isdir(work):
        raise ValueError('no such work folder: %s' % work)
    batches = []
    for here, dirs, names in os.walk(work):
        dirs[:] = sorted(d for d in dirs if d != 'cards')
        batches += [os.path.join(here, n) for n in sorted(names) if BATCH_NAME_RE.search(n)]
    kind = 'ingest'
    if batches and all(os.path.basename(b).startswith('note_') for b in batches):
        kind = 'note'
    elif batches and all(os.path.basename(b).startswith(BACKFILL_PREFIX) for b in batches):
        kind = 'backfill'
    sources = sorted(quote_check.load_batches(batches)[0], key=_sid_n) if batches else []
    cards_dir = os.path.join(work, 'cards')
    have = {os.path.splitext(n)[0].upper(): os.path.join(cards_dir, n)
            for n in (os.listdir(cards_dir) if os.path.isdir(cards_dir) else []) if n.endswith('.jsonl')}
    missing = [s for s in sources if s not in have]
    p = lambda name: os.path.join(work, name)
    newest_cards = max([_mtime(x) for x in have.values()] + [0])
    verified = os.path.isfile(p('accepted.jsonl')) and os.path.isfile(p('report.json')) \
        and _mtime(p('report.json')) >= newest_cards
    rejected = len(_load(p('report.json'), {}).get('rejected', [])) if verified else 0
    retried = os.path.isfile(p('report2.json'))
    filed = _load(p(FILED_LOG) if os.path.isfile(p(FILED_LOG)) else None, [])
    built = _load(p(PAGES_LOG) if os.path.isfile(p(PAGES_LOG)) else None, [])
    touched = {kbconf.topic_key(t): t for r in filed for t in r.get('topics', [])}
    if any(b.get('all') for b in built):
        unbuilt = []
    else:
        done = {kbconf.topic_key(t) for b in built for t in b.get('topics', [])}
        unbuilt = sorted(v for k, v in touched.items() if k not in done)
    got = {'work': work, 'kind': kind, 'batches': batches, 'sources': sources, 'cards_missing': missing,
           'verified': verified, 'rejected': rejected, 'retried': retried,
           'entities': os.path.isfile(p('entities.json')), 'versions': os.path.isfile(p('versions.json')),
           'conflicts': os.path.isfile(p('conflicts.json')), 'filed': bool(filed), 'pages_missing': unbuilt}
    got['done'] = bool(filed) and not unbuilt
    if got['done']:
        step, nxt = 11, 'finished: report from filed.json, then ingest.py work done --work %s' % work
    elif filed:
        step, nxt = 10, 'ingest.py pages --library <library> %s --work %s' % (
            ' '.join('--topic "%s"' % t for t in unbuilt), work)
    elif not batches:
        step, nxt = 1, 'make the batch files (kb_batch.py make ... -o %s)' % os.path.join(work, 'batches')
    elif missing:
        step, nxt = 2, 'write the cards of %s to %s/<Snn>.jsonl, one file per source (an empty file for a ' \
            'source with nothing worth a card)' % (', '.join(missing), cards_dir)
    elif not verified:
        step, nxt = 3, 'ingest.py topics, then quote_check.py verify %s <batch files> --accepted %s --report %s' % (
            cards_dir, p('accepted.jsonl'), p('report.json'))
    elif rejected and not retried:
        step, nxt = 3, 'rewrite the %d rejected cards to %s and verify them (report2.json)' % (rejected, p('retry.jsonl'))
    elif not got['entities']:
        step, nxt = 5, 'ingest.py entities %s --library <library> > %s' % (p('accepted.jsonl'), p('entities.json'))
    elif kind == 'ingest' and not got['versions']:
        step, nxt = 6, 'ingest.py versions <batch files> --library <library> > %s' % p('versions.json')
    elif kind == 'ingest' and not got['conflicts']:
        step, nxt = 7, 'ingest.py conflicts <batch files> --cards %s --library <library> > %s' % (
            p('accepted.jsonl'), p('conflicts.json'))
    else:
        cmd = 'add-cards' if kind == 'backfill' else 'file'
        step, nxt = 8, 'show the preview; after the user confirms, ingest.py %s <batch files> --cards %s ' \
            '--library <library> --work %s' % (cmd, p('accepted.jsonl'), work)
    got['step'], got['next'] = step, nxt
    return got


def render_progress(got):
    w = ['work folder: %s' % got['work'], 'step reached: %d' % got['step'],
         'sources: %d, without a cards file: %d' % (len(got['sources']), len(got['cards_missing']))]
    if got['cards_missing']:
        w.append('  ' + ', '.join(got['cards_missing']))
    w.append('filed: %s' % ('yes' if got['filed'] else 'no'))
    if got['pages_missing']:
        w.append('topic pages not yet rebuilt: ' + ', '.join(got['pages_missing']))
    w.append('finished: %s' % ('yes' if got['done'] else 'no'))
    w.append('next: ' + got['next'])
    return '\n'.join(w) + '\n'


def work_runs(library):
    """[{run, days, done}] of the run folders under <library>/.kb-work, newest first; days counts from
    the newest file in the folder."""
    root = os.path.join(library, WORK_DIR)
    today = datetime.now()
    out = []
    for name in sorted(os.listdir(root), reverse=True) if os.path.isdir(root) else []:
        path = os.path.join(root, name)
        if not (WORK_RE.match(name) and os.path.isdir(path)):
            continue
        newest = os.path.getmtime(path)
        for here, _, names in os.walk(path):
            for n in names:
                newest = max(newest, _mtime(os.path.join(here, n)))
        try:
            done = work_progress(path)['done']
        except (OSError, ValueError):
            done = False
        out.append({'run': name, 'days': (today - datetime.fromtimestamp(newest)).days, 'done': done})
    return out


def work_remove(work, finished):
    """Remove a run folder under .kb-work: finished=True only once progress says the run is finished
    (work done); finished=False removes it whatever its state (work drop, after the user agreed)."""
    work_place(work)
    if finished and not work_progress(work)['done']:
        raise ValueError('the run is not finished (ingest.py progress --work %s says what is left)' % work)
    shutil.rmtree(work)


CHECK_LABELS = {
    'en': {'quotes': 'Cards whose quote is not in its paragraph', 'links': 'Links to files that do not exist',
           'missing': 'Topic pages missing (ingest.py pages --all builds them)',
           'stale': 'Topic pages that differ from the cards (ingest.py pages --all rebuilds them)',
           'extra': 'Year pages no longer built', 'unpaired': 'Cards files without their source',
           'review': 'Status-card items marked for review', 'not_current': 'Status-card items citing a source that is not current',
           'pending': 'Runs waiting for decisions for more than %d days' % PENDING_DAYS,
           'work': 'Unfinished runs in %s for more than %d days (continue, or ingest.py work drop)' % (WORK_DIR, WORK_DAYS),
           'summary': '%d sources, %d of them without cards yet; %d problems.'},
    'zh': {'quotes': '引文不在所链接段落里的卡片', 'links': '指向不存在文件的链接',
           'missing': '缺少的主题页（ingest.py pages --all 可生成）',
           'stale': '与卡片不一致的主题页（ingest.py pages --all 可重建）',
           'extra': '已不再生成的年份页', 'unpaired': '没有对应来源的卡片文件',
           'review': '状态卡中待复核的条目', 'not_current': '状态卡中引用了非现行来源的条目',
           'pending': '等待决定超过 %d 天的入库' % PENDING_DAYS,
           'work': '%s 里超过 %d 天未完成的入库（可继续，或用 ingest.py work drop 放弃）' % (WORK_DIR, WORK_DAYS),
           'summary': '共 %d 份来源，其中 %d 份尚未抽卡；发现 %d 个问题。'},
}


def render_check(got, lang):
    lb = CHECK_LABELS[lang]
    groups = [('quotes', ['%s %s (%s)' % (q['cards'], q['link'], q['reason']) for q in got['quotes']]),
              ('links', ['%s: [[%s]]' % (x['file'], x['link']) for x in got['links']]),
              ('missing', got['pages']['missing']), ('stale', got['pages']['stale']), ('extra', got['pages']['extra']),
              ('unpaired', got['unpaired']), ('review', got['status']['review']),
              ('not_current', got['status']['not_current']),
              ('pending', ['%s (%d)' % (p['run'], p['days']) for p in got['pending']]),
              ('work', ['%s (%d)' % (r['run'], r['days']) for r in got['work']])]
    w = [lb['summary'] % (got['sources'], got['uncarded'], got['problems'])]
    for key, rows in groups:
        if rows:
            w += ['', '%s: %d' % (lb[key], len(rows))] + ['  ' + r for r in rows[:50]]
            if len(rows) > 50:
                w.append('  ...')
    return '\n'.join(w) + '\n'


def replace_pair(text):
    new, sep, old = text.partition('=')
    if not (sep and new.strip() and old.strip()):
        raise argparse.ArgumentTypeError('expected NEW.md=OLD.md, got %r' % text)
    return new.strip(), old.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description='File an intake run into a library and rebuild its topic pages.')
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('file', help='split the batch files back, archive old versions, write the cards')
    f.add_argument('batches', nargs='+', help='batch files of the run')
    f.add_argument('--cards', default=None, help='accepted cards (quote_check.py verify --accepted); '
                   'without it the sources are filed without cards')
    f.add_argument('--names', default=None,
                   help='JSON file mapping a source number or original file name to a file name')
    cf = sub.add_parser('conflicts', help='old cards that a new version changes, drops or does not carry over')
    cf.add_argument('batches', nargs='+', help='batch files of the run')
    cf.add_argument('--cards', required=True, help='accepted cards (quote_check.py verify --accepted)')
    for p in (f, cf):
        p.add_argument('--replaces', action='append', type=replace_pair, default=[],
                       help='NEW.md=OLD.md: the run\'s source NEW is a new version of the library\'s OLD (repeatable)')
    f.add_argument('--restore', default=None, help='JSON file with the conflicts to restore')
    sc = sub.add_parser('status-check', help='a rewritten status card against the current one')
    sc.add_argument('--old', required=True, help='the current status card')
    sc.add_argument('--new', required=True, help='the rewrite')
    sc.add_argument('--write', action='store_true', help='when nothing was removed, changed or lost, put it in the library')
    sc.add_argument('--confirmed', action='store_true', help='write even with changes: the owner accepted the list')
    sc.add_argument('--library', default=None, help='library root, for --write')
    pd = sub.add_parser('pending', help="the owner's decisions of a run through a file (knowledge base client)")
    pd.add_argument('what', choices=['write', 'read', 'done'])
    pd.add_argument('--run', default=None, help='run name (write makes one when none is given)')
    for opt in ('report', 'entities', 'versions', 'conflicts'):
        pd.add_argument('--' + opt, default=None, help='JSON output of the %s step (write)' % opt)
    pd.add_argument('--work', default=None, help='work folder for entity-map.json and restore.json (read)')
    nt = sub.add_parser('note', help='a quick note as the batch file of a one-source run')
    nt.add_argument('--title', required=True, help='a few words naming the note')
    nt.add_argument('--text', required=True, help="text file with the user's words")
    nt.add_argument('--context', default=None, help='one sentence on where the note came up')
    nt.add_argument('-o', '--outdir', required=True, help='work folder for the batch file')
    vs = sub.add_parser('versions', help='library sources that may be older versions of the run\'s sources')
    vs.add_argument('batches', nargs='+', help='batch files of the run')
    en = sub.add_parser('entities', help='the cards\' entities against Table E; --apply writes the decisions')
    en.add_argument('cards', help='accepted cards (JSON lines); rewritten in place with --apply')
    en.add_argument('--apply', action='store_true', help='rewrite the cards and add to Table E')
    en.add_argument('--map', default=None, help='JSON file with the owner\'s decisions (see above)')
    pg = sub.add_parser('pages', help='rebuild topic pages from the cards')
    group = pg.add_mutually_exclusive_group(required=True)
    group.add_argument('--topic', action='append', help='a topic to rebuild (repeatable)')
    group.add_argument('--all', action='store_true', help='every topic with cards')
    tp = sub.add_parser('topics', help="print the topics of the spec's Table A, one per line")
    tp.add_argument('--out', default=None, help='write them to this file as well')
    at = sub.add_parser('add-topic', help='add confirmed topics to Table A (one version step, a revision line each)')
    at.add_argument('--topic', action='append', required=True, help='a topic to add (repeatable)')
    at.add_argument('--partition', default=None, help='two-digit partition (default: partitions.fallback)')
    for p in (f, pg, tp, at, vs, en, cf, nt, pd):
        p.add_argument('--library', required=True, help='library root (its _kb.json gives the names)')
    for p in (f, pg, vs, cf):
        p.add_argument('--target', default=None, help='work on this folder, laid out like the library, instead')
    for p in (f, vs, cf):
        p.add_argument('--groups', default=None, help='JSON file with the decisions on same-named sources of the run')
    pr = sub.add_parser('progress', help='how far the run in a work folder got, and the next step')
    pr.add_argument('--work', required=True, help='the run\'s work folder')
    pr.add_argument('--json', action='store_true', help='print JSON instead of text')
    wk = sub.add_parser('work', help='run folders under <library>/%s' % WORK_DIR)
    wk.add_argument('what', choices=['new', 'list', 'done', 'drop'])
    wk.add_argument('--library', default=None, help='library root (new, list, drop)')
    wk.add_argument('--prefix', choices=['chat', 'client'], default='chat', help='new: who runs it (default chat)')
    wk.add_argument('--work', default=None, help='done: the finished run\'s work folder')
    wk.add_argument('--run', default=None, help='drop: the run folder\'s name')
    for p in (f, pg):
        p.add_argument('--work', default=None, help='the run\'s work folder: the step is recorded there for progress')
    ck = sub.add_parser('check', help='a read-only check of the library (exit 3 when it finds problems)')
    ck.add_argument('--json', action='store_true', help='print JSON instead of text')
    ck.add_argument('--library', required=True, help='library root')
    ac = sub.add_parser('add-cards', help='write the cards of library sources that have none yet')
    ac.add_argument('batches', nargs='+', help='batch files made by backfill')
    ac.add_argument('--cards', required=True, help='accepted cards (quote_check.py verify --accepted)')
    ac.add_argument('--library', required=True, help='library root')
    ac.add_argument('--work', default=None, help='the run\'s work folder: the step is recorded there for progress')
    bf = sub.add_parser('backfill', help='batch files for library sources without cards, newest first')
    bf.add_argument('--library', required=True, help='library root')
    bf.add_argument('-o', '--outdir', required=True, help='work folder for the batch files')
    bf.add_argument('--source', action='append', default=None, help='a source path below the sources folder (repeatable)')
    bf.add_argument('--limit', type=int, default=None, help='at most this many sources')
    for p in (f, cf):
        p.add_argument('--sources', default=None, help='file only these source numbers of the batch files, e.g. S01,S03')
    rt = sub.add_parser('retopic', help="change accepted cards' topic")
    rt.add_argument('cards', help='accepted cards (JSON lines), rewritten in place')
    rt.add_argument('--from', dest='old', required=True)
    rt.add_argument('--to', dest='new', required=True)
    a = ap.parse_args(argv)
    kbconf.setup_logging(a.log_level)

    try:
        if a.cmd == 'status-check':
            with open(a.old, encoding='utf-8') as fh:
                old = fh.read()
            with open(a.new, encoding='utf-8') as fh:
                new = fh.read()
            res = status_check(old, new)
            print(json.dumps(res, ensure_ascii=False))
            if (res['removed'] or res['changed'] or res['lost']) and not (a.write and a.confirmed):
                return 3
            if a.write:
                if not a.library:
                    raise ValueError('--write needs --library')
                cfg = kbconf.load_library(a.library)
                with open(os.path.join(a.library, cfg['names']['status_card']), 'w', encoding='utf-8') as fh:
                    fh.write(new)
            return 0
        if a.cmd == 'progress':
            got = work_progress(a.work)
            print(json.dumps(got, ensure_ascii=False) if a.json else render_progress(got), end='')
            return 0
        if a.cmd == 'work':
            if a.what == 'done':
                if not a.work:
                    raise ValueError('work done needs --work')
                work_remove(a.work, True)
                print('removed: ' + a.work)
                return 0
            if not a.library:
                raise ValueError('work %s needs --library' % a.what)
            if a.what == 'new':
                print(work_new(a.library, kbconf.load_library(a.library), a.prefix))
            elif a.what == 'list':
                for r in work_runs(a.library):
                    print('%s  %s  %d days' % (r['run'], 'finished' if r['done'] else 'unfinished', r['days']))
            else:
                if not a.run or not WORK_RE.match(a.run):
                    raise ValueError('work drop needs --run with a run folder name')
                path = os.path.join(a.library, WORK_DIR, a.run)
                work_remove(path, False)
                print('removed: ' + path)
            return 0
        if a.cmd == 'retopic':
            n = retopic(a.cards, a.old, a.new)
            print('%d card%s now under %s' % (n, '' if n == 1 else 's', a.new))
            return 0
        cfg = kbconf.load_library(a.library)
        if a.cmd == 'backfill':
            for path in backfill_batch(a.library, cfg, a.outdir, a.source, a.limit):
                print(path)
            return 0
        if a.cmd == 'add-cards':
            with open(a.cards, encoding='utf-8') as fh:
                cards = [json.loads(ln) for ln in fh if ln.strip()]
            got = add_cards(a.batches, cards, a.library, cfg)
            log_step(a.work, FILED_LOG, got)
            print(json.dumps(got, ensure_ascii=False))
            return 0
        if a.cmd == 'check':
            got = health_check(a.library, cfg)
            print(json.dumps(got, ensure_ascii=False) if a.json else render_check(got, lang_of(cfg)), end='')
            return 3 if got['problems'] else 0
        if a.cmd == 'topics':
            found = kbconf.topics(read_spec(a.library, cfg), cfg)
            for t in found:
                print(t)
            if a.out:
                with open(a.out, 'w', encoding='utf-8') as fh:
                    fh.write(''.join(t + '\n' for t in found))
            return 0
        if a.cmd == 'pending':
            if a.what == 'write':
                print(pending_write(a.library, cfg, a.run, _load(a.report, None), _load(a.entities, None),
                                    _load(a.versions, None), _load(a.conflicts, None)))
            elif a.what == 'read':
                if not (a.run and a.work):
                    raise ValueError('pending read needs --run and --work')
                print(json.dumps(pending_read(a.library, a.run, a.work), ensure_ascii=False))
            else:
                pending_done(a.library, a.run)
            return 0
        if a.cmd == 'note':
            with open(a.text, encoding='utf-8') as fh:
                words = fh.read()
            for path in note_batch(cfg, a.title, words, a.outdir, a.context):
                print(path)
            return 0
        if a.cmd == 'add-topic':
            added, known = add_topics(a.library, cfg, a.topic, a.partition)
            for t in added:
                print('added: ' + t)
            for t in known:
                print('known: ' + t)
            return 0
        if a.cmd == 'entities':
            if not a.apply:
                with open(a.cards, encoding='utf-8') as fh:
                    cards = [json.loads(ln) for ln in fh if ln.strip()]
                print(json.dumps(entity_report(cards, read_spec(a.library, cfg)), ensure_ascii=False))
                return 0
            decisions = None
            if a.map:
                with open(a.map, encoding='utf-8') as fh:
                    decisions = json.load(fh)
            print(json.dumps(apply_entities(a.cards, a.library, cfg, decisions), ensure_ascii=False))
            return 0
        target = a.target or a.library
        groups = _load(getattr(a, 'groups', None), None)
        only = [x.strip().upper() for x in a.sources.split(',') if x.strip()] if getattr(a, 'sources', None) else None
        if a.cmd == 'conflicts':
            with open(a.cards, encoding='utf-8') as fh:
                cards = [json.loads(ln) for ln in fh if ln.strip()]
            print(json.dumps(conflicts(a.batches, cards, target, cfg, None, dict(a.replaces), groups, only), ensure_ascii=False))
            return 0
        if a.cmd == 'versions':
            print(json.dumps(version_candidates(a.batches, target, cfg, None, groups), ensure_ascii=False))
            return 0
        if a.cmd == 'pages':
            for p in pages_run(target, cfg, None if a.all else a.topic):
                print(p)
            log_step(a.work, PAGES_LOG, {'all': True} if a.all else {'topics': a.topic})
            return 0
        names = None
        if a.names:
            with open(a.names, encoding='utf-8') as fh:
                names = json.load(fh)
        cards = []
        if a.cards:
            with open(a.cards, encoding='utf-8') as fh:
                cards = [json.loads(ln) for ln in fh if ln.strip()]
        restore = None
        if a.restore:
            with open(a.restore, encoding='utf-8') as fh:
                restore = json.load(fh)
        got = file_run(a.batches, cards, target, cfg, names, dict(a.replaces), restore, groups, only)
        log_step(a.work, FILED_LOG, got)
        print(json.dumps(got, ensure_ascii=False))
        return 0
    except (kbconf.ConfigError, OSError, ValueError, sqlite3.Error) as e:
        log.error('%s', e)
        return 2


if __name__ == '__main__':
    sys.exit(main())
