"""Tests for shared/scripts/kbindex.py: the library index follows the files. Standard library only."""
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "shared", "scripts")
sys.path.insert(0, SCRIPTS)
import kbconf  # noqa: E402
import kbindex  # noqa: E402

SAMPLE = os.path.join(ROOT, "examples", "sample-work-kb")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lib = os.path.join(self.tmp, "lib")
        shutil.copytree(SAMPLE, self.lib)
        self.cfg = kbconf.load_library(self.lib)

    def test_follows_the_files(self):
        ix = kbindex.open_index(self.lib, self.cfg)
        self.addCleanup(ix.close)
        self.assertEqual(ix.stats()["sources"], 3)
        self.assertEqual(ix.source_paths()["Atlas pilot plan.md"], ["Plans/Atlas pilot plan.md"])
        self.assertEqual(ix.refresh(), {"added": 0, "changed": 0, "removed": 0})
        write(os.path.join(self.lib, "Sources", "New", "memo.md"), "> Original path: New/memo.docx\n\nA memo line here. ^p1\n")
        os.remove(os.path.join(self.lib, "Cards", "Plans", "Atlas pilot plan.md"))
        self.assertEqual(ix.refresh(), {"added": 1, "changed": 0, "removed": 1})
        self.assertEqual(ix.stats()["carded"], 2)
        self.assertEqual([p for p, _ in ix.uncarded()], ["Plans/Atlas pilot plan.md", "New/memo.md"])  # newest first
        self.assertEqual(ix.find_paragraphs(["memo line"]), [{"source": "New/memo.md", "anchor": "p1",
                                                               "text": "A memo line here."}])

    def test_fingerprint_ignores_notes_anchors_and_spacing(self):
        a = "> Original path: a/x.docx\n> Extracted: 2026-01-01\n\nThe pilot starts. ^p1\n\nNext  line. ^p2\n"
        b = "> Original path: b/y.docx\n\nThe pilot starts.\n\nNext line. ^s01-p2\n"
        self.assertEqual(kbindex.fingerprint(a), kbindex.fingerprint(b))
        self.assertNotEqual(kbindex.fingerprint(a), kbindex.fingerprint(a.replace("starts", "ends")))

    def test_deleted_or_damaged_index_is_made_again(self):
        kbindex.open_index(self.lib, self.cfg).close()
        path = os.path.join(self.lib, kbindex.INDEX_DIR, kbindex.INDEX_FILE)
        with open(path, "wb") as f:
            f.write(b"not a database")
        for suffix in ("-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
        ix = kbindex.open_index(self.lib, self.cfg)
        self.addCleanup(ix.close)
        self.assertEqual((ix.path, ix.stats()["sources"]), (path, 3))

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root writes anywhere")
    def test_read_only_library_gets_an_index_in_memory(self):
        os.chmod(self.lib, stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(os.chmod, self.lib, stat.S_IRWXU)
        ix = kbindex.open_index(self.lib, self.cfg)
        self.addCleanup(ix.close)
        self.assertEqual((ix.path, ix.stats()["sources"]), (":memory:", 3))

    def zh_library(self):
        write(os.path.join(self.lib, "Sources", "Notes", "试点纪要.md"),
              "> Original path: Notes/试点纪要.docx\n> Document last modified: 2026-03-20 10:00\n\n"
              "领导小组同意试点延期两周。 ^p1\n\n预算由示例科技承担。 ^p2\n\n下次会议在周五。 ^p3\n\n"
              "试点在A区进度正常。 ^p4\n")
        write(os.path.join(self.lib, "Sources", "Notes", "旧纪要.md"),
              "> Original path: Notes/旧纪要.docx\n> Document last modified: 2020-01-10 10:00\n\n"
              "试点延期的建议被搁置。 ^p1\n")
        spec = os.path.join(self.lib, "00_Spec.md")
        with open(spec, encoding="utf-8") as f:
            text = f.read()
        write(spec, text.replace("No entries yet.", "示例科技 | organisation | Example Tech; ET | yes |"))
        ix = kbindex.open_index(self.lib, self.cfg)
        self.addCleanup(ix.close)
        return ix

    def test_tokens_split_cjk_into_pairs(self):
        self.assertEqual(kbindex.tokens("试点延期 Pilot-2026 区"), ["试点", "点延", "延期", "pilot", "2026", "区"])
        self.assertEqual(kbindex.phrase("延期"), '"延期"')
        self.assertEqual(kbindex.phrase("steering gr"), '"steering gr"*')
        self.assertEqual(kbindex.phrase("区"), "")            # a single CJK character: LIKE
        self.assertEqual(kbindex.phrase("!!"), "")
        self.assertEqual(kbindex.parse_query('试点 "steering group" “下次 会议” 试点'),
                         ["试点", "steering group", "下次 会议"])

    def test_search_two_character_words_phrases_and_aliases(self):
        ix = self.zh_library()
        self.assertTrue(ix.stats()["full_text"])
        got = ix.search("延期")
        self.assertEqual([(r["source"], r["anchor"]) for r in got["results"]],
                         [("Notes/试点纪要.md", "p1"), ("Notes/旧纪要.md", "p1")])     # the newer document first
        self.assertEqual(got["results"][0]["link"], "Sources/Notes/试点纪要")
        self.assertFalse(got["results"][0]["carded"])
        self.assertEqual([r["anchor"] for r in ix.search("试点 两周")["results"]], ["p1"])   # every word must match
        self.assertEqual(ix.search("两周 预算")["results"], [])
        self.assertEqual([r["anchor"] for r in ix.search('"下次会议"')["results"]], ["p3"])
        self.assertEqual([r["anchor"] for r in ix.search("A区")["results"]], ["p4"])      # single CJK character: LIKE
        ents = kbindex.library_entities(self.lib, self.cfg)
        got = ix.search("ET", ents)
        self.assertEqual(got["keywords"], [["ET", "示例科技", "Example Tech"]])
        self.assertEqual([r["anchor"] for r in got["results"]], ["p2"])
        # cards and paragraphs together: a card comes first, and its own paragraph is not listed again
        got = ix.search('"steering group"')["results"]
        self.assertEqual((got[0]["kind"], got[0]["source"], got[0]["anchor"]),
                         ("card", "Meetings/Atlas steering minutes 2026-03-13.md", "p2"))
        self.assertNotIn(("paragraph", got[0]["link"], "p2"), [(r["kind"], r["link"], r["anchor"]) for r in got])

    def test_search_relaxes_to_some_keywords_and_finds_topic_cards(self):
        ix = self.zh_library()
        got = ix.search(keywords=["试点", "A区"])                       # a full-text group with a LIKE group
        self.assertEqual([(r["anchor"], r["partial"]) for r in got["results"]], [("p4", False)])
        got = ix.search(keywords=["延期", "不存在的词"], relax=5)
        self.assertEqual({r["source"] for r in got["results"]}, {"Notes/试点纪要.md", "Notes/旧纪要.md"})
        self.assertTrue(all(r["partial"] for r in got["results"]))
        self.assertEqual(ix.search(keywords=["延期", "不存在的词"])["results"], [])   # without relax: every keyword
        got = ix.search(keywords=["试点", "两周"], relax=5)                # one holds both, the rest follow
        self.assertEqual((got["results"][0]["anchor"], got["results"][0]["partial"]), ("p1", False))
        self.assertTrue(all(r["partial"] for r in got["results"][1:]))
        topic = [r for r in ix.search(keywords=["milestones"])["results"] if r["kind"] == "card"]
        self.assertEqual({r["topic"] for r in topic}, {"milestones"})

    def test_search_without_full_text(self):
        old = kbindex.USE_FULL_TEXT
        kbindex.USE_FULL_TEXT = False
        self.addCleanup(setattr, kbindex, "USE_FULL_TEXT", old)
        ix = kbindex.Index(self.lib, self.cfg, memory=True)
        self.addCleanup(ix.close)
        ix.refresh()
        self.assertFalse(ix.stats()["full_text"])
        self.assertEqual([r["anchor"] for r in ix.search("next steering")["results"]], ["p5"])

    def test_context(self):
        ix = self.zh_library()
        self.assertEqual([(c["anchor"], c["hit"]) for c in ix.context("Notes/试点纪要.md", "p2", 1)],
                         [("p1", False), ("p2", True), ("p3", False)])
        self.assertEqual(ix.context("Notes/试点纪要.md", "p9"), [])

    def test_index_of_an_earlier_version_is_made_again(self):
        path = os.path.join(self.lib, kbindex.INDEX_DIR, kbindex.INDEX_FILE)
        os.makedirs(os.path.dirname(path))
        db = sqlite3.connect(path)
        db.executescript("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT); INSERT INTO meta VALUES ('version', '1');")
        db.commit()
        db.close()
        ix = kbindex.open_index(self.lib, self.cfg)
        self.addCleanup(ix.close)
        self.assertEqual(ix.stats()["sources"], 3)
        self.assertTrue(ix.search("pilot")["results"])

    def test_command_line(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "kbindex.py"), "stats", self.lib],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["sources"], 3)
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "kbindex.py"), "search", self.lib, "steering meeting"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Status reports/Atlas weekly status 2026-03-09.md#^p5", p.stdout)


if __name__ == "__main__":
    unittest.main()
