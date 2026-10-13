"""Tests for install.py backup, rollback, move and uninstall (kb_manage.py)."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import kb_manage  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class ManageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        self.env = dict(os.environ, HOME=self.home, USERPROFILE=self.home, APPDATA=self.p("home", "appdata"),
                        XDG_CONFIG_HOME=self.p("home", ".config"), PYTHONIOENCODING="utf-8")
        self.env.pop("KB_LIBRARIES", None)
        os.makedirs(self.p("home", ".claude"))
        self.claude_md = self.p("home", ".claude", "CLAUDE.md")
        write(self.claude_md, "# Mine\n")
        self.lib = self.p("home", "kb", "work")
        # language, agent, install, set up, preset, folder, scope, confirm preview, write line
        p = self.run_install(["--wizard"], ["2", "", "", "", "2", self.lib, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.skill = self.p("home", ".claude", "skills", "kb-note", "SKILL.md")
        with mock.patch.dict(os.environ, self.env, clear=True):
            self.registry = kb_manage.registry_path()
            self.state = kb_manage.state_dir()

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def run_install(self, args, answers=()):
        return subprocess.run([sys.executable, os.path.join(ROOT, "install.py"), *args],
                              input="\n".join(answers) + "\n", capture_output=True, text=True,
                              encoding="utf-8", env=self.env)

    def manage(self, args, answers=()):
        return self.run_install(args + ["--lang", "en"], answers)

    def roots(self):
        return [lib["backend"]["root"] for lib in json.loads(read(self.registry))["libraries"]]

    def test_install_is_recorded(self):
        st = json.loads(read(os.path.join(self.state, "state.json")))
        self.assertEqual(st["skills_dirs"], [self.p("home", ".claude", "skills")])
        self.assertEqual(st["instruction_files"], [self.claude_md])

    def test_backup_and_rollback(self):
        before = set(os.listdir(os.path.join(self.state, "backup")))  # the wizard backs up before it writes
        p = self.manage(["backup", "--note", "first"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        bid = p.stdout.split()[1]
        write(self.skill, "changed\n")
        write(self.claude_md, "# Mine\nother\n")
        os.remove(self.registry)
        write(os.path.join(self.lib, "new.md"), "kept\n")
        p = self.manage(["rollback", "--id", bid], ["y"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("name: kb-note", read(self.skill))
        self.assertIn("I keep knowledge bases: Work (team projects).", read(self.claude_md))
        self.assertTrue(os.path.isfile(self.registry))
        self.assertEqual(read(os.path.join(self.lib, "new.md")), "kept\n")  # libraries are not restored
        # the state before the restore is a backup of its own, so the restore can be undone
        new = set(os.listdir(os.path.join(self.state, "backup"))) - before - {bid}
        self.assertEqual(len(new), 1)
        safety = new.pop()
        p = self.manage(["rollback", "--id", safety], ["y"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(read(self.skill), "changed\n")
        self.assertFalse(os.path.exists(self.registry))

    def test_rollback_cancel_and_unknown(self):
        self.manage(["backup"])
        write(self.skill, "changed\n")
        p = self.manage(["rollback"], ["", "n"])
        self.assertIn("Nothing was changed", p.stdout)
        self.assertEqual(read(self.skill), "changed\n")
        self.assertEqual(self.manage(["rollback", "--id", "nope"]).returncode, 2)

    def test_force_install_backs_up_first(self):
        write(self.skill, "local edit\n")
        p = self.run_install(["--target", "claude-code", "--force"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("backup: the present state is saved as", p.stdout)
        self.assertIn("name: kb-note", read(self.skill))
        p = self.manage(["rollback"], ["", "y"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(read(self.skill), "local edit\n")

    def test_move_leaves_material_folders(self):
        write(self.lib + "-inbox/a.txt", "x\n")  # original files stay where they are
        os.makedirs(os.path.join(self.lib, "empty"))
        dest = self.p("home", "disk")
        # confirm the move, then delete the originals with the confirmation word
        p = self.manage(["move", "work", "--to", dest], ["y", "y", "delete"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.roots(), ["~/disk/work"])
        self.assertTrue(os.path.isdir(os.path.join(dest, "work", "empty")))
        self.assertFalse(os.path.exists(os.path.join(dest, "work-inbox")))
        self.assertFalse(os.path.exists(self.lib))
        self.assertEqual(read(self.lib + "-inbox/a.txt"), "x\n")

    def test_move_keeps_originals_by_default(self):
        dest = self.p("elsewhere")
        p = self.manage(["move", "work", "--to", dest], ["y", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.roots(), [os.path.join(dest, "work")])
        self.assertTrue(os.path.isdir(self.lib))
        self.assertIn("Kept the original folders", p.stdout)

    def test_move_refused(self):
        taken = self.p("taken")
        write(os.path.join(taken, "work", "x.txt"), "x\n")
        cases = [(["move", "nope", "--to", taken], "is not registered"),
                 (["move", "work", "--to", taken], "is not empty"),
                 (["move", "work", "--to", os.path.join(self.lib, "sub")], "is inside"),
                 (["move", "work", "--to", os.path.dirname(self.lib)], "already is")]
        for args, msg in cases:
            p = self.manage(args)
            self.assertEqual(p.returncode, 2, args)
            self.assertIn(msg, p.stdout, args)
        write(os.path.join(self.lib, "_intake-batches.json"), "{}\n")
        p = self.manage(["move", "work", "--to", self.p("new")])
        self.assertEqual(p.returncode, 2)
        self.assertIn("unfinished batch intake", p.stdout)
        self.assertEqual(self.roots(), ["~/kb/work"])

    def test_move_mismatch_removes_copy(self):
        dest = self.p("new")
        answers = iter(["y"])

        class Asker:
            def __init__(self, lang):
                pass

            def yes(self, prompt, default=True):
                return next(answers) == "y"

        with mock.patch.dict(os.environ, self.env, clear=True), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(kb_manage, "diff_trees", return_value=["00_Spec.md"]):
            rc = kb_manage.main(["move", "work", "--to", dest, "--lang", "en"], Asker, {})
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(os.path.join(dest, "work")))
        self.assertEqual(self.roots(), ["~/kb/work"])
        self.assertTrue(os.path.isdir(self.lib))

    def test_uninstall_keeps_libraries_by_default(self):
        p = self.manage(["uninstall"], ["", "y"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(self.p("home", ".claude", "skills", "kb-note")))
        self.assertFalse(os.path.exists(self.registry))
        self.assertFalse(os.path.exists(self.state))
        self.assertEqual(read(self.claude_md), "# Mine\n")
        self.assertTrue(os.path.isfile(os.path.join(self.lib, "_kb.json")))
        p = self.manage(["uninstall"])
        self.assertIn("Nothing to uninstall", p.stdout)

    def test_uninstall_picked_library_needs_word(self):
        write(self.lib + "-inbox/a.txt", "x\n")
        p = self.manage(["uninstall"], ["y", "y", "no"])
        self.assertIn("Nothing was changed", p.stdout)
        self.assertTrue(os.path.isdir(self.lib))
        self.assertTrue(os.path.isfile(self.registry))
        p = self.manage(["uninstall"], ["y", "y", "delete"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(self.lib))
        self.assertEqual(read(self.lib + "-inbox/a.txt"), "x\n")  # original files are never deleted
        self.assertFalse(os.path.exists(self.registry))

    def test_uninstall_never_offers_unsafe_folders(self):
        reg = json.loads(read(self.registry))
        plain = self.p("home", "notes")
        write(os.path.join(plain, "a.md"), "x\n")
        reg["libraries"] += [{"id": "home", "label": "Home", "scope": "s", "backend": {"type": "local", "root": "~"}},
                             {"id": "plain", "label": "Plain", "scope": "s",
                              "backend": {"type": "local", "root": plain}}]
        linked = False
        link = self.p("home", "link")
        try:
            os.symlink(self.lib, link)
            linked = True
        except OSError as e:  # no right to create links (Windows without developer mode)
            print(f"symbolic link case left out: {e}", file=sys.stderr)
        if linked:
            reg["libraries"].append({"id": "link", "label": "Link", "scope": "s",
                                     "backend": {"type": "local", "root": link}})
        write(self.registry, json.dumps(reg))
        # only the real library is offered: one question for it, then the plain confirmation
        p = self.manage(["uninstall"], ["y", "n", "y"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(p.stdout.count("Delete "), 1)
        self.assertIn("not offered: Home", p.stdout)
        self.assertIn("not offered: Plain", p.stdout)
        if linked:
            self.assertIn("not offered: Link", p.stdout)
        self.assertTrue(os.path.isdir(self.lib))
        self.assertTrue(os.path.isfile(os.path.join(plain, "a.md")))


if __name__ == "__main__":
    unittest.main()
