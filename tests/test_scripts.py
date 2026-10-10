"""Unit tests for the kb-incremental scripts. Standard library only: python3 -m unittest discover tests"""
import json
import os
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

    def test_validate_problems(self):
        problems = kbconf.validate({"schema": 2, "metadata": "xml", "bogus": 1,
                                    "partitions": {"max": 5, "topic_start": 2, "fallback": "07"},
                                    "names": {"nope": "x"}, "timezone": "Mars/Base"})
        text = " ".join(problems)
        for word in ("schema", "metadata", "bogus", "fallback", "nope", "Mars/Base"):
            self.assertIn(word, text)

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
        self.assertIn("Log file name: _run-log_dedupe_20261010_120500.txt", out)
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
        self.assertTrue(any(n.startswith("_run-log_dedupe_") for n in arch))
        self.assertTrue(any(n.endswith("_README.txt") for n in arch))
        self.assertTrue(os.path.isfile(os.path.join(self.lib, "Entities", "Self.md")))
        self.assertFalse(os.path.exists(os.path.join(self.lib, "README.txt")))

    def test_deliver_detects_change(self):
        plan = self.p("plan.json")
        run("package.py", "preview", self.out, "--library", self.lib, "--plan", plan)
        time.sleep(0.01)
        write(os.path.join(self.lib, "02_Health_Report_A.md"), "edited meanwhile, longer\n")
        p = run("package.py", "deliver", "--plan", plan, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("target changed after preview", p.stdout)
        self.assertEqual(read(os.path.join(self.lib, "02_Health_Report_A.md")), "edited meanwhile, longer\n")


if __name__ == "__main__":
    unittest.main()
