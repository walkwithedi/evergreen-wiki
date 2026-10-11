#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""doc2kb_dedup.py - remove documents from a merged or incremental md whose text is already
in other output files.

Typical case: a subfolder of the source folder was moved or renamed, the incremental mode
saw every file in it as changed and extracted them all again into one large incremental
file, although their text was already in earlier files. This script splits the target file
into its per-document sections, compares each section's text fingerprint with the other
files, removes the sections whose text is identical and lists their paths in the index.

Only the extracted text counts (the same as doc2kb_core.text_fingerprint): a document with
one changed character or a changed table is different and stays. Better to keep too much
than to delete something.

Usage:
  python3 doc2kb_dedup.py target.md                     compare with the other md in its folder
  python3 doc2kb_dedup.py target.md -n                  report only, change nothing
  python3 doc2kb_dedup.py target.md -b DIR_OR_FILE ...  compare with these

Writes:
  target.md                    the cleaned file (the original is backed up as target.md.bak-<time>)
  target_dedup-report.txt      which sections were removed and which file holds their text
  .doc2kb_watch_fp             the text fingerprint file next to the target, so incremental
                               runs skip known text from now on; -N leaves it alone

Works on output in either language (en or zh). Standard library only; source documents and
picture files are never touched.
"""

import argparse
import datetime
import glob
import logging
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc2kb_core as core  # noqa: E402

log = logging.getLogger('doc2kb_dedup')
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s'

FP_DB_NAME = '.doc2kb_watch_fp'
BODY_MARKS = ('<!-- Text below', '<!-- 以下为正文')        # start of core's body_mark label, en and zh
PATH_PREFIX = '(?:> Original path: |> 原始路径：)'          # core's section_path label
SOURCE_PREFIX = '(?:> Source file: |> 来源文件：)'          # first line of core's header label
SECTION_SPLIT = re.compile(r'\n\n---\n\n(?=# [^\n]*\n\n' + PATH_PREFIX + ')')
PATH_LINE = re.compile('^' + PATH_PREFIX + r'(.*)$', re.M)
SOURCE_LINE = re.compile('^' + SOURCE_PREFIX + r'(.*)$', re.M)
COUNT_LINE = re.compile(r'> 共 (\d+) 份文档。|> (\d+) documents\. ')
NO_TEXT_FILES = set(core.both('index_file'))
NO_TEXT_SUFFIXES = tuple(core.both('image_list_file'))

# labels of this script's own report and messages: (English, Chinese)
LABELS = {
    'title': ('Duplicate text clean-up report\n', '重复内容清理报告\n'),
    'target': ('Target file: %s\n', '目标文件：%s\n'),
    'generated': ('Generated: %s\n', '生成时间：%s\n'),
    'dry': ('(dry run, target file not changed)\n', '（试运行，目标文件未改动）\n'),
    'bases': ('\nCompared with (%d files):\n', '\n比对基准（%d 个文件）：\n'),
    'removed': ('\nRemoved %d sections, file size %s → %s\n', '\n删除 %d 节，文件大小 %s → %s\n'),
    'rule': ('Rule: the extracted text is identical (metadata, heading levels, picture paths and '
             'whitespace ignored).\n\n',
             '判定依据：提取出的正文文字完全相同（忽略元信息、标题层级、图片路径和空白差异）。\n\n'),
    'removed_list': ('Removed sections', '已删除的节'),
    'item': ('  • %s\n      old path: %s (text in %s)\n', '  • %s\n      原路径：%s（正文见 %s）\n'),
    'img_dirs': ('\nThese picture folders were used by removed sections. This script deletes no pictures; '
                 'clean them up by hand once no other file uses them:\n',
                 '\n下列图片目录被已删除的节引用过。本脚本不删除图片，确认其他文件不再引用后可手动清理：\n'),
    'summary': ('%d sections, %d duplicate of existing text, %d kept', '共 %d 节，与已有内容重复 %d 节，保留 %d 节'),
    'size': ('file size %s → %s', '文件大小 %s → %s'),
    'report': ('report: %s', '报告: %s'),
    'dry_done': ('dry run: target file not changed. Check the report, then run again without -n.',
                 '试运行：目标文件未改动。确认报告无误后去掉 -n 重新运行。'),
    'backup': ('original backed up: %s', '原文件已备份: %s'),
    'nothing': ('no duplicate text; target file not changed.', '没有重复内容，目标文件未改动。'),
    'fpdb': ('text fingerprint file: %d lines added: %s', '正文指纹库更新 %d 条: %s'),
    'report_suffix': ('_dedup-report.txt', '_去重报告.txt'),
}


def L(key, *args):
    text = LABELS[key][core.LANGS.index(core.LANG)]
    return text % args if args else text


def read_text(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def detect_lang(text):
    return 'zh' if BODY_MARKS[1] in text else 'en'


def split_merged(text):
    """Split a merged file. Returns (index part, body marker line, sections); None if the text is
    not a merged file. Each section is a dict: title, rel, text (the whole section from its
    "# title"), fp."""
    found = [text.find(m) for m in BODY_MARKS if m in text]
    if not found:
        return None
    pos = min(found)
    index_part = text[:pos]
    rest = text[pos:]
    chunks = SECTION_SPLIT.split(rest)
    mark = chunks[0]
    sections = []
    for c in chunks[1:]:
        title = c.split('\n', 1)[0][2:].strip()
        m = PATH_LINE.search(c)
        rel = m.group(1).strip() if m else title
        content = c.split('\n', 1)[1] if '\n' in c else ''
        sections.append({'title': title, 'rel': rel, 'text': c,
                         'fp': core.text_fingerprint(content)})
    return index_part, mark, sections


def single_doc(text, path):
    """Output of one-file-per-document mode: the whole file is one document."""
    m = SOURCE_LINE.search(text)
    rel = m.group(1).strip() if m else os.path.basename(path)
    return {'title': os.path.splitext(os.path.basename(path))[0],
            'rel': rel, 'fp': core.text_fingerprint(text)}


def collect_base_files(target, bases):
    """Files to compare with: by default the other md in the target's folder."""
    target_abs = os.path.abspath(target)
    files = []
    if bases:
        for b in bases:
            if os.path.isdir(b):
                files.extend(sorted(glob.glob(os.path.join(b, '*.md'))))
            elif os.path.isfile(b):
                files.append(b)
            else:
                log.warning('comparison file not found, ignored: %s', b)
    else:
        files = sorted(glob.glob(os.path.join(os.path.dirname(target_abs), '*.md')))
    out = []
    for f in files:
        name = os.path.basename(f)
        if os.path.abspath(f) == target_abs:
            continue
        # image lists and index files hold no document text
        if name.endswith(NO_TEXT_SUFFIXES) or name in NO_TEXT_FILES:
            continue
        out.append(f)
    return out


