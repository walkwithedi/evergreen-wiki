"""Tests for install.py: new and existing libraries, the tier by agent, --agent and --descriptions."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

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
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"), PYTHONIOENCODING="utf-8")
        self.env.pop("KB_LIBRARIES", None)
        self.existing = self.p("home", "atlas")
        write(os.path.join(self.existing, "_kb.json"), json.dumps({"schema": 2, "label": "Atlas"}))
        write(os.path.join(self.existing, "00_Spec.md"), "# Spec\n")

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def install(self, args, answers=()):
        return subprocess.run([sys.executable, os.path.join(ROOT, "install.py"), *args],
                              input="\n".join(answers) + "\n", capture_output=True, text=True,
                              encoding="utf-8", env=self.env)

    def registry(self):
        path = self.p("home", ".config", "kb", "kb-libraries.json")
        return json.loads(read(path))

    def test_existing_library_is_registered_as_it_is(self):
        before = sorted(os.listdir(self.existing))
        # language, install, set up, folder, confirm the registration, write the line
        p = self.install(["--wizard", "--agent", "claude-code"],
                         ["2", "", "", self.existing, "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("already holds a library", p.stdout)
        self.assertNotIn('"init Atlas"', p.stdout)
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
        p = self.install(["--wizard", "--agent", "claude-code"],
                         ["2", "", "", self.existing, "1", new, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))
        self.assertEqual([lib["label"] for lib in self.registry()["libraries"]], ["Work"])

    def test_loose_markdown_is_refused(self):
        loose = self.p("home", "notes")
        write(os.path.join(loose, "a.md"), "x\n")
        new = self.p("home", "kb", "fresh")
        p = self.install(["--wizard", "--agent", "claude-code"],
                         ["2", "", "", loose, new, "", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Not valid", p.stdout)
        self.assertFalse(os.path.exists(os.path.join(loose, "_kb.json")))
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))

    def test_home_and_agent_folders_are_refused(self):
        os.makedirs(self.p("home", "Documents"))
        new = self.p("home", "kb", "fresh")
        # language, install, set up; the home folder, the folder holding the installed skills, a new folder
        p = self.install(["--wizard", "--agent", "claude-code"],
                         ["2", "", "", self.home, self.p("home", ".claude"), new, "", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.count("Not valid"), 2, p.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.home, "_kb.json")))
        self.assertFalse(os.path.exists(self.p("home", ".claude", "_kb.json")))
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))
        roots = [os.path.normpath(lib["backend"]["root"].replace("~", self.home, 1))
                 for lib in self.registry()["libraries"]]
        self.assertEqual(roots, [os.path.normpath(new)])

    def test_new_library_has_no_tier(self):
        for agent in ("opencode", "claude-code"):
            new = self.p("home", "kb", agent)
            # language, install, set up, folder, scope, confirm, line
            p = self.install(["--wizard", "--agent", agent], ["2", "", "", new, "team projects", "", ""])
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            kb = json.loads(read(os.path.join(new, "_kb.json")))
            self.assertEqual(kb["schema"], 2, agent)
            self.assertNotIn("tier", kb)
            self.assertNotIn("Tier", p.stdout)
            self.assertNotIn("Which kind of library", p.stdout)
            self.assertEqual(sorted(n for n in os.listdir(new) if not os.path.isdir(os.path.join(new, n))),
                             ["00_Spec.md", "00_Status-Card.md", "_kb.json"])

    def test_1x_library_is_refused(self):
        old = self.p("home", "old")
        write(os.path.join(old, "_kb.json"), json.dumps({"schema": 1, "label": "Old"}))
        write(os.path.join(old, "00_Spec.md"), "# Spec\n")
        new = self.p("home", "kb", "fresh")
        # language, install, set up, the 1.x folder, a new folder, scope, confirm, line
        p = self.install(["--wizard", "--agent", "claude-code"], ["2", "", "", old, new, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("1.x", p.stdout)
        self.assertEqual([lib["label"] for lib in self.registry()["libraries"]], ["Work"])
        self.assertTrue(os.path.isfile(os.path.join(new, "_kb.json")))

    def test_descriptions_file(self):
        desc = {"kb-note": "Notes one line.", "kb-query": "Query one line.", "kb-ingest": "Intake one line."}
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
        for args in (["--target", "agents", "--agent", "opencode"], ["--wizard", "--preset", "work"],
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
        self.assertEqual(self.choose(agent="agents", agent_default="opencode"), ("agents", []))


class InstallOneTest(unittest.TestCase):
    """install.install_one: the new copy is complete before the old folder goes."""

    def setUp(self):
        sys.path.insert(0, ROOT)
        self.addCleanup(sys.path.remove, ROOT)
        import install
        self.install = install
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.old = os.path.join(self.tmp, "kb-note", "SKILL.md")
        write(self.old, "Version: 0.1.0\n")
        self.opts = install.argparse.Namespace(force=True, dry_run=False, link=False)

    def test_replaces_the_folder(self):
        self.assertTrue(self.install.install_one("kb-note", self.tmp, self.opts, None))
        self.assertEqual(read(self.old), read(os.path.join(ROOT, "skills", "kb-note", "SKILL.md")))
        self.assertEqual(os.listdir(self.tmp), ["kb-note"])  # no temporary folder left

    def test_a_failed_copy_keeps_the_old_folder(self):
        real = shutil.copytree

        def broken(src, dest, **kw):  # copies everything, then fails
            with unittest.mock.patch.object(shutil, "copytree", real):  # it calls itself for subfolders
                real(src, dest, **kw)
            raise OSError("disk full")
        with unittest.mock.patch.object(shutil, "copytree", broken):
            with self.assertRaises(OSError):
                self.install.install_one("kb-note", self.tmp, self.opts, None)
        self.assertEqual(read(self.old), "Version: 0.1.0\n")
        self.assertEqual(os.listdir(self.tmp), ["kb-note"])


if __name__ == "__main__":
    unittest.main()
