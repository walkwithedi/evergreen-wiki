"""Tests for install.py: registering an existing library, --agent, --preset and --descriptions."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class InstallOptionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        os.makedirs(self.p("home", ".claude"))
        self.env = dict(os.environ, HOME=self.home, USERPROFILE=self.home, APPDATA=self.p("home", "appdata"),
                        XDG_CONFIG_HOME=self.p("home", ".config"), PYTHONIOENCODING="utf-8")
        self.env.pop("KB_LIBRARIES", None)
        self.existing = self.p("home", "atlas")
        write(os.path.join(self.existing, "_kb.json"), json.dumps({"schema": 1, "label": "Atlas"}))
        write(os.path.join(self.existing, "00_Spec.md"), "# Spec\n")

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def install(self, args, answers=()):
        return subprocess.run([sys.executable, os.path.join(ROOT, "install.py"), *args],
                              input="\n".join(answers) + "\n", capture_output=True, text=True,
                              encoding="utf-8", env=self.env)

    def registry(self):
        path = self.p("home", "appdata", "kb", "kb-libraries.json") if os.name == "nt" \
            else self.p("home", ".config", "kb", "kb-libraries.json")
        return json.loads(read(path))

    def test_existing_library_is_registered_as_it_is(self):
        before = sorted(os.listdir(self.existing))
        # language, install, set up, folder, confirm the registration, write the line
        p = self.install(["--wizard", "--agent", "claude-code", "--preset", "work"],
                         ["2", "", "", self.existing, "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("already holds a library", p.stdout)
        self.assertIn('"init Atlas"', p.stdout)
        self.assertNotIn("Which agent", p.stdout)
        self.assertNotIn("Which kind of library", p.stdout)
        libs = self.registry()["libraries"]
        self.assertEqual([(lib["id"], lib["label"]) for lib in libs], [("work", "Atlas")])
        self.assertEqual(libs[0]["backend"]["root"], "~/atlas")
        self.assertEqual(sorted(os.listdir(self.existing)), before)
        self.assertIn("I keep knowledge bases: Atlas", read(self.p("home", ".claude", "CLAUDE.md")))

    def test_existing_library_choose_another_folder(self):
        new = self.p("home", "kb", "fresh")
        # language, install, set up, existing folder, "1" for another folder, new folder, scope, confirm, line
        p = self.install(["--wizard", "--agent", "claude-code", "--preset", "work"],
                         ["2", "", "", self.existing, "1", new, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))
        self.assertEqual([lib["label"] for lib in self.registry()["libraries"]], ["Work"])

    def test_loose_markdown_is_refused(self):
        loose = self.p("home", "notes")
        write(os.path.join(loose, "a.md"), "x\n")
        new = self.p("home", "kb", "fresh")
        p = self.install(["--wizard", "--agent", "claude-code", "--preset", "life"],
                         ["2", "", "", loose, new, "", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Not valid", p.stdout)
        self.assertFalse(os.path.exists(os.path.join(loose, "_kb.json")))
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))

    def test_home_and_agent_folders_are_refused(self):
        os.makedirs(self.p("home", "Documents"))
        new = self.p("home", "kb", "fresh")
        # language, install, set up; the home folder, the folder holding the installed skills, a new folder
        p = self.install(["--wizard", "--agent", "claude-code", "--preset", "life"],
                         ["2", "", "", self.home, self.p("home", ".claude"), new, "", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.count("Not valid"), 2, p.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.home, "_kb.json")))
        self.assertFalse(os.path.exists(self.p("home", ".claude", "_kb.json")))
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))
        roots = [os.path.normpath(lib["backend"]["root"].replace("~", self.home, 1))
                 for lib in self.registry()["libraries"]]
        self.assertEqual(roots, [os.path.normpath(new)])

    def test_descriptions_file(self):
        desc = {"kb-note": "Notes one line.", "kb-query": "Query one line.", "kb-incremental": "Intake one line."}
        path = self.p("desc.json")
        write(path, json.dumps(desc))
        dest = self.p("skills")
        p = self.install(["--dest", dest, "--descriptions", path])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for name, text in desc.items():
            self.assertIn("\ndescription: " + text + "\n", read(os.path.join(dest, name, "SKILL.md")))
        write(path, json.dumps({"kb-note": "only one"}))
        p = self.install(["--dest", self.p("other"), "--descriptions", path])
        self.assertEqual(p.returncode, 2)
        self.assertIn("kb-query", p.stderr)
        self.assertFalse(os.path.exists(self.p("other")))

    def test_option_conflicts(self):
        for args in (["--target", "agents", "--agent", "opencode"], ["--dest", self.p("x"), "--preset", "work"],
                     ["--dest", self.p("x"), "--descriptions", "d.json", "--locale", "zh"]):
            p = self.install(args)
            self.assertEqual(p.returncode, 2, args)


class AgentDefaultTest(unittest.TestCase):
    """install.choose_dest: agent_default only changes the agent chosen beforehand."""

    class Asker:
        def __init__(self):
            self.asked = []

        def choose(self, question, options, default):
            self.asked.append((question, [v for v, _ in options], default))
            return default

    def choose(self, agent=None, agent_default=None):
        sys.path.insert(0, ROOT)
        self.addCleanup(sys.path.remove, ROOT)
        import install
        q = self.Asker()
        target, _ = install.choose_dest(q, install.MSG["en"], agent, agent_default)
        return target, q.asked

    def test_default_only(self):
        target, asked = self.choose(agent_default="opencode")
        self.assertEqual(target, "opencode")
        self.assertEqual(len(asked), 1)  # the question is still asked
        self.assertIn("claude-code", asked[0][1])
        plain, _ = self.choose()
        self.assertEqual(self.choose(agent_default="no-such-agent")[0], plain)
        self.assertEqual(self.choose(agent="codex", agent_default="opencode"), ("codex", []))


if __name__ == "__main__":
    unittest.main()
