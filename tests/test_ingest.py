"""Tests for the 2.0 intake scripts: kbconf's 2.0 settings and topics, and shared/scripts/ingest.py.
Standard library only: python3 -m unittest discover tests"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "shared", "scripts")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPTS)
import doc2kb_fixtures as fx  # noqa: E402
import kb_batch  # noqa: E402
import kbconf  # noqa: E402
import quote_check  # noqa: E402
import ingest  # noqa: E402


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name

    def tearDown(self):
        self._t.cleanup()

    def p(self, *parts):
        return os.path.join(self.d, *parts)


class SettingsTest(unittest.TestCase):
    def test_new_settings_are_known_and_checked(self):
        good = {"schema": 1, "tier": "strong", "batch_chars": 50000, "quote_min": 4, "quote_max": 200}
        self.assertEqual(kbconf.validate(good), [])
        bad = {"schema": 1, "tier": "medium", "batch_chars": 999, "quote_min": 0, "quote_max": 3}
        text = " ".join(kbconf.validate(bad))
        for word in ("tier", "batch_chars", "quote_min"):
            self.assertIn(word, text)
        self.assertIn("quote_max", " ".join(kbconf.validate({"schema": 1, "quote_min": 10, "quote_max": 5})))
        self.assertEqual(len(kbconf.validate({"schema": 1, "batch_chars": True})), 1)

    def test_new_folder_names(self):
        names = kbconf.resolve_names()
        self.assertEqual((names["cards_dir"], names["topics_dir"]), ("Cards", "Topics"))
        self.assertEqual(kbconf.resolve_names({"topics_dir": "主题"})["topics_dir"], "主题")


SPEC = """00_Spec

1. Table A: partitions and topics

00 Spec and status card: fixed files only (the spec and the status card).
01 Indexes and logs: fixed files only (file index, open decisions, change log, glossary).
02 Goals and plans: annual and phase goals; work plans; budgets and funding.
03 Projects and tasks: project plans; Progress and weekly reports.

2. Table B: term fixes
"""
SPEC_ZH = """1. 表A：分区与主题

