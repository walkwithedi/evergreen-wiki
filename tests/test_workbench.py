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
        out = subprocess.run([sys.executable, os.path.join(SETUP, "ca_config.py"), "summary-opencode", self.conf],
                             capture_output=True, text=True, encoding="utf-8").stdout
        self.assertIn("AK good…7890（共 19 位）", out)  # the ends, to tell which key it is
        self.assertNotIn("good-key-1234567890", out)

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


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class VersionSwitchTest(unittest.TestCase):
    """The wizard does not restart a client that is busy: a management step, or a conversation that works
    or waits for an answer (an ingest run goes on in a conversation)."""

    def setUp(self):
        sys.path.insert(0, SETUP)
        self.addCleanup(sys.path.remove, SETUP)
        wk = load("wk_web_test", os.path.join(WORKBENCH, "wk_web.py"))
        wk.ca_web = load("ca_web", os.path.join(SETUP, "ca_web.py"))
        cls = wk.make_app_class()
        self.app = cls.__new__(cls)  # no server: only the switching logic is tested
        self.answers = {"/api/state": {"job": None},
                        "/api/chat/state": {"agent": {"windows": [{"id": "w1", "status": "idle", "cards": 0}]}}}
        self.app.kb_call = lambda method, path: self.answers.get(path)
        self.app.kb_proc = type("Running", (), {"poll": lambda _self: None})()
        self.app.kb_url, self.app.kb_simple, self.app.kb_lock = "http://127.0.0.1:1/?t=x", True, threading.Lock()
        self.stopped = []
        self.app.stop_kb = lambda: self.stopped.append(True)

    def windows(self, *wins):
        self.answers["/api/chat/state"] = {"agent": {"windows": list(wins)}}

    def test_busy_states(self):
        self.assertEqual(self.app.kb_busy(), "")
        self.windows({"id": "w1", "status": "idle", "cards": 0}, {"id": "w2", "status": "busy", "cards": 0})
        self.assertEqual(self.app.kb_busy(), "chat")
        self.windows({"id": "w1", "status": "idle", "cards": 1})
        self.assertEqual(self.app.kb_busy(), "chat")
        self.windows({"id": "w1", "status": "idle", "cards": 0})
        self.answers["/api/ingest"] = {"run": {"state": "waiting"}}
        self.assertEqual(self.app.kb_busy(), "ingest")
        self.answers["/api/ingest"] = {"run": {"state": "done"}}
        self.assertEqual(self.app.kb_busy(), "")
        self.answers["/api/state"] = {"job": {"id": 1, "action": "install", "done": False}}
        self.assertEqual(self.app.kb_busy(), "step")

    def test_switch_refused_while_a_conversation_works(self):
        self.windows({"id": "w1", "status": "busy", "cards": 0})
        url, err = self.app.open_kb(simple=False)
        self.assertEqual(url, "")
        self.assertIn("对话", err)
        self.assertEqual(self.stopped, [])

    def test_same_version_is_not_restarted(self):
        self.windows({"id": "w1", "status": "busy", "cards": 0})
        self.assertEqual(self.app.open_kb(simple=True), (self.app.kb_url, ""))


class MaskTest(unittest.TestCase):
    def test_key_shows_its_ends_and_length(self):
        sys.path.insert(0, SETUP)
        self.addCleanup(sys.path.remove, SETUP)
        cfg = load("ca_config_test", os.path.join(SETUP, "ca_config.py"))
        self.assertEqual(cfg.mask("abcd-0000-wxyz"), "abcd…wxyz（共 14 位）")
        self.assertEqual(cfg.mask("short"), "*****")
        self.assertEqual(cfg.mask("{env:KEY}"), "取自环境变量")
        self.assertEqual(cfg.mask(""), "（未设置）")


if __name__ == "__main__":
    unittest.main()
