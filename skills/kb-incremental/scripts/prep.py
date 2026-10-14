#!/usr/bin/env python3
"""Fast intake of one item in two calls (references/fast.md): the mechanical steps of Check 1, step 2
and step 4 before the assistant places the item, and of step 4, output and delivery preparation after.

  scan SOURCE --library ROOT --work WORK --n N [--spec SPEC] [--max-heading-len N] [--no-convert]
      Copies the library's file index into WORK when it is not there yet; checks the source for a
      duplicate upload by content hash and source name (index_tool.py check); stops there on a content
      hash hit. Otherwise converts the source when the library's convert setting is on (convert.py),
      cleans it into WORK/body_N.md (clean.py), reads the document date (meta.py date) and lists the
      Table B wordings in the body (meta.py terms). Prints one card: the duplicate result, the date,
      the size, the headings with line numbers and the opening text, the term hits.
  file --n N --library ROOT --work WORK --partition P --topic T --type T --title T --orig NAME
       [--source FILE] [--same-version] [--close-read] [--backend local|gdrive] [--max-len N]
      Builds the file name (meta.py name) and checks it against the index copy. A name already in
      the index stops with exit 3 and the row, unless --same-version says the item is the next version
      of that file; then the row is updated. Assembles WORK/head_N.md and WORK/body_N.md into
      WORK/out_N/<name> (assemble.py, with the original kept when the library keeps originals), adds
      the consolidation pending mark to the head with --close-read, updates the index copy and the
      consolidation queue copy in WORK, and writes both with a short readme into WORK/out_N, ready for
      package.py preview or zip.

The scripts it runs are the ones next to it; their own rules apply unchanged. Nothing in the library
changes here; delivery does that. stdout: the card or the result lines. stderr: log.
Exit codes: 0 ok; 2 bad arguments or unreadable file; 3 stopped for a decision (duplicate upload,
file name in the index, name too long, assembly refused).
"""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("prep")
HERE = os.path.dirname(os.path.abspath(__file__))
PENDING_MARK = "<!-- kb:conclusions-pending -->"
TEXT_EXT = (".md", ".txt", ".markdown")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
QUEUE_HEAD = {
    "en": ["# Consolidation queue", "",
           "Files filed by fast intake whose key conclusions and status-card check are still due. "
           "Consolidation (kb-incremental) removes each row when it is done.", "",
           "| File | Source file | Filed | Close-read |", "| --- | --- | --- | --- |"],
    "zh": ["# 待整合清单", "",
           "快速入库已落库、还没有补关键结论和核对状态卡的文件。整合（kb-incremental）完成后逐行删去。", "",
           "| 文件名 | 原文件名 | 入库时间 | 精读 |", "| --- | --- | --- | --- |"],
}
YES_NO = {"en": ("yes", "no"), "zh": ("是", "否")}


def lang_of(cfg):
    return "zh" if str(cfg.get("language", "")).lower().startswith("zh") else "en"


