"""Tests for the converter (shared/scripts/doc2kb_core.py), tools/doc2kb and kb-incremental's convert.py.
Standard library only: python3 -m unittest discover tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(ROOT, "shared", "scripts", "doc2kb_core.py")
TOOL = os.path.join(ROOT, "tools", "doc2kb")
SKILL_SCRIPTS = os.path.join(ROOT, "skills", "kb-incremental", "scripts")
sys.path.insert(0, TESTS)
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
import doc2kb_core as core  # noqa: E402
import doc2kb_fixtures as fx  # noqa: E402

HAS_PDF = shutil.which("pdftotext") is not None
HAS_BASH = os.name != "nt" and shutil.which("bash") is not None


def run(args, check=True, env=None, cwd=None):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    e.update(env or {})
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, cwd=cwd)
    if check and p.returncode != 0:
        raise AssertionError(f"{args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def stats(out):
    return {m.group(1): int(m.group(2)) for m in re.finditer(r"^STAT\t(\w+)\t(\d+)$", out, re.M)}


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name
        core.set_lang("en")

    def tearDown(self):
        core.set_lang("en")
        self._t.cleanup()

    def p(self, *parts):
        return os.path.join(self.d, *parts)


class ConverterTest(Tmp):
    def batch(self, lang, *extra):
        src = self.p("src")
        fx.build_all(src, english=(lang == "en"))
        os.makedirs(self.p("src", "sub"), exist_ok=True)
        shutil.copy(self.p("src", f"report-{lang}.docx"), self.p("src", "sub", f"report-{lang}.docx"))
        out = self.p("out")
        p = run([sys.executable, CORE, "--batch", src, "-o", out, "--lang", lang, *extra])
        return out, p.stdout

    def test_english_merged(self):
        out, stdout = self.batch("en", "--merge", "--merge-name", "all")
        md = read(os.path.join(out, "all.md"))
        s = stats(stdout)
        self.assertEqual(s["legacy"], 1)
        self.assertEqual(s["dup"], 1)          # sub/report-en.docx is a copy
        self.assertEqual(s["failed"], 0 if HAS_PDF else 1)
        # docx: headings by three style conventions, content control, merged and nested cells
        for text in ("## Project Atlas report", "### Scope", "#### Details", "Cover text",
                     "| x\\|y |   | inner1 / inner2 |"):
            self.assertIn(text, md)
        # pictures: the described one has no orphan mark, the other has
        self.assertIn("[Image 001: Scope, see images/report-en/img_001.png]\n", md)
        self.assertIn("[Image 002: Details, see images/report-en/img_002.png]  ← orphan image", md)
        self.assertTrue(os.path.isfile(os.path.join(out, "images", "report-en", "img_002.png")))
        # embedded workbook once, with a date; embedded document; legacy object as a gap
        self.assertEqual(md.count("**Inline attachment: book1.xlsx**"), 1)
        self.assertIn("same content as \"book1.xlsx\" above", md)
        self.assertIn("| d | 2026-01-02 |", md)
        self.assertIn("**Inline attachment (Word): inner.docx**", md)
        self.assertIn("could not be opened automatically", md)
        # workbook: blank rows dropped, trailing empty column trimmed
        self.assertIn("## Sheet: Data", md)
        self.assertIn("| Name | Date |\n| --- | --- |\n| a | 2026-01-02 |\n| b | 7 |\n| c | 8 |", md)
        # slides and mail
        self.assertIn("## Slide 2", md)
        self.assertIn("*(no text on this slide)*", md)
        self.assertIn("# Weekly sync", md)
        self.assertIn("Hello team\nLine two & more", md)
        self.assertIn("picture in the mail (chart.png)", md)
        self.assertNotIn("logo.png", md)
        self.assertIn("| 1 | plan.docx |", md)
        # report
        report = read(os.path.join(out, "_batch-report.txt"))
        self.assertIn("charts drawn with shapes", report)
        self.assertIn("Need a new format first", report)
        self.assertIn("legacy-en.doc", report)
        self.assertIn("Duplicate files", report)
        self.assertTrue(os.path.isfile(os.path.join(out, "_image-list.md")))

    def test_chinese_labels_and_files(self):
        out, stdout = self.batch("zh")
        md = read(os.path.join(out, "report-zh.md"))
        self.assertTrue(md.startswith("> 来源文件：report-zh.docx\n> 文档最后修改："))
        self.assertIn("（来源：文档属性）", md)
        self.assertIn("[图 001：范围，见 images/report-zh/img_001.png]\n", md)
        self.assertIn("← 孤儿图（周围无文字描述）", md)
        self.assertIn("> 注：本目录下另有 1 份内容相同的副本，已略去：" + os.path.join("sub", "report-zh.docx"), md)
        for name in ("_知识库索引.md", "_批量处理报告.txt", "_图片清单.md"):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)
        self.assertIn("建议优先人工查看", read(os.path.join(out, "_图片清单.md")))
        self.assertIn("批量完成。", stdout)
        self.assertFalse(os.path.exists(os.path.join(out, "report-zh_2.md")))

    def test_incremental_skip_rebuilds_entries(self):
        out, _ = self.batch("en")
        p = run([sys.executable, CORE, "--batch", self.p("src"), "-o", out, "--lang", "en"])
        self.assertIn("skipped (exists)", p.stdout)
        index = read(os.path.join(out, "_kb-index.md"))
        self.assertIn("| report-en.md |", index)
        self.assertGreater(stats(p.stdout)["kept"], 0)

    def test_fingerprint_across_runs(self):
        src = self.p("src")
        fx.build_all(src, english=True)
        db = self.p("out", ".fp")
        os.makedirs(self.p("out"))
        args = [sys.executable, CORE, "--batch", src, "-o", self.p("out"), "--merge", "--fp-db", db, "--no-images"]
        run(args + ["--merge-name", "one"])
        # the same documents in another folder: text known, only listed as moved
        shutil.move(src, self.p("moved"))
        p = run([sys.executable, CORE, "--batch", self.p("moved"), "-o", self.p("out"), "--merge", "--fp-db", db,
                 "--no-images", "--merge-name", "two"])
        s = stats(p.stdout)
        self.assertEqual(s["written"], 0)
        self.assertGreater(s["moved"], 0)
        self.assertIn("## Documents moved, content unchanged", read(self.p("out", "two.md")))

    def test_scan_only_and_no_match(self):
        src = self.p("src")
        fx.build_all(src, english=True)
        p = run([sys.executable, CORE, "--batch", src, "--scan-only"])
        self.assertIn("LEGACY\tlegacy-en.doc", p.stdout)
        self.assertEqual(len(re.findall(r"^OK\t", p.stdout, re.M)), 5)
        p = run([sys.executable, CORE, "--batch", src, "--since", "2999-01-01", "-o", self.p("o")], check=False)
        self.assertEqual(p.returncode, core.NO_MATCH)

    @unittest.skipUnless(HAS_PDF, "pdftotext not installed")
    def test_pdf(self):
        path = fx.pdf(self.p("n.pdf"), ["Project Atlas notes", "second line"])
        p = run([sys.executable, CORE, path, "-o", self.p("o")])
        md = read(self.p("o", "n.md"))
        self.assertIn("Project Atlas notes", md)
        self.assertIn("PDF is a lossy", read(self.p("o", "_batch-report.txt")))
        self.assertEqual(stats(p.stdout)["new"], 1)

    def test_helpers(self):
        raw = "报告".encode("gbk")
        broken = raw.decode("utf-8", "surrogateescape")
        self.assertEqual(core.fs_text("目录/" + broken), "目录/报告")
        self.assertEqual(core.src_code("文档属性"), "doc")
        self.assertEqual(core.src_code("mail"), "mail")
        self.assertEqual(core.excel_serial_to_text("46024", "date"), "2026-01-02")
        self.assertEqual(core.classify_numfmt("[h]:mm"), None)
        self.assertEqual(core.classify_numfmt("yyyy-mm-dd hh:mm"), "datetime")
        # a single md and its merged section give the same text fingerprint, in either language
        for lang, anchor in (("zh", "见"), ("en", "see")):
            core.set_lang(lang)
            single = core.T("header", "a.docx", "2026-01-01 00:00", "x", "", "now") + \
                f"# Title\n\nBody\n\n[Image 001: s, {anchor} images/a/img_001.png]\n"
            merged = f"## Title\n\nBody\n\n[Image 001: s, {anchor} images/b/c/img_001.png]\n"
            self.assertEqual(core.text_fingerprint(single), core.text_fingerprint(merged))


class ArchiveTest(Tmp):
    """Archives read like folders, and identical files parsed once."""

    def build(self):
        import io
        import tarfile
        import zipfile
        src = self.p("src")
        os.makedirs(src)
        report = read_bytes(fx.docx(os.path.join(src, "report.docx"), english=True))
        book = read_bytes(fx.xlsx(self.p("book.xlsx"), english=True))
        slides = read_bytes(fx.pptx(self.p("slides.pptx"), english=True))
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr("deep/slides.pptx", slides)
        pack = os.path.join(src, "pack.zip")
        with zipfile.ZipFile(pack, "w") as z:
            z.writestr("a/report.docx", report)          # same bytes as the file outside
            z.writestr("../../escape.xlsx", book)         # must not leave the temporary folder
            z.writestr("inner.zip", inner.getvalue())
            z.writestr("old.doc", b"\xd0\xcf\x11\xe0")
            z.writestr("__MACOSX/._x.docx", b"junk")
            z.writestr("notes.7z", b"7z")
            z.writestr("locked.docx", b"x")
            z.writestr("ABCD.pptx", read_bytes(fx.pptx(self.p("zh.pptx"))))
        # a name stored as GBK without the UTF-8 flag, the way Chinese Windows writes it
        raw = read_bytes(pack).replace(b"ABCD.pptx", "报告".encode("gbk") + b".pptx")
        # mark locked.docx encrypted (zipfile cannot write encrypted members)
        name = b"locked.docx"
        for sig, flag_at, name_at in ((b"PK\x03\x04", 6, 30), (b"PK\x01\x02", 8, 46)):
            i = raw.find(sig)
            while i >= 0:
                if raw[i + name_at:i + name_at + len(name)] == name:
                    raw = raw[:i + flag_at] + bytes([raw[i + flag_at] | 1]) + raw[i + flag_at + 1:]
                i = raw.find(sig, i + 4)
        with open(pack, "wb") as f:
            f.write(raw)
        with tarfile.open(os.path.join(src, "b.tar.gz"), "w:gz") as t:
            for name, data in (("x/book.xlsx", book), ("x/slides2.pptx", slides)):
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                ti.mtime = 1700000000
                t.addfile(ti, io.BytesIO(data))
        with open(os.path.join(src, "broken.zip"), "wb") as f:
            f.write(b"not a zip")
        return src

    def arc_tmp(self):
        import tempfile as tf
        return {n for n in os.listdir(tf.gettempdir()) if n.startswith("doc2kb-arc-")}

    def test_batch(self):
        src = self.build()
        before = self.arc_tmp()
        p = run([sys.executable, CORE, "--batch", src, "--scan-only"])
        for rel in ("pack.zip/a/report.docx", "pack.zip/inner.zip/deep/slides.pptx", "pack.zip/escape.xlsx",
                    "pack.zip/报告.pptx", "b.tar.gz/x/book.xlsx", "broken.zip"):
            self.assertIn("OK\t" + rel + "\t", p.stdout)
        self.assertIn("LEGACY\tpack.zip/old.doc", p.stdout)
        self.assertNotIn("__MACOSX", p.stdout)

        out = self.p("out")
        p = run([sys.executable, CORE, "--batch", src, "-o", out, "--no-images"])
        s = stats(p.stdout)
        self.assertEqual((s["new"], s["dup"], s["legacy"]), (4, 3, 1))
        self.assertIn("not parsed again: pack.zip/a/report.docx", p.stdout)
        # the copy outside the archive is kept and keeps its plain name
        self.assertIn("pack.zip/a/report.docx", read(os.path.join(out, "report.md")))
        self.assertTrue(os.path.isfile(os.path.join(out, "报告.md")))
        report = read(os.path.join(out, "_batch-report.txt"))
        self.assertIn("kept     → b.tar.gz/x/book.xlsx", report)
        self.assertIn("left out   pack.zip/escape.xlsx", report)
        self.assertIn("left out   pack.zip/inner.zip/deep/slides.pptx", report)
        for reason in ("archive damaged or not readable", ".7z archives need a tool",
                       "encrypted inside the archive"):
            self.assertIn(reason, report)
        failed = set(re.findall(r"^FAILED\t(.*)$", p.stdout, re.M))
        self.assertEqual(failed, {"broken.zip", "pack.zip/notes.7z", "pack.zip/locked.docx"})
        self.assertIn("| b.tar.gz/x/slides2.pptx |", read(os.path.join(out, "_kb-index.md")))
        self.assertFalse(os.path.exists(self.p("escape.xlsx")))
        self.assertEqual(self.arc_tmp(), before)

        # second run: existing output is kept, the archive copies are still left out
        p = run([sys.executable, CORE, "--batch", src, "-o", out, "--no-images"])
        s = stats(p.stdout)
        self.assertEqual((s["new"], s["kept"], s["dup"]), (0, 4, 3))

        # -D keeps every copy
        p = run([sys.executable, CORE, "--batch", src, "-o", self.p("all"), "--no-images", "-D"])
        self.assertEqual(stats(p.stdout)["new"], 7)

    def test_named_archive_and_only(self):
        src = self.build()
        p = run([sys.executable, CORE, os.path.join(src, "b.tar.gz"), "-o", self.p("o1"), "--no-images"])
        self.assertEqual(stats(p.stdout)["new"], 2)
        self.assertIn("| b.tar.gz/x/book.xlsx |", read(self.p("o1", "_kb-index.md")))
        only = self.p("only.txt")
        with open(only, "w", encoding="utf-8") as f:
            f.write("pack.zip/inner.zip/deep/slides.pptx\n")
        p = run([sys.executable, CORE, "--batch", src, "-o", self.p("o2"), "--only", only, "--no-images"])
        self.assertEqual(stats(p.stdout)["new"], 1)
        self.assertTrue(os.path.isfile(self.p("o2", "slides.md")))
        # members carry the time stored in the archive; the date filter uses it
        p = run([sys.executable, CORE, "--batch", src, "--scan-only", "--since", "2026-01-06"])
        self.assertIn("FILTERED\tb.tar.gz/x/slides2.pptx", p.stdout)
        self.assertIn("OK\tb.tar.gz/x/book.xlsx", p.stdout)

    def test_limits(self):
        import io
        import zipfile
        data = read_bytes(fx.xlsx(self.p("book.xlsx"), english=True))
        for level in range(4):      # four archives deep
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("big.xlsx" if level == 0 else "l%d.zip" % level, data)
                if level == 0:
                    z.writestr("small.xlsx", data[:10])
            data = buf.getvalue()
        os.makedirs(self.p("src"))
        with open(self.p("src", "top.zip"), "wb") as f:
            f.write(data)
        ok, _, _ = core.scan_dir(self.p("src"))
        self.assertEqual([it["rel"] for it in ok], ["top.zip/l3.zip/l2.zip/l1.zip"])
        self.assertIn("nested more than 3", ok[0]["error"])
        old = core.ARC_MAX_MEMBER
        core.ARC_MAX_MEMBER = 100
        try:
            inner = zipfile.ZipFile(io.BytesIO(data)).read("l3.zip")
            with open(self.p("src", "top.zip"), "wb") as f:
                f.write(inner)
            ok, _, _ = core.scan_dir(self.p("src"))
        finally:
            core.ARC_MAX_MEMBER = old
        self.assertEqual(len(ok), 1)
        self.assertIn("larger than", ok[0]["error"])


class DedupToolTest(Tmp):
    def make(self, lang):
        src = self.p(lang, "src")
        fx.build_all(src, english=(lang == "en"))
        run([sys.executable, CORE, "--batch", src, "-o", self.p(lang, "base"), "--merge", "--merge-name", "full",
             "--no-images", "--lang", lang])
        os.makedirs(self.p(lang, "inc"))
        shutil.copy(self.p(lang, "base", "full.md"), self.p(lang, "inc", "big.md"))
        return self.p(lang, "inc", "big.md")

    def test_both_languages(self):
        for lang in ("en", "zh"):
            with self.subTest(lang=lang):
                target = self.make(lang)
                dedup = os.path.join(TOOL, "doc2kb_dedup.py")
                p = run([sys.executable, dedup, target, "-b", self.p(lang, "base"), "-n"])
                self.assertIn("dry run" if lang == "en" else "试运行", p.stdout)
                before = read(target)
                run([sys.executable, dedup, target, "-b", self.p(lang, "base")])
                after = read(target)
                self.assertLess(len(after), len(before))
                self.assertIn(core.both("moved_heading")[0 if lang == "en" else 1], after)
                self.assertTrue(os.path.isfile(self.p(lang, "inc", ".doc2kb_watch_fp")))
                self.assertTrue(any(n.startswith("big.md.bak-") for n in os.listdir(self.p(lang, "inc"))))


class ConvertScriptTest(Tmp):
    def convert(self, *files, limit=10, lang="en"):
        out = self.p("conv")
        p = run([sys.executable, os.path.join(SKILL_SCRIPTS, "convert.py"), out, *files,
                 "--lang", lang, "--image-limit", str(limit)])
        with open(os.path.join(out, "convert.json"), encoding="utf-8") as f:
            return p.stdout, json.load(f)

    def test_verdicts_and_placeholders(self):
        f = fx.build_all(self.p("in"), english=True)
        bad = self.p("in", "broken.docx")
        with open(bad, "wb") as fh:
            fh.write(b"not a zip")
        note = self.p("in", "note.txt")
        with open(note, "w", encoding="utf-8") as fh:
            fh.write("plain")
        out, res = self.convert(f["docx"], f["eml"], f["xlsx"], f["legacy"], bad, note)
        verdicts = {os.path.basename(r["file"]): r["verdict"] for r in res["files"]}
        self.assertEqual(verdicts, {"report-en.docx": "converted", "mail-en.eml": "converted",
                                    "book-en.xlsx": "converted", "legacy-en.doc": "as-is",
                                    "broken.docx": "fallback", "note.txt": "as-is"})
        md = read(self.p("conv", "report-en.md"))
        self.assertIn("\n[Image: img_001.png]\n", md)
        self.assertIn("\n[Image: img_002.png]\n", md)
        self.assertNotIn("Source file:", md)      # no converter header
        self.assertTrue(os.path.isfile(self.p("conv", "images", "report-en", "img_001.png")))
        self.assertEqual(res["images"], 3)
        self.assertEqual(res["decision"], "read")
        self.assertIn("images: 3 in 2 converted files, limit 10: read", out)

    def test_ask_over_limit_and_chinese(self):
        f = fx.build_all(self.p("in"))
        _, res = self.convert(f["docx"], f["pptx"], limit=2, lang="zh")
        self.assertEqual(res["decision"], "ask")
        self.assertIn("[图片：img_001.png]", read(self.p("conv", "report-zh.md")))

    def test_mostly_pictures_falls_back(self):
        body = fx._p("x") + "".join(fx._img_p(f"rId{i}") for i in range(1, 5))
        parts = {"word/document.xml": fx._doc(body), "word/styles.xml": fx.STYLES,
                 "word/_rels/document.xml.rels": fx._rels([(f"rId{i}", f"media/i{i}.png") for i in range(1, 5)])}
        for i in range(1, 5):
            parts[f"word/media/i{i}.png"] = fx.png(200, 200, i)
        path = fx._zip(self.p("shots.docx"), parts)
        _, res = self.convert(path)
        self.assertEqual(res["files"][0]["verdict"], "fallback")
        self.assertIn("mostly pictures", res["files"][0]["reason"])
        self.assertEqual(res["images"], 0)       # pictures of fallback files are not counted

    def test_same_names_kept_apart(self):
        f = fx.build_all(self.p("a"), english=True)
        os.makedirs(self.p("b"))
        other = shutil.copy(f["xlsx"], self.p("b", "book-en.xlsx"))
        _, res = self.convert(f["xlsx"], other)
        self.assertEqual([os.path.basename(r["md"]) for r in res["files"]], ["book-en.md", "book-en_2.md"])


class ConfigTest(Tmp):
    def test_convert_validation(self):
        sys.path.insert(0, SKILL_SCRIPTS)
        import kbconf
        self.assertEqual(kbconf.validate({"schema": 1, "convert": {"enabled": True, "image_limit": 5}}), [])
        problems = kbconf.validate({"schema": 1, "convert": {"enabled": "yes", "image_limit": -1, "x": 1}})
        self.assertEqual(len(problems), 3)
        self.assertTrue(kbconf.validate({"schema": 1, "convert": True}))
        p = self.p("lib", "_kb.json")
        os.makedirs(os.path.dirname(p))
        with open(p, "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "convert": {"enabled": True}}, f)
        cfg = kbconf.load_library(p)
        self.assertEqual(cfg["convert"]["image_limit"], 10)
        self.assertTrue(cfg["convert"]["enabled"])
        self.assertFalse(kbconf.DEFAULTS["convert"]["enabled"])

    def test_init_convert_switch(self):
        script = os.path.join(SKILL_SCRIPTS, "init_library.py")
        base = ["--preset", "work", "--language", "en", "--timezone", "UTC", "--scope", "projects"]
        run([sys.executable, script, "write", "--root", self.p("on"), *base])
        self.assertTrue(json.loads(read(self.p("on", "_kb.json")))["convert"]["enabled"])
        p = run([sys.executable, script, "write", "--root", self.p("off"), *base, "--convert", "off"])
        self.assertIn("convert uploads to Markdown: off", p.stdout)
        self.assertFalse(json.loads(read(self.p("off", "_kb.json")))["convert"]["enabled"])

    def test_tool_copy_is_current(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import sync_shared
        copies = sync_shared.copies()
        self.assertEqual(copies["tools/doc2kb/doc2kb_core.py"], "shared/scripts/doc2kb_core.py")
        self.assertEqual(copies["skills/kb-incremental/scripts/doc2kb_core.py"], "shared/scripts/doc2kb_core.py")


@unittest.skipUnless(HAS_BASH, "needs bash")
class ShellTest(Tmp):
    def sh(self, *args, lang="en"):
        return run(["bash", os.path.join(TOOL, "doc2kb.sh"), *args], check=False, env={"DOC2KB_LANG": lang})

    def test_incremental_flow(self):
        src = self.p("src")
        os.remove(fx.build_all(src, english=True)["pdf"])   # needs poppler; a failure would be retried
        out = self.p("out")
        p = self.sh("-s", src, "-o", out)
        self.assertEqual(p.returncode, 3, p.stderr)
        self.assertIn("no watermark", p.stderr)
        p = self.sh("-s", src, "-o", out, "-t", "2000-01-01")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("_incremental.md", p.stdout)
        names = os.listdir(out)
        self.assertTrue(any(n.endswith("_incremental_report.txt") for n in names), names)
        self.assertIn("last_run=", read(os.path.join(out, ".doc2kb_watch_state")))
        p = self.sh("-s", src, "-o", out)          # nothing new since the run above
        self.assertEqual((p.returncode, p.stdout), (0, ""))
        self.assertIn("nothing new", read(os.path.join(out, "_watch.log")))

    def test_chinese_messages_and_dash_options(self):
        p = self.sh("-s", self.p("nowhere"), "-o", self.p("out"), lang="zh")
        self.assertEqual(p.returncode, 1)
        self.assertIn("源目录不存在", p.stderr)
        p = self.sh("—help")
        self.assertEqual(p.returncode, 0)
        self.assertIn("Exit codes", p.stdout)


if __name__ == "__main__":
    unittest.main()
