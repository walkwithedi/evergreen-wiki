"""Tests for tools/kb-client: the local server answered over HTTP the way the page answers it."""
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "kb-client", "kb_client.py")
CANCEL = object()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class Server:
    """kb_client.py in a subprocess, with requests as the page sends them."""

    def __init__(self, env, *args):
        self.proc = subprocess.Popen([sys.executable, TOOL, "--no-browser", "--lang", "en", *args],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                     env=env, text=True, encoding="utf-8")
        line = self.proc.stdout.readline()
        m = re.search(r"http://127\.0\.0\.1:(\d+)/\?t=(\S+)", line)
        if not m:
            self.proc.kill()
            raise AssertionError("no address printed: " + line + self.proc.stderr.read())
        self.port, self.token = int(m.group(1)), m.group(2)

    def request(self, method, path, body=None, token=True, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        h = dict(headers or {})
        if token:
            h["X-Token"] = self.token
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            return r.status, json.loads(raw or b"null")
        except ValueError:
            return r.status, raw.decode("utf-8", "replace")

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body, **kw):
        return self.request("POST", path, body, **kw)

    def run(self, action, answers, library=None):
        """Starts a step and answers its questions in turn; returns (result, printed text, questions)."""
        body = {"action": action}
        if library:
            body["library"] = library
        status, r = self.post("/api/action", body)
        if status != 200:
            raise AssertionError(f"{status} {r}")
        job = r["job"]
        answers = list(answers)
        out, asked = [], []
        self.asked = asked
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        c.request("GET", f"/api/events?job={job}&t={self.token}")
        resp = c.getresponse()
        self.last_type = resp.getheader("Content-Type")
        try:
            while True:
                line = resp.fp.readline().decode("utf-8")
                if not line:
                    raise AssertionError("event stream ended without an end event")
                if not line.startswith("data: "):
                    continue
                ev = json.loads(line[6:])
                if ev["type"] == "out":
                    out.append(ev["text"])
                elif ev["type"] == "ask":
                    asked.append(ev)
                    if not answers:
                        raise AssertionError("unexpected question: " + json.dumps(ev) + "\n" + "".join(out))
                    a = answers.pop(0)
                    if a is CANCEL:
                        self.post("/api/answer", {"job": job, "cancel": True})
                    else:
                        status, _ = self.post("/api/answer", {"job": job, "seq": ev["seq"], "value": a})
                        assert status == 200, status
                elif ev["type"] == "end":
                    return ev["result"], "".join(out), asked
        finally:
            c.close()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(10)
        self.proc.stdout.close()
        self.proc.stderr.close()


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class KbClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        os.makedirs(self.p("home", ".claude"))
        write(self.p("home", ".claude", "CLAUDE.md"), "# Mine\n")
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"),
                        PYTHONIOENCODING="utf-8", PATH=os.path.dirname(sys.executable))
        for k in ("KB_LIBRARIES", "LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            self.env.pop(k, None)
        self.server = Server(self.env, "--idle", "0")
        self.addCleanup(self.server.stop)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def setup_library(self):
        # agent, install the skills, set up a library, its kind, folder and scope,
        # write it (Enter at the preview), add the knowledge-base line
        return self.server.run("setup", ["claude-code", True, True, "work", self.p("home", "kb", "work"),
                                         "team projects", "", True])

    def test_requests_need_the_token_and_the_local_host(self):
        s = self.server
        self.assertEqual(s.get("/api/state", token=False)[0], 403)
        self.assertEqual(s.get("/api/state?t=wrong", token=False)[0], 403)
        self.assertEqual(s.get(f"/api/state?t={s.token}", token=False)[0], 200)
        self.assertEqual(s.get("/api/state", headers={"Host": "example.com"})[0], 403)
        self.assertEqual(s.post("/api/action", {"action": "backup"}, token=False)[0], 403)
        self.assertEqual(s.post("/api/action", {"action": "rm"})[0], 400)
        self.assertEqual(s.request("POST", "/api/action", {"action": "backup"},
                                   headers={"Content-Type": "text/plain"})[0], 415)
        status, page = s.get("/", token=False)
        self.assertEqual(status, 200)
        self.assertIn("app.js", page)
        self.assertEqual(s.get("/../install.py", token=False)[0], 404)
        self.assertEqual(s.get("/%2e%2e/install.py", token=False)[0], 404)
        self.assertEqual(s.get("/kb_client.py", token=False)[0], 404)
        self.assertEqual(s.get("/app.js", token=False)[0], 200)

    def test_state_before_and_after_setup(self):
        status, st = self.server.get("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(st["libraries"], [])
        self.assertEqual(st["skills"], [])
        self.assertEqual(st["agent"]["program"], "")
        result, out, asked = self.setup_library()
        self.assertEqual(result, "ok", out)
        self.assertEqual(self.server.last_type, "text/event-stream; charset=utf-8")
        self.assertIn("Preview", out)
        self.assertTrue(any(q["kind"] == "folder" for q in asked))
        self.assertTrue(os.path.isfile(self.p("home", ".claude", "skills", "kb-note", "SKILL.md")))
        self.assertTrue(os.path.isfile(self.p("home", "kb", "work", "_kb.json")))
        self.assertIn("I keep knowledge bases: Work (team projects).", read(self.p("home", ".claude", "CLAUDE.md")))
        st = self.server.get("/api/state")[1]
        self.assertEqual([x["id"] for x in st["libraries"]], ["work"])
        self.assertTrue(st["libraries"][0]["exists"] and st["libraries"][0]["movable"])
        self.assertEqual(st["skills"][0]["agent"], "claude-code")
        self.assertGreaterEqual(st["backups"], 1)

    def test_cancel_writes_nothing(self):
        result, out, _ = self.server.run("setup", ["claude-code", CANCEL])
        self.assertEqual(result, "stopped", out)
        self.assertIn("Cancelled", out)
        self.assertFalse(os.path.exists(self.p("home", ".claude", "skills")))
        self.assertFalse(os.path.exists(self.p("home", "kb")))

    def test_one_step_at_a_time_and_stale_answers(self):
        s = self.server
        status, r = s.post("/api/action", {"action": "setup"})
        self.assertEqual(status, 200)
        job = r["job"]
        self.assertEqual(s.post("/api/action", {"action": "backup"})[0], 409)
        for _ in range(100):  # wait for the first question
            if s.get("/api/state")[1]["job"]["id"] == job:
                break
        self.assertEqual(s.post("/api/answer", {"job": job, "seq": 999, "value": "x"})[0], 409)
        self.assertEqual(s.post("/api/answer", {"job": "other", "seq": 1, "value": "x"})[0], 404)
        s.post("/api/answer", {"job": job, "cancel": True})
        for _ in range(100):
            if s.get("/api/state")[1]["job"]["done"]:
                break
            time.sleep(0.05)
        self.assertTrue(s.get("/api/state")[1]["job"]["done"])
        self.assertEqual(s.post("/api/action", {"action": "backup"})[0], 200)

    def test_backup_and_rollback(self):
        self.setup_library()
        result, out, _ = self.server.run("backup", [])
        self.assertEqual(result, "ok", out)
        self.assertIn("Backup", out)
        write(self.p("home", ".claude", "CLAUDE.md"), "# Changed\n")
        n = self.server.get("/api/state")[1]["backups"]
        backups = sorted(os.listdir(self.p("home", ".config", "evergreen-wiki", "backup")))
        result, out, asked = self.server.run("rollback", [backups[-1], True])
        self.assertEqual(result, "ok", out)
        self.assertEqual(asked[0]["kind"], "choose")
        self.assertIn("I keep knowledge bases", read(self.p("home", ".claude", "CLAUDE.md")))
        self.assertEqual(self.server.get("/api/state")[1]["backups"], n + 1)  # the state before the restore

    def test_move_a_library(self):
        self.setup_library()
        dest = self.p("disk")
        os.makedirs(dest)
        # the folder to move into, confirm the move, keep the originals
        result, out, asked = self.server.run("move", [dest, True, False], library="work")
        self.assertEqual(result, "ok", out)
        self.assertEqual(asked[0]["kind"], "folder")
        reg = json.loads(read(self.p("home", ".config", "kb", "kb-libraries.json")))
        self.assertEqual(reg["libraries"][0]["backend"]["root"], os.path.join(dest, "work"))
        self.assertTrue(os.path.isfile(os.path.join(dest, "work", "_kb.json")))
        self.assertTrue(os.path.isdir(self.p("home", "kb", "work")))
        self.assertEqual(self.server.get("/api/state")[1]["libraries"][0]["root"], os.path.join(dest, "work"))

    def test_cancelled_management_step(self):
        self.setup_library()
        result, out, _ = self.server.run("rollback", [CANCEL])
        self.assertEqual(result, "stopped", out)
        self.assertIn("Cancelled", out)

    def test_move_without_a_library(self):
        result, out, asked = self.server.run("move", [])
        self.assertEqual(result, "ok")
        self.assertIn("No registered library", out)
        self.assertEqual(asked, [])

    def test_uninstall_keeps_the_library(self):
        self.setup_library()
        # delete library folders: no (the default), uninstall: yes
        result, out, asked = self.server.run("uninstall", [False, True])
        self.assertEqual(result, "ok", out)
        self.assertFalse(os.path.exists(self.p("home", ".claude", "skills", "kb-note")))
        self.assertNotIn("I keep knowledge bases", read(self.p("home", ".claude", "CLAUDE.md")))
        self.assertTrue(os.path.isfile(self.p("home", "kb", "work", "_kb.json")))
        self.assertEqual(self.server.get("/api/state")[1]["libraries"], [])

    def test_answers_of_the_wrong_type_take_the_default(self):
        # a yes question answered with text counts as its default (yes); a folder question answered with a
        # number counts as no answer, so it is asked again
        result, out, asked = self.server.run("setup", ["claude-code", "yes", True, "work", 7,
                                                       self.p("home", "kb", "work"), "team projects", "", True])
        self.assertEqual(result, "ok", out)
        self.assertEqual([q["kind"] for q in asked].count("folder"), 2)
        self.assertTrue(os.path.isfile(self.p("home", "kb", "work", "_kb.json")))

    def test_folder_listing_reads_only(self):
        os.makedirs(self.p("home", "Documents", "b"))
        os.makedirs(self.p("home", ".hidden"))
        write(self.p("home", "Documents", "a.txt"), "x")
        status, r = self.server.get("/api/fs?path=" + self.p("home", "Documents"))
        self.assertEqual(status, 200)
        self.assertEqual([(e["name"], e["dir"]) for e in r["entries"]], [("b", True), ("a.txt", False)])
        self.assertEqual(r["parent"], self.home)
        names = [e["name"] for e in self.server.get("/api/fs?path=" + self.home)[1]["entries"]]
        self.assertNotIn(".hidden", names)
        names = [e["name"] for e in self.server.get("/api/fs?hidden=1&path=" + self.home)[1]["entries"]]
        self.assertIn(".hidden", names)
        self.assertEqual(self.server.get("/api/fs?path=relative/path")[0], 400)
        self.assertEqual(self.server.get("/api/fs?path=" + self.p("home", "Documents", "a.txt"))[0], 400)
        self.assertEqual(self.server.get("/api/fs?path=" + self.p("missing"))[0], 400)
        r = self.server.get("/api/fs?nearest=1&path=" + self.p("home", "kb", "work"))[1]
        self.assertEqual(r["path"], self.home)  # a folder not made yet opens at its parent
        self.assertEqual(self.server.get("/api/fs?path=" + self.home)[1]["parent"], "")
        # nothing outside the home folder and the mounted drives, not even through a link
        self.assertEqual(self.server.get("/api/fs?path=/")[0], 400)
        self.assertEqual(self.server.get("/api/fs?path=" + self.tmp)[0], 400)
        self.assertEqual(self.server.get("/api/fs?nearest=1&path=" + self.p("elsewhere", "x"))[0], 400)
        os.symlink(self.tmp, self.p("home", "out"))
        self.assertEqual(self.server.get("/api/fs?path=" + self.p("home", "out"))[0], 400)
        self.assertEqual(self.server.request("PUT", "/api/fs?path=" + self.home)[0], 501)
        places = self.server.get("/api/places")[1]["places"]
        self.assertEqual(places[0], {"path": self.home, "kind": "home"})

    def test_model_check(self):
        write(self.p("home", ".config", "opencode", "opencode.jsonc"),
              '{\n  // the model\n  "model": "example/model-1",\n}\n')
        agent = self.server.get("/api/state")[1]["agent"]
        self.assertTrue(agent["model"])
        self.assertTrue(agent["config"].endswith("opencode.jsonc"))

    def test_quit(self):
        self.assertEqual(self.server.post("/api/quit", {})[0], 200)
        self.assertEqual(self.server.proc.wait(10), 0)


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class IdleTest(unittest.TestCase):
    def test_stops_without_the_page(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=os.path.join(tmp, ".config"), PYTHONIOENCODING="utf-8")
        s = Server(env, "--idle", "1")
        self.addCleanup(s.stop)
        self.assertEqual(s.proc.wait(15), 0)


if __name__ == "__main__":
    unittest.main()
