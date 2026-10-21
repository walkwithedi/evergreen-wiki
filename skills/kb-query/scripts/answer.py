#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""answer.py - material for an answer from a library, and a check of the answer's quotes.

select: the status-card items, cards and source paragraphs a question's keywords point to; the
  assistant answers only from what it is given. Cards and paragraphs come from the library's index
  (kbindex.py search, brought up to date first): those holding every keyword first, ranked by BM25
  with a small weight for newer documents; when fewer than RELAX hold every keyword, those holding
  some of them follow, marked as holding only some keywords. A keyword that names an entity of the
  spec's Table E (its name or an alias) stands for all of that entity's names; one that names a topic
  brings that topic's cards. At most LIMIT cards and paragraphs together, cards listed first, each
  with its quote and source link; a paragraph a listed card quotes is left out, the others are marked
  as not on a card. Status-card items match when their text holds a keyword and say when they are
  marked for review. Chinese, Japanese and Korean keywords match wherever the text holds them; a
  keyword ending in a word matches at the start of a word. Case does not matter.

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

LIMIT = 15  # cards and paragraphs together
RELAX = 5  # fewer results holding every keyword than this: those holding some follow
QUOTE_LINE_RE = re.compile(r'^\s*>\s*(.*?)\s*\[\[([^\]#|]+)#\^(p\d+)(?:\|[^\]]*)?\]\]\s*$')

LABELS = {
    'en': {'status': '## Status card', 'cards': '## Cards', 'paragraphs': '## Source paragraphs (not on a card)',
           'uncarded': ' (source without cards yet)', 'partial': ' (only some keywords)',
           'review': '(marked for review: check it against the cards and sources)', 'earlier': ' (earlier version)',
           'nothing': 'Nothing in the library matches these keywords.'},
    'zh': {'status': '## 状态卡', 'cards': '## 卡片', 'paragraphs': '## 来源段落（不在卡片上）',
           'uncarded': '（该来源尚未抽卡）', 'partial': '（只含部分关键词）',
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


def select(library, cfg, keywords, limit=LIMIT):
    """{"status": [{item, review}], "cards": [...], "paragraphs": [{link, anchor, text, carded, partial}]}."""
    terms = [k for k in (' '.join(k.split()) for k in keywords) if k]
    ix = kbindex.open_index(library, cfg)
    try:
        got = ix.search(keywords=terms, entities=kbconf.entities(_spec(library, cfg)), limit=limit, relax=RELAX)
    finally:
        ix.close()
    cards, paragraphs = [], []
    for r in got['results']:
        if r['kind'] == 'card':
            card = {'conclusion': r['conclusion'], 'quote': r['text'], 'topic': r['topic'], 'date': r['card_date'],
                    'entities': r['entities'], 'link': r['link'], 'anchor': r['anchor'], 'earlier': r['earlier'],
                    'partial': r['partial']}
            if r['event_date']:
                card['event_date'] = r['event_date']
            cards.append(card)
        else:
            paragraphs.append({'link': r['link'], 'anchor': r['anchor'], 'text': r['text'], 'carded': r['carded'],
                               'partial': r['partial']})
    patterns = [_pattern(n) for g in got['keywords'] for n in g]
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
            w.append('- %s (%s; %s)%s%s' % (c['conclusion'], c['topic'], day, lb['earlier'] if c['earlier'] else '',
                                            lb['partial'] if c.get('partial') else ''))
            w.append('  > %s [[%s#^%s]]' % (c['quote'], c['link'], c['anchor']))
        w.append('')
    if got['paragraphs']:
        w += [lb['paragraphs'], '']
        for p in got['paragraphs']:
            w.append('> %s [[%s#^%s]]%s' % (' '.join(p['text'].split()), p['link'], p['anchor'],
                                            ('' if p.get('carded', True) else lb['uncarded']) +
                                            (lb['partial'] if p.get('partial') else '')))
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
