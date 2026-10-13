"""Tests for tools/desktop-setup: the dialogs answered by a stand-in zenity, and the terminal fallback."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "desktop-setup", "desktop_setup.py")

# Answers the dialogs from ZENITY_ANSWERS, one line each: the exit code, a space, the printed value.
# Message dialogs need no answer. Every call is logged to ZENITY_LOG as a JSON list of arguments.
FAKE_ZENITY = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["ZENITY_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(args + ([sys.stdin.read()] if "--text-info" in args else []), ensure_ascii=False) + "\n")
if any(a in args for a in ("--info", "--text-info", "--warning", "--error")):
    sys.exit(0)
path = os.environ["ZENITY_ANSWERS"]
with open(path, encoding="utf-8") as f:
    lines = f.read().split("\n")
if not lines or not lines[0]:
    sys.exit(1)
rc, _, value = lines[0].partition(" ")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines[1:]))
print(value)
sys.exit(int(rc))
'''


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@unittest.skipUnless(os.name == "posix", "zenity dialogs run on Linux desktops")
class DesktopSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        os.makedirs(self.p("home", ".claude"))
        write(self.p("home", ".claude", "CLAUDE.md"), "# Mine\n")
        write(self.p("bin", "zenity"), FAKE_ZENITY)
        os.chmod(self.p("bin", "zenity"), 0o700)
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"),
                        PYTHONIOENCODING="utf-8", DISPLAY=":0", ZENITY_LOG=self.p("log"),
                        ZENITY_ANSWERS=self.p("answers"), PATH=self.p("bin") + os.pathsep + os.environ["PATH"])
        for k in ("KB_LIBRARIES", "EVERGREEN_SETUP_UI", "WAYLAND_DISPLAY"):
            self.env.pop(k, None)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def dialogs(self, answers, *args):
        write(self.p("answers"), "\n".join(answers))
        write(self.p("log"), "")
        p = subprocess.run([sys.executable, TOOL, "--lang", "en", *args], capture_output=True, text=True,
                           encoding="utf-8", env=self.env, stdin=subprocess.DEVNULL)
        calls = [json.loads(x) for x in read(self.p("log")).splitlines() if x]
        return p, calls

    def setup_library(self):
        return self.dialogs(["0 setup", "0 claude-code", "0", "0", "0 work", "0 " + self.p("home", "kb", "work"), "0 team projects",
                             "0 ", "0", "0 quit"])

    def test_setup_in_dialogs(self):
        p, calls = self.setup_library()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.isfile(self.p("home", ".claude", "skills", "kb-note", "SKILL.md")))
        self.assertTrue(os.path.isfile(self.p("home", "kb", "work", "_kb.json")))
        self.assertIn("I keep knowledge bases: Work (team projects).", read(self.p("home", ".claude", "CLAUDE.md")))
        shown = "\n".join(" ".join(c) for c in calls)
        self.assertIn("Preview", shown)  # the preview is in a dialog before the confirmation
        self.assertIn("Restart your agent", shown)  # the closing words of the wizard are shown at the end
        self.assertEqual(calls[-1][1], "--list")  # the menu comes back after the setup

    def test_library_folder_has_no_default(self):
        p, calls = self.setup_library()
        chooser = [c for c in calls if "--file-selection" in c][0]
        self.assertIn("--filename=" + self.home + os.sep, chooser)  # opens in the home folder, nothing chosen
        shown = "\n".join(" ".join(c) for c in calls)
        self.assertNotIn("suggested", shown)
        self.assertNotIn(os.path.join("kb", "work") + " (", shown)
        # cancelling the chooser for a new library cancels the setup; nothing is written
        p, calls = self.dialogs(["0 setup", "0 claude-code", "0", "0", "0 life", "1", "0 quit"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(self.p("home", "kb", "life")))

    def test_preselected_agent_and_preset(self):
        p, calls = self.dialogs(["0 setup", "0", "0", "0 " + self.p("home", "kb", "work"), "0 team projects", "0 ", "0", "0 quit"],
                                "--agent", "claude-code", "--preset", "work")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue(os.path.isfile(self.p("home", "kb", "work", "_kb.json")))
        shown = "\n".join(" ".join(c) for c in calls)
        self.assertNotIn("Which agent", shown)
        self.assertNotIn("Which kind of library", shown)

    def test_cancel_writes_nothing(self):
        p, calls = self.dialogs(["0 setup", "0 claude-code", "1", "1", "1"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertFalse(os.path.exists(self.p("home", ".claude", "skills")))
        self.assertFalse(os.path.exists(self.p("home", "kb")))
        p, calls = self.dialogs(["1"])
        self.assertEqual(p.returncode, 0)
        self.assertEqual(len(calls), 1)

    def test_move_with_folder_chooser(self):
        self.setup_library()
        dest = self.p("disk")
        os.makedirs(dest)
        # menu, library, folder chooser, confirm the move, keep the originals, quit
        p, calls = self.dialogs(["0 move", "0 work", "0 " + dest, "0", "1", "0 quit"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        reg = json.loads(read(self.p("home", ".config", "kb", "kb-libraries.json")))
        self.assertEqual(reg["libraries"][0]["backend"]["root"], os.path.join(dest, "work"))
        self.assertTrue(os.path.isdir(self.p("home", "kb", "work")))
        self.assertTrue(any("--file-selection" in c for c in calls))

    def test_terminal_without_zenity(self):
        env = dict(self.env, PATH=os.path.dirname(sys.executable))
        env.pop("DISPLAY")
        p = subprocess.run([sys.executable, TOOL, "--lang", "en"], input="6\n", capture_output=True, text=True,
                           encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("What would you like to do?", p.stdout)
        self.assertEqual(read(self.p("log")) if os.path.exists(self.p("log")) else "", "")


if __name__ == "__main__":
    unittest.main()
