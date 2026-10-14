"""Unit tests for the kb-incremental scripts. Standard library only: python3 -m unittest discover tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "kb-incremental", "scripts")
sys.path.insert(0, SCRIPTS)
import kbconf  # noqa: E402


def run(script, *args, check=True):
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        raise AssertionError(f"{script} {args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name

    def tearDown(self):
        self._t.cleanup()

    def p(self, *parts):
        return os.path.join(self.d, *parts)


class KbconfTest(Tmp):
    def test_defaults_and_overrides(self):
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 1, "language": "zh", "timezone": "+08:00",
                                                     "names": {"status_card": "00_当前有效状态卡.md", "archive_dir": "归档"}}))
        cfg = kbconf.load_library(self.p("lib"))
        self.assertEqual(cfg["names"]["status_card"], "00_当前有效状态卡.md")
        self.assertEqual(cfg["names"]["status_card_key"], "当前有效状态卡")
        self.assertEqual(cfg["names"]["index"], "01_File-Index.md")
        self.assertEqual(cfg["names"]["archive_dir"], "归档")
        self.assertEqual(cfg["partitions"]["topic_start"], 2)

    def test_sources(self):
        self.assertEqual(kbconf.validate({"schema": 1, "sources": {"keep": True, "max_mb": 0}}), [])
        self.assertEqual(len(kbconf.validate({"schema": 1, "sources": {"keep": "yes", "max_mb": -1, "x": 1}})), 3)
        self.assertEqual(kbconf.resolve_names()["sources_dir"], "Sources")
        self.assertFalse(kbconf.DEFAULTS["sources"]["keep"])
        cfg = kbconf.merge(kbconf.DEFAULTS, {"sources": {"keep": True}})
        self.assertTrue(kbconf.keeps_sources(cfg))
        self.assertFalse(kbconf.keeps_sources(cfg, "gdrive"))
        self.assertFalse(kbconf.keeps_sources(dict(cfg, delivery="zip")))
        self.assertFalse(kbconf.keeps_sources(kbconf.DEFAULTS))

    def test_init_sources_by_preset(self):
        script = "init_library.py"
        base = ["--language", "en", "--timezone", "UTC", "--scope", "x"]
        out = run(script, "write", "--root", self.p("work"), "--preset", "work", *base).stdout
        self.assertIn("keep originals in the library: on", out)
        self.assertTrue(json.loads(read(self.p("work", "_kb.json")))["sources"]["keep"])
        self.assertTrue(os.path.isdir(self.p("work", "Sources")))
        run(script, "write", "--root", self.p("life"), "--preset", "life", *base)
        self.assertFalse(json.loads(read(self.p("life", "_kb.json")))["sources"]["keep"])
        self.assertFalse(os.path.exists(self.p("life", "Sources")))
        run(script, "write", "--root", self.p("life2"), "--preset", "life", *base, "--sources", "on")
        self.assertTrue(json.loads(read(self.p("life2", "_kb.json")))["sources"]["keep"])

    def test_validate_problems(self):
        problems = kbconf.validate({"schema": 2, "metadata": "xml", "bogus": 1,
                                    "partitions": {"max": 5, "topic_start": 2, "fallback": "07"},
                                    "names": {"nope": "x"}, "timezone": "Mars Base"})
        text = " ".join(problems)
        for word in ("schema", "metadata", "bogus", "fallback", "nope", "Mars Base"):
            self.assertIn(word, text)

    def test_timezone_check_is_version_independent(self):
        self.assertEqual(kbconf.check_timezone("Europe/London"), [])
        self.assertEqual(kbconf.check_timezone("+08:00"), [])
        self.assertTrue(kbconf.check_timezone("not a zone!"))

    def test_limits(self):
        self.assertEqual(kbconf.default_limits("zh-CN"), (55, 80))
        self.assertEqual(kbconf.default_limits("en"), (90, 120))

    def test_registry(self):
        reg = {"schema": 1, "libraries": [
            {"id": "life", "label": "Life", "scope": "me", "backend": {"type": "local", "root": "~/kb"}},
            {"id": "life", "label": "Dup", "scope": "", "backend": {"type": "ftp"}}]}
        problems = " ".join(kbconf.check_registry(reg))
        self.assertIn("used twice", problems)
        self.assertIn("gdrive or local", problems)
        self.assertIn("scope", problems)


class CleanTest(Tmp):
    def test_clean(self):
        src = self.p("in.md")
        write(src, "Converted by pandoc 3.1\n# \n\n# Real title\n\nBody one.\n\n\n\n"
                   "## This heading ends with a colon:\n| a |  | b |\n|---|---|---|\n| 1 |  | 2 |\n")
        out = run("clean.py", src, self.p("out.md"), "--max-heading-len", "90").stdout
        self.assertIn("header lines dropped 2", out)
        self.assertIn("empty columns dropped 1", out)
        self.assertIn("headings demoted 1", out)
        text = read(self.p("out.md"))
        self.assertTrue(text.startswith("# Real title"))
        self.assertIn("| a | b |", text)
        self.assertNotIn("\n\n\n", text)


class AssembleTest(Tmp):
    BODY = "# Release review\n\nThe launch moves to May. | a | b |\n\n| 1 | 2 |\n"

    def test_yaml_and_text_heads(self):
        write(self.p("body.md"), "\n" + self.BODY)
        for head in ('---\npartition: "05"\ntopic: "Release"\n---\n\n- Launch in May (source: Release review)\n',
                     "Partition: 05\nTopic: Release\n\n- Launch in May (source: Release review)"):
            with self.subTest(head=head[:12]):
                out = self.p("out", head[:3].strip("-\n") or "yaml", "05_Release_minutes_Review.md")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                write(self.p("head.md"), head)
                line = run("assemble.py", self.p("head.md"), self.p("body.md"), out).stdout.strip()
                self.assertEqual(line, f"assembled: 05_Release_minutes_Review.md | head {head.rstrip().count(chr(10)) + 1}"
                                       f" lines | body {len(self.BODY.strip())} characters")
                text = read(out)
                self.assertEqual(text, head.rstrip("\n") + "\n\n" + self.BODY)
                self.assertTrue(text.endswith(self.BODY))  # the body is copied as it is

    def test_refused(self):
        write(self.p("head.md"), "---\ntopic: \"x\"\n\n- conclusion\n")
        write(self.p("body.md"), "  \n")
        write(self.p("out.md"), "old")
        p = run("assemble.py", self.p("head.md"), self.p("body.md"), self.p("out.md"), check=False)
        self.assertEqual(p.returncode, 3)
        for reason in ("output file exists", "body is empty", "front matter opened with --- is not closed"):
            self.assertIn(reason, p.stdout)
        self.assertEqual(read(self.p("out.md")), "old")
        p = run("assemble.py", self.p("missing.md"), self.p("body.md"), self.p("new.md"), check=False)
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(self.p("new.md")))


class AssembleOriginalTest(Tmp):
    def setUp(self):
        super().setUp()
        write(self.p("body.md"), "Body text.\n")
        with open(self.p("scan.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 original bytes")
        os.makedirs(self.p("out"))

    def assemble(self, head, *extra, out="05_Release_minutes_Review.md"):
        write(self.p("head.md"), head)
        return run("assemble.py", self.p("head.md"), self.p("body.md"), self.p("out", out), *extra, check=False)

    def test_original_copied_and_linked(self):
        p = self.assemble('---\ntopic: "Release"\n---\n\n- Launch in May\n',
                          "--source", self.p("scan.pdf"), "--sources-dir", self.p("out", "Sources"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("| original kept: Sources/05_Release_minutes_Review.pdf", p.stdout)
        with open(self.p("out", "Sources", "05_Release_minutes_Review.pdf"), "rb") as f:
            self.assertEqual(f.read(), b"%PDF-1.4 original bytes")
        text = read(self.p("out", "05_Release_minutes_Review.md"))
        self.assertTrue(text.startswith('---\ntopic: "Release"\noriginal: "[[Sources/05_Release_minutes_Review.pdf]]"\n---\n'))

    def test_text_head_gets_no_link(self):
        p = self.assemble("Topic: Release\n\n- Launch in May",
                          "--source", self.p("scan.pdf"), "--sources-dir", self.p("out", "Sources"))
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("original:", read(self.p("out", "05_Release_minutes_Review.md")))
        self.assertTrue(os.path.isfile(self.p("out", "Sources", "05_Release_minutes_Review.pdf")))

    def test_not_kept(self):
        p = self.assemble('---\ntopic: "x"\n---\n', "--source", self.p("missing.pdf"),
                          "--sources-dir", self.p("out", "Sources"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("original not kept: file not found", p.stdout)
        self.assertNotIn("original:", read(self.p("out", "05_Release_minutes_Review.md")))
        with open(self.p("big.pdf"), "wb") as f:
            f.write(b"x" * (1024 * 1024 + 1))
        p = self.assemble('---\ntopic: "x"\n---\n', "--source", self.p("big.pdf"),
                          "--sources-dir", self.p("out", "Sources"), "--max-mb", "1", out="06_Other.md")
        self.assertIn("original not kept: larger than 1 MB", p.stdout)
        self.assertFalse(os.path.exists(self.p("out", "Sources")))

    def test_existing_copy_refused(self):
        write(self.p("out", "Sources", "05_Release_minutes_Review.pdf"), "old")
        p = self.assemble('---\ntopic: "x"\n---\n', "--source", self.p("scan.pdf"),
                          "--sources-dir", self.p("out", "Sources"))
        self.assertEqual(p.returncode, 3)
        self.assertIn("original copy exists", p.stdout)
        self.assertFalse(os.path.exists(self.p("out", "05_Release_minutes_Review.md")))


class IndexTest(Tmp):
    def setUp(self):
        super().setUp()
        self.idx = self.p("01_File-Index.md")
        write(self.idx, "# File index\n\nEntries: 1\nLast updated: 2026-01-01\n\n"
                        "| File name | Source file name |\n| --- | --- |\n| 02_Health_Report_A.md | a.pdf |\n")
        self.src = self.p("b (2).pdf")
        write(self.src, "content b")

    def test_add_check_write(self):
        run("index_tool.py", "add", self.idx, "--name", "03_Money_Plan_B.md", "--orig", "b (2).pdf", "--file", self.src)
        out = run("index_tool.py", "check", self.idx, "--orig", "b.pdf", "--name", "03_Money_Plan_B.md", "--file", self.src).stdout
        self.assertIn("Content hash: HIT", out)
        self.assertIn("Source name: HIT (hash matches)", out)
        self.assertIn("File name: HIT", out)
        run("index_tool.py", "write", self.idx, "--out", self.p("out.md"), "--date", "2026-10-10")
        text = read(self.p("out.md"))
        self.assertIn("Entries: 2", text)
        self.assertIn("Last updated: 2026-10-10", text)
        self.assertIn("| File name | Source file name | Source hash |", text)
        self.assertIn("| --- | --- | --- |", text)

    def test_add_twice_refused(self):
        p = run("index_tool.py", "add", self.idx, "--name", "02_Health_Report_A.md", "--orig", "x", check=False)
        self.assertEqual(p.returncode, 4)

    def test_chinese_index(self):
        idx = self.p("zh.md")
        write(idx, "条目数：1\n最后更新：2026-01-01\n文件名 ｜ 原始文件名\n02_体检_报告_甲.md ｜ 甲.pdf\n")
        run("index_tool.py", "add", idx, "--name", "02_体检_报告_乙.md", "--orig", "乙.pdf", "--file", self.src)
        run("index_tool.py", "write", idx, "--out", idx, "--date", "2026-10-10")
        text = read(idx)
        self.assertIn("条目数：2", text)
        self.assertIn("文件名 ｜ 原始文件名 ｜ 原文哈希", text)
        self.assertIn("02_体检_报告_乙.md ｜ 乙.pdf ｜ ", text)

    def test_refuses_library_index(self):
        lib = self.p("lib")
        write(os.path.join(lib, "_kb.json"), "{}")
        idx = os.path.join(lib, "01_File-Index.md")
        write(idx, read(self.idx))
        p = run("index_tool.py", "add", idx, "--name", "02_X.md", "--orig", "x", check=False)
        self.assertEqual(p.returncode, 5)
        p = run("index_tool.py", "write", self.idx, "--out", idx, "--date", "2026-10-10", check=False)
        self.assertEqual(p.returncode, 5)
        self.assertEqual(read(idx), read(self.idx))
        run("index_tool.py", "add", idx, "--name", "02_X.md", "--orig", "x", "--in-library")

    def test_empty_index(self):
        idx = self.p("empty.md")
        write(idx, "Entries: 0\nLast updated: 2026-01-01\n\n| File name | Source file name | Source hash |\n| --- | --- | --- |\n")
        self.assertEqual(run("index_tool.py", "write", idx, "--out", idx, "--date", "2026-10-10", check=False).returncode, 4)
        run("index_tool.py", "add", idx, "--name", "02_X_Y_Z.md", "--orig", "z.pdf")
        lines = read(idx).splitlines()
        self.assertEqual(lines[-1], "| 02_X_Y_Z.md | z.pdf |")


class CardCheckTest(Tmp):
    def test_pass_and_fail(self):
        old = self.p("old.md")
        new = self.p("new.md")
        changes = self.p("changes.txt")
        write(old, "# Status card\nLast updated: 2026-01-01\n1. Limit is 10 GB (basis: [[a]])\n2. Owner is Team A (basis: [[b]])\n")
        write(new, "# Status card\nLast updated: 2026-10-10\n1. Limit is 20 GB (basis: [[c]])\n2. Owner is Team A (basis: [[b]])\n")
        write(changes, "")
        p = run("card_check.py", old, new, "--changes", changes, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("1 unexplained losses", p.stdout)
        write(changes, "Item 1: Limit is 10 GB (basis: [[a]]) -> Limit is 20 GB (basis: [[c]])\n")
        p = run("card_check.py", old, new, "--changes", changes)
        self.assertIn("Result: passed", p.stdout)

    def test_locked_fields(self):
        old, new = self.p("o.md"), self.p("n.md")
        write(old, '---\ntype: "entity"\naliases: ["A", "B"]\n---\n# Atlas\ntext\n')
        write(new, '---\ntype: "note"\naliases: ["A"]\n---\n# Atlas2\ntext\n')
        out = run("card_check.py", old, new, check=False).stdout
        self.assertIn("locked field changed: type", out)
        self.assertIn("aliases lost entries", out)
        self.assertIn("level-1 heading changed", out)


class ArchivePlanTest(Tmp):
    def test_plan_and_log(self):
        files = [
            {"id": "1", "title": "02_A.md", "fileSize": 10, "createdTime": "2026-10-01T00:00:00Z", "modifiedTime": "2026-10-01T00:00:00Z", "parentId": "root"},
            {"id": "2", "title": "02_A.md", "fileSize": 12, "createdTime": "2026-10-05T00:00:00Z", "modifiedTime": "2026-10-05T00:00:00Z", "parentId": "root"},
            {"id": "3", "title": "02_B.md", "fileSize": 5, "createdTime": "2026-10-05T00:00:00Z", "modifiedTime": "2026-10-01T00:00:00Z", "parentId": "root"},
            {"id": "4", "title": "02_B.md", "fileSize": 5, "createdTime": "2026-10-01T00:00:00Z", "modifiedTime": "2026-10-05T00:00:00Z", "parentId": "root"},
            {"id": "5", "title": "02_C_old20260101000000.md", "createdTime": "2026-10-01T00:00:00Z", "modifiedTime": "2026-10-01T00:00:00Z", "parentId": "root"},
        ]
        cand = self.p("c.json")
        write(cand, json.dumps(files))
        out = run("archive_plan.py", "--tz", "+08:00", "plan", "--files", cand, "--base-time", "2026-10-10 12:00:00",
                  "--folder-name", "Life", "--scope", "test", "--out", self.p("plan.json")).stdout
        self.assertIn("Older copies to archive: 1", out)
        self.assertIn("02_A_old20261010120000.md", out)
        self.assertIn("Needs a human decision", out)
        write(self.p("r.json"), json.dumps({"1": "ok"}))
        out = run("archive_plan.py", "log", "--plan", self.p("plan.json"), "--results", self.p("r.json"),
                  "--end-time", "2026-10-10 12:05:00", "--out", self.p("log.txt")).stdout
        self.assertIn("Log file name: _run-log_20261010_120500.txt", out)
        self.assertIn("Archived 1, failed 0.", out)


class PackageTest(Tmp):
    def setUp(self):
        super().setUp()
        self.lib = self.p("lib")
        write(os.path.join(self.lib, "_kb.json"), json.dumps({"schema": 1, "label": "Life", "timezone": "UTC"}))
        write(os.path.join(self.lib, "02_Health_Report_A.md"), "old version\n")
        self.out = self.p("out")
        write(os.path.join(self.out, "02_Health_Report_A.md"), "new version\n")
        write(os.path.join(self.out, "02_Health_Report_B.md"), "brand new\n")
        write(os.path.join(self.out, "01_File-Index.md"), "index\n")
        write(os.path.join(self.out, "README.txt"), "readme\n")
        write(os.path.join(self.out, "Entities", "Self.md"), "entity\n")

    def test_zip(self):
        dest = self.p("x.zip")
        run("package.py", "zip", self.out, dest, "--library", self.lib)
        with zipfile.ZipFile(dest) as z:
            self.assertEqual(sorted(z.namelist()), ["01_File-Index.md", "02_Health_Report_A.md",
                                                    "02_Health_Report_B.md", "Entities/Self.md", "README.txt"])

    def test_zip_rejects_bad_output(self):
        write(os.path.join(self.out, "deep", "x.md"), "x\n")
        write(os.path.join(self.out, "02_X_old20260101000000.md"), "x\n")
        p = run("package.py", "zip", self.out, self.p("x.zip"), "--library", self.lib, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("folder not allowed", p.stdout)
        self.assertIn("must not be delivered", p.stdout)

    def test_preview_and_deliver(self):
        plan = self.p("plan.json")
        out = run("package.py", "preview", self.out, "--library", self.lib, "--plan", plan).stdout
        self.assertIn("New versions (old copy goes to Archive/): 1", out)
        self.assertEqual(read(os.path.join(self.lib, "02_Health_Report_A.md")), "old version\n")
        run("package.py", "deliver", "--plan", plan)
        self.assertEqual(read(os.path.join(self.lib, "02_Health_Report_A.md")), "new version\n")
        arch = os.listdir(os.path.join(self.lib, "Archive"))
        self.assertTrue(any(n.startswith("02_Health_Report_A_old") for n in arch))
        self.assertTrue(any(n.startswith("_run-log_") for n in arch))
        self.assertTrue(any(n.endswith("_README.txt") for n in arch))
        self.assertTrue(os.path.isfile(os.path.join(self.lib, "Entities", "Self.md")))
        self.assertFalse(os.path.exists(os.path.join(self.lib, "README.txt")))

    def originals(self):
        """The library keeps originals: A had a .docx original; this run brings A as a .pdf, B new with a
        .xlsx, and a new version of C (pasted text, no original)."""
        src = os.path.join(self.lib, "Sources")
        for name, data in (("02_Health_Report_A.docx", b"old a"), ("02_Health_Report_C.pdf", b"old c"),
                           ("02_Health_Report_D.pdf", b"untouched")):
            os.makedirs(src, exist_ok=True)
            with open(os.path.join(src, name), "wb") as f:
                f.write(data)
        write(os.path.join(self.lib, "02_Health_Report_C.md"), "old c\n")
        write(os.path.join(self.out, "02_Health_Report_C.md"), "new c\n")
        for name, data in (("02_Health_Report_A.pdf", b"%PDF new a"), ("02_Health_Report_B.xlsx", b"PK\x03\x04 b")):
            os.makedirs(os.path.join(self.out, "Sources"), exist_ok=True)
            with open(os.path.join(self.out, "Sources", name), "wb") as f:
                f.write(data)

    def test_originals_delivered_and_old_ones_archived(self):
        self.originals()
        plan = self.p("plan.json")
        out = run("package.py", "preview", self.out, "--library", self.lib, "--plan", plan).stdout
        self.assertIn("+ Sources/02_Health_Report_A.pdf", out)
        self.assertIn("+ Sources/02_Health_Report_B.xlsx", out)
        self.assertIn("~ Sources/02_Health_Report_A.docx  old original, no new copy -> Archive/", out)
        self.assertIn("~ Sources/02_Health_Report_C.pdf  old original, no new copy -> Archive/", out)
        self.assertNotIn("Report_D", out)
        run("package.py", "deliver", "--plan", plan)
        src = os.path.join(self.lib, "Sources")
        self.assertEqual(sorted(os.listdir(src)), ["02_Health_Report_A.pdf", "02_Health_Report_B.xlsx",
                                                   "02_Health_Report_D.pdf"])
        with open(os.path.join(src, "02_Health_Report_A.pdf"), "rb") as f:
            self.assertEqual(f.read(), b"%PDF new a")
        arch = os.listdir(os.path.join(self.lib, "Archive"))
        for stem, ext in (("02_Health_Report_A", ".docx"), ("02_Health_Report_C", ".pdf"), ("02_Health_Report_C", ".md")):
            self.assertTrue(any(n.startswith(stem + "_old") and n.endswith(ext) for n in arch), (stem, ext, arch))

    def test_original_with_the_same_name_is_archived_once(self):
        self.originals()
        with open(os.path.join(self.out, "Sources", "02_Health_Report_C.pdf"), "wb") as f:
            f.write(b"new c")
        plan = self.p("plan.json")
        run("package.py", "preview", self.out, "--library", self.lib, "--plan", plan)
        rels = [i["rel"] for i in json.loads(read(plan))["items"]]
        self.assertEqual(rels.count("Sources/02_Health_Report_C.pdf"), 1)
        run("package.py", "deliver", "--plan", plan)
        with open(os.path.join(self.lib, "Sources", "02_Health_Report_C.pdf"), "rb") as f:
            self.assertEqual(f.read(), b"new c")

    def test_zip_refuses_originals(self):
        self.originals()
        write(os.path.join(self.out, "Sources", "deep", "x.pdf"), "x")
        p = run("package.py", "zip", self.out, self.p("x.zip"), "--library", self.lib, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("delivered only into a local library that keeps originals", p.stdout)
        p = run("package.py", "preview", self.out, "--library", self.lib, "--plan", self.p("plan.json"), check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("Sources/ must not contain folders: deep", p.stdout)

    def test_remote_preview_and_log(self):
        existing = self.p("existing.json")
        write(existing, json.dumps([
            {"rel": "02_Health_Report_A.md", "id": "id-old-2", "modified": "2026-10-02T00:00:00Z"},
            {"rel": "02_Health_Report_A.md", "id": "id-old-1", "modified": "2026-10-01T00:00:00Z"}]))
        plan = self.p("plan.json")
        out = run("package.py", "remote-preview", self.out, "--library", os.path.join(self.lib, "_kb.json"),
                  "--existing", existing, "--plan", plan).stdout
        self.assertIn("(Google Drive)", out)
        self.assertIn("+ 02_Health_Report_B.md", out)
        self.assertIn("+ Entities/Self.md", out)
        p = json.loads(read(plan))
        a = next(i for i in p["items"] if i["rel"] == "02_Health_Report_A.md")
        self.assertEqual([o["id"] for o in a["archive"]], ["id-old-1", "id-old-2"])
        names = [o["archive_as"] for o in a["archive"]]
        self.assertTrue(all(n.startswith("02_Health_Report_A_old") and n.endswith(".md") for n in names))
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(next(i for i in p["items"] if i["rel"] == "Entities/Self.md")["folder"], "entities")
        self.assertNotIn("README.txt", [i["rel"] for i in p["items"]])
        results = self.p("results.json")
        write(results, json.dumps({i["rel"]: "ok" for i in p["items"]}))
        out = run("package.py", "remote-log", "--plan", plan, "--results", results).stdout
        self.assertIn("Written 4, failed 0.", out)
        self.assertIn("Run log file name: _run-log_", out)
        write(results, json.dumps({"02_Health_Report_B.md": "permission denied"}))
        p2 = run("package.py", "remote-log", "--plan", plan, "--results", results, check=False)
        self.assertEqual(p2.returncode, 3)
        self.assertIn("failed  | 02_Health_Report_B.md | permission denied", p2.stdout)

    def test_default_delivery(self):
        self.assertEqual(kbconf.default_delivery({}, "gdrive"), "direct")
        self.assertEqual(kbconf.default_delivery({}, "local"), "direct")
        self.assertEqual(kbconf.default_delivery({"inbox": {"folder": "x"}}, "gdrive"), "zip")
        self.assertEqual(kbconf.default_delivery({"delivery": "zip"}, "local"), "zip")

    def test_deliver_detects_change(self):
        plan = self.p("plan.json")
        run("package.py", "preview", self.out, "--library", self.lib, "--plan", plan)
        time.sleep(0.01)
        write(os.path.join(self.lib, "02_Health_Report_A.md"), "edited meanwhile, longer\n")
        p = run("package.py", "deliver", "--plan", plan, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("target changed after preview", p.stdout)
        self.assertEqual(read(os.path.join(self.lib, "02_Health_Report_A.md")), "edited meanwhile, longer\n")


@unittest.skipIf(os.name == "nt", "fake zenity is a shell script")
class PickMaterialsTest(Tmp):
    """pick_materials.py against a fake zenity that replays scripted answers."""

    def pick(self, answers, display=True, zenity=True, args=None):
        bin_dir = self.p("bin")
        os.makedirs(bin_dir, exist_ok=True)
        # each call takes the next "<exit code> <output>" line and logs its arguments
        write(os.path.join(bin_dir, "zenity"),
              "#!/bin/sh\n"
              'n=$(cat "$ZDIR/n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$ZDIR/n"\n'
              'echo "$*" >> "$ZDIR/calls"\n'
              'line=$(sed -n "${n}p" "$ZDIR/answers")\n'
              'printf \'%b\' "${line#* }"\n'
              'exit "${line%% *}"\n')
        os.chmod(os.path.join(bin_dir, "zenity"), 0o700)
        write(self.p("answers"), "".join(a + "\n" for a in answers))
        # without zenity, PATH holds only an empty folder, so a real zenity on the machine is not found
        path = bin_dir + os.pathsep + "/usr/bin:/bin" if zenity else self.p("empty")
        env = dict(os.environ, ZDIR=self.d, PATH=path)
        env.pop("WAYLAND_DISPLAY", None)
        if display:
            env["DISPLAY"] = ":0"
        else:
            env.pop("DISPLAY", None)
        args = ["--start", self.d] if args is None else args
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "pick_materials.py"),
                            "--timeout", "7", "--language", "zh"] + args,
                           capture_output=True, text=True, encoding="utf-8", env=env)
        calls = read(self.p("calls")).splitlines() if os.path.exists(self.p("calls")) else []
        return p.returncode, p.stdout.splitlines(), calls

    def test_folder(self):
        rc, out, calls = self.pick(["0 folder\\n", "0 " + self.p("in") + "\\n"])
        self.assertEqual((rc, out), (0, [self.p("in")]))
        self.assertIn("--directory", calls[1])
        self.assertIn("--multiple", calls[1])
        self.assertIn("--timeout 7", calls[0])
        self.assertIn("选择要入库的材料", calls[0])

    def test_several_files(self):
        rc, out, calls = self.pick(["0 files\\n", "0 /a b.docx\\n/c.pdf\\n"])
        self.assertEqual((rc, out), (0, ["/a b.docx", "/c.pdf"]))
        self.assertIn("--multiple", calls[1])
        self.assertNotIn("--directory", calls[1])

    def test_cancel_and_timeout(self):
        self.assertEqual(self.pick(["1 "])[0], 4)
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["0 folder\\n", "5 "])[0], 5)

    def test_no_dialog_possible(self):
        self.assertEqual(self.pick([], display=False)[:2], (3, []))
        self.assertEqual(self.pick([], zenity=False)[:2], (3, []))
        self.assertEqual(self.pick([], display=False, args=["--library"])[:2], (3, []))

    def test_library_folder(self):
        rc, out, calls = self.pick(["0 " + self.p("kb") + "\\n"], args=["--library", "--start", self.d])
        self.assertEqual((rc, out), (0, [self.p("kb")]))
        self.assertEqual(len(calls), 1)
        self.assertIn("--directory", calls[0])
        self.assertIn("选择知识库文件夹", calls[0])
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["1 "], args=["--library"])[0], 4)
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["5 "], args=["--library"])[0], 5)

    def test_several_folders_from_home(self):
        lib = self.p("kb")
        os.makedirs(lib + "-待整理")
        rc, out, calls = self.pick(["0 folder\\n", "0 /x\\n/y z\\n"], args=[])
        self.assertEqual((rc, out), (0, ["/x", "/y z"]))
        self.assertIn("--filename " + os.path.expanduser("~") + os.sep, calls[1])  # no folder chosen in advance


class BatchPlanTest(Tmp):
    def setUp(self):
        super().setUp()
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 1, "intake": {"batch_files": 2}}))
        write(self.p("known.docx"), "already filed")
        h = run("index_tool.py", "hash", self.p("known.docx")).stdout.strip()
        write(self.p("lib", "01_File-Index.md"), "| File name | Source file name | Source hash |\n| --- | --- | --- |\n"
                                                 f"| 03_Projects_Report_Old.md | known.docx | {h} |\n")
        write(self.p("lib", "03_Projects_Report_Old.md"), "never material")
        for i in range(3):
            write(self.p("mat", "Alpha", f"a{i}.docx"), f"alpha {i}")
        write(self.p("mat", "Beta", "deep", "b.pdf"), "beta")
        write(self.p("mat", "Beta", "again.docx"), "already filed")
        write(self.p("mat", "Beta", "copy.pdf"), "alpha 0")
        write(self.p("mat", "Beta", "pack.zip"), "zip")
        write(self.p("mat", "Beta", "~$lock.docx"), "lock")
        write(self.p("mat", "loose.txt"), "loose")
        self.plan = self.p("lib", "_intake-batches.json")

    def bp(self, *args, check=True):
        return run("batch_plan.py", *args, "--plan", self.plan, check=check)

    def make_plan(self, *extra):
        return run("batch_plan.py", "plan", self.p("mat"), self.p("lib"), "--plan", self.plan,
                   "--library-root", self.p("lib"), "--index", self.p("lib", "01_File-Index.md"), *extra)

    def test_plan_groups_limits_and_exclusions(self):
        out = self.make_plan().stdout
        self.assertIn("left out, duplicates: 2", out)
        self.assertIn("already in the library as 03_Projects_Report_Old.md", out)
        self.assertIn("same content as mat/Alpha/a0.docx", out)
        self.assertIn("archive: unpack it first", out)
        self.assertNotIn("lock", out)
        self.assertIn("batches: 4", out)
        plan = json.loads(read(self.plan))
        got = [(b["group"], b["part"], [f["rel"] for f in b["files"]]) for b in plan["batches"]]
        self.assertEqual(got, [("mat/Alpha", "1/2", ["mat/Alpha/a0.docx", "mat/Alpha/a1.docx"]),
                               ("mat/Alpha", "2/2", ["mat/Alpha/a2.docx"]),
                               ("mat/Beta", "", ["mat/Beta/deep/b.pdf"]),
                               ("mat/(loose files)", "", ["mat/loose.txt"])])
        self.assertTrue(all(f["kind"] in ("convert", "text") for b in plan["batches"] for f in b["files"]))

    def test_first_and_size_limit(self):
        out = self.make_plan("--first", "Beta", "--batch-files", "5").stdout
        self.assertIn("batch 1: mat/Beta |", out)
        self.assertIn("batch 2: mat/Alpha |", out)

    def test_single_batch_writes_nothing(self):
        out = run("batch_plan.py", "plan", self.p("mat", "Alpha"), "--plan", self.plan, "--batch-files", "10").stdout
        self.assertIn("one batch, no batching needed", out)
        self.assertFalse(os.path.exists(self.plan))

    def test_progress_and_resume(self):
        self.make_plan()
        nxt = self.bp("next").stdout
        self.assertIn("batch: 1/4 | mat/Alpha part 1/2 | 2 files", nxt)
        self.assertIn("file: " + self.p("mat", "Alpha", "a0.docx"), nxt)
        self.bp("done", "--batch", "1", "--written", "2")
        self.bp("skip", "--batch", "2")
        self.bp("add", "--batch", "3", "--kind", "trigger", "--text", "status card item 4: new deadline",
                "--file", "b.pdf")
        self.bp("add", "--batch", "3", "--kind", "review", "--text", "renamed to distinguish")
        p = run("batch_plan.py", "plan", self.p("mat"), "--plan", self.plan, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("a plan with pending batches exists", p.stdout)
        self.assertIn("--append", p.stdout)
        status = self.bp("status").stdout
        self.assertIn("batches: 4 | done 1 | skipped 1 | pending 2", status)
        self.assertIn("next: batch 3 mat/Beta", status)
        self.assertIn("batch 3 [b.pdf]: status card item 4: new deadline", status)
        self.bp("done", "--batch", "3")
        self.bp("done", "--batch", "4")
        self.assertEqual(self.bp("next", check=False).returncode, 1)
        fin = self.bp("finish").stdout
        self.assertIn("renamed to distinguish", fin)
        self.assertIn("final step: done", fin)
        self.assertIn("result: archive the plan", fin)
        self.assertNotIn("renamed to distinguish", self.bp("status").stdout)
        self.assertEqual(run("batch_plan.py", "plan", self.p("mat"), "--plan", self.plan).returncode, 0)

    def test_append_new_sources(self):
        self.make_plan()
        write(self.p("other", "Gamma", "g1.docx"), "gamma 1")
        write(self.p("other", "Gamma", "g2.docx"), "gamma 2")
        write(self.p("other", "Gamma", "dup.docx"), "alpha 1")  # same content as a file in the run
        out = run("batch_plan.py", "plan", self.p("other"), "--plan", self.plan, "--append",
                  "--library-root", self.p("lib")).stdout
        self.assertIn("same content as mat/Alpha/a1.docx", out)
        self.assertIn("1 batches added", out)
        plan = json.loads(read(self.plan))
        self.assertEqual([b["n"] for b in plan["batches"]], [1, 2, 3, 4, 5])
        self.assertEqual(plan["batches"][-1]["group"], "other/Gamma")
        self.assertIn(self.p("other"), plan["sources"])
        write(self.p("third", "t.txt"), "third")
        write(self.p("third", "u.txt"), "third u")
        write(self.p("third", "v.txt"), "third v")
        run("batch_plan.py", "plan", self.p("third"), "--plan", self.plan, "--append", "--front",
            "--library-root", self.p("lib"))
        plan = json.loads(read(self.plan))
        self.assertEqual(plan["batches"][0]["group"], "third/(loose files)")
        self.assertIn("batch: 6/7 | third/(loose files) part 1/2", self.bp("next").stdout)

    def test_interrupted_batch_resumes(self):
        self.make_plan()
        index = self.p("lib", "01_File-Index.md")
        self.assertNotIn("resumed", self.bp("next").stdout)
        status = self.bp("status").stdout
        self.assertIn("interrupted, started", status)
        # a0 was filed before the interruption
        h = run("index_tool.py", "hash", self.p("mat", "Alpha", "a0.docx")).stdout.strip()
        with open(index, "a", encoding="utf-8") as f:
            f.write(f"| 03_Projects_Alpha.md | a0.docx | {h} |\n")
        nxt = run("batch_plan.py", "next", "--plan", self.plan, "--index", index).stdout
        self.assertIn("resumed (interrupted)", nxt)
        self.assertIn("filed: " + self.p("mat", "Alpha", "a0.docx") + " as 03_Projects_Alpha.md", nxt)
        self.assertIn("file: " + self.p("mat", "Alpha", "a1.docx"), nxt)

    def test_missing_batch_and_skip_rest(self):
        self.make_plan()
        shutil.rmtree(self.p("mat", "Alpha"))
        p = self.bp("next", check=False)
        self.assertEqual(p.returncode, 4)
        self.assertIn("missing folder: " + self.p("mat", "Alpha"), p.stdout)
        self.assertNotIn("started", read(self.plan))
        self.bp("skip", "--rest")
        self.assertIn("batches: 4 | done 0 | skipped 4 | pending 0", self.bp("status").stdout)
        self.assertEqual(self.bp("skip", check=False).returncode, 2)

    def test_bad_input(self):
        self.make_plan()
        self.assertEqual(self.bp("done", "--batch", "9", check=False).returncode, 2)
        self.assertEqual(run("batch_plan.py", "plan", self.p("nope"), "--plan", self.p("x.json"), check=False).returncode, 2)
        problems = kbconf.validate({"schema": 1, "intake": {"batch_files": 0, "pages": 3}})
        self.assertIn("intake.batch_files must be a whole number of 1 or more", problems)
        self.assertIn("unknown intake key 'pages'", problems)


class InitLibraryTest(Tmp):
    def test_write_matches_preset(self):
        root = self.p("kb", "life")
        out = run("init_library.py", "write", "--root", root, "--preset", "life", "--language", "zh",
                  "--timezone", "+08:00", "--scope", "我和家人", "--date", "2026-10-10").stdout
        self.assertIn("result: written 8 files and 3 folders", out)
        cfg = kbconf.load_library(root)
        self.assertEqual((cfg["label"], cfg["language"], cfg["timezone"]), ("生活", "zh", "+08:00"))
        self.assertTrue(cfg["sensitivity"]["enabled"])
        self.assertEqual(kbconf.validate(json.loads(read(os.path.join(root, "_kb.json")))), [])
        names = cfg["names"]
        spec = read(os.path.join(root, names["spec"]))
        self.assertIn("Last updated: 2026-10-10", spec)
        self.assertIn("| 55", spec)
        self.assertNotIn("{{", spec)
        for k in kbconf.SUMMARY_KEYS:
            self.assertNotIn("{{", read(os.path.join(root, names[k])))
        self.assertIn("Entries: 0", read(os.path.join(root, names["index"])))
        for d in ("archive_dir", "notes_dir", "entities_dir"):
            self.assertTrue(os.path.isdir(os.path.join(root, names[d])))

    def test_work_preset_follows_language(self):
        for lang, heading, field, index in (("zh", "表 A（Table A）：分区与主题", "entities:", "条目数：0"),
                                            ("en", "Table A: partitions and topics", "entities:", "Entries: 0")):
            root = self.p("kb", "work-" + lang)
            run("init_library.py", "write", "--root", root, "--preset", "work", "--language", lang,
                "--timezone", "UTC", "--scope", "x", "--date", "2026-10-10")
            names = kbconf.load_library(root)["names"]
            spec = read(os.path.join(root, names["spec"]))
            self.assertIn(heading, spec)
            self.assertIn(field, spec)
            self.assertNotIn("systems", spec)
            self.assertNotIn("{{", spec)
            self.assertIn(index, read(os.path.join(root, names["index"])))
            for k in kbconf.SUMMARY_KEYS:
                self.assertNotIn("{{", read(os.path.join(root, names[k])))
            self.assertNotIn("{{", read(os.path.join(root, kbconf.PARAMS_FILE)))

    def test_refuses_existing_library(self):
        root = self.p("lib")
        write(os.path.join(root, "notes.md"), "mine\n")
        p = run("init_library.py", "write", "--root", root, "--preset", "work", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertEqual(os.listdir(root), ["notes.md"])

    def test_render_for_upload(self):
        out = run("init_library.py", "render", "--out", self.p("out"), "--preset", "work", "--language", "en",
                  "--timezone", "UTC").stdout
        self.assertIn("create the folders in the library: Archive, Quick-Notes, Entities", out)
        self.assertEqual(len(os.listdir(self.p("out"))), 8)

    def test_register_and_instructions(self):
        reg = self.p("cfg", "kb-libraries.json")
        run("init_library.py", "register", "--registry", reg, "--id", "life", "--label", "Life",
            "--scope", "me and my family", "--type", "local", "--root", self.p("life"))
        run("init_library.py", "register", "--registry", reg, "--id", "work", "--label", "Work",
            "--scope", "team projects", "--type", "gdrive", "--root", "abc123")
        p = run("init_library.py", "register", "--registry", reg, "--id", "work", "--label", "W",
                "--scope", "x", "--type", "gdrive", "--root", "zzz", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertEqual([lib["id"] for lib in kbconf.load_registry(reg)["libraries"]], ["life", "work"])
        md = self.p("CLAUDE.md")
        write(md, "# My rules\n\nBe brief.\n")
        out = run("init_library.py", "instructions", "--registry", reg, "--file", md).stdout
        self.assertIn("would be added", out)
        self.assertEqual(read(md), "# My rules\n\nBe brief.\n")
        run("init_library.py", "instructions", "--registry", reg, "--file", md, "--apply")
        text = read(md)
        self.assertIn("Be brief.", text)
        self.assertIn("I keep knowledge bases: Life (me and my family); Work (team projects).", text)
        self.assertIn("unfinished batch intake, ask whether to continue it.", text)
        out = run("init_library.py", "instructions", "--registry", reg, "--file", md, "--apply").stdout
        self.assertIn("unchanged", out)
        block = run("init_library.py", "instructions", "--registry", reg, "--project-block").stdout
        self.assertIn("Knowledge base registry (kb-libraries.json):", block)
        self.assertIn('"root": "abc123"', block)

    def test_every_preset_has_defaults(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        presets = sorted(os.listdir(il.PRESETS_DIR))
        self.assertEqual(presets, sorted(il.PRESETS))
        for p in presets:
            self.assertEqual(sorted(il.PRESET_DEFAULTS[p]), sorted(il.LANGUAGES))

    def test_drive_line(self):
        out = run("init_library.py", "instructions", "--drive-folder", "1AbCdEfGhIjKlMnOpQ", "--language", "zh").stdout
        self.assertIn("registry: Google Drive folder 1AbCdEfGhIjKlMnOpQ, file kb-libraries.json", out)
        self.assertTrue(out.startswith("我有知识库"))
        self.assertEqual(run("init_library.py", "instructions", "--drive-folder", "x y", check=False).returncode, 2)
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        text, what = il.upsert_line("a\n我有知识库：生活（x）。\n", il.drive_line("1AbCdEfGhIjKlMnOpQ", "zh"))
        self.assertEqual(what, "updated")
        self.assertEqual(text.count("我有知识库"), 1)

    def test_upsert_line(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        text, what = il.upsert_line("a\n我有知识库：旧（x）。\nb\n", "I keep knowledge bases: New (y).")
        self.assertEqual(what, "updated")
        self.assertEqual(text, "a\nI keep knowledge bases: New (y).\nb\n")
        self.assertEqual(il.upsert_line("", "L")[0], "L\n")


class WizardTest(Tmp):
    def wizard(self, answers):
        env = dict(os.environ, HOME=self.p("home"), USERPROFILE=self.p("home"), APPDATA=self.p("home", "appdata"),
                   XDG_CONFIG_HOME=self.p("home", ".config"), PYTHONIOENCODING="utf-8")
        env.pop("KB_LIBRARIES", None)
        return subprocess.run([sys.executable, os.path.join(ROOT, "install.py"), "--wizard"],
                              input="\n".join(answers) + "\n", capture_output=True, text=True,
                              encoding="utf-8", env=env)

    def registry(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        old = dict(os.environ)
        os.environ.update(HOME=self.p("home"), USERPROFILE=self.p("home"), APPDATA=self.p("home", "appdata"),
                          XDG_CONFIG_HOME=self.p("home", ".config"))
        os.environ.pop("KB_LIBRARIES", None)
        try:
            return kbconf.load_registry(il.registry_path())
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_install_setup_and_second_library(self):
        os.makedirs(self.p("home", ".claude"))
        claude_md = self.p("home", ".claude", "CLAUDE.md")
        write(claude_md, "# Mine\n")
        lib1, lib2 = self.p("home", "kb", "work"), self.p("home", "kb", "work2")
        # language, agent, install, set up, preset, folder, scope, confirm preview, write line
        p = self.wizard(["2", "", "", "", "2", lib1, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for s in ("kb-note", "kb-query", "kb-incremental"):
            self.assertTrue(os.path.isfile(self.p("home", ".claude", "skills", s, "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(lib1, "_kb.json")))
        self.assertIn("I keep knowledge bases: Work (team projects).", read(claude_md))
        # second run: keep the installed skills, a second work library gets a free id
        p = self.wizard(["2", "", "", "n", "", "2", lib2, "", "3", "acme", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("using 'work-2'", p.stdout)
        libs = self.registry()["libraries"]
        self.assertEqual([lib["id"] for lib in libs], ["work", "acme"])
        text = read(claude_md)
        self.assertTrue(text.startswith("# Mine\n"))
        self.assertEqual(text.count("I keep knowledge bases:"), 1)
        self.assertIn("Work (team projects); Work (work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports).", text)

    def test_cancel_writes_nothing(self):
        p = self.wizard(["2", "6", self.p("skills"), "n", "", "1", self.p("lib"), "", "n"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Nothing was written", p.stdout)
        self.assertFalse(os.path.exists(self.p("lib")))
        self.assertFalse(os.path.exists(self.p("skills")))

    def test_no_terminal_needs_options(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, "install.py")], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("--target", p.stderr)


SPEC_EN = """# Spec