def build_base_map(base_files):
    """fingerprint -> (original path, name of the file holding the text); the first file in
    sort order wins."""
    base = {}
    for f in base_files:
        try:
            text = read_text(f)
        except OSError as e:
            log.warning('cannot read, ignored: %s (%s)', f, e)
            continue
        parsed = split_merged(text)
        secs = parsed[2] if parsed else [single_doc(text, f)]
        n = 0
        for s in secs:
            if s['fp'] and s['fp'] not in base:
                base[s['fp']] = (s['rel'], os.path.basename(f))
                n += 1
        log.debug('%s: %d sections, %d new fingerprints', f, len(secs), n)
    return base


def remove_index_entries(index_part, md_names):
    """Remove the removed documents' table rows and summary blocks from the index and fix the
    document count."""
    m = re.search(r'\n+---\n+\Z', index_part)
    tail = index_part[m.start():] if m else ''
    head = index_part[:m.start()] if m else index_part

    kept = []
    for ln in head.split('\n'):
        if ln.startswith('| ') and ln.split(' | ')[0][2:] in md_names:
            continue
        kept.append(ln)
    head = '\n'.join(kept)

    for name in md_names:
        head = re.sub(r'\n### ' + re.escape(name) + r'\n.*?(?=\n### |\n## |\Z)',
                      '', head, flags=re.S)

    def fix_count(mm):
        n = max(0, int(mm.group(1) or mm.group(2)) - len(md_names))
        return ('> 共 %d 份文档。' % n) if mm.group(1) else ('> %d documents. ' % n)
    head = COUNT_LINE.sub(fix_count, head, count=1)
    return head, tail


def add_moved_table(head, moved):
    """Add the moved-documents table to the index; if the section exists, append the rows."""
    pos = -1
    for h in core.both('moved_heading'):
        if h in head:
            pos = head.find(h)
            break
    if pos < 0:
        return head.rstrip('\n') + '\n' + core.moved_section_text(moved)
    lines = head[pos:].split('\n')
    last = max(i for i, ln in enumerate(lines) if ln.startswith('|'))
    lines[last + 1:last + 1] = core.moved_rows(moved)
    return head[:pos] + '\n'.join(lines)