00 规范与状态卡：固定文件。
02 目标与计划：年度目标；工作计划；预算与经费。
"""


class TopicsTest(unittest.TestCase):
    def test_topics_from_table_a(self):
        cfg = kbconf.merge(kbconf.DEFAULTS, {})
        self.assertEqual(kbconf.topics(SPEC, cfg), ["annual and phase goals", "work plans", "budgets and funding",
                                                    "project plans", "Progress and weekly reports"])
        self.assertEqual(kbconf.topics(SPEC_ZH, cfg), ["年度目标", "工作计划", "预算与经费"])
        self.assertEqual(kbconf.topics("no tables here", cfg), [])

    def test_topic_matching_ignores_case_and_space(self):
        known = kbconf.topics(SPEC, kbconf.merge(kbconf.DEFAULTS, {}))
        self.assertEqual(kbconf.match_topic("Work  Plans", known), "work plans")
        self.assertEqual(kbconf.match_topic("progress and weekly reports", known), "Progress and weekly reports")
        self.assertIsNone(kbconf.match_topic("Risks", known))



def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def make_run(folder, sources, limit=20000):
    """Batch files for sources (name, path, modified, body); returns their paths."""
    units, _ = kb_batch.build_units([{"name": n, "path": p, "modified": m, "meta": "> Original path: %s\n" % p,
                                      "body": b} for n, p, m, b in sources], limit)
    os.makedirs(folder, exist_ok=True)
    paths = []
    batches = kb_batch.pack(units, limit)
    for i, b in enumerate(batches, 1):
        path = os.path.join(folder, "run_b%02d.md" % i)
        with open(path, "w", encoding="utf-8") as f:
            f.write(kb_batch.render(b, i, len(batches), "run_b%02d" % i, "weak", limit))
        paths.append(path)
    return paths


def accepted(batches, *cards):
    table, by_sid = quote_check.load_batches(batches)
    acc, rep = quote_check.check([json.dumps(c, ensure_ascii=False) for c in cards], table, by_sid)
    assert not rep["rejected"], rep["rejected"]
    return acc


PLAN_V1 = "The pilot starts in April.\n\nRiverside Clinic hosts the pilot."
PLAN_V2 = "The pilot starts in May.\n\nRiverside Clinic hosts the pilot."
MINUTES = "Budget stays as planned.\n\n- Next review on Friday"


def card(source, anchor, quote, conclusion, topic, **kw):
    return dict(source=source, anchor=anchor, quote=quote, conclusion=conclusion, topic=topic, entities=[], **kw)


class LibraryCase(Tmp):
    def setUp(self):
        super().setUp()
        self.cfg = kbconf.merge(kbconf.DEFAULTS, {})
        self.cfg["names"] = kbconf.resolve_names()

    def first_run(self):
        b = make_run(self.p("run1"), [("plan.docx", "Atlas/plan.docx", "2026-03-01 09:00", PLAN_V1),
                                      ("minutes.docx", "Atlas/minutes.docx", "2026-03-02 10:00", MINUTES)])
        cards = accepted(b, card("S01", "p1", "The pilot starts in April.", "Pilot starts in April", "Pilot"),
                         card("S01", "p2", "Riverside Clinic hosts the pilot.", "Riverside hosts", "Pilot",
                              event_date="2026-02-20"),
                         card("S02", "p1", "Budget stays as planned.", "Budget unchanged", "Budget"))
        return ingest.file_run(b, cards, self.p("lib"), self.cfg)


class FileTest(LibraryCase):
    def test_first_run_files_sources_and_cards(self):
        rec = self.first_run()
        src = read(self.p("lib", "Sources", "plan.md"))
        self.assertIn("The pilot starts in April. ^p1", src)
        self.assertIn("> Original path: Atlas/plan.docx", src)
        cards = read(self.p("lib", "Cards", "plan.md"))
        self.assertIn("[[Sources/plan#^p2]]", cards)
        self.assertIn("[[Topics/Pilot|Pilot]]", cards)
        self.assertEqual(sorted(rec["sources"]), ["minutes.md", "plan.md"])
        self.assertEqual(rec["archived"], [])
        self.assertEqual(rec["topics"], ["Budget", "Pilot"])

    def test_same_name_in_one_run_gets_its_folder(self):
        b = make_run(self.p("run"), [("plan.docx", "Atlas/plan.docx", "", PLAN_V1),
                                     ("plan.docx", "Beacon/plan.docx", "", MINUTES)])
        rec = ingest.file_run(b, [], self.p("lib"), self.cfg)
        self.assertEqual(sorted(rec["sources"]), ["Atlas_plan.md", "Beacon_plan.md"])
        self.assertIn("Budget stays", read(self.p("lib", "Sources", "Beacon_plan.md")))

    def test_new_version_archives_source_and_cards(self):
        self.first_run()
        b = make_run(self.p("run2"), [("plan.docx", "Atlas/plan.docx", "2026-04-01 09:00", PLAN_V2)])
        cards = accepted(b, card("S01", "p1", "The pilot starts in May.", "Pilot moves to May", "Schedule"))
        rec = ingest.file_run(b, cards, self.p("lib"), self.cfg)
        self.assertIn("starts in May", read(self.p("lib", "Sources", "plan.md")))
        old = sorted(os.listdir(self.p("lib", "Archive", "Sources")))
        self.assertEqual(len(old), 1)
        self.assertRegex(old[0], r"^plan_old\d{14}\.md$")
        self.assertIn("starts in April", read(self.p("lib", "Archive", "Sources", old[0])))
        self.assertEqual(os.listdir(self.p("lib", "Archive", "Cards")), old)
        self.assertNotIn("April", read(self.p("lib", "Cards", "plan.md")))
        self.assertEqual(rec["archived"], ["Sources/plan.md", "Cards/plan.md"])
        self.assertEqual(rec["topics"], ["Pilot", "Schedule"])         # the old cards' topics too
        self.assertTrue(os.path.isfile(self.p("lib", "Cards", "minutes.md")))

    def test_missing_part_refused(self):
        b = make_run(self.p("run"), [("long.docx", "long.docx", "", "\n\n".join(["x" * 600] * 4))], limit=1000)
        self.assertGreater(len(b), 1)
        with self.assertRaises(ValueError):
            ingest.file_run(b[:1], [], self.p("lib"), self.cfg)
        self.assertFalse(os.path.exists(self.p("lib", "Sources")))



class PagesTest(LibraryCase):
    def test_page_newest_first(self):
        self.first_run()
        written = ingest.pages_run(self.p("lib"), self.cfg)
        self.assertEqual(sorted(os.path.basename(p) for p in written), ["Budget.md", "Pilot.md"])
        page = read(self.p("lib", "Topics", "Pilot.md"))
        self.assertTrue(page.startswith("# Pilot\n"))
        self.assertIn("generated from the cards", page)
        # event date 2026-02-20 comes after the source date 2026-03-01
        self.assertLess(page.index("Pilot starts in April"), page.index("Riverside hosts"))
        self.assertIn("- 2026-03-01 · Pilot starts in April", page)
        self.assertIn("  > The pilot starts in April. [[Sources/plan#^p1]] · [[Cards/plan|card]]", page)
        self.assertIn("- 2026-02-20 · Riverside hosts", page)

    def test_only_named_topics_and_emptied_page(self):
        self.first_run()
        ingest.pages_run(self.p("lib"), self.cfg)
        b = make_run(self.p("run2"), [("plan.docx", "Atlas/plan.docx", "2026-04-01 09:00", PLAN_V2)])
        rec = ingest.file_run(b, accepted(b, card("S01", "p1", "The pilot starts in May.", "Moved to May", "Schedule")),
                              self.p("lib"), self.cfg)
        before = read(self.p("lib", "Topics", "Budget.md"))
        written = ingest.pages_run(self.p("lib"), self.cfg, rec["topics"])
        self.assertEqual(sorted(os.path.basename(p) for p in written), ["Pilot.md", "Schedule.md"])
        self.assertEqual(read(self.p("lib", "Topics", "Budget.md")), before)
        self.assertNotIn("April", read(self.p("lib", "Topics", "Pilot.md")))
        self.assertIn("No current cards", read(self.p("lib", "Topics", "Pilot.md")))
        self.assertIn("Moved to May", read(self.p("lib", "Topics", "Schedule.md")))

    def test_chinese_labels_and_unsafe_topic(self):
        self.cfg["language"] = "zh"
        b = make_run(self.p("run"), [("计划.docx", "计划.docx", "2026-03-01 09:00", "试点于三月启动。")])
        ingest.file_run(b, accepted(b, card("S01", "p1", "试点于三月启动", "三月启动", "目标/计划")), self.p("lib"), self.cfg)
        ingest.pages_run(self.p("lib"), self.cfg)
        page = read(self.p("lib", "Topics", "目标-计划.md"))
        self.assertTrue(page.startswith("# 目标/计划\n"))
        self.assertIn("本页由脚本根据卡片生成", page)
        self.assertIn("[[Cards/计划|卡片]]", page)



def cli(*args):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, "ingest.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)


class CommandLineTest(Tmp):
    def test_file_then_pages(self):
        os.makedirs(self.p("lib"))
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "language": "en", "names": {"topics_dir": "Subjects"}}, f)
        b = make_run(self.p("run"), [("plan.docx", "plan.docx", "2026-03-01 09:00", PLAN_V1)])
        with open(self.p("acc.jsonl"), "w", encoding="utf-8") as f:
            for c in accepted(b, card("S01", "p1", "The pilot starts in April.", "April start", "Pilot")):
                f.write(json.dumps(c) + "\n")
        with open(self.p("names.json"), "w", encoding="utf-8") as f:
            json.dump({"S01": "Atlas plan.md"}, f)
        p = cli("file", *b, "--cards", self.p("acc.jsonl"), "--library", self.p("lib"), "--names", self.p("names.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {"sources": ["Atlas plan.md"], "archived": [], "topics": ["Pilot"]})
        self.assertIn("[[Subjects/Pilot|Pilot]]", read(self.p("lib", "Cards", "Atlas plan.md")))
        p = cli("pages", "--library", self.p("lib"), "--topic", "Pilot")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("April start", read(self.p("lib", "Subjects", "Pilot.md")))
        # a staging folder: written there, the library itself untouched
        p = cli("file", *b, "--cards", self.p("acc.jsonl"), "--library", self.p("lib"), "--target", self.p("stage"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.path.isfile(self.p("stage", "Sources", "plan.md")))
        self.assertFalse(os.path.exists(self.p("lib", "Sources", "plan.md")))

    def test_errors(self):
        b = make_run(self.p("run"), [("long.docx", "long.docx", "", "\n\n".join(["x" * 600] * 4))], limit=1000)
        os.makedirs(self.p("lib"))
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1}, f)
        with open(self.p("none.jsonl"), "w", encoding="utf-8") as f:
            f.write("")
        p = cli("file", b[0], "--cards", self.p("none.jsonl"), "--library", self.p("lib"))
        self.assertEqual(p.returncode, 2)
        self.assertIn("parts missing", p.stderr)
        p = cli("pages", "--library", self.p("nowhere"), "--all")
        self.assertEqual(p.returncode, 2)



class EndToEndTest(Tmp):
    """doc2kb batch files -> quote_check -> ingest file -> pages, then a new version of one source."""

    def run_tool(self, script, *args):
        e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def intake(self, src, cards, tag):
        out = self.p("out-" + tag)
        self.run_tool("doc2kb_core.py", "--batch", src, "-o", out, "--kb-batch", "--library", self.p("lib"))
        batches = sorted(os.path.join(out, n) for n in os.listdir(out) if re.search(r"_b\d+\.md$", n))
        table, _ = quote_check.load_batches(batches)
        sid = {v["name"]: s for s, v in table.items()}
        with open(self.p("cards-" + tag), "w", encoding="utf-8") as f:
            for name, c in cards:
                f.write(json.dumps(dict(c, source=sid[name])) + "\n")
        acc = self.p("acc-" + tag)
        self.run_tool("quote_check.py", "check", self.p("cards-" + tag), *batches, "--accepted", acc,
                      "--report", self.p("rep-" + tag))
        rec = json.loads(self.run_tool("ingest.py", "file", *batches, "--cards", acc, "--library", self.p("lib")))
        self.run_tool("ingest.py", "pages", "--library", self.p("lib"), *sum([["--topic", t] for t in rec["topics"]], []))
        return rec

    def test_two_runs(self):
        os.makedirs(self.p("lib"))
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1, "tier": "weak"}, f)
        os.makedirs(self.p("src1"))
        os.makedirs(self.p("src2"))
        fx.docx(self.p("src1", "report.docx"), english=True)
        rec = self.intake(self.p("src1"), [("report.docx", {"anchor": "p1", "quote": "This report covers the pilot.",
                                                            "conclusion": "Report covers the pilot", "topic": "Pilot",
                                                            "entities": ["Project Atlas"]})], "1")
        self.assertEqual((rec["sources"], rec["archived"], rec["topics"]), (["report.md"], [], ["Pilot"]))
        self.assertIn("Report covers the pilot", read(self.p("lib", "Topics", "Pilot.md")))
        fx.docx(self.p("src2", "report.docx"), english=True, modified="2026-05-06T07:08:09Z")
        rec = self.intake(self.p("src2"), [("report.docx", {"anchor": "p3", "quote": "The menu is shown below.",
                                                            "conclusion": "Menu shown", "topic": "Interface",
                                                            "entities": []})], "2")
        self.assertEqual(rec["archived"], ["Sources/report.md", "Cards/report.md"])
        self.assertEqual(rec["topics"], ["Interface", "Pilot"])
        self.assertIn("No current cards", read(self.p("lib", "Topics", "Pilot.md")))
        self.assertIn("- 2026-05-06 · Menu shown", read(self.p("lib", "Topics", "Interface.md")))



SPEC_FILE = """00_Spec
Version: v1
Last updated: 2026-01-01
Note: read by the skills.

