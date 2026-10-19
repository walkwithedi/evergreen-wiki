"""Tests for shared/scripts/kbindex.py: the library index follows the files. Standard library only."""
import json
import os
import shutil
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
