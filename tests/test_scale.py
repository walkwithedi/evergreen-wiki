"""A library of the size the scripts are built for: SCALE_SOURCES sources (default 10000) in nested folders,
ten cards each, written straight to disk from made-up text. Checks that the index is built and kept current
in reasonable time and that an answer's material comes within ANSWER_SECONDS.

SCALE_SOURCES=500 python3 -m unittest tests.test_scale runs a smaller library. Standard library only."""
import os
import random
import shutil
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "skills", "kb-query", "scripts"))
import answer  # noqa: E402
import ingest  # noqa: E402
import kb_batch  # noqa: E402
import kbconf  # noqa: E402
import kbindex  # noqa: E402

SOURCES = int(os.environ.get("SCALE_SOURCES", "10000"))
CARDS_PER_SOURCE = 10
PARAS_PER_SOURCE = 25
ANSWER_SECONDS = 5.0
WORDS = ("试点 项目 预算 进度 会议 纪要 方案 评审 上线 测试 数据 导出 服务器 培训 验收 合同 采购 风险 计划 里程碑 "
         "the pilot budget review clinic schedule export server training contract risk plan milestone").split()
TOPICS = ["topic %02d" % i for i in range(40)]


def sentence(rng, n=18):
    return " ".join(rng.choice(WORDS) for _ in range(n)) + "."


def make_library(root, n):
    """A schema 3 library of n sources with cards, written directly; returns its config."""
    rng = random.Random(7)
    os.makedirs(root)
    with open(os.path.join(root, "_kb.json"), "w", encoding="utf-8") as f:
        f.write('{"schema": 3, "label": "Scale", "language": "zh"}')
    cfg = kbconf.load_library(root)
    for i in range(n):
        folder = "dept %02d/%d/%s" % (i % 25, 2018 + i % 8, "minutes" if i % 3 else "plans")
        name = "doc %05d" % i
        paras = [sentence(rng) for _ in range(PARAS_PER_SOURCE)]
        if i == n // 2:
            paras[20] = "The needle phrase sits in one paragraph only, on no card."
        src_dir = os.path.join(root, "Sources", *folder.split("/"))
        card_dir = os.path.join(root, "Cards", *folder.split("/"))
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(card_dir, exist_ok=True)
        modified = "%d-%02d-%02d 09:00" % (2018 + i % 8, 1 + i % 12, 1 + i % 28)
        with open(os.path.join(src_dir, name + ".md"), "w", encoding="utf-8") as f:
            f.write("> Original path: %s/%s.docx\n> Document last modified: %s (from: file)\n\n" % (folder, name, modified))
            f.write("\n\n".join("%s ^p%d" % (p, k) for k, p in enumerate(paras, 1)) + "\n")
        link = "Sources/%s/%s" % (folder, name)
        w = ["# Cards: [[%s]]" % link, "", "Source: [[%s]] · Document last modified: %s" % (link, modified), ""]
        for k in range(1, CARDS_PER_SOURCE + 1):
            topic = TOPICS[(i + k) % len(TOPICS)]
            w += ["## %s" % paras[k - 1][:40], "", "> %s [[%s#^p%d]]" % (paras[k - 1][:60], link, k), "",
                  "- Topic: [[Topics/%s|%s]]" % (topic, topic), "- Date: %s" % modified, ""]
        with open(os.path.join(card_dir, name + ".md"), "w", encoding="utf-8") as f:
            f.write("\n".join(w))
    return cfg


class ScaleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.lib = os.path.join(cls.tmp, "lib")
        t0 = time.time()
        cls.cfg = make_library(cls.lib, SOURCES)
        cls.made = time.time() - t0
        t0 = time.time()
        ix = kbindex.open_index(cls.lib, cls.cfg)
        cls.stats = ix.stats()
        ix.close()
        cls.built = time.time() - t0
        sys.stderr.write("\n[scale] %d sources written in %.1f s, index built in %.1f s (full text: %s)\n"
                         % (SOURCES, cls.made, cls.built, cls.stats["full_text"]))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_index_holds_everything(self):
        self.assertEqual(self.stats["sources"], SOURCES)
        self.assertEqual(self.stats["carded"], SOURCES)
        self.assertEqual(self.stats["cards"], SOURCES * CARDS_PER_SOURCE)
        self.assertEqual(self.stats["paragraphs"], SOURCES * PARAS_PER_SOURCE)

    def test_refresh_with_nothing_changed_is_quick(self):
        t0 = time.time()
        ix = kbindex.open_index(self.lib, self.cfg)
        ix.close()
        self.assertLess(time.time() - t0, ANSWER_SECONDS)

    def test_answer_material_in_time(self):
        for words in (["预算", "评审"], ["needle phrase"], ["topic 07"]):
            t0 = time.time()
            got = answer.select(self.lib, self.cfg, words)
            took = time.time() - t0
            sys.stderr.write("[scale] answer.select %s: %.2f s, %d cards, %d paragraphs\n"
                             % (words, took, len(got["cards"]), len(got["paragraphs"])))
            self.assertLess(took, ANSWER_SECONDS, words)
        got = answer.select(self.lib, self.cfg, ["needle phrase"])
        self.assertEqual([p["anchor"] for p in got["paragraphs"]], ["p21"])

    def test_health_check_in_time(self):
        t0 = time.time()
        got = ingest.health_check(self.lib, self.cfg)
        took = time.time() - t0
        sys.stderr.write("[scale] health check: %.1f s, %d problems\n" % (took, got["problems"]))
        self.assertEqual(got["quotes"], [])
        self.assertLess(took, ANSWER_SECONDS * 12)

    def test_versions_and_pages_in_time(self):
        work = os.path.join(self.tmp, "run")
        units, _ = kb_batch.build_units([{"name": "doc %05d final.docx" % (SOURCES // 3), "path": "new/doc final.docx",
                                          "modified": "2026-01-01 09:00", "meta": "", "body": "A new paragraph here."},
                                         {"name": "doc %05d.docx" % 1, "path": "dept 01/doc.docx",
                                          "modified": "2026-01-01 09:00", "meta": "", "body": "Changed text."}], 20000)
        os.makedirs(work, exist_ok=True)
        path = os.path.join(work, "run_b01.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(kb_batch.render(units, 1, 1, "run_b01", "weak", 20000))
        t0 = time.time()
        got = ingest.version_candidates([path], self.lib, self.cfg)
        took = time.time() - t0
        sys.stderr.write("[scale] versions for 2 sources: %.2f s\n" % took)
        self.assertEqual(got["same_name"], ["doc 00001.md"])
        self.assertLess(took, ANSWER_SECONDS * 2)
        t0 = time.time()
        ingest.pages_run(self.lib, self.cfg, ["topic 07"])
        took = time.time() - t0
        sys.stderr.write("[scale] one topic page (%d cards): %.2f s\n" % (SOURCES * CARDS_PER_SOURCE // len(TOPICS), took))
        self.assertLess(took, ANSWER_SECONDS * 2)
        years = [n for n in os.listdir(os.path.join(self.lib, "Topics")) if n.startswith("topic 07 (")]
        self.assertTrue(years)                       # earlier years on pages of their own


if __name__ == "__main__":
    unittest.main()
