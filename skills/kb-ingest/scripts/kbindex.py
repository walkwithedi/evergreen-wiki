#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kbindex.py - the search index of a library: its sources, their paragraphs and the cards.

The index is <library>/_index/kb.sqlite (SQLite, in the Python standard library). It is made from the
library's files and kept current from them: the files stay the only record, and the index can be
deleted at any time. refresh() compares every file of the sources and cards folders with what the
index holds (size and modification time) and reads only the files that changed, were added or went
away, so a command calls it before it reads and gets a current index without a full rebuild.

What it holds:
  sources     one row per source file: its path below the sources folder ("folder/name.md"), name,
              folder, name key (ingest.name_key), content fingerprint, last-modified time (from the
              source's "Document last modified" line), characters, whether it has a cards file.
  paragraphs  the anchored paragraphs of every source (anchor pN and text).
  cards       every card of every cards file: the cards file, source link, anchor, quote, conclusion,
              topic (and its key), entities, date, event date, and the link of a card citing an
              earlier version.

Search uses SQLite's full-text index (FTS5) when this Python's SQLite has it: paragraphs, and each
card's conclusion and quote, are split into words (tokens()): Chinese, Japanese and Korean text into
overlapping pairs of characters, other text into words. A keyword matches as a phrase of its words,
so a keyword of two or more such characters matches wherever the text holds it, and a keyword
ending in a word matches at the start of a word. Results are ranked with BM25. Keywords that leave
a single CJK character, and SQLites without FTS5, use LIKE. An index made by an earlier version is
made again. A folder the index cannot be written to gets an index in memory for that run.

search() is the search of the client's search bar: a query of words and "quoted phrases" that must
all match, a word naming an entity of the spec's Table E standing for any of its names; paragraphs
and cards ranked together by BM25 with a small weight for newer documents.

fingerprint() is the content fingerprint of a source's text: the text without its notes (lines
starting with ">"), anchors and white space, compared as quote_check compares quotes. Two files with
the same fingerprint hold the same document.

Python 3 standard library only.

Usage:
  kbindex.py build LIBRARY            make the index anew
  kbindex.py refresh LIBRARY          bring it up to date; prints what changed
  kbindex.py stats LIBRARY            counts, as JSON
  kbindex.py search LIBRARY KEYWORD [KEYWORD ...] [--limit 20]   paragraphs holding any keyword
  kbindex.py query LIBRARY "QUERY" [--limit 30]                  search(), as JSON
"""
import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402
import quote_check  # noqa: E402

log = logging.getLogger('kbindex')

INDEX_DIR = '_index'
INDEX_FILE = 'kb.sqlite'
INDEX_VERSION = 2
USE_FULL_TEXT = os.environ.get('KBINDEX_FULL_TEXT', '1') != '0'   # 0: LIKE only, as on an SQLite without FTS5
ANCHORED_RE = re.compile(r'^(.*?)\s*\^(p\d+)\s*$', re.S)
ANCHOR_END_RE = re.compile(r'\s*\^(?:s\d{2,}-)?p\d+\s*$', re.M)
CJK = '\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af\U00020000-\U0002ffff'
RUN_RE = re.compile('([%s]+)|((?:(?![%s])[^\\W_])+)' % (CJK, CJK))
QUERY_RE = re.compile(r'"([^"]+)"|\u201c([^\u201d]+)\u201d|(\S+)')
FRESH_DAYS = 1825     # a document this many days older than the newest result gets no freshness weight
FRESH_WEIGHT = 0.2    # the newest result's score is raised by this share
CARD_WEIGHT = 0.1     # added to a card's score, so that a card comes before its own paragraph's equals
MODIFIED_RE = re.compile(r'^>\s*(?:Document last modified|文档最后修改)\s*[:：]\s*(\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?)', re.M)

TABLES = '''
CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE files (path TEXT PRIMARY KEY, sig TEXT);
CREATE TABLE sources (path TEXT PRIMARY KEY, name TEXT, folder TEXT, key TEXT, fp TEXT, modified TEXT,
                      chars INTEGER, carded INTEGER DEFAULT 0);
CREATE INDEX sources_name ON sources (name);
CREATE INDEX sources_fp ON sources (fp);
CREATE TABLE paragraphs (id INTEGER PRIMARY KEY, source TEXT, anchor TEXT, text TEXT);
CREATE INDEX paragraphs_source ON paragraphs (source);
CREATE TABLE cards (id INTEGER PRIMARY KEY, cards TEXT, source TEXT, anchor TEXT, quote TEXT, conclusion TEXT,
                    topic TEXT, tkey TEXT, entities TEXT, date TEXT, event_date TEXT, link TEXT);
CREATE INDEX cards_cards ON cards (cards);
CREATE INDEX cards_tkey ON cards (tkey);
'''


def fingerprint(text):
    """Content fingerprint of a source's text (see the module notes)."""
    body = '\n'.join(ln for ln in text.replace('\r\n', '\n').split('\n') if not ln.lstrip().startswith('>'))
    body = ANCHOR_END_RE.sub('', body)
    return hashlib.sha256(quote_check.norm(body).encode('utf-8')).hexdigest()


