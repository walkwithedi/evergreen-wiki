"""Tests for skills/kb-query/scripts/answer.py: weak-tier selection of cards and status-card items,
and the check of an answer's quoted sentences. The sample library is the fixture.
Standard library only: python3 -m unittest discover tests"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "kb-query", "scripts")
SAMPLE = os.path.join(ROOT, "examples", "sample-work-kb")
sys.path.insert(0, SCRIPTS)
import answer  # noqa: E402
import kbconf  # noqa: E402

STEERING = "Sources/Atlas steering minutes 2026-03-13"
STATUS = """# Status card
Last updated: 2026-03-14

## Items

1. The pilot ends on 2026-04-27. [[%s#^p2]] ⏳ review: Atlas steering minutes 2026-03-13 has a new version (2026-03-20)
2. Support is capped at 40 hours a week. [[Sources/Atlas pilot plan#^p4]]
""" % STEERING


def cli(*args):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, "answer.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)


class SampleCase(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.lib = os.path.join(self._t.name, "lib")
        shutil.copytree(SAMPLE, self.lib)
        self.cfg = kbconf.load_library(self.lib)

    def tearDown(self):
        self._t.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.lib, name), "w", encoding="utf-8") as f:
            f.write(text)

    def add_entity(self, row):
        path = os.path.join(self.lib, "00_Spec.md")
        with open(path, encoding="utf-8") as f:
            spec = f.read()
        self.write("00_Spec.md", spec.replace("Name | Type | Aliases | Core | Note\nNo entries yet.",
                                              "Name | Type | Aliases | Core | Note\n" + row))


class SelectTest(SampleCase):
    def test_keyword_matches_newest_first(self):
        got = answer.select(self.lib, self.cfg, ["export"])
        self.assertEqual([c["conclusion"] for c in got["cards"]],     # event date 2026-03-20, then source date 2026-03-13
                         ["The data export moves to 2026-03-20 while the test server is replaced.",
                          "The integration lead owns the data export."])
        c = got["cards"][0]
        self.assertEqual((c["link"], c["anchor"], c["topic"]), ("Sources/Atlas weekly status 2026-03-09", "p4", "milestones"))
        self.assertEqual(got["paragraphs"], [])

    def test_same_event_date_newer_source_first(self):
        self.write(os.path.join("Cards", "Atlas weekly status 2026-03-16.md"),
                   "# Cards: [[Sources/Atlas weekly status 2026-03-16]]\n\n"
                   "Source: [[Sources/Atlas weekly status 2026-03-16]] · Document last modified: 2026-03-16 17:00\n\n"
                   "## The data export is on track for 2026-03-20.\n\n"
                   "> the data export is on track for 2026-03-20. [[Sources/Atlas weekly status 2026-03-16#^p4]]\n\n"
                   "- Topic: [[Topics/milestones|milestones]]\n- Date: 2026-03-16 17:00 (event: 2026-03-20)\n")
        got = answer.select(self.lib, self.cfg, ["data export"])
        self.assertEqual([c["date"][:10] for c in got["cards"][:2]], ["2026-03-16", "2026-03-09"])

    def test_aliases_of_table_e_and_topic_names(self):
        self.add_entity("Riverside Clinic | organisation | RC; the clinic |  |")
        got = answer.select(self.lib, self.cfg, ["rc"])
        self.assertEqual(len(got["cards"]), 3)              # the three cards naming Riverside Clinic
        self.assertTrue(all("Riverside Clinic" in c["entities"] for c in got["cards"]))
        got = answer.select(self.lib, self.cfg, ["Milestones"])
        self.assertEqual(sorted(c["topic"] for c in got["cards"]), ["milestones", "milestones"])

    def test_score_order_and_limit(self):
        got = answer.select(self.lib, self.cfg, ["pilot", "two weeks"])
        self.assertEqual(got["cards"][0]["conclusion"], "The pilot is extended by two weeks, to 2026-04-27.")
        self.assertEqual(len(answer.select(self.lib, self.cfg, ["pilot"], limit=2)["cards"]), 2)

    def test_status_card_items_with_review_marks(self):
        self.write("00_Status-Card.md", STATUS)
        got = answer.select(self.lib, self.cfg, ["pilot ends"])
        self.assertEqual(got["status"], [{"item": "1. The pilot ends on 2026-04-27. [[%s#^p2]]" % STEERING,
                                          "review": True}])
        got = answer.select(self.lib, self.cfg, ["40 hours"])
        self.assertEqual([s["review"] for s in got["status"]], [False])

    def test_source_paragraphs_when_no_card_matches(self):
        got = answer.select(self.lib, self.cfg, ["steering meeting"])
        self.assertEqual(got["cards"], [])
        self.assertEqual(got["paragraphs"], [{"link": "Sources/Atlas weekly status 2026-03-09", "anchor": "p5",
                                              "text": "The next steering meeting is on 2026-03-13."}])

    def test_command_line_text(self):
        self.write("00_Status-Card.md", STATUS)
        p = cli("select", self.lib, "pilot ends", "export")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("## Status card", p.stdout)
        self.assertIn("(marked for review: check it against the cards and sources)", p.stdout)
        self.assertIn("> The data export is delayed until 2026-03-20 because the test server is being replaced. "
                      "[[Sources/Atlas weekly status 2026-03-09#^p4]]", p.stdout)
        p = cli("select", self.lib, "nothing-like-this")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Nothing in the library matches", p.stdout)


class CheckTest(SampleCase):
    GOOD = ("Library: Sample Work\n\nThe pilot was extended to 2026-04-27.\n"
            "> The steering group approved extending the pilot by two weeks, to 2026-04-27. [[%s#^p2]]\n" % STEERING)

    def test_quotes_must_be_in_the_linked_paragraph(self):
        self.assertEqual(answer.check(self.lib, self.GOOD), {"checked": 1, "failed": []})
        bad = (self.GOOD
               + "> The steering group approved extending the pilot by three weeks. [[%s#^p2]]\n" % STEERING
               + "> The support budget stays at 40 hours per week for the extra two weeks. [[%s#^p2]]\n" % STEERING
               + "> Anything. [[Sources/nowhere#^p1]]\n")
        got = answer.check(self.lib, bad)
        self.assertEqual(got["checked"], 4)
        self.assertEqual([f["reason"] for f in got["failed"]],
                         ["quote not in the linked paragraph", "quote not in the linked paragraph", "no such source file"])

    def test_command_line(self):
        path = os.path.join(self._t.name, "answer.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.GOOD)
        p = cli("check", self.lib, path)
        self.assertEqual((p.returncode, json.loads(p.stdout)["checked"]), (0, 1))
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.GOOD.replace("two weeks", "2 weeks"))
        p = cli("check", self.lib, path)
        self.assertEqual(p.returncode, 3)
        with open(path, "w", encoding="utf-8") as f:
            f.write("Library: Sample Work\n\nNot recorded in the knowledge base.\n")
        p = cli("check", self.lib, path)
        self.assertEqual((p.returncode, json.loads(p.stdout)), (0, {"checked": 0, "failed": []}))


if __name__ == "__main__":
    unittest.main()
