"""Unit tests for scripts/sensitive_scan.py. Standard library only: python3 -m unittest discover tests

Sample secrets are built by joining pieces, so this file itself holds no complete one and passes
both the scanner and gitleaks."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import sensitive_scan as ss  # noqa: E402

# Variables that point git at another repository: a hook (git commit -a sets GIT_INDEX_FILE to its own
# index) passes them on, and the temporary repositories below must use only their own.
OUTER_GIT = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
             "GIT_COMMON_DIR", "GIT_PREFIX")
ENV = dict({k: v for k, v in os.environ.items() if k not in OUTER_GIT}, SENSITIVE_TERMS="",
           SENSITIVE_TERMS_FILE=os.devnull, GITHUB_ACTIONS="", PYTHONIOENCODING="utf-8")


def labels(line, terms=()):
    sc = ss.Scanner(terms=[ss.re.compile(ss.re.escape(t), ss.re.I) for t in terms])
    sc.line("x.md", 1, line)
    return [f.label for f in sc.findings]


def png(*chunks):
    out = b"\x89PNG\r\n\x1a\n"
    for kind, body in chunks + ((b"IEND", b""),):
        out += len(body).to_bytes(4, "big") + kind + body + b"\0\0\0\0"
    return out


def office(core="", app=""):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("docProps/core.xml", core)
        z.writestr("docProps/app.xml", app)
    return buf.getvalue()


class RuleTest(unittest.TestCase):
    def test_personal(self):
        self.assertEqual(labels("mail " + "li.lei" + "@gmail.com"), ["e-mail"])
        self.assertEqual(labels("call 1" + "3812345678"), ["phone"])
        self.assertEqual(labels("tel 021-" + "12345678"), ["landline"])
        self.assertEqual(labels("id 11010519491231002" + "X"), ["ID number"])
        self.assertEqual(labels("id 11010519491231002" + "1"), [])  # wrong check digit
        self.assertEqual(labels("card 4111 1111 " + "1111 1111"), ["card number"])
        self.assertEqual(labels("order 62220212345" + "67890123"), [])  # fails Luhn
        self.assertEqual(labels("姓名" + "：王伟"), ["personal field"])
        self.assertEqual(labels("/home/" + "liwei/notes"), ["home path"])

    def test_work(self):
        self.assertEqual(labels("build01" + ".corp"), ["internal domain"])
        self.assertEqual(labels("北京星河科技" + "有限公司"), ["organisation"])
        self.assertEqual(labels("星河（北京）" + "有限公司"), ["organisation"])
        self.assertEqual(labels("Shanghai Foo " + "Co., Ltd"), ["organisation"])
        self.assertEqual(labels("10.1." + "2.3"), ["IP address"])
        self.assertEqual(labels("8.8." + "4.4"), ["IP address"])
        self.assertEqual(labels("\\\\" + "fileserv\\share"), ["UNC path"])
        self.assertEqual(labels("D:" + "\\Projects"), ["Windows path"])
        self.assertEqual(labels("/media/" + "wang/USB/"), ["mount path"])
        self.assertEqual(labels("/mnt/" + "nas/x"), ["mount path"])
        self.assertEqual(labels("smb" + "://nas"), ["network share"])
        self.assertEqual(labels("/opt/" + "acme/bin"), ["system directory"])
        for line in ("本文件为内部" + "资料", "严禁" + "外传", "CONFIDEN" + "TIAL", "Internal use " + "only",
                     "Do not " + "distribute", "Proprie" + "tary and private"):
            self.assertEqual(labels(line), ["confidentiality marker"], line)
        self.assertEqual(labels("keeps confidential data out"), [])
        # everyday words, too common to block on
        self.assertEqual(labels("请注意保密，这不是秘密"), [])

    def test_credentials(self):
        self.assertEqual(labels("ghp_" + "a" * 36), ["GitHub token"])
        self.assertEqual(labels("AIza" + "b" * 35), ["Google API key"])
        self.assertEqual(labels("AKIA" + "ABCDEFGHIJKLMNOP"), ["AWS key"])
        self.assertEqual(labels("sk-ant-" + "x" * 30), ["API key"])
        self.assertEqual(labels("-----BEGIN RSA " + "PRIVATE KEY-----"), ["private key"])
        self.assertEqual(labels("postgres://app:" + "hunter22@db"), ["password in URL"])
        self.assertEqual(labels("password = '" + "S3cretPassw0rd'"), ["secret value"])

    def test_placeholders_pass(self):
        for line in ("上海某某" + "有限公司", "密码" + "：<your password>", "password: '<your-" + "password>'",
                     "see 192.0." + "2.10 and 127.0.0.1", "version 1.2.0 and 1.2.300.4", "FileManager.local()",
                     "Scope.INTERNAL", "单位名称后缀（有限" + "公司、集团）", "「姓名" + "：」「密码：」", "escape \\n", "/home/user/x and /mnt/user-data/outputs",
                     "~/.config/x", "https://example.com/opt/x", "a@example.com", "x " + ss.MARK + " 10.1." + "2.3"):
            self.assertEqual(labels(line), [], line)

    def test_private_terms(self):
        self.assertEqual(labels("Report for ACME team", ["acme"]), ["private term"])
        # the ignore marker does not hide a private term
        self.assertEqual(labels("ACME " + ss.MARK, ["acme"]), ["private term"])

    def test_load_terms(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "terms.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# comment\nAcme\n\nX\n星河\n")
            old = dict(os.environ)
            try:
                os.environ.update(SENSITIVE_TERMS="acme\nOrbit", SENSITIVE_TERMS_FILE=path)
                terms = ss.load_terms()
            finally:
                os.environ.clear()
                os.environ.update(old)
        self.assertEqual(len(terms), 3)  # acme once, Orbit, 星河; "X" is too short
        sc = ss.Scanner(terms=terms)
        for line in ("acme-corp", "an Orbit", "星河项目"):
            sc.line("x", 1, line)
        sc.line("x", 1, "Acmeville and orbital")  # whole words only for Latin terms
        self.assertEqual(len(sc.findings), 3)

    def test_redaction(self):
        f = ss.Finding("a.md", 3, "e-mail", "secret@corp")
        self.assertEqual(f.show(True), "a.md:3: e-mail")
        self.assertIn("secret@corp", f.show(False))


class MetadataTest(unittest.TestCase):
    def test_jpeg(self):
        exif = b"Exif\0\0" + b"\x88\x25" + b"\0" * 8
        jpg = b"\xff\xd8\xff\xe1" + (len(exif) + 2).to_bytes(2, "big") + exif + b"\xff\xda"
        self.assertEqual(ss.file_metadata("a.jpg", jpg), ["EXIF metadata with GPS location"])
        self.assertEqual(ss.file_metadata("a.jpg", b"\xff\xd8\xff\xda"), [])

    def test_png(self):
        self.assertEqual(ss.file_metadata("a.png", png((b"tEXt", b"Author\0Li"))), ["PNG text chunk 'Author'"])
        self.assertEqual(ss.file_metadata("a.png", png((b"eXIf", b"MM"))), ["EXIF metadata"])
        self.assertEqual(ss.file_metadata("a.png", png((b"tEXt", b"Software\0x"))), [])

    def test_office_pdf_heic(self):
        self.assertEqual(ss.file_metadata("a.docx", office("<dc:creator>Li</dc:creator>", "<Company>Q</Company>")),
                         ["document author", "document company or manager"])
        self.assertEqual(ss.file_metadata("a.docx", office("<dc:creator></dc:creator>")), [])
        self.assertEqual(ss.file_metadata("a.pdf", b"%PDF-1.7 /Author (Li)"), ["PDF author"])
        self.assertEqual(ss.file_metadata("a.pdf", b"%PDF-1.7 /Author ()"), [])
        self.assertTrue(ss.file_metadata("IMG_1.HEIC", b"")[0].startswith("HEIC photo"))


class GitTest(unittest.TestCase):
    """--range, --history and --unpushed against a scratch repository with a copy of the script."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = self._t.name
        os.makedirs(os.path.join(self.d, "scripts"))
        shutil.copy(os.path.join(ROOT, "scripts", "sensitive_scan.py"), os.path.join(self.d, "scripts"))
        self.git("init", "-q", "-b", "main")
        self.commit("start", "README.md", "hello\n")

    def tearDown(self):
        self._t.cleanup()

    def git(self, *args, email="1+me@users.noreply.github.com"):
        env = dict(ENV, GIT_AUTHOR_NAME="me", GIT_COMMITTER_NAME="me", GIT_AUTHOR_EMAIL=email,
                   GIT_COMMITTER_EMAIL=email)
        return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=self.d, env=env,
                              capture_output=True, text=True, check=True).stdout

    def commit(self, msg, name, content, **kw):
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(os.path.join(self.d, name), mode) as f:
            f.write(content)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, **kw)

    def scan(self, *args, **env):
        return subprocess.run([sys.executable, os.path.join(self.d, "scripts", "sensitive_scan.py"), *args],
                              cwd=self.d, env=dict(ENV, **env), capture_output=True, text=True, encoding="utf-8")

    def test_history_finds_removed_lines(self):
        self.commit("add", "notes.md", "server 10.1." + "2.3\n")
        self.commit("remove", "notes.md", "nothing here\n")
        self.assertEqual(self.scan().returncode, 0)  # the current tree is clean
        p = self.scan("--history")
        self.assertEqual(p.returncode, 1)
        self.assertIn("notes.md@", p.stdout)
        self.assertIn("IP address", p.stdout)

    def test_range_checks_messages_identities_and_images(self):
        base = self.git("rev-parse", "HEAD").strip()
        self.commit("ask li.lei" + "@gmail.com", "a.md", "ok\n", email="li.lei" + "@gmail.com")
        self.commit("photo", "p.png", png((b"tEXt", b"Author\0Li")))
        p = self.scan("--range", base + "..HEAD")
        self.assertEqual(p.returncode, 1)
        for text in ("message", "author e-mail is not a noreply address", "committer e-mail",
                     "PNG text chunk 'Author'"):
            self.assertIn(text, p.stdout)

    def test_untracked_file_is_scanned(self):
        with open(os.path.join(self.d, "new.md"), "w") as f:
            f.write("host build01" + ".corp\n")
        p = self.scan()
        self.assertEqual(p.returncode, 1)
        self.assertIn("new.md:1: internal domain", p.stdout)

    def test_actions_output_is_redacted(self):
        self.commit("add", "notes.md", "mail li.lei" + "@gmail.com\n")
        p = self.scan(GITHUB_ACTIONS="true")
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("li.lei", p.stdout)
        self.assertIn("notes.md:1: e-mail", p.stdout)

    def test_private_terms_from_environment(self):
        self.commit("add", "notes.md", "Report for the Orbit team\n")
        self.assertEqual(self.scan().returncode, 0)
        p = self.scan(SENSITIVE_TERMS="orbit", GITHUB_ACTIONS="true")
        self.assertEqual(p.returncode, 1)
        self.assertIn("private term", p.stdout)
        self.assertNotIn("rbit", p.stdout)

    def test_unpushed(self):
        self.commit("add", "notes.md", "/media/" + "wang/USB/\n")
        p = self.scan("--unpushed")  # no remote: every local commit counts
        self.assertEqual(p.returncode, 1)
        self.assertIn("mount path", p.stdout)


