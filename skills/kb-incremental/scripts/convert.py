#!/usr/bin/env python3
"""Convert uploaded material to Markdown before intake (Check 1, when the library's convert setting is on).

Each Office, PDF or mail file is converted with doc2kb_core.py (a copy of shared/scripts/
doc2kb_core.py). You then read the converted text instead of the original, which costs far
fewer tokens. Every file gets one of three verdicts:

  converted   use <out>/<name>.md from here on
  fallback    read the original as before; the reason says why (conversion failed, a PDF with
              little text per page, a document that is mostly pictures)
  as-is       not a format the converter handles (pictures, plain text, legacy .doc/.xls);
              read it as before. Not a failure.

Converted text longer than --outline-chars also gets <out>/<name>.outline.txt: its size, the
opening text and the headings (levels 1 to 3) with their line numbers in <name>.md. The assistant
reads the outline first and the full text, or a section by its line numbers, only where needed
(references/convert.md); 0 turns outlines off.

Pictures inside converted files are exported to <out>/images/<name>/ and appear in the text
as one placeholder line each, "[Image: <file>]" ("[图片：<file>]" in Chinese). PDF pictures
have no position, so their placeholders follow the text. The batch line at the end counts
the pictures in converted files and compares them with the image limit: "read" means read
them all, "ask" means ask the user once whether to read them.

stdout: one line per file, then the batch line; <out>/convert.json holds the same as JSON.
stderr: log lines.
Usage: python3 convert.py OUT FILE [FILE ...] [--lang en|zh] [--image-limit 10]
       [--min-pdf-chars 200] [--min-chars-per-image 100] [--outline-chars 6000]
Take the limits from the library (python3 scripts/kbconf.py show <library>: convert).
"""
import argparse
import json
import logging
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc2kb_core as core  # noqa: E402
import kbconf  # noqa: E402

log = logging.getLogger("convert")

MIN_TEXT = 20      # fewer characters than this and no pictures: nothing useful came out
PLACEHOLDER = {"en": "[Image: %s]", "zh": "[图片：%s]"}
# An anchor line written by doc2kb_core: "[Image 001: section, see images/x/img_001.png]  ← ..."
ANCHOR_RE = re.compile(r"^\[(?:图|Image)[^\n]*?(?:见|see) images/(?:\S+/)?([^/\s\]]+)\][^\n]*$", re.M)


def placeholders(md, lang):
    """Replace doc2kb picture anchors with placeholder lines; returns (text, file names in order)."""
    names = []

    def repl(m):
        names.append(m.group(1))
        return PLACEHOLDER[lang] % m.group(1)
    return ANCHOR_RE.sub(repl, md), names


def body_chars(md):
    """Characters of real text: no placeholders, whitespace or table and heading markup."""
    text = re.sub(r"^\[(?:Image|图片)[:：][^\n]*$", "", md, flags=re.M)
    return len(re.sub(r"[\s|#:\-*>]", "", text))


OUTLINE_HEADING_RE = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$")
OUTLINE_MAX_HEADINGS = 200


def outline(md, name, chars, pictures):
    """The outline of a converted text: size, opening text (doc2kb_core.extract_outline) and the
    headings of levels 1 to 3, each with its line number in the converted file."""
    lines = md.split("\n")
    summary, _, _ = core.extract_outline(md, summary_chars=600)
    tables = sum(1 for ln in lines if re.match(r"^\|\s*:?-{3,}", ln.strip()))
    heads = [(i, m.group(1), m.group(2)) for i, ln in enumerate(lines, 1)
             for m in [OUTLINE_HEADING_RE.match(ln)] if m]
    out = [f"Outline of {name}: read this first; read the full text, or a section by its line numbers, where needed.",
           f"characters: {chars} | lines: {len(lines)} | tables: {tables} | pictures: {pictures}",
           "", "opening:", summary or "(none)", "", "headings (line: heading):"]
    out += [f"{i}: {marks} {text}" for i, marks, text in heads[:OUTLINE_MAX_HEADINGS]] or ["(none)"]
    if len(heads) > OUTLINE_MAX_HEADINGS:
        out.append(f"({len(heads) - OUTLINE_MAX_HEADINGS} more headings not listed)")
    return "\n".join(out) + "\n"


def unique_stem(path, used):
    stem = core.safe_name(os.path.splitext(os.path.basename(path))[0])
    n = used.get(stem, 0) + 1
    used[stem] = n
    return stem if n == 1 else f"{stem}_{n}"