2. Table B: term fixes

Original | Fixed | Note
Atlass | Atlas | typo

5. Table E: entities

| Name | Type | Aliases | Core | Note |
| --- | --- | --- | --- | --- |
| Project Atlas | project | Atlas; (PA) | yes | |
| Payments Gateway | system | | no | |

Only names in Table E may be written as links.

6. Table F: value filters

Empty-value forms | Noise values | Maintenance
none; n/a; - | placeholders, generic words such as "system" or "platform" | add new noise

7. Naming
"""


class MetaTest(Tmp):
    def test_name(self):
        out = run("meta.py", "name", "--partition", "05", "--topic", "Primary home", "--type", "report",
                  "--title", "Roof repair: quote/2026", "--language", "en").stdout
        self.assertEqual(out.split(" | ")[0], "05_Primary-home_report_Roof-repair-quote-2026.md")
        p = run("meta.py", "name", "--partition", "05", "--topic", "x", "--type", "y", "--title", "a" * 100,
                "--max-len", "60", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("shorten the short title by 50", p.stdout)
        p = run("meta.py", "name", "--partition", "05", "--topic", "x", "--type", "y", "--title", "///", check=False)
        self.assertEqual(p.returncode, 3)

    def test_entities(self):
        write(self.p("spec.md"), SPEC_EN)
        out = run("meta.py", "entities", self.p("spec.md"),
                  "--field", "entities=Atlas, PA, payments gateway, n/a, system, the vendor (east, west)",
                  "--keywords", "Atlas, settlement").stdout
        self.assertIn("Table E: 2 entities; Table F: 3 empty-value forms, 2 quoted noise values", out)
        self.assertIn("  Atlas -> [[Project Atlas]]", out)
        self.assertIn("  PA -> [[Project Atlas]]", out)  # brackets around an alias are not part of it
        self.assertIn("payments gateway -> no match: decide (entity to register, plain text, or alias); "
                      "possible alias of: Payments Gateway", out)
        self.assertIn("n/a -> dropped (empty-value form in Table F)", out)
        self.assertIn("system -> dropped (noise value in Table F)", out)
        self.assertIn("the vendor (east, west) -> no match", out)  # not split inside brackets
        self.assertIn('  entities: ["[[Project Atlas]]", "payments gateway", "the vendor (east, west)"]', out)
        self.assertIn('  entities_note: "Atlas, PA, payments gateway, n/a, system, the vendor (east, west)"', out)
        self.assertIn('  keywords: ["[[Project Atlas]]", "settlement"]', out)

    def test_entities_presets_and_missing_table(self):
        presets = os.path.join(ROOT, "skills", "kb-incremental", "assets", "presets")
        out = run("meta.py", "entities", os.path.join(presets, "work", "zh", "00_Spec.md"),
                  "--field", "实体=暂无、示例系统").stdout
        self.assertIn("Table E: 0 entities", out)
        self.assertIn("暂无 -> dropped (empty-value form in Table F)", out)
        self.assertIn("示例系统 -> no match", out)
        out = run("meta.py", "entities", os.path.join(ROOT, "examples", "sample-life-kb", "00_Spec.md"),
                  "--field", "organisations=Riverside").stdout
        self.assertIn("Riverside -> [[Riverside Clinic]]", out)
        write(self.p("spec.md"), "# Spec\n\nNo tables here.\n")
        p = run("meta.py", "entities", self.p("spec.md"), "--field", "a=b", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("by hand", p.stdout)

    def test_terms(self):
        write(self.p("spec.md"), SPEC_EN)
        write(self.p("body.md"), "# Notes\n\nAtlass starts in May.\nNothing here.\n")
        out = run("meta.py", "terms", self.p("spec.md"), self.p("body.md")).stdout
        self.assertIn("Atlass -> Atlas: 1 lines", out)
        self.assertIn("  line 3: Atlass starts in May.", out)
        write(self.p("body.md"), "clean\n")
        self.assertIn("Term fixes: none", run("meta.py", "terms", self.p("spec.md"), self.p("body.md")).stdout)

    def test_yaml(self):
        write(self.p("f.json"), json.dumps({"event_date": "2025-10-02", "file_date": "2025-10-06 09:14",
                                            "partition": "02", "topic": 'Say "hi" \\ there',
                                            "people": ["[[Self]]"], "size": None, "source_characters": 1840}))
        self.assertEqual(run("meta.py", "yaml", self.p("f.json")).stdout,
                         '---\nevent_date: 2025-10-02\nfile_date: 2025-10-06T09:14\npartition: "02"\n'
                         'topic: "Say \\"hi\\" \\\\ there"\npeople: ["[[Self]]"]\nsource_characters: 1840\n---\n')
        write(self.p("f.json"), "[1]")
        self.assertEqual(run("meta.py", "yaml", self.p("f.json"), check=False).returncode, 3)

    def test_date(self):
        doc = self.p("a.docx")
        with zipfile.ZipFile(doc, "w") as z:
            z.writestr("docProps/core.xml", '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/'
                       'package/2006/metadata/core-properties" xmlns:dcterms="http://purl.org/dc/terms/">'
                       '<dcterms:modified>2025-03-04T05:06:00Z</dcterms:modified></cp:coreProperties>')
        write(self.p("b.txt"), "x")
        out = run("meta.py", "date", doc, self.p("b.txt"), "--timezone", "+08:00").stdout.splitlines()
        self.assertEqual(out[0], "a.docx | 2025-03-04 13:06 | document metadata | +08:00")
        self.assertIn("file system time, unreliable", out[1])


QUERY = os.path.join(ROOT, "skills", "kb-query", "scripts", "kbfind.py")


def kbfind(*args):
    p = subprocess.run([sys.executable, QUERY, *args], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise AssertionError(f"kbfind {args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.stdout


class KbFindTest(Tmp):
    def setUp(self):
        super().setUp()
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 1, "names": {"old_suffix": "_alt"}}))
        card = ["# Status card", "", "## Payments", ""] + [f"{i}. Item {i} about routine things" for i in range(1, 40)]
        card += ["40. Settlement window moves to 18:00 (basis: [[05_Ops_minutes_Window]])", "    continued line", "",
                 "## Projects", "", "Atlas launches in May; the settlement report follows.", "",
                 "| Item | Owner |", "| --- | --- |", "| Settlement report | Finance |"]
        write(self.p("lib", "00_Status-Card.md"), "\n".join(card) + "\n")
        write(self.p("lib", "05_Ops_minutes_Window.md"), "---\ntopic: \"Settlement\"\n---\n\nBody.\n")
        write(self.p("lib", "05_Ops_minutes_Window_alt20260101120000.md"), "settlement old\n")
        write(self.p("lib", "_intake-batches.json"), "settlement")
        write(self.p("lib", "_note.md"), "settlement")
        write(self.p("lib", "snapshot_card.md"), "settlement")
        write(self.p("lib", "Archive", "x.md"), "settlement")
        write(self.p("lib", "Entities", "Atlas.md"), "# Atlas\n\nSettlement owner.\n")

    def test_find_blocks(self):
        out = kbfind("find", self.p("lib"), "SETTLEMENT")
        self.assertIn("files searched: 2 | files with hits: 2 | blocks: 4", out)
        self.assertIn("-- lines 44-45 | Status card > Payments\n40. Settlement window moves to 18:00", out)
        self.assertIn("continued line", out)
        self.assertIn("| Status card > Projects\nAtlas launches in May", out)
        self.assertIn("| Item | Owner |\n| Settlement report | Finance |", out)  # the header row comes along
        self.assertIn("-- lines 1-3 | (no heading) | front matter", out)
        for skipped in ("old", "Archive", "snapshot", "_note", "Entities"):
            self.assertNotIn(skipped, out.split("\n", 1)[1])
        self.assertNotIn("Item 5 about", out)

    def test_find_options_and_caps(self):
        out = kbfind("find", self.p("lib"), "settlement", "atlas", "--all")
        self.assertIn("blocks: 1", out)
        out = kbfind("find", self.p("lib"), "item", "--file", "Status-Card", "--max-per-file", "3")
        self.assertIn("files searched: 1", out)
        self.assertIn("more blocks in this file", out)
        out = kbfind("find", self.p("lib"), "settlement", "--in", "Entities")
        self.assertIn("== Atlas.md", out)
        self.assertIn("no match", kbfind("find", self.p("lib"), "nothing-like-this"))
        p = subprocess.run([sys.executable, QUERY, "find", self.p("lib"), "x", "--in", "../.."], capture_output=True)
        self.assertEqual(p.returncode, 2)

    def test_toc(self):
        out = kbfind("toc", self.p("lib", "00_Status-Card.md"))
        self.assertIn("1-2 | # Status card", out)
        self.assertIn("3-46 | ## Payments |", out)
        self.assertIn("40 items", out)
        self.assertIn("| ## Projects |", out)
        self.assertIn("2 table rows", out)


class HookTest(unittest.TestCase):
    def test_commit_detection(self):
        sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
        import pre_commit
        for cmd in ("git commit -m x", "cd a && git -C sub commit -qam 'y'", "git -c user.name=t commit",
                    "git add -A && git commit -F msg.txt", "git add x;git commit -m y", "/usr/bin/git --no-pager commit"):
            self.assertTrue(pre_commit.is_commit(cmd), cmd)
        for cmd in ("git status", "git log --grep commit", "echo commit", "git commit-tree abc", "",
                    "git -C commit status", "legit commit"):
            self.assertFalse(pre_commit.is_commit(cmd), cmd)

    def hook(self, name, data):
        return subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", name)],
                              input=json.dumps(data), capture_output=True, text=True, encoding="utf-8")

    def test_shared_copy_edit_blocked(self):
        copy = os.path.join(ROOT, "skills", "kb-query", "references", "config.md")
        p = self.hook("shared_copies.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                          "tool_input": {"file_path": copy}})
        self.assertEqual(p.returncode, 2)
        self.assertIn("shared/references/config.md", p.stderr)
        for path in ("shared/references/config.md", "README.md", "/etc/hosts"):
            p = self.hook("shared_copies.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                              "tool_input": {"file_path": path}})
            self.assertEqual(p.returncode, 0, path)

    def test_commit_message_scan(self):
        with tempfile.TemporaryDirectory() as d:
            msg = os.path.join(d, "MSG")
            write(msg, "Fix it\n\n# real.person@gmail.com in a comment line\nCo-Authored-By: X <noreply@anthropic.com>\n")  # sensitive-scan: ignore
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 0)
            write(msg, "Bump actions\n\nSigned-off-by: dependabot[bot] <support@github.com>\n")
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 0)
            write(msg, "Ask real.person@gmail.com\n")  # sensitive-scan: ignore
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 1)

    def test_other_commands_pass(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", "pre_commit.py")],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


SAMPLE = os.path.join(ROOT, "examples", "sample-life-kb")
PENDING = "<!-- kb:conclusions-pending -->"


class FastIntakeTest(Tmp):
    """prep.py scan and file on a copy of the sample library, then per-item delivery with --run."""

    def setUp(self):
        super().setUp()
        self.lib = self.p("lib")
        shutil.copytree(SAMPLE, self.lib)
        self.work = self.p("work")
        self.mat = self.p("mat")
        write(os.path.join(self.mat, "water.md"), "# Water bill\n\nAmount due 42.10 by 2026-11-01.\n")
        write(os.path.join(self.mat, "gas.txt"), "Gas bill\n\nAmount due 30.00.\n")

    def scan(self, n, name, check=True):
        return run("prep.py", "scan", os.path.join(self.mat, name), "--library", self.lib, "--work", self.work,
                   "--n", str(n), check=check)

    def file(self, n, name, title, *extra, check=True):
        write(os.path.join(self.work, f"head_{n}.md"), f'---\ntitle: "{title}"\n---\n')
        return run("prep.py", "file", "--n", str(n), "--library", self.lib, "--work", self.work,
                   "--partition", "05", "--topic", "Utilities", "--type", "bill", "--title", title,
                   "--orig", name, "--source", os.path.join(self.mat, name), *extra, check=check)

    def deliver(self, n):
        plan = os.path.join(self.work, f"plan_{n}.json")
        run("package.py", "preview", os.path.join(self.work, f"out_{n}"), "--library", self.lib, "--plan", plan,
            "--run", os.path.join(self.work, "run.json"))
        run("package.py", "deliver", "--plan", plan)

    def test_scan_card(self):
        out = self.scan(1, "water.md").stdout
        self.assertIn("Content hash: no hit", out)
        self.assertIn("line 1: Water bill", out)
        self.assertIn("date:", out)
        self.assertTrue(os.path.isfile(os.path.join(self.work, "body_1.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.work, "01_File-Index.md")))

    def test_file_queue_and_mark(self):
        self.scan(1, "water.md")
        out = self.file(1, "water.md", "Water-2026-10", "--close-read").stdout
        self.assertIn("queued: 05_Utilities_bill_Water-2026-10.md (close-read", out)
        topic = read(os.path.join(self.work, "out_1", "05_Utilities_bill_Water-2026-10.md"))
        self.assertIn(PENDING, topic)
        self.assertTrue(topic.rstrip().endswith("Amount due 42.10 by 2026-11-01."))
        queue = read(os.path.join(self.work, "out_1", "_Consolidation-Queue.md"))
        self.assertIn("| 05_Utilities_bill_Water-2026-10.md | water.md |", queue)
        self.assertIn("| yes |", queue)
        self.assertIn("water.md", read(os.path.join(self.work, "out_1", "01_File-Index.md")))
        self.scan(2, "gas.txt")
        self.file(2, "gas.txt", "Gas-2026-10")
        self.assertNotIn(PENDING, read(os.path.join(self.work, "out_2", "05_Utilities_bill_Gas-2026-10.md")))
        self.assertIn("| no |", read(os.path.join(self.work, "_Consolidation-Queue.md")))

    def test_name_hit_needs_a_decision(self):
        self.scan(1, "water.md")
        self.file(1, "water.md", "Water")
        self.scan(2, "gas.txt")
        p = self.file(2, "gas.txt", "Water", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("File name: HIT", p.stdout)
        out = self.file(2, "gas.txt", "Water", "--same-version").stdout
        self.assertIn("Updated", out)
        p = self.file(3, "gas.txt", "Other", "--same-version", check=False)
        self.assertEqual(p.returncode, 2)  # no scan for item 3: no body file

    def test_duplicate_upload_stops(self):
        self.scan(1, "water.md")
        self.file(1, "water.md", "Water")
        self.deliver(1)
        shutil.rmtree(self.work)
        p = self.scan(2, "water.md", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("duplicate upload by content hash", p.stdout)

    def test_run_archives_index_once(self):
        for n, (name, title) in enumerate((("water.md", "Water"), ("gas.txt", "Gas")), 1):
            self.scan(n, name)
            self.file(n, name, title)
            self.deliver(n)
        arch = sorted(os.listdir(os.path.join(self.lib, "Archive")))
        self.assertEqual(len([a for a in arch if a.startswith("01_File-Index_old")]), 1)
        self.assertFalse([a for a in arch if a.startswith("_Consolidation-Queue")])
        self.assertEqual(len([a for a in arch if a.startswith("_run-log_")]), 1)
        self.assertEqual(len([a for a in arch if a.endswith("_README.txt")]), 1)
        index = read(os.path.join(self.lib, "01_File-Index.md"))
        self.assertIn("water.md", index)
        self.assertIn("gas.txt", index)
        self.assertEqual(read(os.path.join(self.lib, "_Consolidation-Queue.md")).count("| 05_Utilities_bill_"), 2)
        log = [a for a in arch if a.startswith("_run-log_")][0]
        self.assertIn("archived earlier in this run", read(os.path.join(self.lib, "Archive", log)))

    def test_without_run_every_delivery_archives(self):
        self.scan(1, "water.md")
        self.file(1, "water.md", "Water")
        plan = self.p("plan.json")
        run("package.py", "preview", os.path.join(self.work, "out_1"), "--library", self.lib, "--plan", plan)
        run("package.py", "deliver", "--plan", plan)
        self.assertTrue(any(a.startswith("01_File-Index_old") for a in os.listdir(os.path.join(self.lib, "Archive"))))


class ConsolidateTest(Tmp):
    def setUp(self):
        super().setUp()
        self.topic = self.p("lib", "05_X_bill_A.md")
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 1}))
        write(self.topic, '---\ntitle: "A"\noriginal: "[[Sources/05_X_bill_A.pdf]]"\n---\n\n' + PENDING +
              "\n\nBody line one.\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n")
        self.head = self.p("head.md")
        write(self.head, '---\ntitle: "A"\noriginal: "[[Sources/05_X_bill_A.pdf]]"\n---\n\nKey conclusions\n- one\n')
        queue = "# Consolidation queue\n\n| File | Source file | Filed | Close-read |\n| --- | --- | --- | --- |\n"
        queue += "| b.md | b.txt | 2026-10-02 10:00 | no |\n| a.md | a.txt | 2026-10-01 10:00 | yes |\n"
        write(self.p("work", "_Consolidation-Queue.md"), queue)
        write(self.p("lib", "_Consolidation-Queue.md"), queue)

    def test_fill_keeps_body(self):
        out = self.p("out", "05_X_bill_A.md")
        os.makedirs(self.p("out"))
        self.assertIn("body unchanged", run("consolidate.py", "fill", self.topic, self.head, out).stdout)
        text = read(out)
        self.assertNotIn(PENDING, text)
        self.assertIn("Key conclusions\n- one\n\nBody line one.", text)
        self.assertTrue(text.endswith("| 1 | 2 |\n"))
        p = run("consolidate.py", "fill", self.topic, self.head, out, check=False)
        self.assertEqual(p.returncode, 3)  # output exists

    def test_fill_refusals(self):
        os.makedirs(self.p("out"))
        write(self.p("nomark.md"), "---\ntitle: x\n---\n\nbody\n")
        p = run("consolidate.py", "fill", self.p("nomark.md"), self.head, self.p("out", "a.md"), check=False)
        self.assertIn("no pending mark", p.stdout)
        write(self.p("h2.md"), '---\ntitle: "A"\n---\n\nKey conclusions\n')
        p = run("consolidate.py", "fill", self.topic, self.p("h2.md"), self.p("out", "b.md"), check=False)
        self.assertIn("original line", p.stdout)
        write(self.p("h3.md"), "---\ntitle: A\n" + PENDING + "\n")
        p = run("consolidate.py", "fill", self.topic, self.p("h3.md"), self.p("out", "c.md"), check=False)
        self.assertEqual(p.returncode, 3)
        self.assertFalse(os.listdir(self.p("out")))

    def test_list_and_done(self):
        out = run("consolidate.py", "list", self.p("work", "_Consolidation-Queue.md"), "--limit", "1").stdout
        self.assertIn("queue: 2 files, oldest filed 2026-10-01 10:00", out)
        self.assertIn("a.md | a.txt | 2026-10-01 10:00 | close-read", out)
        self.assertNotIn("b.md |", out)
        out = run("consolidate.py", "done", self.p("work", "_Consolidation-Queue.md"), "--name", "a.md",
                  "--name", "zz.md").stdout
        self.assertIn("not in the queue: zz.md", out)
        self.assertIn("1 files still wait", out)
        self.assertNotIn("| a.md |", read(self.p("work", "_Consolidation-Queue.md")))
        p = run("consolidate.py", "done", self.p("lib", "_Consolidation-Queue.md"), "--name", "a.md", check=False)
        self.assertEqual(p.returncode, 3)


class IntakeSettingsTest(Tmp):
    def test_mode_defaults_to_fast(self):
        write(self.p("_kb.json"), json.dumps({"schema": 1}))
        cfg = kbconf.load_library(self.d)
        self.assertEqual(cfg["intake"]["mode"], "fast")
        self.assertEqual(cfg["intake"]["consolidate_files"], 10)
        self.assertEqual(cfg["names"]["consolidation_queue"], "_Consolidation-Queue.md")
        self.assertEqual(kbconf.validate({"schema": 1, "intake": {"mode": "full"}}), [])
        self.assertTrue(kbconf.validate({"schema": 1, "intake": {"mode": "slow"}}))


if __name__ == "__main__":
    unittest.main()