class OuterGitTest(unittest.TestCase):
    def test_temporary_repositories_ignore_the_outer_index(self):
        # a hook run by `git commit -a` gets GIT_INDEX_FILE pointing at that commit's own index; the
        # temporary repositories of these tests must never write into it
        with tempfile.TemporaryDirectory() as d:
            index = os.path.join(d, "outer-index")
            p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p",
                                "test_sensitive_scan.py", "-k", "GitTest.test_history_finds_removed_lines"],
                               cwd=ROOT, env=dict(os.environ, GIT_INDEX_FILE=index), capture_output=True,
                               text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("Ran 1 test", p.stderr)
            self.assertFalse(os.path.exists(index))


class PushHookTest(unittest.TestCase):
    def test_push_detection(self):
        sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
        import pre_commit
        self.assertEqual(pre_commit.git_subcommands("git add x && git commit -m y && git push -u origin b"),
                         {"add", "commit", "push"})
        self.assertNotIn("push", pre_commit.git_subcommands("git log --grep push"))

    def test_message_file(self):
        sys.path.insert(0, os.path.join(ROOT, ".claude", "hooks"))
        import pre_commit
        for cmd, want in (("git commit -F msg.txt", "msg.txt"), ("git commit -aF m.txt", "m.txt"),
                          ("git commit --file=x.txt", "x.txt"), ("git commit -am 'F x'", None),
                          ("git commit -m y", None)):
            self.assertEqual(pre_commit.message_file(cmd), want, cmd)

    def test_commit_command_scanned(self):
        p = subprocess.run([sys.executable, os.path.join(ROOT, ".claude", "hooks", "pre_commit.py")],
                           input=json.dumps({"tool_name": "Bash", "tool_input": {
                               "command": "git commit -m 'ask li.lei" + "@gmail.com'"}}),
                           capture_output=True, text=True, encoding="utf-8", env=ENV)
        self.assertEqual(p.returncode, 2)
        self.assertIn("report the findings above to the user", p.stderr)


if __name__ == "__main__":
    unittest.main()