def run(script, *args):
    """Run a sibling script; returns (exit code, stdout). Its log goes to our stderr."""
    cmd = [sys.executable, os.path.join(HERE, script)] + [str(x) for x in args]
    log.debug("run: %s", " ".join(cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                       encoding="utf-8", errors="replace")
    if p.stderr:
        for line in p.stderr.rstrip("\n").split("\n"):
            log.debug("%s: %s", script, line)
    return p.returncode, p.stdout


def load(lib):
    try:
        return kbconf.load_library(lib)
    except kbconf.ConfigError as e:
        log.error("%s", e)
        sys.exit(2)


def library_root(cfg):
    return os.path.dirname(cfg["_path"])


def work_copy(work, root, name, make=None):
    """WORK/<name>, copied from the library root the first time; made by make() when the library has none."""
    dst = os.path.join(work, name)
    if os.path.isfile(dst):
        return dst
    src = os.path.join(root, name)
    os.makedirs(work, exist_ok=True)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        log.info("copied %s into the work folder", name)
    elif make:
        with open(dst, "w", encoding="utf-8", newline="\n") as f:
            f.write(make())
        log.info("started %s in the work folder", name)
    else:
        return None
    return dst


def outline(text, max_headings=30, opening=300):
    lines = text.split("\n")
    heads = [(i, m.group(1), m.group(2)) for i, ln in enumerate(lines, 1) for m in [HEADING_RE.match(ln)] if m]
    body = re.sub(r"\s+", " ", " ".join(ln for ln in lines if ln.strip() and not HEADING_RE.match(ln))).strip()
    out = [f"opening: {body[:opening]}{'…' if len(body) > opening else ''}"]
    out.append(f"headings: {len(heads)}" + ("" if heads else " (none)"))
    for i, level, title in heads[:max_headings]:
        out.append(f"  line {i}: {'  ' * (len(level) - 1)}{title[:120]}")
    if len(heads) > max_headings:
        out.append(f"  ({len(heads) - max_headings} more; toc with kb-query's kbfind.py or read by line)")
    return out


# ---------- scan ----------

def cmd_scan(a):
    cfg = load(a.library)
    root, names = library_root(cfg), cfg["names"]
    if not os.path.isfile(a.source):
        print(f"refused: source not found: {a.source}")
        return 2
    os.makedirs(a.work, exist_ok=True)
    base = os.path.basename(a.source)
    card = [f"=== Item {a.n}: {base} ==="]
    index = work_copy(a.work, root, names["index"])
    if index:
        _, out = run("index_tool.py", "check", index, "--orig", base, "--file", a.source)
        dup = [ln for ln in out.split("\n") if ln.strip()]
        card += dup
        if any(ln.startswith("Content hash: HIT") for ln in dup):
            card.append("result: duplicate upload by content hash; no file, no index row (step 4)")
            print("\n".join(card))
            return 3
    else:
        card.append("index: not found in the library; treat as new material and mark it not de-duplicated")

    conv = cfg.get("convert") or {}
    text_path, how = None, ""
    ext = os.path.splitext(base)[1].lower()
    if conv.get("enabled") and not a.no_convert and ext not in TEXT_EXT:
        cdir = os.path.join(a.work, f"conv_{a.n}")
        code, out = run("convert.py", cdir, a.source, "--lang", lang_of(cfg),
                        "--image-limit", conv.get("image_limit", 10),
                        "--min-pdf-chars", conv.get("min_pdf_chars_per_page", 200),
                        "--min-chars-per-image", conv.get("min_chars_per_image", 100),
                        "--outline-chars", 0)
        try:
            with open(os.path.join(cdir, "convert.json"), encoding="utf-8") as f:
                res = json.load(f)["files"][0]
        except (OSError, ValueError, KeyError, IndexError):
            res = {"verdict": "fallback", "reason": f"converter did not run (exit {code})"}
        if res["verdict"] == "converted":
            text_path, how = res["md"], "converted"
            if res.get("images"):
                card.append(f"pictures: {len(res['images'])} in {res.get('image_dir', '')} "
                            f"(limit {conv.get('image_limit', 10)} per run; references/convert.md)")
        else:
            card.append(f"conversion: {res['verdict']}, {res.get('reason', '')}: read the original "
                        "(Check 1) and write the body file by hand")
    elif ext in TEXT_EXT:
        text_path, how = a.source, "text"
    else:
        card.append("conversion: off or not possible for this type: read the original (Check 1) and write "
                    "the body file by hand")

    body = os.path.join(a.work, f"body_{a.n}.md")
    if text_path:
        limit = a.max_heading_len or kbconf.default_limits(cfg.get("language"))[0]
        if os.path.exists(body):
            os.remove(body)  # a scan run again starts from the source
        code, out = run("clean.py", text_path, body, "--max-heading-len", limit)
        if code:
            card.append(f"cleanup failed (exit {code}): clean the body by hand")
        else:
            card.append(f"body: {body} ({how}) | {out.strip()}")
    code, out = run("meta.py", "date", a.source, "--timezone", cfg.get("timezone") or "UTC")
    card.append("date: " + (out.strip().split(" | ", 1)[-1] if out.strip() else "not read"))
    if os.path.isfile(body):
        with open(body, encoding="utf-8") as f:
            text = f.read()
        card.append(f"size: {len(text)} characters, {text.count(chr(10))} lines")
        card += outline(text)
        spec = a.spec or work_copy(a.work, root, names["spec"])
        if spec and os.path.isfile(spec):
            code, out = run("meta.py", "terms", spec, body)
            card += ["terms: " + ln if i == 0 else "  " + ln
                     for i, ln in enumerate(l for l in out.rstrip("\n").split("\n") if l)]
        else:
            card.append("terms: spec not found; search Table B entries by hand")
    card.append("next: place it (step 1), write the head file, then prep.py file")
    print("\n".join(card))
    return 0


# ---------- file ----------

def queue_lines(path, lang):
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n").rstrip("\n").split("\n")
    return list(QUEUE_HEAD[lang])


def queue_row(name, orig, when, close, lang):
    yes, no = YES_NO[lang]
    return f"| {name} | {orig.replace('|', '-')} | {when} | {yes if close else no} |"


def readme(lang, name, orig, close, same):
    if lang == "zh":
        return "\n".join([
            "1. 新增文件", f"   {name}（来自 {orig}）" if not same else "   无",
            "2. 更新文件", f"   {name}（同名新版本，来自 {orig}）" if same else "   无",
            "   文件索引；待整合清单",
            "3. 变更", "   快速入库：关键结论与状态卡核对留待整合" + ("；本文件在精读清单上" if close else ""),
            "4. 读取的库文件", "   文件索引；规范（术语表）", ""])
    return "\n".join([
        "1. New files", f"   {name} (from {orig})" if not same else "   none",
        "2. Updated files", f"   {name} (same-name new version, from {orig})" if same else "   none",
        "   file index; consolidation queue",
        "3. Changes", "   Fast intake: key conclusions and the status-card check wait for consolidation"
        + ("; this file is on the close-reading list" if close else ""),
        "4. Library files read", "   file index; spec (term table)", ""])


def cmd_file(a):
    cfg = load(a.library)
    root, names, lang = library_root(cfg), cfg["names"], lang_of(cfg)
    head_p, body_p = (os.path.join(a.work, f"{k}_{a.n}.md") for k in ("head", "body"))
    for p in (head_p, body_p):
        if not os.path.isfile(p):
            print(f"refused: {p} not found")
            return 2
    args = ["name", "--partition", a.partition, "--topic", a.topic, "--type", a.type, "--title", a.title]
    args += ["--max-len", a.max_len] if a.max_len else ["--language", cfg.get("language", "en")]
    code, out = run("meta.py", *args)
    if code:
        print(out.strip())
        return 3
    name = out.strip().split(" | ")[0]
    index = work_copy(a.work, root, names["index"])
    if not index:
        print("refused: no file index in the library or the work folder")
        return 2
    _, out = run("index_tool.py", "check", index, "--orig", a.orig, "--name", name)
    hit = [ln for ln in out.split("\n") if ln.startswith("File name: HIT")]
    if hit and not a.same_version:
        print(f"name: {name}")
        print("\n".join(hit))
        print("decide (step 4): the next version of that file -> run again with --same-version; "
              "different material -> run again with a short title that tells them apart")
        return 3
    if a.same_version and not hit:
        print(f"refused: --same-version, but {name} is not in the index")
        return 3

    out_dir = os.path.join(a.work, f"out_{a.n}")
    if os.path.isdir(out_dir):
        print(f"refused: {out_dir} exists; this item was prepared already (deliver it, or remove the folder)")
        return 3
    with open(head_p, encoding="utf-8") as f:
        head = f.read().replace("\r\n", "\n")
    if a.close_read and PENDING_MARK not in head:
        head = head.rstrip("\n") + "\n\n" + PENDING_MARK + "\n"
    head_ready = os.path.join(a.work, f"head_{a.n}.ready.md")
    with open(head_ready, "w", encoding="utf-8", newline="\n") as f:
        f.write(head)
    target = os.path.join(out_dir, name)
    os.makedirs(out_dir)
    asm = ["assemble.py", head_ready, body_p, target]
    if a.source and kbconf.keeps_sources(cfg, a.backend):
        asm += ["--source", a.source, "--sources-dir", os.path.join(out_dir, names["sources_dir"]),
                "--max-mb", (cfg.get("sources") or {}).get("max_mb", 50)]
    code, out = run(*asm)
    if code:
        print(out.strip())
        shutil.rmtree(out_dir, ignore_errors=True)
        return 3
    lines = [out.strip()]
    sub = "update" if a.same_version else "add"
    idx = [sub, index, "--name", name, "--orig", a.orig] + (["--file", a.source] if a.source else [])
    code, out = run("index_tool.py", *idx)
    if code:
        print(out.strip() or f"index {sub} failed (exit {code})")
        shutil.rmtree(out_dir, ignore_errors=True)
        return 3
    lines.append(out.strip())
    today = kbconf.now(cfg["timezone"])
    run("index_tool.py", "write", index, "--out", os.path.join(out_dir, names["index"]),
        "--date", today.strftime("%Y-%m-%d"))

    queue = os.path.join(a.work, names["consolidation_queue"])
    if not os.path.isfile(queue) and os.path.isfile(os.path.join(root, names["consolidation_queue"])):
        shutil.copy2(os.path.join(root, names["consolidation_queue"]), queue)
    q = [ln for ln in queue_lines(queue, lang) if not ln.startswith(f"| {name} |")]
    q.append(queue_row(name, a.orig, today.strftime("%Y-%m-%d %H:%M"), a.close_read, lang))
    text = "\n".join(q) + "\n"
    for p in (queue, os.path.join(out_dir, names["consolidation_queue"])):
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    with open(os.path.join(out_dir, names["readme"]), "w", encoding="utf-8", newline="\n") as f:
        f.write(readme(lang, name, a.orig, a.close_read, a.same_version))
    lines.append(f"queued: {name} ({'close-read, conclusions pending' if a.close_read else 'status-card check pending'})")
    lines.append(f"ready: {out_dir} -> package.py preview (or zip) with --run")
    print("\n".join(lines))
    return 0


def main():
    kbconf.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("source")
    p.add_argument("--library", required=True, help="library root or its _kb.json")
    p.add_argument("--work", required=True)
    p.add_argument("--n", required=True, type=int)
    p.add_argument("--spec", help="the spec, if not <work>/<spec name> or the library's")
    p.add_argument("--max-heading-len", type=int, default=0, help="Table D heading limit")
    p.add_argument("--no-convert", action="store_true", help="the user asked not to convert this time")
    p = sub.add_parser("file")
    p.add_argument("--n", required=True, type=int)
    p.add_argument("--library", required=True)
    p.add_argument("--work", required=True)
    for k in ("--partition", "--topic", "--type", "--title", "--orig"):
        p.add_argument(k, required=True)
    p.add_argument("--source", help="the original file (hash, kept original); none for pasted text")
    p.add_argument("--same-version", action="store_true")
    p.add_argument("--close-read", action="store_true", help="on the params close-reading list")
    p.add_argument("--backend", choices=["local", "gdrive"], default="local")
    p.add_argument("--max-len", type=int, default=0, help="Table D file name limit")
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    return {"scan": cmd_scan, "file": cmd_file}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
