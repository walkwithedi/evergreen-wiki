#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer.py - material for an answer from a library, and a check of the answer's quotes.

select: the cards and status-card items a question's keywords point to; the assistant answers only
  from what it is given. A keyword that names an entity of the spec's
  Table E (its name or an alias) stands for all of that entity's names. A card scores one point
  for each keyword in its conclusion or quote, two for each of its entities a keyword names and
  two when a keyword names its topic; the best LIMIT cards are listed, newest first among equals,
  with their quotes and source links. Status-card items score by their text and say when they are
  marked for review. Paragraphs holding a keyword are listed too (at most PARAGRAPH_LIMIT), marked as
  not on a card: those of sources without cards yet, and, when no card matches, those of any source.
  Cards and paragraphs come from the library's index (kbindex.py), brought up to date first.
  ASCII keywords match at the start of a word; others anywhere. Case does not matter.

check: every quote line of an answer, "> <sentence> [[<source>#^pN]]", must hold a sentence of
  that source's paragraph pN (compared as quote_check does: white space, full- and half-width
  punctuation and Markdown emphasis are ignored). Prints JSON with the quotes checked and the
  ones that failed; exit 3 when any failed.

Python 3 standard library only. Read-only.

Exit codes: 0 done; 3 check found quotes that failed; 2 bad arguments or unreadable input.
Usage:
  answer.py select LIBRARY KEYWORD [KEYWORD ...] [--limit 12] [--json]
  answer.py check LIBRARY ANSWER.md
"""
import argparse
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402
import kbindex  # noqa: E402
import quote_check  # noqa: E402
from ingest import ITEM_RE, MARK_RE, anchored  # noqa: E402

log = logging.getLogger('answer')

LIMIT = 12
PARAGRAPH_LIMIT = 5
PARAGRAPH_SCAN = 200  # paragraphs the index hands over for the keyword check
QUOTE_LINE_RE = re.compile(r'^\s*>\s*(.*?)\s*\[\[([^\]#|]+)#\^(p\d+)(?:\|[^\]]*)?\]\]\s*$')

LABELS = {
    'en': {'status': '## Status card', 'cards': '## Cards', 'paragraphs': '## Source paragraphs (not on a card)',
           'uncarded': ' (source without cards yet)',
           'review': '(marked for review: check it against the cards and sources)', 'earlier': ' (earlier version)',
           'nothing': 'Nothing in the library matches these keywords.'},
    'zh': {'status': '## 状态卡', 'cards': '## 卡片', 'paragraphs': '## 来源段落（不在卡片上）',
           'uncarded': '（该来源尚未抽卡）',
           'review': '（待复核：须对照卡片和来源核实）', 'earlier': '（旧版本）',
           'nothing': '知识库里没有与这些关键词匹配的内容。'},
}


def _pattern(term):
    t = re.escape(' '.join(term.split()))
    return re.compile(r'(?<![a-z0-9])' + t if term.isascii() else t, re.I)


def _hits(patterns, text):
    return sum(1 for p in patterns if p.search(text))


def _spec(library, cfg):
    path = os.path.join(library, cfg['names']['spec'])
    if not os.path.isfile(path):
        return ''
    with open(path, encoding='utf-8') as f:
        return f.read()


def _expand(keywords, spec):
    """(keyword terms, entity keys named, topic keys named) for the question's keywords."""
    terms = [k for k in (' '.join(k.split()) for k in keywords) if k]
    rows = kbconf.entities(spec)
    named = set()
    for row in rows:
        names = [row['name']] + row['aliases']
        if any(kbconf.topic_key(n) == kbconf.topic_key(k) for n in names for k in terms):
            named.update(kbconf.topic_key(n) for n in names)
            terms += [n for n in names if kbconf.topic_key(n) not in map(kbconf.topic_key, terms)]
    return terms, named