def convert_one(path, out, stem, lang, limits):
    """Convert one file; returns a result dict (see the module docstring)."""
    ext = os.path.splitext(path)[1].lower()
    res = {"file": path, "verdict": "as-is", "reason": "", "md": "", "outline": "", "chars": 0,
           "images": [], "image_dir": "", "warnings": []}
    if ext not in core.SUPPORTED_EXT:
        res["reason"] = "not a format the converter handles"
        return res
    imgdir = os.path.join(out, "images", core.safe_component(stem))
    report = core.Report()
    try:
        md, manifest = core.convert(path, ext, out, report, imgdir=imgdir,
                                    img_ref="images/" + core.safe_component(stem))
    except Exception as e:  # damaged, encrypted or unexpected content: read the original instead
        log.debug("conversion of %s failed", path, exc_info=True)
        res.update(verdict="fallback", reason=f"conversion failed: {str(e)[:120] or type(e).__name__}")
        return res
    res["warnings"] = report.warnings
    if not md.strip():
        res.update(verdict="fallback", reason="conversion failed: nothing was extracted")
        return res

    md, names = placeholders(md, lang)
    if ext == ".pdf":
        # PDF pictures have no position in the text; list them after it
        names = [m["file"] for m in manifest]
        if names:
            md = md.rstrip("\n") + "\n\n" + "\n".join(PLACEHOLDER[lang] % n for n in names) + "\n"
    # the title line the converter adds to workbooks and PDFs is the file name, not content
    chars = body_chars(re.sub(r"\A# [^\n]*\n", "", md) if ext in (".pdf", ".xlsx", ".xlsm") else md)
    res.update(chars=chars, images=names, image_dir=imgdir if names else "")
    if not names and os.path.isdir(imgdir) and not os.listdir(imgdir):
        os.rmdir(imgdir)
    if chars < MIN_TEXT and not names:
        res.update(verdict="fallback", reason=f"almost no text extracted ({chars} characters)")
        return res

    if ext == ".pdf":
        pages = core.pdf_pages(path)
        if pages and chars / pages < limits["min_pdf_chars"]:
            res.update(verdict="fallback",
                       reason=f"little text per page ({chars // pages} characters on {pages} pages), probably a scan")
            return res
    if len(names) >= 3 and chars / len(names) < limits["min_chars_per_image"]:
        res.update(verdict="fallback",
                   reason=f"mostly pictures ({len(names)} pictures, {chars} characters of text)")
        return res

    dest = os.path.join(out, stem + ".md")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    res.update(verdict="converted", md=dest)
    if limits.get("outline_chars") and chars > limits["outline_chars"]:
        res["outline"] = os.path.join(out, stem + ".outline.txt")
        with open(res["outline"], "w", encoding="utf-8", newline="\n") as f:
            f.write(outline(md, stem + ".md", chars, len(names)))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out", help="output folder (inside the work folder)")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--lang", default="en", help="library language; zh gives Chinese labels, anything else English")
    d = kbconf.CONVERT_DEFAULTS
    ap.add_argument("--image-limit", type=int, default=d["image_limit"])
    ap.add_argument("--min-pdf-chars", type=int, default=d["min_pdf_chars_per_page"])
    ap.add_argument("--min-chars-per-image", type=int, default=d["min_chars_per_image"])
    ap.add_argument("--outline-chars", type=int, default=d["outline_chars"],
                    help="converted text longer than this also gets an outline; 0 turns outlines off")
    kbconf.add_log_args(ap)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    lang = "zh" if a.lang.lower().startswith("zh") else "en"
    core.set_lang(lang)
    limits = {"min_pdf_chars": a.min_pdf_chars, "min_chars_per_image": a.min_chars_per_image,
              "outline_chars": max(0, a.outline_chars)}
    os.makedirs(a.out, exist_ok=True)

    used, results = {}, []
    for path in a.files:
        if not os.path.isfile(path):
            log.error("not found: %s", path)
            results.append({"file": path, "verdict": "fallback", "reason": "file not found", "md": "",
                            "outline": "", "chars": 0, "images": [], "image_dir": "", "warnings": []})
            continue
        res = convert_one(path, a.out, unique_stem(path, used), lang, limits)
        log.info("%s: %s %s", path, res["verdict"], res["reason"])
        results.append(res)

    n_img = sum(len(r["images"]) for r in results if r["verdict"] == "converted")
    n_files = sum(1 for r in results if r["verdict"] == "converted" and r["images"])
    decision = "read" if n_img <= a.image_limit else "ask"
    for r in results:
        detail = r["md"] if r["verdict"] == "converted" else r["reason"]
        extra = f" | {len(r['images'])} images" if r["images"] and r["verdict"] == "converted" else ""
        warn = f" | {len(r['warnings'])} warnings" if r["warnings"] else ""
        ol = f" | outline {r['outline']}" if r["outline"] else ""
        print(f"{r['verdict']}: {os.path.basename(r['file'])} | {detail}{extra}{ol}{warn}")
    print(f"images: {n_img} in {n_files} converted files, limit {a.image_limit}: {decision}")
    summary = {"lang": lang, "image_limit": a.image_limit, "outline_chars": limits["outline_chars"],
               "images": n_img, "decision": decision, "files": results}
    with open(os.path.join(a.out, "convert.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    sys.exit(0)


if __name__ == "__main__":
    main()
