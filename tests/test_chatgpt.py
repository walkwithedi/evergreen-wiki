"""Tests for the ChatGPT versions of the skills: the prompt.md checks of scripts/check_repo.py and the
-chatgpt.zip built by scripts/build_skill.py. Standard library only."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_skill  # noqa: E402
import check_repo  # noqa: E402

SKILL = """---
name: kb-x
description: x
---

# X

Version: 2.0.0

## Step 1

Do it.

## Hard rules

1. Never write a card whose quote did not pass the check.
2. Replies follow the library language.
"""
PROMPT = """# kb-x for ChatGPT

Version: 2.0.0

Steps in short.

Hard rules:
1. Never write a card whose quote did not pass the check.
2. Replies follow the library language.
"""


class PromptCheckTest(unittest.TestCase):
    def tree(self, prompt=PROMPT, skill=SKILL):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "skills", "kb-x"))
        with open(os.path.join(d, "skills", "kb-x", "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(skill)
        if prompt is not None:
            with open(os.path.join(d, "skills", "kb-x", "prompt.md"), "w", encoding="utf-8") as f:
                f.write(prompt)
        return d

    def test_good_prompt(self):
        self.assertEqual(check_repo.check_prompts(self.tree(), ["kb-x"]), [])

    def test_problems(self):
        cases = [(None, "no prompt.md"),
                 (PROMPT + "x" * check_repo.PROMPT_MAX, "longer than"),
                 (PROMPT.replace("2.0.0", "2.0.1"), "version"),
                 (PROMPT.replace("2. Replies follow the library language.\n", ""), "hard rule")]
        for prompt, word in cases:
            with self.subTest(word=word):
                got = check_repo.check_prompts(self.tree(prompt), ["kb-x"])
                self.assertEqual(len(got), 1, got)
                self.assertIn(word, got[0])
        got = check_repo.check_prompts(self.tree(skill=SKILL.replace("## Hard rules", "## Rules")), ["kb-x"])
        self.assertIn("no Hard rules section", got[0])

    def test_repository_prompts(self):
        self.assertEqual(check_repo.check_prompts(ROOT, check_repo.SKILLS), [])


class ChatGPTZipTest(unittest.TestCase):
    def test_zip_holds_the_prompt_and_the_skill_folder(self):
        with tempfile.TemporaryDirectory() as d:
            for name, script in (("kb-query", ["scripts/answer.py", "--help"]),
                                 ("kb-ingest", ["scripts/init_library.py", "defaults", "--preset", "work"])):
                path = build_skill.build_chatgpt(name, d)
                self.assertRegex(os.path.basename(path), r"^%s-\d+\.\d+\.\d+-chatgpt\.zip$" % name)
                with zipfile.ZipFile(path) as z:
                    self.assertEqual(sorted(z.namelist()), ["%s-chatgpt/%s-files.zip" % (name, name),
                                                            "%s-chatgpt/%s-prompt.md" % (name, name)])
                    inner = zipfile.ZipFile(io.BytesIO(z.read("%s-chatgpt/%s-files.zip" % (name, name))))
                    prompt = z.read("%s-chatgpt/%s-prompt.md" % (name, name)).decode("utf-8")
                self.assertIn("%s-files.zip" % name, prompt)
                self.assertIn("%s/SKILL.md" % name, inner.namelist())
                out = os.path.join(d, "unpacked-" + name)
                inner.extractall(out)
                p = subprocess.run([sys.executable, os.path.join(out, name, *script[0].split("/"))] + script[1:],
                                   capture_output=True, text=True, cwd=d, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
                self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