1. Table A: partitions and topics

02 Goals and plans: annual and phase goals; work plans.
09 Reference and templates: reference material; templates.

2. Table B: term fixes
"""
SPEC_FILE_ZH = """00_Spec
版本：v5.2
最后更新：2026-01-01
修订：v5.2（2026-01-01）分区 02 增加主题「预算」，未新增分区号。

1. 表A：分区与主题

02 目标与计划：年度目标；预算。
09 参考与模板：参考资料。
"""


class LibraryCommandsTest(Tmp):
    def library(self, spec=SPEC_FILE, **kb):
        os.makedirs(self.p("lib"), exist_ok=True)
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump(dict({"schema": 1, "partitions": {"max": 9, "topic_start": 2, "fallback": "09"}}, **kb), f)
        with open(self.p("lib", "00_Spec.md"), "w", encoding="utf-8") as f:
            f.write(spec)

    def test_topics(self):
        self.library()
        p = cli("topics", "--library", self.p("lib"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.splitlines(), ["annual and phase goals", "work plans", "reference material", "templates"])
        p = cli("topics", "--library", self.p("lib"), "--out", self.p("topics.txt"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(read(self.p("topics.txt")).splitlines(), ["annual and phase goals", "work plans",
                                                                   "reference material", "templates"])

    def test_add_topic_to_fallback_partition(self):
        self.library()
        p = cli("add-topic", "--library", self.p("lib"), "--topic", "Risks", "--topic", "work  Plans", "--topic", "Vendors")
        self.assertEqual(p.returncode, 0, p.stderr)
        spec = read(self.p("lib", "00_Spec.md"))
        self.assertIn("09 Reference and templates: reference material; templates; Risks; Vendors.\n", spec)
        self.assertIn("02 Goals and plans: annual and phase goals; work plans.\n", spec)     # known: not added
        self.assertIn("Version: v1.1\n", spec)
        self.assertNotIn("2026-01-01", spec)
        self.assertRegex(spec, r'Version: v1\.1\nRevision: v1\.1 \(\d{4}-\d{2}-\d{2}\) partition 09 gets topic "Risks"; '
                               r'no partition number added\.\nRevision: v1\.1 \(\d{4}-\d{2}-\d{2}\) partition 09 gets topic "Vendors"')
        self.assertEqual(p.stdout.splitlines(), ["added: Risks", "added: Vendors", "known: work plans"])

    def test_add_topic_chinese_named_partition_and_nothing_new(self):
        self.library(SPEC_FILE_ZH, language="zh")
        p = cli("add-topic", "--library", self.p("lib"), "--topic", "风险", "--partition", "02")
        self.assertEqual(p.returncode, 0, p.stderr)
        spec = read(self.p("lib", "00_Spec.md"))
        self.assertIn("02 目标与计划：年度目标；预算；风险。\n", spec)
        self.assertIn("版本：v5.3\n", spec)
        self.assertRegex(spec, r"修订：v5\.2（2026-01-01）[^\n]*\n修订：v5\.3（\d{4}-\d{2}-\d{2}）分区 02 增加主题「风险」，未新增分区号。\n")
        before = read(self.p("lib", "00_Spec.md"))
        p = cli("add-topic", "--library", self.p("lib"), "--topic", "风险")
        self.assertEqual((p.returncode, p.stdout), (0, "known: 风险\n"))
        self.assertEqual(read(self.p("lib", "00_Spec.md")), before)              # nothing new: spec unchanged
        p = cli("add-topic", "--library", self.p("lib"), "--topic", "x", "--partition", "05")
        self.assertEqual(p.returncode, 2)
        self.assertIn("partition 05", p.stderr)

    def test_retopic(self):
        path = self.p("acc.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"source": "S01", "topic": "Risk"}) + "\n" + json.dumps({"source": "S02", "topic": "Plans"}) + "\n")
        p = cli("retopic", path, "--from", "risk", "--to", "work plans")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([json.loads(ln)["topic"] for ln in read(path).splitlines()], ["work plans", "Plans"])
        self.assertIn("1 card", p.stdout)


class CheckPageTest(LibraryCase):
    def test_strong_page_must_cite_exactly_the_cards(self):
        self.first_run()
        os.makedirs(self.p("work"))
        good = ("# Pilot\n\nThe pilot starts in April [[Sources/plan#^p1]], hosted by Riverside "
                "[[Sources/plan#^p2]].\n")
        bad = "# Pilot\n\nThe pilot starts in April [[Sources/plan#^p1]] in all regions [[Sources/plan#^p7]].\n"
        with open(self.p("work", "good.md"), "w", encoding="utf-8") as f:
            f.write(good)
        with open(self.p("work", "bad.md"), "w", encoding="utf-8") as f:
            f.write(bad)
        res = ingest.check_page(self.p("lib"), self.cfg, "pilot", bad)
        self.assertEqual(res, {"unknown": ["Sources/plan#^p7"], "missing": ["Sources/plan#^p2"]})
        self.assertEqual(ingest.check_page(self.p("lib"), self.cfg, "Pilot", good), {"unknown": [], "missing": []})
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 1}, f)
        p = cli("check-page", "--library", self.p("lib"), "--topic", "Pilot", "--page", self.p("work", "bad.md"), "--write")
        self.assertEqual(p.returncode, 3)
        self.assertFalse(os.path.exists(self.p("lib", "Topics", "Pilot.md")))
        self.assertEqual(json.loads(p.stdout)["unknown"], ["Sources/plan#^p7"])
        p = cli("check-page", "--library", self.p("lib"), "--topic", "Pilot", "--page", self.p("work", "good.md"), "--write")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(read(self.p("lib", "Topics", "Pilot.md")), good)


if __name__ == "__main__":
    unittest.main()
