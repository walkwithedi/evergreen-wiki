"""Tests for shared/scripts/quote_check.py: cards checked against batch files, and the cards files.
Standard library only: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ROOT, "shared", "scripts")
QC = os.path.join(SCRIPTS, "quote_check.py")
CORE = os.path.join(SCRIPTS, "doc2kb_core.py")
sys.path.insert(0, TESTS)
sys.path.insert(0, SCRIPTS)
import doc2kb_fixtures as fx  # noqa: E402
import kb_batch  # noqa: E402
import quote_check as qc  # noqa: E402


BODY_A = "\n\n".join([
    "# 项目进度",
    "试点于三月三日启动，由**河畔诊所**承办。",
    "- 第一阶段：需求确认\n- 第二阶段：上线试运行",
    "| 阶段 | 开始 |\n| --- | --- |\n| 试点阶段 | 四月中旬 |",
    "> 转换器加的说明，不带锚点。",
    "下次例会定在周五。",
])
BODY_B = "\n\n".join(["The pilot runs at Riverside Clinic.", "Budget stays as planned.",
                      "The pilot runs at Riverside Clinic."])


def run(args, check=True):
    e = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    if check and p.returncode not in (0, 3):
        raise AssertionError(f"{args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name
        units, _ = kb_batch.build_units([
            {"name": "进度.docx", "path": "a/进度.docx", "modified": "2026-03-04 05:06", "meta": "> m\n", "body": BODY_A},
            {"name": "plan.docx", "path": "plan.docx", "modified": "", "meta": "> m\n", "body": BODY_B},
        ], 20000)
        self.batch = os.path.join(self.d, "run_b01.md")
        with open(self.batch, "w", encoding="utf-8") as f:
            f.write(kb_batch.render(units, 1, 1, "run_b01", "weak", 20000))
        self.table, self.by_sid = qc.load_batches([self.batch])

    def tearDown(self):
        self._t.cleanup()

    def p(self, *parts):
        return os.path.join(self.d, *parts)

    def card(self, **kw):
        c = {"source": "S01", "anchor": "s01-p1", "quote": "试点于三月三日启动", "conclusion": "试点三月三日启动",
             "topic": "试点", "entities": ["河畔诊所"]}
        c.update(kw)
        return c

    def check(self, *cards, topics=None, **kw):
        return qc.check([json.dumps(c, ensure_ascii=False) if not isinstance(c, str) else c for c in cards],
                        self.table, self.by_sid, topics, **kw)


class BlocksTest(Tmp):
    def test_anchor_blocks_and_table(self):
        b = self.by_sid["S01"]
        self.assertEqual(sorted(b), ["s01-p1", "s01-p2", "s01-p3", "s01-p4", "s01-p5"])
        self.assertIn("河畔诊所", b["s01-p1"])
        self.assertEqual(b["s01-p2"], "- 第一阶段：需求确认")
        self.assertIn("| 试点阶段 | 四月中旬 |", b["s01-p4"])
        self.assertNotIn("转换器", "".join(b.values()))
        self.assertEqual(self.table["S01"], {"name": "进度.docx", "path": "a/进度.docx", "modified": "2026-03-04 05:06"})
        self.assertEqual(self.table["S02"]["modified"], "")


class CheckTest(Tmp):
    def test_formatting_differences_pass(self):
        acc, rep = self.check(
            self.card(quote="试点于三月三日启动,由河畔诊所承办."),          # half-width punctuation, no bold
            self.card(anchor="^s01-p3", quote="第二阶段: 上线试运行", conclusion="二阶段上线"),
            self.card(anchor="p4", quote="试点阶段 | 四月中旬", conclusion="四月开始"),
            self.card(source="s02", anchor="s02-p2", quote="Budget  stays\nas planned.", conclusion="budget"))
        self.assertEqual(rep["rejected"], [])
        self.assertEqual([c["anchor"] for c in acc], ["s01-p1", "s01-p3", "s01-p4", "s02-p2"])
        self.assertEqual(acc[0]["date"], "2026-03-04 05:06")
        self.assertEqual(acc[3]["source"], "S02")

    def test_changed_wording_fails(self):
        for q in ("试点于三月四日启动", "试点于三月三日开始", "试点未于三月三日启动"):
            _, rep = self.check(self.card(quote=q))
            self.assertEqual(rep["rejected"][0]["reason"], qc.REASONS["quote_not_found"], q)

    def test_across_paragraphs_fails(self):
        _, rep = self.check(self.card(quote="由河畔诊所承办。第一阶段：需求确认"))
        self.assertEqual(rep["rejected"][0]["reason"], qc.REASONS["quote_not_found"])

    def test_anchor_corrected_or_ambiguous(self):
        acc, rep = self.check(self.card(anchor="s01-p1", quote="下次例会定在周五"))
        self.assertEqual(acc[0]["anchor"], "s01-p5")
        self.assertEqual(rep["anchors_fixed"], [{"line": 1, "from": "s01-p1", "to": "s01-p5"}])
        acc, rep = self.check(self.card(source="S02", anchor="s02-p2", quote="The pilot runs at Riverside Clinic."))
        self.assertEqual(acc, [])
        self.assertEqual(rep["rejected"][0]["reason"], qc.REASONS["quote_ambiguous"] % "s02-p1, s02-p3")
        acc, _ = self.check(self.card(source="S02", anchor="s02-p3", quote="The pilot runs at Riverside Clinic."))
        self.assertEqual(acc[0]["anchor"], "s02-p3")          # right anchor given: no ambiguity

    def test_fields_lengths_and_sources(self):
        cases = [
            ("not json", qc.REASONS["bad_json"]),
            ('["a list"]', qc.REASONS["bad_json"]),
            (self.card(topic=" "), qc.REASONS["missing_field"] % "topic"),
            (self.card(source="S09"), qc.REASONS["unknown_source"] % "S09"),
            (self.card(anchor="para 1"), qc.REASONS["bad_anchor"] % "para 1"),
            (self.card(quote="试点于"), qc.REASONS["quote_short"] % 6),
        ]
        _, rep = self.check(*[c for c, _ in cases])
        self.assertEqual([r["reason"] for r in rep["rejected"]], [r for _, r in cases])
        self.assertEqual(rep["cards"], len(cases))
        _, rep = self.check(self.card(), qmax=5)
        self.assertEqual(rep["rejected"][0]["reason"], qc.REASONS["quote_long"] % 5)

    def test_topics_duplicates_and_event_date(self):
        acc, rep = self.check(
            self.card(event_date="2026-03-03"),
            self.card(quote="试点于三月三日启动 "),               # same card again
            self.card(topic="预算", anchor="s01-p5", quote="下次例会定在周五", event_date="Friday"),
            topics={"试点"})
        self.assertEqual(rep["duplicates"], 1)
        self.assertEqual(rep["new_topics"], ["预算"])
        self.assertEqual(acc[0]["event_date"], "2026-03-03")
        self.assertNotIn("event_date", acc[1])
        _, rep = self.check(self.card(topic="预算"))
        self.assertEqual(rep["new_topics"], [])            # no list given: no topic check

    def test_known_topic_ignores_case_and_space(self):
        acc, rep = self.check(self.card(topic="work  Plans", entities=[]), topics={"Work plans"})
        self.assertEqual(rep["new_topics"], [])
        self.assertEqual(acc[0]["topic"], "Work plans")      # the library's spelling


class WriteTest(Tmp):
    def test_cards_file(self):
        acc, _ = self.check(
            self.card(anchor="s01-p5", quote="下次例会定在周五", conclusion="例会改在周五", entities=[]),
            self.card(event_date="2026-03-03", entities=["河畔诊所", "Atlas [beta]"]))
        paths = qc.write(acc, self.table, self.p("Cards"), names={"S01": "Atlas_进度.md"}, lang="zh")
        self.assertEqual([os.path.basename(p) for p in paths], ["Atlas_进度.md"])
        text = read(paths[0])
        self.assertTrue(text.startswith("# 卡片：[[Atlas_进度]]\n\n来源：[[Atlas_进度]] · 文档最后修改：2026-03-04 05:06\n"))
        first = text.index("## 试点三月三日启动")
        self.assertLess(first, text.index("## 例会改在周五"))       # in anchor order
        self.assertIn("> 试点于三月三日启动 [[Atlas_进度#^p1]]", text)
        self.assertIn("- 主题：[[试点]]", text)
        self.assertIn("- 实体：[[河畔诊所]], [[Atlas beta]]", text)
        self.assertIn("- 日期：2026-03-04 05:06（事件日期：2026-03-03）", text)
        self.assertIn("> 下次例会定在周五 [[Atlas_进度#^p5]]", text)
        self.assertNotIn("- 实体：", text[text.index("## 例会改在周五"):])
        acc, _ = self.check(self.card(source="S02", anchor="s02-p2", quote="Budget stays as planned.",
                                      conclusion="Budget unchanged", topic="Budget", entities=[]))
        text = read(qc.write(acc, self.table, self.p("Cards"))[0])
        self.assertIn("# Cards: [[plan]]", text)
        self.assertIn("Document last modified: unknown", text)


class FolderLinkTest(Tmp):
    def test_links_name_their_folders(self):
        acc, _ = self.check(self.card(topic="Work/plans: Q3", entities=["河畔诊所"]))
        text = read(qc.write(acc, self.table, self.p("Cards"), sources_dir="Sources", topics_dir="Topics")[0])
        self.assertIn("# Cards: [[Sources/进度]]", text)
        self.assertIn("> 试点于三月三日启动 [[Sources/进度#^p1]]", text)
        self.assertIn("- Topic: [[Topics/Work-plans- Q3|Work/plans: Q3]]", text)
        self.assertIn("- Entities: [[河畔诊所]]", text)
        self.assertEqual(qc.page_name("试点"), "试点")
        self.assertEqual(qc.page_name(" .a?b* "), "a-b-")


class ReadBackTest(Tmp):
    def test_cards_file_reads_back(self):
        acc, _ = self.check(self.card(event_date="2026-03-03", entities=["河畔诊所", "Atlas"]),
                            self.card(anchor="s01-p5", quote="下次例会定在周五", conclusion="例会改在周五",
                                      topic="Work/plans: Q3", entities=[]))
        for lang in ("en", "zh"):
            path = qc.write(acc, self.table, self.p(lang), lang=lang, sources_dir="Sources", topics_dir="Topics")[0]
            got = qc.read_cards(read(path))
            self.assertEqual(got["source"], "Sources/进度", lang)
            self.assertEqual([(c["conclusion"], c["quote"], c["anchor"], c["topic"], c["entities"], c["date"],
                               c.get("event_date")) for c in got["cards"]],
                             [("试点三月三日启动", "试点于三月三日启动", "p1", "试点", ["河畔诊所", "Atlas"],
                               "2026-03-04 05:06", "2026-03-03"),
                              ("例会改在周五", "下次例会定在周五", "p5", "Work/plans: Q3", [], "2026-03-04 05:06", None)])
        got = qc.read_cards(read(qc.write(acc[:1], self.table, self.p("bare"))[0]))
        self.assertEqual((got["source"], got["cards"][0]["topic"]), ("进度", "试点"))
        self.assertEqual(qc.read_cards("# just a note\n\ntext"), {"source": "", "cards": []})


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name

    def tearDown(self):
        self._t.cleanup()

    def test_from_doc2kb_batches(self):
        src, out = os.path.join(self.d, "src"), os.path.join(self.d, "out")
        fx.build_all(src, english=True)
        run([sys.executable, CORE, "--batch", src, "-o", out, "--kb-batch", "--batch-chars", "1000"])
        batches = sorted(os.path.join(out, n) for n in os.listdir(out) if n.endswith(".md") and "_b0" in n)
        table, by_sid = qc.load_batches(batches)
        sid = next(s for s, v in table.items() if v["name"] == "report-en.docx")
        cards = os.path.join(self.d, "cards.jsonl")
        with open(cards, "w", encoding="utf-8") as f:
            for c in ({"source": sid, "anchor": "p5", "quote": "Owner list follows.", "conclusion": "An owner list follows",
                       "topic": "Owners", "entities": []},                                   # in part 2
                      {"source": sid, "anchor": "p2", "quote": "This report covers the pilot.",
                       "conclusion": "Covers the pilot", "topic": "Pilot", "entities": ["Project Atlas"]},
                      {"source": sid, "anchor": "p6", "quote": "This report covers everything.",
                       "conclusion": "Covers everything", "topic": "Pilot", "entities": []}):
                f.write(json.dumps(c) + "\n")
        topics = os.path.join(self.d, "topics.txt")
        with open(topics, "w", encoding="utf-8") as f:
            f.write("# known topics\nPilot\n")
        acc, rep = os.path.join(self.d, "acc.jsonl"), os.path.join(self.d, "rep.json")
        p = run([sys.executable, QC, "check", cards, *batches, "--accepted", acc, "--report", rep, "--topics", topics])
        self.assertEqual(p.returncode, 3, p.stderr)
        report = json.loads(read(rep))
        self.assertEqual(report["accepted"], 1)
        reasons = sorted(r["reason"] for r in report["rejected"])
        self.assertEqual(reasons, sorted([qc.REASONS["quote_ambiguous"] % ("%s-p1, %s-p11" % (sid.lower(), sid.lower())),
                                          qc.REASONS["quote_not_found"]]))
        self.assertEqual(report["new_topics"], ["Owners"])
        self.assertIn("accepted 1  rejected 2", p.stdout)
        p = run([sys.executable, QC, "write", acc, *batches, "-o", os.path.join(self.d, "Cards")])
        self.assertEqual(p.returncode, 0, p.stderr)
        text = read(os.path.join(self.d, "Cards", "report-en.md"))
        self.assertIn("> Owner list follows. [[report-en#^p5]]", text)
        self.assertIn("- Date: 2026-03-04 05:06", text)
        p = run([sys.executable, QC, "check", cards, os.path.join(self.d, "missing.md"),
                 "--accepted", acc, "--report", rep], check=False)
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