def tokens(text):
    """The words of a text for the full-text index: runs of CJK characters as overlapping pairs (a run of
    one character as itself), other letters and digits as words; case folded."""
    out = []
    for m in RUN_RE.finditer(text.casefold()):
        run = m.group(1)
        if run:
            out += [run] if len(run) == 1 else [run[i:i + 2] for i in range(len(run) - 1)]
        else:
            out.append(m.group(2))
    return out


def body(text):
    """A text as the full-text index holds it."""
    return ' '.join(tokens(text))


def _cjk(tok):
    return RUN_RE.match(tok).group(1) is not None


def phrase(term):
    """The full-text query of one keyword: its words as a phrase, the last one as a prefix when it is not
    CJK; '' when the index cannot answer it (no words, or a single CJK character among them)."""
    toks = tokens(term)
    if not toks or any(len(t) == 1 and _cjk(t) for t in toks):
        return ''
    return '"%s"%s' % (' '.join(toks), '' if _cjk(toks[-1]) else '*')


def parse_query(query):
    """The keywords of a search-bar query: words, and phrases in straight or curly double quotes."""
    out = []
    for m in QUERY_RE.finditer(query or ''):
        t = ' '.join((m.group(1) or m.group(2) or m.group(3) or '').split())
        if t and t not in out:
            out.append(t)
    return out


def expand(keywords, entities=()):
    """[[keyword, other names...]]: a keyword naming an entity (its name or an alias, entities as
    kbconf.entities gives them) stands for all of that entity's names."""
    groups = []
    for k in keywords:
        g = [k]
        for row in entities:
            names = [row['name']] + list(row['aliases'])
            if any(kbconf.topic_key(n) == kbconf.topic_key(k) for n in names):
                g += [n for n in names if kbconf.topic_key(n) not in map(kbconf.topic_key, g)]
        groups.append(g)
    return groups


def _day(text):
    m = re.match(r'\d{4}-\d{2}-\d{2}', text or '')
    return m.group(0) if m else ''


def _days(a, b):
    """Days from a to b ('YYYY-MM-DD'), 0 when either is missing."""
    if not (a and b):
        return 0
    return (time.mktime(time.strptime(b, '%Y-%m-%d')) - time.mktime(time.strptime(a, '%Y-%m-%d'))) / 86400


def anchored(text):
    """{pN: paragraph text} of a source file (anchors at the end, a table's on the line below)."""
    out, prev = {}, ''
    for block in re.split(r'\n\s*\n', text):
        block = block.strip()
        m = ANCHORED_RE.match(block)
        if m:
            out[m.group(2)] = m.group(1).strip() or prev
        prev = block
    return out


NAME_DATE_RE = re.compile(r'\d{4}[-_./年]?\d{1,2}[-_./月]?\d{1,2}日?')
NAME_MARK_RE = re.compile(r'(?<![a-z])(?:v\d+(?:\.\d+)*|rev\d*|ver\d*|version\d*|final|draft|copy)(?![a-z])'
                          r'|副本|终稿|定稿|修订版|最终版|草稿|[(（]\d+[)）]')


