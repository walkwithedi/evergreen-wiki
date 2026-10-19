"""The sample library examples/sample-work-kb is what the scripts make of examples/sample-materials with the
cards in examples/sample-work-cards.jsonl: doc2kb batch files, quote_check, ingest.py file and pages.

After a change to the scripts or the material, rebuild it with
  SAMPLE_UPDATE=1 python3 -m unittest tests.test_examples
Standard library only."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "shared", "scripts")
EXAMPLES = os.path.join(ROOT, "examples")
SAMPLE = os.path.join(EXAMPLES, "sample-work-kb")
MATERIAL = os.path.join(EXAMPLES, "sample-materials")
CARDS = os.path.join(EXAMPLES, "sample-work-cards.jsonl")
BUILT = ("Sources", "Cards", "Topics")  # what the scripts write; _kb.json, the spec and the status card are kept
EXTRACTED = re.compile(r"^> (Extracted|提取时间)[:：].*$", re.M)  # the time of the conversion run


def run(script, *args):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    if p.returncode != 0:
        raise AssertionError(f"{script} {args[:1]}: exit {p.returncode}\n{p.stdout}{p.stderr}")
    return p.stdout


def build(work):
    """Builds the library in work/lib from the sample's settings and spec; returns (library, quote report)."""
    lib = os.path.join(work, "lib")
    os.makedirs(lib)
    for name in os.listdir(SAMPLE):
        if os.path.isfile(os.path.join(SAMPLE, name)):
            shutil.copy(os.path.join(SAMPLE, name), lib)
    out = os.path.join(work, "batches")
    run("doc2kb_core.py", "--batch", MATERIAL, "-o", out, "--kb-batch", "--library", lib)
    batches = sorted(os.path.join(out, n) for n in os.listdir(out) if re.search(r"_b\d+\.md$", n))
    topics = os.path.join(work, "topics.txt")
    run("ingest.py", "topics", "--library", lib, "--out", topics)
    acc, report = os.path.join(work, "accepted.jsonl"), os.path.join(work, "report.json")
    run("quote_check.py", "check", CARDS, *batches, "--accepted", acc, "--report", report, "--topics", topics)
    run("ingest.py", "file", *batches, "--cards", acc, "--library", lib)
    run("ingest.py", "pages", "--library", lib, "--all")
    with open(report, encoding="utf-8") as f:
        return lib, json.load(f)


def tree(root):
    """{relative path: text without the conversion time} of the built folders."""
    files = {}
    for top in BUILT:
        for here, _, names in os.walk(os.path.join(root, top)):
            for n in names:
                p = os.path.join(here, n)
                with open(p, encoding="utf-8") as f:
                    files[os.path.relpath(p, root).replace(os.sep, "/")] = EXTRACTED.sub("> Extracted: -", f.read())
    return files


class SampleLibraryTest(unittest.TestCase):
    def test_sample_is_what_the_scripts_make(self):
        with tempfile.TemporaryDirectory() as work:
            lib, report = build(work)
            self.assertEqual((report["rejected"], report["new_topics"]), ([], []), report)
            self.assertEqual(report["accepted"], report["cards"])
            if os.environ.get("SAMPLE_UPDATE"):
                for top in BUILT:
                    shutil.rmtree(os.path.join(SAMPLE, top), ignore_errors=True)
                    shutil.copytree(os.path.join(lib, top), os.path.join(SAMPLE, top))
            self.assertEqual(tree(lib), tree(SAMPLE),
                             "examples/sample-work-kb is out of date: SAMPLE_UPDATE=1 python3 -m unittest tests.test_examples")

    def test_every_source_has_cards_and_every_card_a_topic_page(self):
        files = tree(SAMPLE)
        sources = {p.split("/", 1)[1] for p in files if p.startswith("Sources/")}
        cards = {p.split("/", 1)[1] for p in files if p.startswith("Cards/")}
        self.assertTrue(sources)
        self.assertEqual(sources, cards)
        pages = {p.split("/", 1)[1][:-3] for p in files if p.startswith("Topics/")}
        linked = set(re.findall(r"\[\[Topics/[^|\]]+\|([^\]]+)\]\]", "".join(v for k, v in files.items() if k.startswith("Cards/"))))
        self.assertEqual(linked, pages)


if __name__ == "__main__":
    unittest.main()
