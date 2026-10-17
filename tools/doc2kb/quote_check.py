#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quote_check.py - check cards against their batch file and write the cards that pass.

A card is one claim taken from a source, written by the assistant as one JSON object per line:

    {"source": "S01", "anchor": "s01-p2", "quote": "Riverside Clinic will host the pilot.",
     "conclusion": "Riverside Clinic hosts the pilot.", "topic": "Pilot",
     "entities": ["Riverside Clinic"], "event_date": "2026-03-03"}

anchor may also be written ^s01-p2 or p2; event_date (YYYY-MM-DD) is optional, and so is
entity_types, the assistant's suggested type for entities not yet in the spec's Table E
({"Riverside Clinic": "organisation"}; one of ENTITY_TYPES). The card's date is not the
assistant's to give: it is the source's last-modified time from the batch file.

check: every card is checked against the batch files of its run (kb_batch.py format):
  - the fields are there and the source number exists;
  - the quote is QUOTE_MIN to QUOTE_MAX characters and occurs in the paragraph (list item,
    table) of its anchor. Comparison ignores white space, the difference between full- and
    half-width punctuation and Markdown emphasis; any other difference fails;
  - a quote found in exactly one other paragraph of the same source passes with its anchor
    corrected; one found in several paragraphs, across paragraphs or nowhere fails;
  - with --topics, a topic not in the list passes and is listed as a new topic to confirm;
    topics compare without regard to case and spacing, and a known one takes the list's spelling;
  - a card with the same source, quote and conclusion as an earlier one is dropped.
  Cards that pass go to ACCEPTED (JSON lines, anchors corrected, date added, entity_types kept
  for the card's own entities and known types); the report
  (JSON) lists rejected cards with the reason, corrected anchors and new topics.

write: the accepted cards go to one Markdown file per source in the cards folder, named like
the source file (kb_batch.py split names, --names the same map), rewritten as a whole.

Python 3 standard library only.

Exit codes: 0 every card passed (check) or files written (write); 3 some cards rejected;
2 bad arguments or unreadable input.
Usage:
  quote_check.py check CARDS.jsonl BATCH.md [BATCH.md ...] --accepted OUT.jsonl --report OUT.json
                 [--topics TOPICS.txt] [--quote-min 6] [--quote-max 300]
  quote_check.py write ACCEPTED.jsonl BATCH.md [BATCH.md ...] -o CARDS_DIR [--names NAMES.json]
                 [--lang en|zh]
"""
import argparse
import json
import logging
import os
import re
import sys
import unicodedata

import kb_batch

log = logging.getLogger('quote_check')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'

QUOTE_MIN = 6
QUOTE_MAX = 300
REQUIRED = ('source', 'anchor', 'quote', 'conclusion', 'topic')
ENTITY_TYPES = ('project', 'team', 'organisation', 'system', 'other')

ANCHOR_RE = re.compile(r'^\^?(?:(s\d{2,})-)?p(\d+)$', re.I)
END_ANCHOR_RE = re.compile(r' \^(s\d{2,}-p\d+)$')
OWN_ANCHOR_RE = re.compile(r'^\^(s\d{2,}-p\d+)$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# punctuation that NFKC leaves apart from its half-width form
PUNCT = str.maketrans({'。': '.', '、': ',', '“': '"', '”': '"', '‘': "'", '’': "'",
                       '「': '"', '」': '"', '『': '"', '』': '"', '《': '<', '》': '>',
                       '【': '[', '】': ']', '—': '-', '–': '-', '…': '...'})
DROP_RE = re.compile(r'[\s*_`~|]+')
LINK_UNSAFE_RE = re.compile(r'[\[\]|#^\n\r]+')
PAGE_UNSAFE_RE = re.compile(r'[\\/:*?"<>|#^\[\]]')

LABELS = {
    'en': {'title': '# Cards: [[%s]]', 'source': 'Source: [[%s]] · Document last modified: %s',
           'topic': '- Topic: %s', 'entities': '- Entities: %s', 'date': '- Date: %s',
           'event': ' (event: %s)', 'unknown': 'unknown'},
    'zh': {'title': '# 卡片：[[%s]]', 'source': '来源：[[%s]] · 文档最后修改：%s',
           'topic': '- 主题：%s', 'entities': '- 实体：%s', 'date': '- 日期：%s',
           'event': '（事件日期：%s）', 'unknown': '未知'},
}

REASONS = {
    'bad_json': 'not a JSON object',
    'missing_field': 'missing or empty field: %s',
    'unknown_source': 'source %s is not in the batch files',
    'bad_anchor': 'anchor %r is not of the form s01-p2',
    'quote_short': 'quote shorter than %d characters',
    'quote_long': 'quote longer than %d characters',
    'quote_not_found': 'quote not found in one paragraph of the source',
    'quote_ambiguous': 'quote found in several paragraphs (%s); give the anchor',
}


def norm(s):
    """Text for comparison: Unicode width folded, the punctuation above made half-width,
    white space and Markdown emphasis, code and table marks removed."""
    s = unicodedata.normalize('NFKC', s).translate(PUNCT)
    return DROP_RE.sub('', s)


# ---------------------------------------------------------------- reading batch files

def blocks(section_text):
    """{anchor: text of the paragraph, list item or table it marks} for one source section."""
    out = {}
    pending, last = [], []
    for ln in section_text.split('\n'):
        s = ln.strip()
        m = OWN_ANCHOR_RE.match(s)
        if m:                                 # a table's anchor, on its own line below it
            out[m.group(1).lower()] = '\n'.join(last)
            pending = []
            continue
        if not s:
            if pending:
                last = pending
            pending = []
            continue
        if s.startswith('#') or s.startswith('>'):
            pending = []
            continue
        m = END_ANCHOR_RE.search(ln)
        if m:
            pending.append(ln[:m.start()])
            out[m.group(1).lower()] = '\n'.join(pending)
            last, pending = pending, []
            continue
        pending.append(ln)
    return out


def load_batches(paths):
    """(sources table, {sid: {anchor: block text}}) over a run's batch files."""
    table, by_sid = {}, {}
    for p in paths:
        try:
            with open(p, encoding='utf-8') as f:
                text = f.read().replace('\r\n', '\n')
        except OSError as e:
            raise ValueError('cannot read %s: %s' % (p, e))
        table.update(kb_batch.sources_table(text))
        for sec in kb_batch.parse(text):
            by_sid.setdefault(sec['sid'], {}).update(blocks(sec['text']))
            table.setdefault(sec['sid'], {'name': sec['name'], 'path': '', 'modified': ''})
    return table, by_sid


# ---------------------------------------------------------------- checking

def anchor_of(card):
    m = ANCHOR_RE.match(str(card.get('anchor', '')).strip())
    if not m:
        return None
    sid = (m.group(1) or str(card['source'])).lower()
    return '%s-p%s' % (sid, int(m.group(2)))


def check_card(card, table, by_sid, qmin, qmax):
    """(card with anchor and date set, None, note) when it passes; (None, reason, None) when not.
    note is (old anchor, new anchor) when the anchor was corrected."""
    if not isinstance(card, dict):
        return None, REASONS['bad_json'], None
    for k in REQUIRED:
        if not str(card.get(k) or '').strip():
            return None, REASONS['missing_field'] % k, None
    sid = str(card['source']).strip().upper()
    if sid not in by_sid:
        return None, REASONS['unknown_source'] % sid, None
    anchor = anchor_of(dict(card, source=sid))
    if anchor is None:
        return None, REASONS['bad_anchor'] % card['anchor'], None
    q = norm(str(card['quote']))
    if len(q) < qmin:
        return None, REASONS['quote_short'] % qmin, None
    if len(q) > qmax:
        return None, REASONS['quote_long'] % qmax, None
    found = by_sid[sid]
    note = None
    if anchor not in found or q not in norm(found[anchor]):
        hits = [a for a, text in found.items() if q in norm(text)]
        if not hits:
            return None, REASONS['quote_not_found'], None
        if len(hits) > 1:
            return None, REASONS['quote_ambiguous'] % ', '.join(sorted(hits, key=_anchor_n)), None
        note = (anchor, hits[0])
        anchor = hits[0]
    ents = card.get('entities') or []
    if isinstance(ents, str):
        ents = [ents]
    out = {'source': sid, 'anchor': anchor, 'quote': str(card['quote']).strip(),
           'conclusion': str(card['conclusion']).strip(), 'topic': str(card['topic']).strip(),
           'entities': [str(e).strip() for e in ents if str(e).strip()],
           'date': table.get(sid, {}).get('modified', '')}
    ev = str(card.get('event_date') or '').strip()
    if ev and DATE_RE.match(ev):
        out['event_date'] = ev
    types = card.get('entity_types') if isinstance(card.get('entity_types'), dict) else {}
    types = {e: str(types[e]) for e in out['entities'] if str(types.get(e, '')) in ENTITY_TYPES}
    if types:
        out['entity_types'] = types
    return out, None, note


def topic_key(name):
    """Topics compare without regard to case and spacing (kbconf.topic_key does the same)."""
    return ' '.join(name.split()).casefold()


def _anchor_n(a):
    return int(a.rsplit('p', 1)[1])


def check(lines, table, by_sid, topics=None, qmin=QUOTE_MIN, qmax=QUOTE_MAX):
    """(accepted cards, report) for the card lines given."""
    accepted, rejected, fixed, seen = [], [], [], set()
    new_topics, dups, total = [], 0, 0
    known = {topic_key(t): t for t in topics or ()}
    for i, ln in enumerate(lines, 1):
        if not ln.strip():
            continue
        total += 1
        try:
            card = json.loads(ln)
        except ValueError:
            card = None
        if card is None or not isinstance(card, dict):
            rejected.append({'line': i, 'card': ln.strip(), 'reason': REASONS['bad_json']})
            continue
        out, reason, note = check_card(card, table, by_sid, qmin, qmax)
        if reason:
            rejected.append({'line': i, 'card': card, 'reason': reason})
            continue
        key = (out['source'], norm(out['quote']), norm(out['conclusion']))
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        if note:
            fixed.append({'line': i, 'from': note[0], 'to': note[1]})
        if topics is not None:
            out['topic'] = known.get(topic_key(out['topic']), out['topic'])
            if out['topic'] not in topics and out['topic'] not in new_topics:
                new_topics.append(out['topic'])
        accepted.append(out)
    report = {'cards': total, 'accepted': len(accepted), 'rejected': rejected,
              'anchors_fixed': fixed, 'duplicates': dups, 'new_topics': new_topics}
    return accepted, report


# ---------------------------------------------------------------- writing

def link_text(s):
    return ' '.join(LINK_UNSAFE_RE.sub(' ', s).split())


def page_name(topic):
    """File name (without .md) of a topic's page."""
    return PAGE_UNSAFE_RE.sub('-', ' '.join(topic.split())).strip().lstrip('.').strip()


def topic_link(topic, topics_dir=''):
    if not topics_dir:
        return '[[%s]]' % link_text(topic)
    return '[[%s/%s|%s]]' % (topics_dir, page_name(topic), link_text(topic))


def render_cards(stem, cards, date, lang='en', sources_dir='', topics_dir=''):
    lb = LABELS[lang]
    src = '%s/%s' % (sources_dir, stem) if sources_dir else stem
    w = [lb['title'] % src, '', lb['source'] % (src, date or lb['unknown']), '']
    for c in sorted(cards, key=lambda c: _anchor_n(c['anchor'])):
        n = _anchor_n(c['anchor'])
        w.append('## ' + ' '.join(c['conclusion'].split()).lstrip('#').strip())
        w.append('')
        w.append('> %s [[%s#^p%d]]' % (' '.join(c['quote'].split()), src, n))
        w.append('')
        w.append(lb['topic'] % topic_link(c['topic'], topics_dir))
        if c.get('entities'):
            w.append(lb['entities'] % ', '.join('[[%s]]' % link_text(e) for e in c['entities']))
        d = (c.get('date') or lb['unknown']) + (lb['event'] % c['event_date'] if c.get('event_date') else '')
        w.append(lb['date'] % d)
        w.append('')
    return '\n'.join(w)


def write(cards, table, outdir, names=None, lang='en', sources_dir='', topics_dir=''):
    """One file per source; returns the paths written. With sources_dir and topics_dir the links
    name their folders, as a library needs: a source and its cards file share a name."""
    by_sid = {}
    for c in cards:
        by_sid.setdefault(c['source'], []).append(c)
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for sid in sorted(by_sid, key=lambda x: int(x[1:])):
        src = table.get(sid, {})
        fname = kb_batch.output_name(sid, src.get('name', sid), names or {})
        stem = os.path.splitext(fname)[0]
        path = os.path.join(outdir, fname)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(render_cards(stem, by_sid[sid], src.get('modified', ''), lang, sources_dir, topics_dir))
        paths.append(path)
    return paths


CARD_QUOTE_RE = re.compile(r'^> (.*) \[\[([^\]#|]+)#\^(p\d+)\]\]\s*$')
LINK_RE = re.compile(r'\[\[([^\]]+)\]\]')
PAREN_RE = re.compile(r'[(（][^)）]*[)）]')
STAMP_RE = re.compile(r'\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?')


def _shown(link):
    return link.split('|', 1)[1] if '|' in link else link


def read_cards(text):
    """A cards file written by write(), back as {'source': link target, 'cards': [...]}; each card
    has conclusion, quote, anchor (pN), topic, entities, date and, when given, event_date.
    Read by structure, so either label language works."""
    lines = text.replace('\r\n', '\n').split('\n')
    m = LINK_RE.search(lines[0]) if lines and lines[0].startswith('# ') else None
    out = {'source': m.group(1) if m else '', 'cards': []}
    card = None
    for ln in lines[1:]:
        if ln.startswith('## '):
            card = {'conclusion': ln[3:].strip(), 'quote': '', 'anchor': '', 'topic': '',
                    'entities': [], 'date': '', '_bullets': 0}
            out['cards'].append(card)
            continue
        if card is None:
            continue
        q = CARD_QUOTE_RE.match(ln)
        if q:
            card['quote'], card['anchor'] = q.group(1).strip(), q.group(3)
        elif ln.startswith('- '):
            links = [_shown(x) for x in LINK_RE.findall(ln)]
            if card['_bullets'] == 0:
                card['topic'] = links[0] if links else ''
            elif links:
                card['entities'] = links
            else:
                ev = PAREN_RE.search(ln)
                if ev and STAMP_RE.search(ev.group(0)):
                    card['event_date'] = STAMP_RE.search(ev.group(0)).group(0)
                d = STAMP_RE.search(PAREN_RE.sub('', ln))
                card['date'] = d.group(0) if d else ''
            card['_bullets'] += 1
    for c in out['cards']:
        del c['_bullets']
    return out


# ---------------------------------------------------------------- command line

def read_lines(path):
    with open(path, encoding='utf-8') as f:
        return f.read().replace('\r\n', '\n').split('\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Check cards against their batch files and write the ones that pass.')
    ap.add_argument('--log-level', default=os.environ.get('LOG_LEVEL', 'WARNING').upper(),
                    type=str.upper, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                    help='default: environment variable LOG_LEVEL, else WARNING')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check', help='check cards; write the accepted ones and a report')
    c.add_argument('cards', help='cards, one JSON object per line')
    c.add_argument('batches', nargs='+', help='batch files of the run')
    c.add_argument('--accepted', required=True, help='output: accepted cards (JSON lines)')
    c.add_argument('--report', required=True, help='output: report (JSON)')
    c.add_argument('--topics', default=None, help='known topics, one per line')
    c.add_argument('--quote-min', type=int, default=QUOTE_MIN, help='default %d' % QUOTE_MIN)
    c.add_argument('--quote-max', type=int, default=QUOTE_MAX, help='default %d' % QUOTE_MAX)
    w = sub.add_parser('write', help='write accepted cards, one Markdown file per source')
    w.add_argument('cards', help='accepted cards from check')
    w.add_argument('batches', nargs='+', help='batch files of the run')
    w.add_argument('-o', '--outdir', required=True, help='cards folder')
    w.add_argument('--names', default=None,
                   help='JSON file mapping a source number or original file name to a file name')
    w.add_argument('--lang', choices=sorted(LABELS), default='en')
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)

    try:
        table, by_sid = load_batches(a.batches)
        lines = read_lines(a.cards)
        if a.cmd == 'check':
            topics = None
            if a.topics:
                topics = {t.strip() for t in read_lines(a.topics) if t.strip() and not t.startswith('#')}
            accepted, report = check(lines, table, by_sid, topics, a.quote_min, a.quote_max)
            with open(a.accepted, 'w', encoding='utf-8') as f:
                for card in accepted:
                    f.write(json.dumps(card, ensure_ascii=False) + '\n')
            with open(a.report, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=1)
            print('cards %d  accepted %d  rejected %d  anchors corrected %d  duplicates %d  new topics %d'
                  % (report['cards'], report['accepted'], len(report['rejected']),
                     len(report['anchors_fixed']), report['duplicates'], len(report['new_topics'])))
            return 3 if report['rejected'] else 0
        names = {}
        if a.names:
            with open(a.names, encoding='utf-8') as f:
                names = json.load(f)
        cards = [json.loads(ln) for ln in lines if ln.strip()]
        for p in write(cards, table, a.outdir, names, a.lang):
            print(p)
        return 0
    except (OSError, ValueError) as e:
        log.error('%s', e)
        return 2


if __name__ == '__main__':
    sys.exit(main())
