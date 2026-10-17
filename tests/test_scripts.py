"""Tests for kbconf, kb-ingest's setup scripts (init_library, pick_materials), the installer wizard, kb-query's
kbfind and the repository hooks. Standard library only: python3 -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "kb-ingest", "scripts")
sys.path.insert(0, SCRIPTS)
import kbconf  # noqa: E402


def run(script, *args, check=True):
    p = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        raise AssertionError(f"{script} {args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name

    def tearDown(self):
        self._t.cleanup()

    def p(self, *parts):
        return os.path.join(self.d, *parts)

class KbconfTest(Tmp):
    def test_defaults_and_overrides(self):
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 2, "language": "zh", "timezone": "+08:00",
                                                     "names": {"status_card": "00_当前有效状态卡.md", "archive_dir": "归档"}}))
        cfg = kbconf.load_library(self.p("lib"))
        self.assertEqual(cfg["names"]["status_card"], "00_当前有效状态卡.md")
        self.assertEqual(cfg["names"]["status_card_key"], "当前有效状态卡")
        self.assertEqual(cfg["names"]["index"], "01_File-Index.md")
        self.assertEqual(cfg["names"]["archive_dir"], "归档")
        self.assertEqual(cfg["partitions"]["topic_start"], 2)

    def test_validate_problems(self):
        problems = kbconf.validate({"schema": 3, "metadata": "xml", "bogus": 1,
                                    "partitions": {"max": 5, "topic_start": 2, "fallback": "07"},
                                    "names": {"nope": "x"}, "timezone": "Mars Base"})
        text = " ".join(problems)
        for word in ("schema", "metadata", "bogus", "fallback", "nope", "Mars Base"):
            self.assertIn(word, text)

    def test_timezone_check_is_version_independent(self):
        self.assertEqual(kbconf.check_timezone("Europe/London"), [])
        self.assertEqual(kbconf.check_timezone("+08:00"), [])
        self.assertTrue(kbconf.check_timezone("not a zone!"))

    def test_timezone_without_zone_data(self):
        # Python 3.8 has no zoneinfo: the system's own zone uses the current local offset, UTC names
        # are UTC, and any other name still asks for a fixed offset
        from unittest import mock
        with mock.patch.dict(sys.modules, {"zoneinfo": None}), \
                mock.patch.object(kbconf, "system_zone", return_value="Asia/Example"):
            self.assertEqual(kbconf.tzinfo("Asia/Example").utcoffset(None),
                             kbconf.datetime.now().astimezone().utcoffset())
            self.assertEqual(kbconf.tzinfo("Etc/UTC"), kbconf.timezone.utc)
            with self.assertRaises(kbconf.TimezoneUnavailable):
                kbconf.tzinfo("Europe/Elsewhere")
            self.assertEqual(kbconf.check_timezone("Europe/Elsewhere"), [])

    def test_limits(self):
        self.assertEqual(kbconf.default_limits("zh-CN"), (55, 80))
        self.assertEqual(kbconf.default_limits("en"), (90, 120))

    def test_registry(self):
        reg = {"schema": 1, "libraries": [
            {"id": "life", "label": "Life", "scope": "me", "backend": {"type": "local", "root": "~/kb"}},
            {"id": "life", "label": "Dup", "scope": "", "backend": {"type": "ftp"}}]}
        problems = " ".join(kbconf.check_registry(reg))
        self.assertIn("used twice", problems)
        self.assertIn("gdrive or local", problems)
        self.assertIn("scope", problems)


@unittest.skipIf(os.name == "nt", "fake zenity is a shell script")
class PickMaterialsTest(Tmp):
    """pick_materials.py against a fake zenity that replays scripted answers."""

    def pick(self, answers, display=True, zenity=True, args=None):
        bin_dir = self.p("bin")
        os.makedirs(bin_dir, exist_ok=True)
        # each call takes the next "<exit code> <output>" line and logs its arguments
        write(os.path.join(bin_dir, "zenity"),
              "#!/bin/sh\n"
              'n=$(cat "$ZDIR/n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$ZDIR/n"\n'
              'echo "$*" >> "$ZDIR/calls"\n'
              'line=$(sed -n "${n}p" "$ZDIR/answers")\n'
              'printf \'%b\' "${line#* }"\n'
              'exit "${line%% *}"\n')
        os.chmod(os.path.join(bin_dir, "zenity"), 0o700)
        write(self.p("answers"), "".join(a + "\n" for a in answers))
        # without zenity, PATH holds only an empty folder, so a real zenity on the machine is not found
        path = bin_dir + os.pathsep + "/usr/bin:/bin" if zenity else self.p("empty")
        env = dict(os.environ, ZDIR=self.d, PATH=path)
        env.pop("WAYLAND_DISPLAY", None)
        if display:
            env["DISPLAY"] = ":0"
        else:
            env.pop("DISPLAY", None)
        args = ["--start", self.d] if args is None else args
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, "pick_materials.py"),
                            "--timeout", "7", "--language", "zh"] + args,
                           capture_output=True, text=True, encoding="utf-8", env=env)
        calls = read(self.p("calls")).splitlines() if os.path.exists(self.p("calls")) else []
        return p.returncode, p.stdout.splitlines(), calls

    def test_folder(self):
        rc, out, calls = self.pick(["0 folder\\n", "0 " + self.p("in") + "\\n"])
        self.assertEqual((rc, out), (0, [self.p("in")]))
        self.assertIn("--directory", calls[1])
        self.assertIn("--multiple", calls[1])
        self.assertIn("--timeout 7", calls[0])
        self.assertIn("选择要入库的材料", calls[0])

    def test_several_files(self):
        rc, out, calls = self.pick(["0 files\\n", "0 /a b.docx\\n/c.pdf\\n"])
        self.assertEqual((rc, out), (0, ["/a b.docx", "/c.pdf"]))
        self.assertIn("--multiple", calls[1])
        self.assertNotIn("--directory", calls[1])

    def test_cancel_and_timeout(self):
        self.assertEqual(self.pick(["1 "])[0], 4)
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["0 folder\\n", "5 "])[0], 5)

    def test_no_dialog_possible(self):
        self.assertEqual(self.pick([], display=False)[:2], (3, []))
        self.assertEqual(self.pick([], zenity=False)[:2], (3, []))
        self.assertEqual(self.pick([], display=False, args=["--library"])[:2], (3, []))

    def test_library_folder(self):
        rc, out, calls = self.pick(["0 " + self.p("kb") + "\\n"], args=["--library", "--start", self.d])
        self.assertEqual((rc, out), (0, [self.p("kb")]))
        self.assertEqual(len(calls), 1)
        self.assertIn("--directory", calls[0])
        self.assertIn("选择知识库文件夹", calls[0])
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["1 "], args=["--library"])[0], 4)
        os.remove(self.p("n"))
        self.assertEqual(self.pick(["5 "], args=["--library"])[0], 5)

    def test_several_folders_from_home(self):
        lib = self.p("kb")
        os.makedirs(lib + "-待整理")
        rc, out, calls = self.pick(["0 folder\\n", "0 /x\\n/y z\\n"], args=[])
        self.assertEqual((rc, out), (0, ["/x", "/y z"]))
        self.assertIn("--filename " + os.path.expanduser("~") + os.sep, calls[1])  # no folder chosen in advance


class InitLibraryTest(Tmp):
    def test_write_matches_preset(self):
        root = self.p("kb", "work")
        out = run("init_library.py", "write", "--root", root, "--preset", "work", "--language", "zh",
                  "--timezone", "+08:00", "--scope", "工作资料", "--date", "2026-10-10").stdout
        self.assertIn("result: written 3 files and 5 folders", out)
        cfg = kbconf.load_library(root)
        self.assertEqual((cfg["label"], cfg["language"], cfg["timezone"], cfg["tier"]), ("工作", "zh", "+08:00", "weak"))
        self.assertEqual(kbconf.validate(json.loads(read(os.path.join(root, "_kb.json")))), [])
        names = cfg["names"]
        spec = read(os.path.join(root, names["spec"]))
        self.assertIn("最后更新：2026-10-10", spec)
        self.assertNotIn("{{", spec)
        self.assertIn("2026-10-10", read(os.path.join(root, names["status_card"])))
        for d in ("sources_dir", "cards_dir", "topics_dir", "archive_dir", "notes_dir"):
            self.assertTrue(os.path.isdir(os.path.join(root, names[d])), d)

    def test_work_preset_follows_language(self):
        for lang, heading, card in (("zh", "表 A（Table A）：分区与主题", "# 状态卡"),
                                    ("en", "Table A: partitions and topics", "# Status card")):
            root = self.p("kb", "work-" + lang)
            run("init_library.py", "write", "--root", root, "--preset", "work", "--language", lang,
                "--timezone", "UTC", "--scope", "x", "--date", "2026-10-10")
            names = kbconf.load_library(root)["names"]
            spec = read(os.path.join(root, names["spec"]))
            self.assertIn(heading, spec)
            self.assertNotIn("{{", spec)
            self.assertTrue(read(os.path.join(root, names["status_card"])).startswith(card))

    def test_refuses_existing_library(self):
        root = self.p("lib")
        write(os.path.join(root, "notes.md"), "mine\n")
        p = run("init_library.py", "write", "--root", root, "--preset", "work", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertEqual(os.listdir(root), ["notes.md"])

    def test_render_for_upload(self):
        out = run("init_library.py", "render", "--out", self.p("out"), "--preset", "work", "--language", "en",
                  "--timezone", "UTC", "--tier", "strong").stdout
        self.assertIn("create the folders in the library: Sources, Cards, Topics, Archive, Quick-Notes", out)
        self.assertEqual(sorted(os.listdir(self.p("out"))), ["00_Spec.md", "00_Status-Card.md", "_kb.json"])
        self.assertEqual(json.loads(read(self.p("out", "_kb.json")))["tier"], "strong")

    def test_register_and_instructions(self):
        reg = self.p("cfg", "kb-libraries.json")
        run("init_library.py", "register", "--registry", reg, "--id", "atlas", "--label", "Atlas",
            "--scope", "Project Atlas", "--type", "local", "--root", self.p("atlas"))
        run("init_library.py", "register", "--registry", reg, "--id", "work", "--label", "Work",
            "--scope", "team projects", "--type", "gdrive", "--root", "abc123")
        p = run("init_library.py", "register", "--registry", reg, "--id", "work", "--label", "W",
                "--scope", "x", "--type", "gdrive", "--root", "zzz", check=False)
        self.assertEqual(p.returncode, 3)
        self.assertEqual([lib["id"] for lib in kbconf.load_registry(reg)["libraries"]], ["atlas", "work"])
        md = self.p("CLAUDE.md")
        write(md, "# My rules\n\nBe brief.\n")
        out = run("init_library.py", "instructions", "--registry", reg, "--file", md).stdout
        self.assertIn("would be added", out)
        self.assertEqual(read(md), "# My rules\n\nBe brief.\n")
        run("init_library.py", "instructions", "--registry", reg, "--file", md, "--apply")
        text = read(md)
        self.assertIn("Be brief.", text)
        self.assertIn("I keep knowledge bases: Atlas (Project Atlas); Work (team projects).", text)
        self.assertIn("to add documents, use kb-ingest.", text)
        self.assertNotIn("batch intake", text)
        out = run("init_library.py", "instructions", "--registry", reg, "--file", md, "--apply").stdout
        self.assertIn("unchanged", out)
        block = run("init_library.py", "instructions", "--registry", reg, "--project-block").stdout
        self.assertIn("Knowledge base registry (kb-libraries.json):", block)
        self.assertIn('"root": "abc123"', block)

    def test_every_preset_has_defaults(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        presets = sorted(os.listdir(il.PRESETS_DIR))
        self.assertEqual(presets, sorted(il.PRESETS))
        for p in presets:
            self.assertEqual(sorted(il.PRESET_DEFAULTS[p]), sorted(il.LANGUAGES))

    def test_drive_line(self):
        out = run("init_library.py", "instructions", "--drive-folder", "1AbCdEfGhIjKlMnOpQ", "--language", "zh").stdout
        self.assertIn("registry: Google Drive folder 1AbCdEfGhIjKlMnOpQ, file kb-libraries.json", out)
        self.assertTrue(out.startswith("我有知识库"))
        self.assertEqual(run("init_library.py", "instructions", "--drive-folder", "x y", check=False).returncode, 2)
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        text, what = il.upsert_line("a\n我有知识库：工作（x）。\n", il.drive_line("1AbCdEfGhIjKlMnOpQ", "zh"))
        self.assertEqual(what, "updated")
        self.assertEqual(text.count("我有知识库"), 1)

    def test_upsert_line(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        text, what = il.upsert_line("a\n我有知识库：旧（x）。\nb\n", "I keep knowledge bases: New (y).")
        self.assertEqual(what, "updated")
        self.assertEqual(text, "a\nI keep knowledge bases: New (y).\nb\n")
        self.assertEqual(il.upsert_line("", "L")[0], "L\n")


class WizardTest(Tmp):
    def wizard(self, answers):
        env = dict(os.environ, HOME=self.p("home"), USERPROFILE=self.p("home"), APPDATA=self.p("home", "appdata"),
                   XDG_CONFIG_HOME=self.p("home", ".config"), PYTHONIOENCODING="utf-8")
        env.pop("KB_LIBRARIES", None)
        return subprocess.run([sys.executable, os.path.join(ROOT, "install.py"), "--wizard"],
                              input="\n".join(answers) + "\n", capture_output=True, text=True,
                              encoding="utf-8", env=env)

    def registry(self):
        sys.path.insert(0, SCRIPTS)
        import init_library as il
        old = dict(os.environ)
        os.environ.update(HOME=self.p("home"), USERPROFILE=self.p("home"), APPDATA=self.p("home", "appdata"),
                          XDG_CONFIG_HOME=self.p("home", ".config"))
        os.environ.pop("KB_LIBRARIES", None)
        try:
            return kbconf.load_registry(il.registry_path())
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_install_setup_and_second_library(self):
        os.makedirs(self.p("home", ".claude"))
        claude_md = self.p("home", ".claude", "CLAUDE.md")
        write(claude_md, "# Mine\n")
        lib1, lib2 = self.p("home", "kb", "work"), self.p("home", "kb", "work2")
        # language, agent, install, set up, folder, scope, confirm preview, write line
        p = self.wizard(["2", "", "", "", lib1, "team projects", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        for s in ("kb-note", "kb-query", "kb-ingest"):
            self.assertTrue(os.path.isfile(self.p("home", ".claude", "skills", s, "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(lib1, "_kb.json")))
        self.assertIn("I keep knowledge bases: Work (team projects).", read(claude_md))
        # second run: keep the installed skills, a second work library gets a free id
        p = self.wizard(["2", "", "", "n", "", lib2, "", "3", "acme", "", ""])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("using 'work-2'", p.stdout)
        libs = self.registry()["libraries"]
        self.assertEqual([lib["id"] for lib in libs], ["work", "acme"])
        text = read(claude_md)
        self.assertTrue(text.startswith("# Mine\n"))
        self.assertEqual(text.count("I keep knowledge bases:"), 1)
        self.assertIn("Work (team projects); Work (work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports).", text)

    def test_cancel_writes_nothing(self):
        p = self.wizard(["2", "6", self.p("skills"), "n", "", self.p("lib"), "", "n"])
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("Nothing was written", p.stdout)
        self.assertFalse(os.path.exists(self.p("lib")))
        self.assertFalse(os.path.exists(self.p("skills")))

    def test_no_terminal_needs_options(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, "install.py")], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("--target", p.stderr)


QUERY = os.path.join(ROOT, "skills", "kb-query", "scripts", "kbfind.py")


def kbfind(*args):
    p = subprocess.run([sys.executable, QUERY, *args], capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise AssertionError(f"kbfind {args} exited {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p.stdout


class KbFindTest(Tmp):
    def setUp(self):
        super().setUp()
        write(self.p("lib", "_kb.json"), json.dumps({"schema": 2, "names": {"old_suffix": "_alt"}}))
        card = ["# Status card", "", "## Payments", ""] + [f"{i}. Item {i} about routine things" for i in range(1, 40)]
        card += ["40. Settlement window moves to 18:00 (basis: [[05_Ops_minutes_Window]])", "    continued line", "",
                 "## Projects", "", "Atlas launches in May; the settlement report follows.", "",
                 "| Item | Owner |", "| --- | --- |", "| Settlement report | Finance |"]
        write(self.p("lib", "00_Status-Card.md"), "\n".join(card) + "\n")
        write(self.p("lib", "05_Ops_minutes_Window.md"), "---\ntopic: \"Settlement\"\n---\n\nBody.\n")
        write(self.p("lib", "05_Ops_minutes_Window_alt20260101120000.md"), "settlement old\n")
        write(self.p("lib", "_intake-batches.json"), "settlement")
        write(self.p("lib", "_note.md"), "settlement")
        write(self.p("lib", "snapshot_card.md"), "settlement")
        write(self.p("lib", "Archive", "x.md"), "settlement")
        write(self.p("lib", "Entities", "Atlas.md"), "# Atlas\n\nSettlement owner.\n")

    def test_find_blocks(self):
        out = kbfind("find", self.p("lib"), "SETTLEMENT")
        self.assertIn("files searched: 2 | files with hits: 2 | blocks: 4", out)
        self.assertIn("-- lines 44-45 | Status card > Payments\n40. Settlement window moves to 18:00", out)
        self.assertIn("continued line", out)
        self.assertIn("| Status card > Projects\nAtlas launches in May", out)
        self.assertIn("| Item | Owner |\n| Settlement report | Finance |", out)  # the header row comes along
        self.assertIn("-- lines 1-3 | (no heading) | front matter", out)
        for skipped in ("old", "Archive", "snapshot", "_note", "Entities"):
            self.assertNotIn(skipped, out.split("\n", 1)[1])
        self.assertNotIn("Item 5 about", out)

    def test_find_options_and_caps(self):
        out = kbfind("find", self.p("lib"), "settlement", "atlas", "--all")
        self.assertIn("blocks: 1", out)
        out = kbfind("find", self.p("lib"), "item", "--file", "Status-Card", "--max-per-file", "3")
        self.assertIn("files searched: 1", out)
        self.assertIn("more blocks in this file", out)
        out = kbfind("find", self.p("lib"), "settlement", "--in", "Entities")
        self.assertIn("== Atlas.md", out)
        self.assertIn("no match", kbfind("find", self.p("lib"), "nothing-like-this"))
        p = subprocess.run([sys.executable, QUERY, "find", self.p("lib"), "x", "--in", "../.."], capture_output=True)
        self.assertEqual(p.returncode, 2)

    def test_toc(self):
        out = kbfind("toc", self.p("lib", "00_Status-Card.md"))
        self.assertIn("1-2 | # Status card", out)
        self.assertIn("3-46 | ## Payments |", out)
        self.assertIn("40 items", out)
        self.assertIn("| ## Projects |", out)
        self.assertIn("2 table rows", out)


class HookTest(unittest.TestCase):
    def test_commit_detection(self):
        sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
        import pre_commit
        for cmd in ("git commit -m x", "cd a && git -C sub commit -qam 'y'", "git -c user.name=t commit",
                    "git add -A && git commit -F msg.txt", "git add x;git commit -m y", "/usr/bin/git --no-pager commit"):
            self.assertTrue(pre_commit.is_commit(cmd), cmd)
        for cmd in ("git status", "git log --grep commit", "echo commit", "git commit-tree abc", "",
                    "git -C commit status", "legit commit"):
            self.assertFalse(pre_commit.is_commit(cmd), cmd)

    def hook(self, name, data):
        return subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", name)],
                              input=json.dumps(data), capture_output=True, text=True, encoding="utf-8")

    def test_shared_copy_edit_blocked(self):
        copy = os.path.join(ROOT, "skills", "kb-query", "references", "config.md")
        p = self.hook("shared_copies.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                          "tool_input": {"file_path": copy}})
        self.assertEqual(p.returncode, 2)
        self.assertIn("shared/references/config.md", p.stderr)
        for path in ("shared/references/config.md", "README.md", "/etc/hosts"):
            p = self.hook("shared_copies.py", {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                                              "tool_input": {"file_path": path}})
            self.assertEqual(p.returncode, 0, path)

    def test_commit_message_scan(self):
        with tempfile.TemporaryDirectory() as d:
            msg = os.path.join(d, "MSG")
            write(msg, "Fix it\n\n# real.person@gmail.com in a comment line\nCo-Authored-By: X <noreply@anthropic.com>\n")  # sensitive-scan: ignore
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 0)
            write(msg, "Bump actions\n\nSigned-off-by: dependabot[bot] <support@github.com>\n")
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 0)
            write(msg, "Ask real.person@gmail.com\n")  # sensitive-scan: ignore
            self.assertEqual(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "sensitive_scan.py"),
                                             "--message", msg], capture_output=True).returncode, 1)

    def test_other_commands_pass(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", "pre_commit.py")],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