def write_report(path, target, base_files, moved, before, after, dry_run):
    with open(path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(L('title') + '=' * 70 + '\n\n')
        f.write(L('target', target))
        f.write(L('generated', datetime.datetime.now().strftime('%Y-%m-%d %H:%M')))
        if dry_run:
            f.write(L('dry'))
        f.write(L('bases', len(base_files)))
        for b in base_files:
            f.write('  • %s\n' % b)
        f.write(L('removed', len(moved), human(before), human(after)))
        f.write(L('rule'))
        if moved:
            f.write('-' * 70 + '\n' + L('removed_list') + '\n' + '-' * 70 + '\n')
            for m in moved:
                f.write(L('item', m['rel'], m['old_rel'], m['kb_file']))
            imgs = sorted(set(d for m in moved for d in m['img_dirs']))
            if imgs:
                f.write(L('img_dirs'))
                for d in imgs:
                    f.write('  • %s\n' % d)


def human(n):
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return ('%d %s' % (n, unit)) if unit == 'B' else ('%.1f %s' % (n, unit))
        n /= 1024.0
    return '%.1f GB' % n


def update_fp_db(db_path, base_map, kept, target_name, moved):
    """Merge the fingerprints of the compared files and the target into the fingerprint file,
    so incremental runs skip that text from now on. Lines that pointed to the target are
    rewritten from the cleaned result (removed sections are no longer in it)."""
    lines = []
    try:
        with open(db_path, encoding='utf-8', errors='replace') as f:
            for ln in f:
                parts = ln.rstrip('\n').split('\t')
                if len(parts) >= 3 and parts[0] and parts[2] != target_name:
                    lines.append(tuple(parts[:3]))
    except OSError:
        pass  # no fingerprint file yet: it is created below
    known = set(r[0] for r in lines)
    n0 = len(lines)
    for fp, (rel, kb) in sorted(base_map.items(), key=lambda x: x[1]):
        if fp not in known:
            lines.append((fp, rel, kb))
            known.add(fp)
    for s in kept:
        if s['fp'] and s['fp'] not in known:
            lines.append((s['fp'], s['rel'], target_name))
            known.add(s['fp'])
    # moved documents point to their newest path
    lines += [(m['fp'], m['rel'], m['kb_file']) for m in moved]
    tmp = db_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', errors='replace') as f:
        for r in lines:
            f.write('%s\t%s\t%s\n' % r)
    os.replace(tmp, db_path)
    return len(lines) - n0


def main(argv=None):
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(errors='replace')
        except (AttributeError, ValueError):
            pass  # a stream that cannot be reconfigured keeps its encoding

    ap = argparse.ArgumentParser(
        description='Remove sections of a merged or incremental md whose text is already in other md files.')
    ap.add_argument('target', help='the merged or incremental md to clean')
    ap.add_argument('-b', '--base', action='append', metavar='PATH',
                    help='md file or folder to compare with (repeatable); '
                         'default: the other md in the target\'s folder')
    ap.add_argument('-n', '--dry-run', action='store_true',
                    help='write the report only; change neither the target nor the fingerprint file')
    ap.add_argument('-N', '--no-db', action='store_true',
                    help='do not write the text fingerprint file %s' % FP_DB_NAME)
    ap.add_argument('--log-level', default=os.environ.get('LOG_LEVEL', 'INFO'),
                    type=str.upper, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                    help='default: environment variable LOG_LEVEL, else INFO')
    args = ap.parse_args(argv)
    logging.basicConfig(level=args.log_level, format=LOG_FORMAT, stream=sys.stderr)

    target = os.path.abspath(args.target)
    if not os.path.isfile(target):
        log.error('target not found: %s', target)
        return 2
    text = read_text(target)
    parsed = split_merged(text)
    if not parsed:
        log.error('the target is not a doc2kb merged file (no body marker): %s', target)
        return 2
    core.set_lang(detect_lang(text))
    index_part, mark, sections = parsed
    log.info('target %s: %d sections', os.path.basename(target), len(sections))

    base_files = collect_base_files(target, args.base)
    if not base_files:
        log.error('no files to compare with')
        return 2
    base_map = build_base_map(base_files)
    log.info('%d files to compare with, %d text fingerprints', len(base_files), len(base_map))

    kept, moved, seen = [], [], {}
    for s in sections:
        hit = base_map.get(s['fp']) or seen.get(s['fp'])
        if s['fp'] and hit:
            moved.append({
                'rel': s['rel'], 'old_rel': hit[0], 'kb_file': hit[1],
                'fp': s['fp'], 'md': s['title'] + '.md',
                'img_dirs': sorted(set(
                    os.path.dirname(p) for p in
                    re.findall(r'(?:见|see) (images/\S+)', s['text']))),
            })
            log.debug('duplicate: %s <- %s (%s)', s['rel'], hit[0], hit[1])
            continue
        if s['fp']:
            seen[s['fp']] = (s['rel'], os.path.basename(target))
        kept.append(s)

    before = len(text.encode('utf-8'))
    if moved:
        head, tail = remove_index_entries(index_part, set(m['md'] for m in moved))
        head = add_moved_table(head, moved)
        new_text = head + tail + mark + ''.join('\n\n---\n\n' + s['text'] for s in kept)
        if not new_text.endswith('\n'):
            new_text += '\n'
    else:
        new_text = text
    after = len(new_text.encode('utf-8'))

    report_path = os.path.splitext(target)[0] + L('report_suffix')
    write_report(report_path, target, base_files, moved, before, after, args.dry_run)

    print(L('summary', len(sections), len(moved), len(kept)))
    print(L('size', human(before), human(after)))
    print(L('report', report_path))

    if args.dry_run:
        print(L('dry_done'))
        return 0

    if moved:
        bak = target + '.bak-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        shutil.copy2(target, bak)
        with open(target, 'w', encoding='utf-8', errors='replace') as f:
            f.write(new_text)
        print(L('backup', bak))
    else:
        print(L('nothing'))

    if not args.no_db:
        db_path = os.path.join(os.path.dirname(target), FP_DB_NAME)
        n = update_fp_db(db_path, base_map, kept, os.path.basename(target), moved)
        print(L('fpdb', n, db_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