def select(library, cfg, keywords, limit=LIMIT):
    """{"status": [{item, review}], "cards": [...], "paragraphs": [{link, anchor, text, carded}]}."""
    spec = _spec(library, cfg)
    terms, named = _expand(keywords, spec)
    patterns = [_pattern(t) for t in terms]
    topic_keys = {kbconf.topic_key(t) for t in terms}
    sdir = cfg['names']['sources_dir']
    ix = kbindex.open_index(library, cfg)
    try:
        entity_names = [n for row in kbconf.entities(spec) for n in [row['name']] + row['aliases']
                        if kbconf.topic_key(n) in named]
        scored = []
        for _, src, c in ix.find_cards(terms, entity_names, topic_keys):
            score = _hits(patterns, c['conclusion'] + '\n' + c['quote'])
            score += 2 * sum(1 for e in c['entities'] if kbconf.topic_key(e) in named)
            score += 2 if kbconf.topic_key(c['topic']) in topic_keys else 0
            if score:
                day = c.get('event_date') or c['date'][:10]
                scored.append((score, day, dict(c, link=c.get('link') or src, earlier=bool(c.get('link')))))
        scored.sort(key=lambda s: (s[0], s[1], s[2]['date']), reverse=True)  # newer source first on the same day
        cards = [s[2] for s in scored[:limit]]
        # paragraphs: of sources without cards yet, and of every source when no card matched
        paragraphs = []
        carded = {p for p, in ix.db.execute('SELECT path FROM sources WHERE carded')}
        for p in ix.find_paragraphs(terms, PARAGRAPH_SCAN, uncarded_first=True):
            if len(paragraphs) >= PARAGRAPH_LIMIT or (cards and p['source'] in carded):
                break
            if _hits(patterns, p['text']):
                paragraphs.append({'link': '%s/%s' % (sdir, p['source'][:-3]), 'anchor': p['anchor'],
                                   'text': p['text'], 'carded': p['source'] in carded})
    finally:
        ix.close()

    status = []
    path = os.path.join(library, cfg['names']['status_card'])
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            for line in f.read().split('\n'):
                if ITEM_RE.match(line) and _hits(patterns, MARK_RE.sub('', line)):
                    status.append({'item': MARK_RE.sub('', line).strip(), 'review': '⏳' in line})
    return {'status': status, 'cards': cards, 'paragraphs': paragraphs}


def render(got, lang):
    lb = LABELS[lang]
    if not (got['status'] or got['cards'] or got['paragraphs']):
        return lb['nothing'] + '\n'
    w = []
    if got['status']:
        w += [lb['status'], '']
        w += [s['item'] + (' ' + lb['review'] if s['review'] else '') for s in got['status']]
        w.append('')
    if got['cards']:
        w += [lb['cards'], '']
        for c in got['cards']:
            day = c['date'] + (' / %s' % c['event_date'] if c.get('event_date') else '')
            w.append('- %s (%s; %s)%s' % (c['conclusion'], c['topic'], day, lb['earlier'] if c['earlier'] else ''))
            w.append('  > %s [[%s#^%s]]' % (c['quote'], c['link'], c['anchor']))
        w.append('')
    if got['paragraphs']:
        w += [lb['paragraphs'], '']
        for p in got['paragraphs']:
            w.append('> %s [[%s#^%s]]%s' % (' '.join(p['text'].split()), p['link'], p['anchor'],
                                            '' if p.get('carded', True) else lb['uncarded']))
        w.append('')
    return '\n'.join(w)


def check(library, text):
    """{"checked": n, "failed": [{quote, link, reason}]} for the quote lines of an answer."""
    checked, failed, cache = 0, [], {}
    for line in text.replace('\r\n', '\n').split('\n'):
        m = QUOTE_LINE_RE.match(line)
        if not m:
            continue
        checked += 1
        quote, link, anchor = m.group(1), m.group(2).strip(), m.group(3)
        path = os.path.join(library, *link.split('/')) + '.md'
        if link not in cache:
            if os.path.isfile(path):
                with open(path, encoding='utf-8') as f:
                    cache[link] = anchored(f.read())
            else:
                cache[link] = None
        paras = cache[link]
        if paras is None:
            failed.append({'quote': quote, 'link': '%s#^%s' % (link, anchor), 'reason': 'no such source file'})
        elif quote_check.norm(quote) not in quote_check.norm(paras.get(anchor, '')) or not quote.strip():
            failed.append({'quote': quote, 'link': '%s#^%s' % (link, anchor), 'reason': 'quote not in the linked paragraph'})
    return {'checked': checked, 'failed': failed}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Material for an answer from a library, and a check of its quotes.')
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('select', help='cards and status-card items for the keywords')
    s.add_argument('library')
    s.add_argument('keywords', nargs='+')
    s.add_argument('--limit', type=int, default=LIMIT, help='cards listed at most (default %d)' % LIMIT)
    s.add_argument('--json', action='store_true', help='print JSON instead of text')
    c = sub.add_parser('check', help="check an answer's quote lines against the sources")
    c.add_argument('library')
    c.add_argument('answer', help='the answer as written')
    a = ap.parse_args(argv)
    kbconf.setup_logging(a.log_level)
    try:
        cfg = kbconf.load_library(a.library)
        if a.cmd == 'select':
            got = select(a.library, cfg, a.keywords, a.limit)
            lang = 'zh' if str(cfg.get('language', 'en')).lower().startswith('zh') else 'en'
            print(json.dumps(got, ensure_ascii=False) if a.json else render(got, lang))
            return 0
        with open(a.answer, encoding='utf-8') as f:
            res = check(a.library, f.read())
        print(json.dumps(res, ensure_ascii=False))
        return 3 if res['failed'] else 0
    except (kbconf.ConfigError, OSError, ValueError) as e:
        log.error('%s', e)
        return 2


if __name__ == '__main__':
    sys.exit(main())
