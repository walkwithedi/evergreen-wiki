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

Pictures inside converted files are exported to <out>/images/<name>/ and appear in the text
as one placeholder line each, "[Image: <file>]" ("[图片：<file>]" in Chinese). PDF pictures
have no position, so their placeholders follow the text. The batch line at the end counts
the pictures in converted files and compares them with the image limit: "read" means read
them all, "ask" means ask the user once whether to read them.

stdout: one line per file, then the batch line; <out>/convert.json holds the same as JSON.
stderr: log lines.
Usage: python3 convert.py OUT FILE [FILE ...] [--lang en|zh] [--image-limit 10]
       [--min-pdf-chars 200] [--min-chars-per-image 100]
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


def unique_stem(path, used):
    stem = core.safe_name(os.path.splitext(os.path.basename(path))[0])
    n = used.get(stem, 0) + 1
    used[stem] = n
    return stem if n == 1 else f"{stem}_{n}"


def convert_one(path, out, stem, lang, limits):
    """Convert one file; returns a result dict (see the module docstring)."""
    ext = os.path.splitext(path)[1].lower()
    res = {"file": path, "verdict": "as-is", "reason": "", "md": "", "chars": 0,
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
    kbconf.add_log_args(ap)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    lang = "zh" if a.lang.lower().startswith("zh") else "en"
    core.set_lang(lang)
    limits = {"min_pdf_chars": a.min_pdf_chars, "min_chars_per_image": a.min_chars_per_image}
    os.makedirs(a.out, exist_ok=True)

    used, results = {}, []
    for path in a.files:
        if not os.path.isfile(path):
            log.error("not found: %s", path)
            results.append({"file": path, "verdict": "fallback", "reason": "file not found", "md": "",
                            "chars": 0, "images": [], "image_dir": "", "warnings": []})
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
        print(f"{r['verdict']}: {os.path.basename(r['file'])} | {detail}{extra}{warn}")
    print(f"images: {n_img} in {n_files} converted files, limit {a.image_limit}: {decision}")
    summary = {"lang": lang, "image_limit": a.image_limit, "images": n_img, "decision": decision,
               "files": results}
    with open(os.path.join(a.out, "convert.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    sys.exit(0)


if __name__ == "__main__":
    main()