def name_key(fname):
    """A file name without folder, extension, dates, version marks, punctuation and case, for comparing names."""
    stem = os.path.splitext(os.path.basename(fname))[0].casefold()
    stem = NAME_MARK_RE.sub(' ', NAME_DATE_RE.sub(' ', stem))
    return re.sub(r'[\W_]+', '', stem)


def _sig(st):
    return '%d:%d' % (st.st_mtime_ns, st.st_size)


def _walk(folder):
    """{path below folder, "/" separated: stat} of the .md files under it."""
    out = {}
    for here, dirs, names in os.walk(folder):
        dirs.sort()
        for n in names:
            if n.endswith('.md'):
                p = os.path.join(here, n)
                try:
                    out[os.path.relpath(p, folder).replace(os.sep, '/')] = os.stat(p)
                except OSError:
                    continue
    return out


class Index:
    """An open index of one library (or a folder laid out like one)."""

    def __init__(self, root, cfg, memory=False):
        self.root, self.cfg = root, cfg
        self.names = cfg['names']
        self.path = ':memory:' if memory else os.path.join(root, INDEX_DIR, INDEX_FILE)
        self.db = self._open()
        self.fts = self._has_fts()

    def _open(self):
        if self.path != ':memory:':
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                db = sqlite3.connect(self.path, timeout=60)
                try:
                    db.execute('PRAGMA journal_mode=WAL')
                    if self._current(db):
                        return db
                except sqlite3.DatabaseError as e:
                    log.warning('index %s is damaged (%s); making it again', self.path, e)
                db.close()
                for suffix in ('', '-wal', '-shm'):
                    if os.path.exists(self.path + suffix):
                        os.remove(self.path + suffix)
                db = sqlite3.connect(self.path, timeout=60)
                db.execute('PRAGMA journal_mode=WAL')
                self._create(db)
                return db
            except (OSError, sqlite3.Error) as e:
                log.warning('index %s cannot be used (%s); keeping one in memory for this run', self.path, e)
                self.path = ':memory:'
        db = sqlite3.connect(':memory:')
        self._create(db)
        return db

    @staticmethod
    def _current(db):
        """True when the index was made by this version and this SQLite can read all of it (an index with a
        full-text table, opened by an SQLite without it, is made anew)."""
        try:
            row = db.execute("SELECT v FROM meta WHERE k = 'version'").fetchone()
            if db.execute("SELECT 1 FROM meta WHERE k = 'fts'").fetchone():
                db.execute('SELECT rowid FROM paragraphs_fts LIMIT 1').fetchall()
                db.execute('SELECT rowid FROM cards_fts LIMIT 1').fetchall()
        except sqlite3.Error:
            return False
        return bool(row) and row[0] == str(INDEX_VERSION)

    @staticmethod
    def _create(db):
        db.executescript(TABLES)
        try:
            if not USE_FULL_TEXT:
                raise sqlite3.OperationalError('switched off (KBINDEX_FULL_TEXT=0)')
            db.execute("CREATE VIRTUAL TABLE paragraphs_fts USING fts5(body, tokenize='unicode61')")
            db.execute("CREATE VIRTUAL TABLE cards_fts USING fts5(body, tokenize='unicode61')")
            db.execute("INSERT INTO meta VALUES ('fts', 'pairs')")
        except sqlite3.Error as e:
            for t in ('paragraphs_fts', 'cards_fts'):
                db.execute('DROP TABLE IF EXISTS %s' % t)
            log.info('no full-text index (%s); the index is searched with LIKE', e)
        db.execute("INSERT INTO meta VALUES ('version', ?)", (str(INDEX_VERSION),))
        db.commit()

    def _has_fts(self):
        return bool(self.db.execute("SELECT 1 FROM meta WHERE k = 'fts'").fetchone())

    def close(self):
        self.db.close()

    # ------------------------------------------------------------ keeping it current

    def refresh(self):
        """Read the files that changed since the index last saw them; returns {added, changed, removed}."""
        t0 = time.time()
        n = self.names
        seen = {}
        for top in (n['sources_dir'], n['cards_dir']):
            for rel, st in _walk(os.path.join(self.root, top)).items():
                seen['%s/%s' % (top, rel)] = _sig(st)
        held = dict(self.db.execute('SELECT path, sig FROM files'))
        added = [p for p in seen if p not in held]
        changed = [p for p in seen if p in held and held[p] != seen[p]]
        removed = [p for p in held if p not in seen]
        if not (added or changed or removed):
            return {'added': 0, 'changed': 0, 'removed': 0}
        with self.db:
            for p in removed + changed:
                self._drop(p)
            for p in sorted(added + changed):
                self._read(p)
                self.db.execute('INSERT OR REPLACE INTO files VALUES (?, ?)', (p, seen[p]))
            self.db.execute('UPDATE sources SET carded = (SELECT COUNT(*) > 0 FROM files WHERE files.path = ? || '
                            "'/' || sources.path)", (n['cards_dir'],))
        log.info('index of %s: %d added, %d changed, %d removed in %.1f s', self.root, len(added), len(changed),
                 len(removed), time.time() - t0)
        return {'added': len(added), 'changed': len(changed), 'removed': len(removed)}

    def _split(self, path):
        top, _, rel = path.partition('/')
        return top, rel

    def _drop(self, path):
        top, rel = self._split(path)
        self.db.execute('DELETE FROM files WHERE path = ?', (path,))
        if top == self.names['sources_dir']:
            if self.fts:
                self.db.execute('DELETE FROM paragraphs_fts WHERE rowid IN (SELECT id FROM paragraphs WHERE source = ?)',
                                (rel,))
            self.db.execute('DELETE FROM paragraphs WHERE source = ?', (rel,))
            self.db.execute('DELETE FROM sources WHERE path = ?', (rel,))
        else:
            if self.fts:
                self.db.execute('DELETE FROM cards_fts WHERE rowid IN (SELECT id FROM cards WHERE cards = ?)', (rel,))
            self.db.execute('DELETE FROM cards WHERE cards = ?', (rel,))

    def _read(self, path):
        top, rel = self._split(path)
        try:
            with open(os.path.join(self.root, *path.split('/')), encoding='utf-8') as f:
                text = f.read().replace('\r\n', '\n')
        except (OSError, UnicodeDecodeError) as e:
            log.warning('cannot read %s: %s', path, e)
            return
        if top == self.names['sources_dir']:
            name = rel.rsplit('/', 1)[-1]
            folder = rel.rsplit('/', 1)[0] if '/' in rel else ''
            m = MODIFIED_RE.search(text)
            paras = anchored(text)
            self.db.execute('INSERT OR REPLACE INTO sources (path, name, folder, key, fp, modified, chars) '
                            'VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (rel, name, folder, name_key(name), fingerprint(text), m.group(1) if m else '', len(text)))
            for anchor, ptext in paras.items():
                cur = self.db.execute('INSERT INTO paragraphs (source, anchor, text) VALUES (?, ?, ?)', (rel, anchor, ptext))
                if self.fts:
                    self.db.execute('INSERT INTO paragraphs_fts (rowid, body) VALUES (?, ?)', (cur.lastrowid, body(ptext)))
            return
        got = quote_check.read_cards(text)
        for c in got['cards']:
            cur = self.db.execute('INSERT INTO cards (cards, source, anchor, quote, conclusion, topic, tkey, entities, date, '
                            'event_date, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                            (rel, got['source'], c['anchor'], c['quote'], c['conclusion'], c['topic'],
                             kbconf.topic_key(c['topic']), json.dumps(c['entities'], ensure_ascii=False),
                             c['date'], c.get('event_date', ''), c.get('link', '')))
            if self.fts:
                self.db.execute('INSERT INTO cards_fts (rowid, body) VALUES (?, ?)',
                                (cur.lastrowid, body(c['conclusion'] + '\n' + c['quote'])))

    # ------------------------------------------------------------ lookups

    def source_paths(self):
        """{name: [paths]} of the library's sources."""
        out = {}
        for path, name in self.db.execute('SELECT path, name FROM sources ORDER BY path'):
            out.setdefault(name, []).append(path)
        return out

    def by_fingerprint(self, fps):
        """{fingerprint: path} for the fingerprints that are in the library."""
        out = {}
        fps = list(fps)
        for i in range(0, len(fps), 500):
            chunk = fps[i:i + 500]
            q = 'SELECT fp, path FROM sources WHERE fp IN (%s) ORDER BY path' % ','.join('?' * len(chunk))
            for fp, path in self.db.execute(q, chunk):
                out.setdefault(fp, path)
        return out

    def keys(self):
        """[(path, name key)] of every source."""
        return list(self.db.execute('SELECT path, key FROM sources'))

    def cards(self, tkeys=None):
        """[(cards file, source link, card)] of the topics named by key (all cards when None)."""
        q = 'SELECT cards, source, anchor, quote, conclusion, topic, entities, date, event_date, link FROM cards'
        rows = self.db.execute(q) if tkeys is None else (
            r for k in dict.fromkeys(tkeys) for r in self.db.execute(q + ' WHERE tkey = ?', (k,)))
        return [_card_row(r) for r in rows]

    def topics(self):
        """{topic key: (topic as first written, cards)} over every card."""
        out = {}
        for tkey, topic, n in self.db.execute('SELECT tkey, MIN(topic), COUNT(*) FROM cards GROUP BY tkey'):
            out[tkey] = (topic, n)
        return out

    def find_cards(self, terms, entity_names=(), topic_keys=(), cap=5000):
        """Cards whose conclusion or quote holds a term, or whose entities or topic are named; at most cap."""
        where, args, phrases = [], [], []
        for t in terms:
            ph = phrase(t) if self.fts else ''
            if ph:
                phrases.append(ph)
                continue
            where.append('(conclusion LIKE ? ESCAPE \'\\\' OR quote LIKE ? ESCAPE \'\\\')')
            args += [_like(t)] * 2
        if phrases:
            where.append('id IN (SELECT rowid FROM cards_fts WHERE cards_fts MATCH ?)')
            args.append(' OR '.join(phrases))
        for e in entity_names:
            where.append('entities LIKE ? ESCAPE \'\\\'')
            args.append(_like(json.dumps(e, ensure_ascii=False)))
        for k in topic_keys:
            where.append('tkey = ?')
            args.append(k)
        if not where:
            return []
        q = ('SELECT cards, source, anchor, quote, conclusion, topic, entities, date, event_date, link FROM cards '
             'WHERE %s LIMIT %d' % (' OR '.join(where), cap))
        return [_card_row(r) for r in self.db.execute(q, args)]

    def find_paragraphs(self, terms, limit=20, uncarded_first=False):
        """[{source, anchor, text}] of paragraphs holding any of the terms; with uncarded_first, paragraphs
        of sources without a cards file come first."""
        terms = [t for t in (' '.join(x.split()) for x in terms) if t]
        if not terms:
            return []
        first = 's.carded, ' if uncarded_first else ''
        phrases = [phrase(t) for t in terms] if self.fts else []
        if phrases and all(phrases):
            q = ('SELECT p.source, p.anchor, p.text FROM paragraphs_fts JOIN paragraphs p ON p.id = paragraphs_fts.rowid '
                 'JOIN sources s ON s.path = p.source WHERE paragraphs_fts MATCH ? '
                 'ORDER BY %sbm25(paragraphs_fts), p.source, p.id LIMIT ?' % first)
            rows = self.db.execute(q, (' OR '.join(phrases), limit))
        else:
            where = ' OR '.join(["p.text LIKE ? ESCAPE '\\'"] * len(terms))
            q = ('SELECT p.source, p.anchor, p.text FROM paragraphs p JOIN sources s ON s.path = p.source '
                 'WHERE %s ORDER BY %sp.source, p.id LIMIT ?' % (where, first))
            rows = self.db.execute(q, [_like(t) for t in terms] + [limit])
        return [{'source': s, 'anchor': a, 'text': t} for s, a, t in rows]

    def _matches(self, kind, groups, cap):
        """[(row id, relevance)] of the paragraphs or cards (kind) matching every group of keywords; the
        groups the full-text index can answer are matched there and give BM25, the others use LIKE."""
        table, text = ('paragraphs', 'x.text') if kind == 'paragraphs' else ('cards', "x.conclusion || ' ' || x.quote")
        fts, where, args = [], [], []
        for g in groups:
            phrases = [phrase(t) for t in g] if self.fts else []
            if phrases and all(phrases):
                fts.append('(%s)' % ' OR '.join(phrases))
            else:
                where.append('(%s)' % ' OR '.join(["%s LIKE ? ESCAPE '\\'" % text] * len(g)))
                args += [_like(t) for t in g]
        if fts:
            q = ('SELECT x.id, -bm25({t}_fts) FROM {t}_fts JOIN {t} x ON x.id = {t}_fts.rowid WHERE {t}_fts MATCH ?{w} '
                 'ORDER BY bm25({t}_fts) LIMIT ?').format(t=table, w=''.join(' AND ' + w for w in where))
            return list(self.db.execute(q, [' AND '.join(fts)] + args + [cap]))
        q = 'SELECT x.id, 1.0 FROM %s x WHERE %s LIMIT ?' % (table, ' AND '.join(where))
        return list(self.db.execute(q, args + [cap]))

    def search(self, query, entities=(), limit=30):
        """{"keywords": [[keyword, other names...]], "results": [...]} for a search-bar query: paragraphs and
        cards holding every keyword (a group: any of its names), best first. Relevance is BM25 (1 for
        all when only LIKE could answer), divided by the best of its kind; a result gains up to
        FRESH_WEIGHT of it for a newer document (none for one FRESH_DAYS older than the newest result),
        and a card CARD_WEIGHT. A paragraph a listed card quotes is left out. Each result:
        {kind: "card" or "paragraph", source (path below the sources folder), link, anchor, text (the
        paragraph, or the card's quote), date, carded; a card also conclusion and topic, score}."""
        groups = expand(parse_query(query), entities)
        if not groups:
            return {'keywords': [], 'results': []}
        sdir = self.names['sources_dir']
        cap = max(limit * 4, 100)
        found = []
        for kind in ('cards', 'paragraphs'):
            hits = self._matches(kind, groups, cap)
            best = max([r for _, r in hits] or [1]) or 1
            rel = {i: r / best for i, r in hits}
            if not rel:
                continue
            ids = ','.join(str(i) for i in rel)
            if kind == 'cards':
                q = ('SELECT id, cards, source, anchor, quote, conclusion, topic, entities, date, event_date, link '
                     'FROM cards WHERE id IN (%s)' % ids)
                for r in self.db.execute(q):
                    _, src, c = _card_row(r[1:])
                    link = c.get('link') or src
                    found.append({'kind': 'card', 'source': link.split('/', 1)[-1] + '.md', 'link': link,
                                  'anchor': c['anchor'], 'text': c['quote'], 'conclusion': c['conclusion'],
                                  'topic': c['topic'], 'date': _day(c['date']), 'carded': True, 'rel': rel[r[0]]})
            else:
                q = ('SELECT p.id, p.source, p.anchor, p.text, s.modified, s.carded FROM paragraphs p '
                     'JOIN sources s ON s.path = p.source WHERE p.id IN (%s)' % ids)
                for pid, src, anchor, text, modified, carded in self.db.execute(q):
                    found.append({'kind': 'paragraph', 'source': src, 'link': '%s/%s' % (sdir, src[:-3]),
                                  'anchor': anchor, 'text': text, 'date': _day(modified), 'carded': bool(carded),
                                  'rel': rel[pid]})
        quoted = {(f['link'], f['anchor']) for f in found if f['kind'] == 'card'}
        found = [f for f in found if f['kind'] == 'card' or (f['link'], f['anchor']) not in quoted]
        newest = max([f['date'] for f in found if f['date']] or [''])
        for f in found:
            fresh = max(0.0, 1 - _days(f['date'], newest) / FRESH_DAYS) if f['date'] else 0.0
            f['score'] = round(f.pop('rel') * (1 + FRESH_WEIGHT * fresh) + (CARD_WEIGHT if f['kind'] == 'card' else 0), 4)
        found.sort(key=lambda f: (-f['score'], -int(f['date'].replace('-', '') or 0), f['source'], f['anchor']))
        return {'keywords': groups, 'results': found[:limit]}

    def context(self, source, anchor, around=2):
        """[{anchor, text, hit}] of the paragraph source#anchor and up to around paragraphs before and after it,
        in the source's order; [] when there is no such paragraph."""
        rows = list(self.db.execute('SELECT anchor, text FROM paragraphs WHERE source = ? ORDER BY id', (source,)))
        at = next((i for i, (a, _) in enumerate(rows) if a == anchor), None)
        if at is None:
            return []
        return [{'anchor': a, 'text': t, 'hit': a == anchor} for a, t in rows[max(0, at - around):at + around + 1]]

    def uncarded(self):
        """[(path, modified)] of the sources without a cards file, newest first."""
        return list(self.db.execute('SELECT path, modified FROM sources WHERE carded = 0 ORDER BY modified DESC, path'))

    def stats(self):
        one = lambda q: self.db.execute(q).fetchone()[0]  # noqa: E731
        return {'sources': one('SELECT COUNT(*) FROM sources'), 'carded': one('SELECT COUNT(*) FROM sources WHERE carded'),
                'paragraphs': one('SELECT COUNT(*) FROM paragraphs'), 'cards': one('SELECT COUNT(*) FROM cards'),
                'topics': one('SELECT COUNT(DISTINCT tkey) FROM cards'), 'full_text': self.fts,
                'file': self.path}


