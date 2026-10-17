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
        good = {"schema": 2, "tier": "strong", "batch_chars": 50000, "quote_min": 4, "quote_max": 200}
        self.assertEqual(kbconf.validate(good), [])
        bad = {"schema": 2, "tier": "medium", "batch_chars": 999, "quote_min": 0, "quote_max": 3}
        text = " ".join(kbconf.validate(bad))
        for word in ("tier", "batch_chars", "quote_min"):
            self.assertIn(word, text)
        self.assertIn("quote_max", " ".join(kbconf.validate({"schema": 2, "quote_min": 10, "quote_max": 5})))
        self.assertEqual(len(kbconf.validate({"schema": 2, "batch_chars": True})), 1)

    def test_schema_2_only(self):
        self.assertEqual(kbconf.validate({"schema": 2}), [])
        self.assertIn("1.x", " ".join(kbconf.validate({"schema": 1})))
        for old in ("convert", "intake", "sources", "delivery", "inbox", "sensitivity", "metadata"):
            self.assertIn("unknown key", " ".join(kbconf.validate({"schema": 2, old: {}})), old)
        self.assertNotIn("convert", kbconf.DEFAULTS)

    def test_old_library_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "_kb.json"), "w", encoding="utf-8") as f:
                json.dump({"schema": 1, "label": "Old"}, f)
            with self.assertRaises(kbconf.ConfigError) as e:
                kbconf.load_library(d)
            self.assertIn("1.x", str(e.exception))
            self.assertIn("not migrated", str(e.exception))

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
            json.dump({"schema": 2, "language": "en", "names": {"topics_dir": "Subjects"}}, f)
        b = make_run(self.p("run"), [("plan.docx", "plan.docx", "2026-03-01 09:00", PLAN_V1)])
        with open(self.p("acc.jsonl"), "w", encoding="utf-8") as f:
            for c in accepted(b, card("S01", "p1", "The pilot starts in April.", "April start", "Pilot")):
                f.write(json.dumps(c) + "\n")
        with open(self.p("names.json"), "w", encoding="utf-8") as f:
            json.dump({"S01": "Atlas plan.md"}, f)
        p = cli("file", *b, "--cards", self.p("acc.jsonl"), "--library", self.p("lib"), "--names", self.p("names.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout), {"sources": ["Atlas plan.md"], "archived": [], "topics": ["Pilot"],
                                                 "restored": [], "review": []})
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
            json.dump({"schema": 2}, f)
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
            json.dump({"schema": 2, "tier": "weak"}, f)
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
            json.dump(dict({"schema": 2, "partitions": {"max": 9, "topic_start": 2, "fallback": "09"}}, **kb), f)
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
            json.dump({"schema": 2}, f)
        p = cli("check-page", "--library", self.p("lib"), "--topic", "Pilot", "--page", self.p("work", "bad.md"), "--write")
        self.assertEqual(p.returncode, 3)
        self.assertFalse(os.path.exists(self.p("lib", "Topics", "Pilot.md")))
        self.assertEqual(json.loads(p.stdout)["unknown"], ["Sources/plan#^p7"])
        p = cli("check-page", "--library", self.p("lib"), "--topic", "Pilot", "--page", self.p("work", "good.md"), "--write")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(read(self.p("lib", "Topics", "Pilot.md")), good)



REPORT = ("Week 1 of the pilot is complete and all clinics joined.\n\n"
          "The data export is planned for the end of the month.\n\n"
          "The review board meets every second Friday.\n\n"
          "Training material is ready for the second group.")
REPORT_FINAL = REPORT.replace("Training material is ready", "Training material is printed")
WEEK_A = "Week 3: the clinics report fewer missed appointments.\n\nThe pilot budget is on track this week."
WEEK_B = "Week 4: two clinics asked for evening slots to be added.\n\nA new scheduling screen goes live next week."


