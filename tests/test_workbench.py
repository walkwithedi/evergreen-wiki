"""Tests for tools/opencode-setup (with a fake model endpoint), tools/workbench and
scripts/build_workbench.py. Standard library only: python3 -m unittest discover tests"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP = os.path.join(ROOT, "tools", "opencode-setup")
WORKBENCH = os.path.join(ROOT, "tools", "workbench")
LAUNCHER = "启动OpenCode工作台.desktop"
HAS_BASH = os.name == "posix" and shutil.which("bash") is not None and shutil.which("setsid") is not None


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class FakeModel:
    """A /v1/chat/completions endpoint that accepts one key and answers OK."""

    def __init__(self, key):
        seen = self.seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                seen.append((self.path, self.headers.get("Authorization"), json.loads(body)))
                ok = self.headers.get("Authorization") == "Bearer " + key
                data = {"choices": [{"message": {"content": "OK"}}]} if ok else {"error": "bad key"}
                out = json.dumps(data).encode()
                self.send_response(200 if ok else 401)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def log_message(self, *a):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/v1" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


@unittest.skipUnless(HAS_BASH, "needs bash and setsid")
class OpencodeSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.conf = os.path.join(self.home, ".config", "opencode", "opencode.jsonc")
        self.api = FakeModel("good-key-1234567890")
        self.addCleanup(self.api.stop)
        write(self.conf, '{\n  // the provider\n  "provider": {"local": {"options": {"baseURL": "%s",\n'
                         '    "apiKey": "placeholder"}, "models": {"m1": {}}}},\n  "model": "local/m1"\n}\n' % self.api.url)
        write(os.path.join(self.home, ".bashrc"), "# mine\n")

    def run_setup(self, *args, ak=None, extra=None):
        env = {"HOME": self.home, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "NO_PROXY": "127.0.0.1",
               "no_proxy": "127.0.0.1", "XDG_CONFIG_HOME": os.path.join(self.home, ".config")}
        if ak:
            env["CA_AK"] = ak
        env.update(extra or {})
        return subprocess.run(["bash", os.path.join(SETUP, "codeagent-setup.sh"), *args], env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_setup_replaces_the_key_after_a_passing_test(self):
        p = self.run_setup("setup", "-y", ak="good-key-1234567890")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        text = read(self.conf)
        self.assertIn('"apiKey": "good-key-1234567890"', text)  # sensitive-scan: ignore
        self.assertIn("// the provider", text)  # comments and the rest stay
        self.assertEqual(stat.S_IMODE(os.stat(self.conf).st_mode), 0o600)
        self.assertTrue(any(n.startswith("opencode.jsonc.bak.") for n in os.listdir(os.path.dirname(self.conf))))
        bashrc = read(os.path.join(self.home, ".bashrc"))
        self.assertTrue(bashrc.startswith("# mine\n"))
        self.assertIn("export OPENCODE_DISABLE_AUTOUPDATE=1", bashrc)
        path, auth, body = self.api.seen[-1]
        self.assertEqual((path, auth, body["model"]), ("/v1/chat/completions", "Bearer good-key-1234567890", "m1"))
        self.assertNotIn("good-key-1234567890", p.stderr)  # only the masked form is shown

    def test_a_failing_test_writes_nothing(self):
        before = read(self.conf)
        p = self.run_setup("setup", "-y", ak="wrong-key-0987654321")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("HTTP 401", p.stdout + p.stderr)
        self.assertEqual(read(self.conf), before)
        self.assertNotIn("OPENCODE_DISABLE", read(os.path.join(self.home, ".bashrc")))

    def test_hints_are_general_unless_a_hints_file_says_otherwise(self):
        def status(extra=None):
            out = self.run_setup("status", extra=extra).stdout
            return dict(ln.split("\t", 1) for ln in out.splitlines() if "\t" in ln)
        st = status()
        self.assertIn("管理方", st["ak_hint"])
        self.assertIn("nvm", st["node_hint"])
        hints = os.path.join(self.tmp, "hints.conf")
        write(hints, "# local wording\nAK_HINT=在示例门户的个人设置里查看\nOTHER=x\nNODE_HINT=$(touch pwned)\n")
        st = status({"CA_HINTS": hints})
        self.assertEqual(st["ak_hint"], "在示例门户的个人设置里查看")
        self.assertEqual(st["node_hint"], "$(touch pwned)")  # read as text, never run
        self.assertFalse(os.path.exists(os.path.join(self.home, "pwned")))


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def repo_zip(self, leave_out=()):
        path = os.path.join(self.tmp, "repo.zip")
        with zipfile.ZipFile(path, "w") as z:
            for rel in ("README.md", "tools/workbench/wk_web.py", "tools/workbench/" + LAUNCHER,
                        "tools/opencode-setup/ca_web.py", "tools/kb-client/kb_client.py"):
                if rel not in leave_out:
                    z.writestr("evergreen-wiki/" + rel, "x\n")
        return path

    def build(self, src):
        return subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_workbench.py"), src,
                               os.path.join(self.tmp, "bundle.zip")], capture_output=True, text=True)

    def test_entry_on_top_and_repository_beside_it(self):
        p = self.build(self.repo_zip())
        self.assertEqual(p.returncode, 0, p.stderr)
        with zipfile.ZipFile(os.path.join(self.tmp, "bundle.zip")) as z:
            names = z.namelist()
            self.assertEqual(names[0], LAUNCHER)
            self.assertEqual(z.getinfo(LAUNCHER).external_attr >> 16 & 0o777, 0o755)
            self.assertIn("evergreen-wiki/tools/kb-client/kb_client.py", names)

    def test_missing_tool_fails(self):
        p = self.build(self.repo_zip(leave_out=("tools/kb-client/kb_client.py",)))
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "bundle.zip")))

    def test_launcher_looks_next_to_itself_and_inside_the_bundle(self):
        text = read(os.path.join(WORKBENCH, LAUNCHER))
        self.assertIn("$d/evergreen-wiki/tools/workbench", text.replace("\\", ""))


@unittest.skipUnless(os.name == "posix", "the wizard runs on Linux desktops")
class WizardServerTest(unittest.TestCase):
    def test_wizard_finds_the_tools_of_this_repository(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=os.path.join(tmp, ".config"), PYTHONIOENCODING="utf-8")
        p = subprocess.Popen([sys.executable, os.path.join(WORKBENCH, "wk_web.py"), "--no-browser", "--idle", "0"],
                             env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.addCleanup(p.stdout.close)
        self.addCleanup(p.wait, 10)
        self.addCleanup(p.terminate)
        url = None
        deadline = time.time() + 30
        while url is None and time.time() < deadline:
            m = re.search(r"(http://127\.0\.0\.1:\d+/)\?t=(\S+)", p.stdout.readline())
            url = m and m.groups()
        self.assertTrue(url, "the wizard printed no address")
        with urllib.request.urlopen(url[0] + "api/state?t=" + url[1], timeout=60) as r:
            data = json.loads(r.read())
        self.assertTrue(data["wizard"]["kb_ready"])
        self.assertTrue(os.path.isfile(os.path.join(tmp, ".config", "work-kb", "location")))


if __name__ == "__main__":
    unittest.main()