def _like(term):
    return '%' + term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'


def _card_row(r):
    cards, source, anchor, quote, conclusion, topic, entities, date, event_date, link = r
    c = {'anchor': anchor, 'quote': quote, 'conclusion': conclusion, 'topic': topic,
         'entities': json.loads(entities or '[]'), 'date': date or ''}
    if event_date:
        c['event_date'] = event_date
    if link:
        c['link'] = link
    return cards, source, c


def library_entities(root, cfg):
    """The entities of the library's spec (Table E), as kbconf.entities gives them; [] without a spec."""
    try:
        with open(os.path.join(root, cfg['names']['spec']), encoding='utf-8') as f:
            return kbconf.entities(f.read())
    except OSError:
        return []


def open_index(root, cfg, refresh=True):
    """The library's index, brought up to date unless refresh is False."""
    ix = Index(root, cfg)
    if refresh:
        ix.refresh()
    return ix


def main(argv=None):
    ap = argparse.ArgumentParser(description='The search index of a library.')
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for c in ('build', 'refresh', 'stats'):
        sub.add_parser(c).add_argument('library')
    s = sub.add_parser('search')
    s.add_argument('library')
    s.add_argument('keywords', nargs='+')
    s.add_argument('--limit', type=int, default=20)
    s = sub.add_parser('query')
    s.add_argument('library')
    s.add_argument('query')
    s.add_argument('--limit', type=int, default=30)
    a = ap.parse_args(argv)
    kbconf.setup_logging(a.log_level)
    try:
        cfg = kbconf.load_library(a.library)
        if a.cmd == 'build':
            path = os.path.join(a.library, INDEX_DIR, INDEX_FILE)
            for suffix in ('', '-wal', '-shm'):
                if os.path.exists(path + suffix):
                    os.remove(path + suffix)
        ix = Index(a.library, cfg)
        if a.cmd == 'search':
            ix.refresh()
            for p in ix.find_paragraphs(a.keywords, a.limit):
                print('%s#^%s\t%s' % (p['source'], p['anchor'], ' '.join(p['text'].split())))
        elif a.cmd == 'query':
            ix.refresh()
            print(json.dumps(ix.search(a.query, library_entities(a.library, cfg), a.limit), ensure_ascii=False))
        elif a.cmd == 'stats':
            ix.refresh()
            print(json.dumps(ix.stats(), ensure_ascii=False))
        else:
            print(json.dumps(ix.refresh(), ensure_ascii=False))
        ix.close()
        return 0
    except (kbconf.ConfigError, OSError, sqlite3.Error) as e:
        log.error('%s', e)
        return 2


if __name__ == '__main__':
    sys.exit(main())
