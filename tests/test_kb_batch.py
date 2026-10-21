"""Tests for knowledge-base batch files: kb_batch.py make (with the doc2kb converter) and split.
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
KB_BATCH = os.path.join(ROOT, "shared", "scripts", "kb_batch.py")
sys.path.insert(0, TESTS)
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
import doc2kb_core as core  # noqa: E402
import kb_batch  # noqa: E402
import doc2kb_fixtures as fx  # noqa: E402

HAS_PDF = shutil.which("pdftotext") is not None


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


class KbBatchTest(Tmp):
    """Knowledge-base batch files (kb_batch.py make) and splitting them back (kb_batch.py split)."""

    def batches(self, *extra, src=None, out=None):
        src = src or self.p("src")
        if not os.path.isdir(src):
            fx.build_all(src, english=True)
        out = out or self.p("out")
        p = run([sys.executable, KB_BATCH, "make", "--batch", src, "-o", out, *extra])
        names = sorted(n for n in os.listdir(out) if re.search(r"_b\d+\.md$", n))
        return p, out, names

    def test_anchors_order_and_header(self):
        p, out, names = self.batches("--tier", "strong")
        self.assertEqual(len(names), 1, names)
        self.assertRegex(names[0], r"^src_\d{8}_b01\.md$")
        text = read(os.path.join(out, names[0]))
        self.assertIn("Batch file %s (1 of 1)" % names[0][:-3], text)
        self.assertIn("Tier: strong  Character limit: 100000", text)
        heads = re.findall(r"^# (S\d+) (\S+)$", text, re.M)
        order = [n for _, n in heads if not n.endswith(".pdf")]
        # oldest document first
        self.assertEqual(order, ["slides-en.pptx", "book-en.xlsx", "mail-en.eml", "report-en.docx"])
        self.assertEqual([s for s, _ in heads], ["S%02d" % i for i in range(1, len(heads) + 1)])
        sid = dict((n, s) for s, n in heads)["report-en.docx"].lower()
        self.assertRegex(text, r"\nThis report covers the pilot\. \^%s-p1\n" % sid)
        self.assertRegex(text, r"\n\| x\\\|y \|[^\n]*\|\n\n\^%s-p\d+\n" % sid)   # table: anchor below
        self.assertRegex(text, r"\n## Project Atlas report\n")                    # heading demoted, no anchor
        self.assertNotRegex(text, r"\[Image[^\n]*\^s\d+-p")                     # placeholders: none
        self.assertNotRegex(text, r"(?m)^>.*\^s\d+-p")
        self.assertFalse(os.path.isdir(os.path.join(out, "images")))
        self.assertIn("batch file 1 of 1: %s, sources:" % names[0], p.stdout)
        self.assertIn("Batch files: 1, tier strong", read(os.path.join(out, "_batch-report.txt")))

    def test_cut_at_headings_and_numbering(self):
        body = "\n\n".join(["# Part A", "a" * 300, "- one\n- two", "# Part B", "b" * 300,
                            "## B.1", "c" * 300, "## B.2", "d" * 300])
        units, over = kb_batch.build_units(
            [{"name": "long.docx", "path": "long.docx", "modified": "", "meta": "> meta\n", "body": body}], 1000)
        self.assertEqual(over, [])
        titles = [u["text"].split("\n", 1)[0] for u in units]
        self.assertEqual(titles[0], "# S01 long.docx · 1/%d" % len(units))
        self.assertGreater(len(units), 1)
        self.assertTrue(units[1]["text"].split("\n")[2:4] == ["", "## Part B"], units[1]["text"][:80])
        anchors = [int(n) for u in units for n in re.findall(r"\^s01-p(\d+)", u["text"])]
        self.assertEqual(anchors, list(range(1, 7)))    # continuous over the parts
        self.assertIn("- one ^s01-p2\n- two ^s01-p3", units[0]["text"])
        self.assertTrue(all(u["chars"] <= 1000 for u in units))
        # no headings: cut between paragraphs
        units, _ = kb_batch.build_units(
            [{"name": "flat.pdf", "meta": "", "body": "\n\n".join(["x" * 400] * 5)}], 1000)
        self.assertGreater(len(units), 2)

    def test_block_over_limit_is_a_batch_of_its_own(self):
        units, over = kb_batch.build_units(
            [{"name": "a.docx", "meta": "", "body": "short"},
             {"name": "b.docx", "meta": "", "body": "y" * 2500},
             {"name": "c.docx", "meta": "", "body": "short too"}], 1000)
        self.assertEqual([u["sid"] for u in over], ["S02"])
        self.assertEqual([[u["sid"] for u in b] for b in kb_batch.pack(units, 1000)],
                         [["S01"], ["S02"], ["S03"]])
        units, _ = kb_batch.build_units([{"name": n, "meta": "", "body": "z" * 300} for n in "abcde"], 1000)
        self.assertEqual([len(b) for b in kb_batch.pack(units, 1000)], [3, 2])

    def test_split_back_matches_the_conversion(self):
        p, out, names = self.batches("--batch-chars", "1000")
        self.assertGreater(len(names), 2)
        split = self.p("split")
        run([sys.executable, KB_BATCH, "split", *[os.path.join(out, n) for n in names], "-o", split])
        single = self.p("single")
        run([sys.executable, CORE, "--batch", self.p("src"), "-o", single, "--no-images"])

        def lines(text):
            return [ln.rstrip() for ln in text.split("\n") if ln.strip() and not ln.startswith("> ")]
        for name in ("report-en", "mail-en", "book-en", "slides-en"):
            got = read(os.path.join(split, name + ".md"))
            self.assertNotRegex(got, r"\^s\d+-p")
            self.assertRegex(got, r"\^p1\n")
            self.assertEqual(lines(kb_batch.strip_anchors(got)), lines(read(os.path.join(single, name + ".md"))), name)
        joined = read(os.path.join(split, "report-en.md"))
        self.assertEqual(joined.count("> Original path:"), 1)
        # a missing part is not written
        first = [n for n in names if "· 1/" in read(os.path.join(out, n))]
        self.assertTrue(first)
        p = run([sys.executable, KB_BATCH, "split", os.path.join(out, first[0]), "-o", self.p("partial")],
                check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("missing", p.stderr)

    def test_names_map(self):
        _, out, names = self.batches()
        with open(self.p("names.json"), "w", encoding="utf-8") as f:
            json.dump({"S01": "first.md", "mail-en.eml": "mail.md"}, f)
        run([sys.executable, KB_BATCH, "split", os.path.join(out, names[0]), "-o", self.p("s"),
                 "--names", self.p("names.json")])
        self.assertIn("first.md", os.listdir(self.p("s")))
        self.assertIn("mail.md", os.listdir(self.p("s")))

    def test_limits(self):
        lib = self.p("lib")
        os.makedirs(lib)
        with open(os.path.join(lib, "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"tier": "strong"}, f)
        self.assertEqual(kb_batch.batch_limit(), (20000, "weak"))
        self.assertEqual(kb_batch.batch_limit(library=lib), (20000, "weak"))  # a library's tier is ignored
        self.assertEqual(kb_batch.batch_limit("strong", library=lib), (100000, "strong"))
        self.assertEqual(kb_batch.batch_limit(chars=5000, library=lib), (5000, "weak"))
        with open(os.path.join(lib, "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"tier": "strong", "batch_chars": 30000}, f)
        self.assertEqual(kb_batch.batch_limit(library=lib), (30000, "weak"))
        for bad in ({"tier": "medium"}, {"chars": 10}):
            with self.assertRaises(ValueError):
                kb_batch.batch_limit(**bad)
        with self.assertRaises(ValueError):
            kb_batch.batch_limit(library=self.p("nowhere"))
        p = run([sys.executable, CORE, "--batch", self.p("x"), "--tier", "weak"], check=False)
        self.assertEqual(p.returncode, 2)                 # the batch options belong to kb_batch.py make
        p = run([sys.executable, KB_BATCH, "make", "-o", self.p("x"), "--batch-chars", "10"], check=False)
        self.assertEqual(p.returncode, 2)
        p, out, names = self.batches("--library", lib)
        self.assertIn("Character limit: 30000", read(os.path.join(out, names[0])))

    def test_same_day_and_fingerprints(self):
        db = self.p("fp.tsv")
        p, out, first = self.batches("--fp-db", db)
        rows = [ln.split("\t") for ln in read(db).splitlines() if ln and not ln.startswith("#")]
        self.assertTrue(rows and all(r[-1] == first[0] for r in rows), rows)
        p, out, names = self.batches("--fp-db", db)       # nothing new: no batch file
        self.assertEqual(names, first)
        p, out, names = self.batches()                    # same day again: a time is added
        self.assertEqual(len(names), 2)
        self.assertRegex(sorted(set(names) - set(first))[0], r"^src_\d{8}-\d{4}_b01\.md$")

    def test_named_files_and_chinese_labels(self):
        made = fx.build_all(self.p("src"), english=False)
        out = self.p("out")
        listed = self.p("list.txt")
        with open(listed, "w", encoding="utf-8") as f:
            f.write(made["docx"] + "\n" + made["eml"] + "\n")
        p = run([sys.executable, KB_BATCH, "make", "--files", listed, "-o", out, "--lang", "zh"])
        names = sorted(n for n in os.listdir(out) if re.search(r"_b\d+\.md$", n))
        self.assertEqual(len(names), 1, os.listdir(out))
        text = read(os.path.join(out, names[0]))
        self.assertIn("档位：weak", text)
        self.assertEqual(len(re.findall(r"^# S\d+ ", text, re.M)), 2)
        self.assertIn("批文件 1/1", p.stdout)


if __name__ == "__main__":
    unittest.main()