class VersionsTest(LibraryCase):
    def library_with(self, *sources):
        b = make_run(self.p("lib-run"), [(n, n, "2026-03-01 09:00", body) for n, body in sources])
        ingest.file_run(b, [], self.p("lib"), self.cfg)

    def test_name_key_drops_dates_and_version_marks(self):
        k = ingest.name_key
        self.assertEqual(k("Atlas status report v2 final.md"), k("Atlas status report.md"))
        self.assertEqual(k("Atlas status report (1).docx"), k("atlas_status-report.pdf"))
        self.assertEqual(k("weekly 2026-03-09.md"), k("weekly 20260316.md"))
        self.assertEqual(k("周报2026年3月9日.md"), k("周报 终稿.md"))
        self.assertEqual(k("方案 副本 修订版.md"), k("方案.md"))
        self.assertNotEqual(k("budget.md"), k("minutes.md"))

    def test_candidates_need_a_close_name_and_shared_paragraphs(self):
        self.library_with(("status report.docx", REPORT), ("weekly 2026-03-09.docx", WEEK_A),
                          ("budget.docx", MINUTES), ("plan.docx", PLAN_V1))
        b = make_run(self.p("run"), [("status report final.docx", "x/status report final.docx", "", REPORT_FINAL),
                                     ("weekly 2026-03-16.docx", "x/weekly 2026-03-16.docx", "", WEEK_B),
                                     ("summary.docx", "x/summary.docx", "", REPORT),
                                     ("plan.docx", "x/plan.docx", "", PLAN_V2)])
        got = ingest.version_candidates(b, self.p("lib"), self.cfg)
        self.assertEqual(got["same_name"], ["plan.md"])
        self.assertEqual([(c["new"], c["old"]) for c in got["candidates"]], [("status report final.md", "status report.md")])
        c = got["candidates"][0]
        self.assertGreaterEqual(c["name_score"], 0.8)
        self.assertEqual(c["overlap"], 0.75)
        self.assertFalse(c["read"])

    def test_known_names_absent_from_a_staging_folder_are_marked_to_read(self):
        self.library_with(("plan.docx", PLAN_V1))
        b = make_run(self.p("run"), [("status report v3.docx", "status report v3.docx", "", REPORT)])
        with open(self.p("known.txt"), "w", encoding="utf-8") as f:
            f.write("status report.md\nplan.md\nminutes 2026.md\n")
        got = ingest.version_candidates(b, self.p("lib"), self.cfg, known=self.p("known.txt"))
        self.assertEqual(got["candidates"], [{"new": "status report v3.md", "old": "status report.md",
                                              "name_score": 1.0, "overlap": None, "read": True}])

    def test_file_replaces_archives_the_old_version(self):
        self.first_run()
        b = make_run(self.p("run2"), [("plan final.docx", "Atlas/plan final.docx", "2026-04-01 09:00", PLAN_V2)])
        cards = accepted(b, card("S01", "p1", "The pilot starts in May.", "Pilot moves to May", "Schedule"))
        with self.assertRaises(ValueError):
            ingest.file_run(b, cards, self.p("lib"), self.cfg, replaces={"plan final.md": "nothing.md"})
        self.assertFalse(os.path.exists(self.p("lib", "Sources", "plan final.md")))
        rec = ingest.file_run(b, cards, self.p("lib"), self.cfg, replaces={"plan final.md": "plan.md"})
        self.assertEqual(rec["sources"], ["plan final.md"])
        self.assertEqual(rec["archived"], ["Sources/plan.md", "Cards/plan.md"])
        self.assertEqual(rec["topics"], ["Pilot", "Schedule"])
        self.assertFalse(os.path.exists(self.p("lib", "Sources", "plan.md")))
        self.assertRegex(os.listdir(self.p("lib", "Archive", "Sources"))[0], r"^plan_old\d{14}\.md$")

    def test_command_line(self):
        self.first_run()
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 2}, f)
        b = make_run(self.p("run2"), [("plan v2.docx", "plan v2.docx", "2026-04-01 09:00", PLAN_V1 + "\n\nAdded line.")])
        p = cli("versions", *b, "--library", self.p("lib"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([(c["new"], c["old"]) for c in json.loads(p.stdout)["candidates"]], [("plan v2.md", "plan.md")])
        with open(self.p("none.jsonl"), "w", encoding="utf-8") as f:
            f.write("")
        p = cli("file", *b, "--cards", self.p("none.jsonl"), "--library", self.p("lib"), "--replaces", "plan v2.md=plan.md")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["archived"], ["Sources/plan.md", "Cards/plan.md"])
        p = cli("file", *b, "--cards", self.p("none.jsonl"), "--library", self.p("lib"), "--replaces", "no-equals-sign")
        self.assertEqual(p.returncode, 2)


SPEC_E = """00_Spec
Version: v2
Last updated: 2026-01-01

1. Table A: partitions and topics

02 Goals and plans: work plans.
09 Reference and templates: reference material.

4. Table E: entities

Name | Type | Aliases | Core | Note
Project Atlas | project | Atlas; PA | yes |
Riverside Clinic | organisation |  |  |

Types: project, department or team, organisation, system or product, other.

5. Table F: value filters
"""
SPEC_E_ZH = """00_Spec
版本：v1
最后更新：2026-01-01

4. 表 E（Table E）：实体

名称 | 类型 | 别名 | 核心 | 备注
暂无条目。

类型：项目、部门或团队、单位、系统或产品、其他。
"""


class EntitiesTest(LibraryCommandsTest):
    CARDS = [{"source": "S01", "entities": ["Atlas", "Scheduling Service"], "entity_types": {"Scheduling Service": "system"}},
             {"source": "S02", "entities": ["riverside  clinic", "Project Atlass", "Harbour Team"]},
             {"source": "S03", "entities": ["Scheduling Service"]}]

    def cards_file(self):
        path = self.p("acc.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(c) + "\n" for c in self.CARDS))
        return path

    def test_table_e_is_read(self):
        self.assertEqual(kbconf.entities(SPEC_E), [
            {"name": "Project Atlas", "type": "project", "aliases": ["Atlas", "PA"]},
            {"name": "Riverside Clinic", "type": "organisation", "aliases": []}])
        self.assertEqual(kbconf.entities(SPEC_E_ZH), [])
        self.assertEqual(kbconf.entities("00_Spec\n"), [])

    def test_report_merges_known_names_and_lists_new_ones(self):
        rep = ingest.entity_report(self.CARDS, SPEC_E)
        self.assertEqual(rep["merged"], {"Atlas": "Project Atlas", "riverside  clinic": "Riverside Clinic"})
        new = {e["name"]: e for e in rep["new"]}
        self.assertEqual(list(new), ["Scheduling Service", "Project Atlass", "Harbour Team"])
        self.assertEqual((new["Scheduling Service"]["type"], new["Scheduling Service"]["cards"]), ("system", 2))
        self.assertEqual(new["Harbour Team"]["type"], "other")
        self.assertEqual(new["Project Atlass"]["closest"][0], "Project Atlas")

    def test_apply_rewrites_cards_and_table_e(self):
        self.library(SPEC_E)
        path = self.cards_file()
        with open(self.p("map.json"), "w", encoding="utf-8") as f:
            json.dump({"Project Atlass": "Project Atlas", "Harbour Team": {"type": "team"}}, f)
        p = cli("entities", path, "--library", self.p("lib"), "--apply", "--map", self.p("map.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        cards = [json.loads(ln) for ln in read(path).splitlines()]
        self.assertEqual(cards[0]["entities"], ["Project Atlas", "Scheduling Service"])
        self.assertEqual(cards[1]["entities"], ["Riverside Clinic", "Project Atlas", "Harbour Team"])
        spec = read(self.p("lib", "00_Spec.md"))
        self.assertIn("Project Atlas | project | Atlas; PA; Project Atlass | yes |\n", spec)
        self.assertIn("Riverside Clinic | organisation |  |  |\nScheduling Service | system or product |  |  | \n"
                      "Harbour Team | department or team |  |  | \n\nTypes:", spec)
        self.assertIn("Version: v2.1\n", spec)
        self.assertRegex(spec, r'Version: v2\.1\nRevision: v2\.1 \(\d{4}-\d{2}-\d{2}\) "Project Atlass" recorded as an alias '
                               r'of "Project Atlas"\.\nRevision: v2\.1 \(\d{4}-\d{2}-\d{2}\) entity "Scheduling Service" '
                               r'added to Table E\.\nRevision: v2\.1 \(\d{4}-\d{2}-\d{2}\) entity "Harbour Team" added to Table E\.\n')
        out = json.loads(p.stdout)
        self.assertEqual((out["added"], out["aliases"]), (["Scheduling Service", "Harbour Team"], {"Project Atlass": "Project Atlas"}))
        p = cli("entities", path, "--library", self.p("lib"))       # a second look finds nothing new
        self.assertEqual(json.loads(p.stdout)["new"], [])

    def test_apply_without_a_map_adds_every_new_name_chinese(self):
        self.library(SPEC_E_ZH, language="zh")
        path = self.p("acc.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"source": "S01", "entities": ["阿特拉斯项目"], "entity_types": {"阿特拉斯项目": "project"}}) + "\n")
        p = cli("entities", path, "--library", self.p("lib"), "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        spec = read(self.p("lib", "00_Spec.md"))
        self.assertIn("名称 | 类型 | 别名 | 核心 | 备注\n阿特拉斯项目 | 项目 |  |  | \n\n类型：", spec)
        self.assertNotIn("暂无条目", spec)
        self.assertRegex(spec, r"版本：v1\.1\n修订：v1\.1（\d{4}-\d{2}-\d{2}）表 E 增加实体「阿特拉斯项目」。\n")

    def test_map_naming_an_unknown_entity_is_refused(self):
        self.library(SPEC_E)
        path = self.cards_file()
        with open(self.p("map.json"), "w", encoding="utf-8") as f:
            json.dump({"Harbour Team": "Nobody"}, f)
        before = read(path)
        p = cli("entities", path, "--library", self.p("lib"), "--apply", "--map", self.p("map.json"))
        self.assertEqual(p.returncode, 2)
        self.assertIn("Nobody", p.stderr)
        self.assertEqual(read(path), before)


class EntityTypesTest(unittest.TestCase):
    def test_quote_check_keeps_entity_types_of_the_card(self):
        with tempfile.TemporaryDirectory() as d:
            b = make_run(d, [("plan.docx", "plan.docx", "", PLAN_V1)])
            c = card("S01", "p2", "Riverside Clinic hosts the pilot.", "Riverside hosts", "Pilot",
                     entity_types={"Riverside Clinic": "organisation", "Elsewhere": "project", "X": "planet"})
            acc = accepted(b, dict(c, entities=["Riverside Clinic", "Y"], entity_types=dict(c["entity_types"], Y="planet")))
        self.assertEqual(acc[0]["entity_types"], {"Riverside Clinic": "organisation"})


STATUS = """# Status card
Last updated: 2026-01-01

## Items

1. The pilot starts in April. [[Sources/plan#^p1]]
2. The budget stays as planned. [[Sources/minutes#^p1]]
3. Riverside Clinic hosts the pilot. [[Sources/plan#^p2|plan]] and [[Sources/minutes#^p1]]
"""
MINUTES_V2 = "The review moved to Monday.\n\n- Next review on Friday"


class ConflictsTest(LibraryCase):
    def second_run(self):
        b = make_run(self.p("run2"), [("plan.docx", "Atlas/plan.docx", "2026-04-01 09:00", PLAN_V2),
                                      ("minutes.docx", "Atlas/minutes.docx", "2026-04-02 10:00", MINUTES_V2)])
        cards = accepted(b, card("S01", "p1", "The pilot starts in May.", "Pilot starts in May", "Pilot"),
                         card("S02", "p1", "The review moved to Monday.", "Review moved to Monday", "Budget"))
        return b, cards

    def test_old_cards_are_compared_with_the_new_version(self):
        self.first_run()
        b, cards = self.second_run()
        got = ingest.conflicts(b, cards, self.p("lib"), self.cfg)
        kinds = [(c["id"], c["kind"], c["source"], c["old_source"], c["old"]["conclusion"]) for c in got]
        self.assertEqual(kinds, [("c1", "changed", "plan.md", "plan.md", "Pilot starts in April"),
                                 ("c2", "not_carried", "plan.md", "plan.md", "Riverside hosts"),
                                 ("c3", "removed", "minutes.md", "minutes.md", "Budget unchanged")])
        self.assertEqual(got[0]["new"]["conclusion"], "Pilot starts in May")
        self.assertEqual(got[1]["new_anchor"], "p2")
        self.assertIsNone(got[2]["new"])

    def test_replaced_pair_and_unchanged_cards(self):
        self.first_run()
        b = make_run(self.p("run2"), [("plan final.docx", "Atlas/plan final.docx", "2026-04-01 09:00", PLAN_V1)])
        cards = accepted(b, card("S01", "p1", "The pilot starts in April.", "Pilot starts in April", "Pilot"),
                         card("S01", "p2", "Riverside Clinic hosts the pilot.", "Riverside hosts", "Pilot"))
        self.assertEqual(ingest.conflicts(b, cards, self.p("lib"), self.cfg, replaces={"plan final.md": "plan.md"}), [])
        self.assertEqual(ingest.conflicts(b, cards, self.p("lib"), self.cfg), [])   # nothing replaced

    def test_restore_keeps_old_cards(self):
        self.first_run()
        b, cards = self.second_run()
        got = ingest.conflicts(b, cards, self.p("lib"), self.cfg)
        rec = ingest.file_run(b, cards, self.p("lib"), self.cfg, restore=[got[0], got[1]])
        old = os.listdir(self.p("lib", "Archive", "Sources"))
        plan_old = [n for n in old if n.startswith("plan_old")][0][:-3]
        text = read(self.p("lib", "Cards", "plan.md"))
        self.assertIn("> The pilot starts in April. [[Archive/Sources/%s#^p1]]" % plan_old, text)
        self.assertIn("from an earlier version", text)
        self.assertIn("> Riverside Clinic hosts the pilot. [[Sources/plan#^p2]]", text)
        self.assertIn("> The pilot starts in May. [[Sources/plan#^p1]]", text)
        self.assertEqual(rec["restored"], ["c1", "c2"])
        back = quote_check.read_cards(text)["cards"]
        self.assertEqual(sorted(c.get("link", "") for c in back), ["", "", "Archive/Sources/" + plan_old])
        ingest.pages_run(self.p("lib"), self.cfg, ["Pilot"])
        page = read(self.p("lib", "Topics", "Pilot.md"))
        self.assertIn("[[Archive/Sources/%s#^p1]] · [[Cards/plan|card]] · earlier version" % plan_old, page)
        self.assertIn("Pilot starts in May", page)
        cited = "".join("[[%s#^%s]]" % (c.get("link") or "Sources/plan", c["anchor"]) for c in back)
        self.assertEqual(ingest.check_page(self.p("lib"), self.cfg, "Pilot", cited), {"unknown": [], "missing": []})

    def test_command_line(self):
        self.first_run()
        with open(self.p("lib", "_kb.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": 2}, f)
        b, cards = self.second_run()
        with open(self.p("acc.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(c) + "\n" for c in cards))
        p = cli("conflicts", *b, "--cards", self.p("acc.jsonl"), "--library", self.p("lib"))
        self.assertEqual(p.returncode, 0, p.stderr)
        found = json.loads(p.stdout)
        self.assertEqual([c["kind"] for c in found], ["changed", "not_carried", "removed"])
        with open(self.p("restore.json"), "w", encoding="utf-8") as f:
            json.dump([found[2]], f)
        p = cli("file", *b, "--cards", self.p("acc.jsonl"), "--library", self.p("lib"), "--restore", self.p("restore.json"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["restored"], ["c3"])
        self.assertIn("Budget unchanged", read(self.p("lib", "Cards", "minutes.md")))


class ReviewMarkTest(LibraryCase):
    def test_items_citing_a_replaced_source_are_marked_once(self):
        self.first_run()
        with open(self.p("lib", "00_Status-Card.md"), "w", encoding="utf-8") as f:
            f.write(STATUS)
        b = make_run(self.p("run2"), [("plan.docx", "Atlas/plan.docx", "2026-04-01 09:00", PLAN_V2)])
        rec = ingest.file_run(b, [], self.p("lib"), self.cfg)
        self.assertEqual(rec["review"], ["1. The pilot starts in April. [[Sources/plan#^p1]]",
                                         "3. Riverside Clinic hosts the pilot. [[Sources/plan#^p2|plan]] and [[Sources/minutes#^p1]]"])
        text = read(self.p("lib", "00_Status-Card.md"))
        self.assertRegex(text, r"1\. The pilot starts in April\. \[\[Sources/plan#\^p1\]\] ⏳ review: plan has a new version "
                               r"\(\d{4}-\d{2}-\d{2}\)\n2\. The budget stays as planned\. \[\[Sources/minutes#\^p1\]\]\n")
        b = make_run(self.p("run3"), [("plan.docx", "Atlas/plan.docx", "2026-05-01 09:00", PLAN_V1)])
        rec = ingest.file_run(b, [], self.p("lib"), self.cfg)
        self.assertEqual(rec["review"], [])
        self.assertEqual(read(self.p("lib", "00_Status-Card.md")).count("⏳"), 2)

    def test_replaced_pair_marks_too_chinese(self):
        self.first_run()
        self.cfg["language"] = "zh"
        with open(self.p("lib", "00_Status-Card.md"), "w", encoding="utf-8") as f:
            f.write(STATUS)
        b = make_run(self.p("run2"), [("minutes v2.docx", "minutes v2.docx", "2026-04-02 10:00", MINUTES)])
        rec = ingest.file_run(b, [], self.p("lib"), self.cfg, replaces={"minutes v2.md": "minutes.md"})
        self.assertEqual(len(rec["review"]), 2)
        self.assertRegex(read(self.p("lib", "00_Status-Card.md")), r"⏳ 待复核：minutes 有新版本（\d{4}-\d{2}-\d{2}）")

    def test_no_status_card_no_marks(self):
        self.first_run()
        b = make_run(self.p("run2"), [("plan.docx", "Atlas/plan.docx", "2026-04-01 09:00", PLAN_V2)])
        self.assertEqual(ingest.file_run(b, [], self.p("lib"), self.cfg)["review"], [])


class StatusCheckTest(LibraryCommandsTest):
    NEW = """# Status card
Last updated: 2026-05-01

## Items

1. The pilot starts in April. [[Sources/plan#^p1]]
2. The budget is cut by a tenth. [[Sources/minutes#^p1]]
3. A new review board meets monthly. [[Sources/board#^p4]]
"""

    def test_removed_changed_lost_and_added(self):
        old = STATUS.replace("[[Sources/plan#^p1]]\n", "[[Sources/plan#^p1]] ⏳ review: plan has a new version (2026-04-01)\n")
        got = ingest.status_check(old, self.NEW)
        self.assertEqual(got["changed"], [{"old": "2. The budget stays as planned. [[Sources/minutes#^p1]]",
                                           "new": "2. The budget is cut by a tenth. [[Sources/minutes#^p1]]"}])
        self.assertEqual(got["removed"], ["3. Riverside Clinic hosts the pilot. [[Sources/plan#^p2|plan]] and [[Sources/minutes#^p1]]"])
        self.assertEqual(got["lost"], ["Sources/plan#^p2"])
        self.assertEqual(got["added"], ["3. A new review board meets monthly. [[Sources/board#^p4]]"])

    def test_command_line_writes_only_a_clean_rewrite(self):
        self.library(SPEC_FILE)
        with open(self.p("lib", "00_Status-Card.md"), "w", encoding="utf-8") as f:
            f.write(STATUS)
        with open(self.p("new.md"), "w", encoding="utf-8") as f:
            f.write(self.NEW)
        p = cli("status-check", "--old", self.p("lib", "00_Status-Card.md"), "--new", self.p("new.md"),
                "--write", "--library", self.p("lib"))
        self.assertEqual(p.returncode, 3)
        self.assertEqual(read(self.p("lib", "00_Status-Card.md")), STATUS)
        grown = STATUS + "4. A new review board meets monthly. [[Sources/board#^p4]]\n"
        with open(self.p("new.md"), "w", encoding="utf-8") as f:
            f.write(grown)
        p = cli("status-check", "--old", self.p("lib", "00_Status-Card.md"), "--new", self.p("new.md"),
                "--write", "--library", self.p("lib"))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["added"], ["4. A new review board meets monthly. [[Sources/board#^p4]]"])
        self.assertEqual(read(self.p("lib", "00_Status-Card.md")), grown)


INGEST_SCRIPTS = os.path.join(ROOT, "skills", "kb-ingest", "scripts")


def init(*args):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    return subprocess.run([sys.executable, os.path.join(INGEST_SCRIPTS, "init_library.py"), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)


class InitTest(Tmp):
    BASE = ["--language", "en", "--timezone", "UTC", "--scope", "work material"]

    def test_new_library_is_a_2_0_library(self):
        p = init("write", "--root", self.p("lib"), "--preset", "work", *self.BASE, "--tier", "weak")
        self.assertEqual(p.returncode, 0, p.stderr)
        kb = json.loads(read(self.p("lib", "_kb.json")))
        self.assertEqual((kb["schema"], kb["tier"], kb["label"]), (2, "weak", "Work"))
        self.assertEqual(kbconf.validate(kb), [])
        self.assertEqual(sorted(os.listdir(self.p("lib"))),
                         ["00_Spec.md", "00_Status-Card.md", "Archive", "Cards", "Quick-Notes", "Sources", "Topics", "_kb.json"])
        self.assertIn("Version: v1", read(self.p("lib", "00_Spec.md")))
        self.assertNotIn("{{", read(self.p("lib", "00_Spec.md")))
        cfg = kbconf.load_library(self.p("lib"))
        self.assertIn("work plans", kbconf.topics(read(self.p("lib", "00_Spec.md")), cfg))

    def test_tier_default_and_chinese(self):
        p = init("write", "--root", self.p("zh"), "--preset", "work", "--language", "zh", "--timezone", "UTC",
                 "--scope", "工作资料")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(read(self.p("zh", "_kb.json")))["tier"], "weak")
        self.assertIn("版本：v1", read(self.p("zh", "00_Spec.md")))
        p = init("write", "--root", self.p("s"), "--preset", "work", *self.BASE, "--tier", "strong")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(read(self.p("s", "_kb.json")))["tier"], "strong")

    def test_life_preset_and_1x_options_gone(self):
        p = init("write", "--root", self.p("life"), "--preset", "life", *self.BASE)
        self.assertEqual(p.returncode, 2)
        p = init("write", "--root", self.p("x"), "--preset", "work", *self.BASE, "--sources", "on")
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(self.p("x")))


if __name__ == "__main__":
    unittest.main()
