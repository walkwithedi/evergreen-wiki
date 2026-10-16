"""Tests for tools/kb-client: the local server answered over HTTP the way the page answers it."""
import http.client
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "kb-client", "kb_client.py")
FAKE = os.path.join(ROOT, "tests", "kb_client_fake_opencode.py")
CANCEL = object()
sys.path.insert(0, os.path.join(ROOT, "tools", "kb-client"))
import agent  # noqa: E402
import intake as intake_mod  # noqa: E402
import kb_client  # noqa: E402


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

    def run(self, action, answers, library=None, skill=None):
        """Starts a step and answers its questions in turn; returns (result, printed text, questions)."""
        body = {"action": action}
        if library:
            body["library"] = library
        if skill:
            body["skill"] = skill
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
        os.makedirs(self.p("tmp"))
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"), TMPDIR=self.p("tmp"),
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

    def test_page_layout(self):
        # the knowledge-base button follows the title; the read-only skill list sits in the side column
        page = self.server.get("/", token=False)[1]
        self.assertLess(page.index('id="title"'), page.index('id="kb-toggle"'))
        self.assertLess(page.index('id="kb-toggle"'), page.index('id="status"'))
        side = page[page.index('<aside class="side">'):page.index("</aside>")]
        for part in ('id="skills-panel"', 'id="skills-filter"', 'id="skill-rows"'):
            self.assertIn(part, side)
        # answers are built as DOM nodes: the page never writes HTML from text
        script = self.server.get("/app.js", token=False)[1]
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("insertAdjacentHTML", script)

    def test_simple_refuses_the_hidden_steps(self):
        self.assertFalse(self.server.get("/api/state")[1]["simple"])
        s = Server(self.env, "--idle", "0", "--simple")
        self.addCleanup(s.stop)
        self.assertTrue(s.get("/api/state")[1]["simple"])
        for action in ("rollback", "move", "uninstall", "skill_backup", "skill_restore", "skill_import", "skill_new"):
            self.assertEqual(s.post("/api/action", {"action": action})[0], 403, action)
        self.assertEqual(s.post("/api/chat/forget", {})[0], 403)
        self.assertNotEqual(s.post("/api/chat/allow_all", {"on": True})[0], 403)  # Allow everything stays
        self.assertEqual(s.post("/api/action", {"action": "backup"})[0], 200)
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
        kind = [q for q in asked if q["kind"] == "choose" and [o["value"] for o in q["options"]] == ["life", "work"]]
        self.assertEqual(kind[0]["default"], "work")  # the client suggests a work library
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

    def test_checklist_state(self):
        st = self.server.get("/api/state")[1]
        self.assertEqual((st["opencode_skills"], st["instructions"]), (False, False))
        self.assertIsInstance(st["pdftotext"], bool)
        result, out, _ = self.setup_library()
        self.assertEqual(result, "ok", out)
        st = self.server.get("/api/state")[1]
        # OpenCode reads Claude Code's skills, and its CLAUDE.md while it has no AGENTS.md of its own
        self.assertEqual((st["opencode_skills"], st["instructions"]), (True, True))
        write(self.p("home", ".config", "opencode", "AGENTS.md"), "# Mine\n")
        self.assertFalse(self.server.get("/api/state")[1]["instructions"])

    def test_preview_answered_with_choices(self):
        # agent, install, set up, kind, folder, scope; at the preview: change item 2 (Label), then write
        result, out, asked = self.server.run("setup", ["claude-code", True, True, "work", self.p("home", "kb", "work"),
                                                       "team projects", "change", "2", "Team", "write", True])
        self.assertEqual(result, "ok", out)
        previews = [q for q in asked if q["kind"] == "choose" and q["options"][0]["value"] == "write"]
        self.assertEqual(len(previews), 2)
        self.assertEqual([o["value"] for o in previews[0]["options"]], ["write", "change", "cancel"])
        items = next(q for q in asked if q["kind"] == "choose" and q["options"][0]["value"] == "1")
        self.assertEqual(len(items["options"]), 9)
        self.assertEqual(json.loads(read(self.p("home", "kb", "work", "_kb.json")))["label"], "Team")

    def test_preview_cancelled_with_a_choice(self):
        result, out, _ = self.server.run("setup", ["claude-code", True, True, "work", self.p("home", "kb", "work"),
                                                   "team projects", "cancel"])
        self.assertIn("Cancelled", out)
        self.assertFalse(os.path.exists(self.p("home", "kb", "work", "_kb.json")))

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

    def test_progress(self):
        self.assertEqual(self.server.get("/api/progress")[1], {"progress": []})
        result, out, _ = self.setup_library()
        self.assertEqual(result, "ok", out)
        self.assertEqual(self.server.get("/api/progress")[1], {"progress": []})  # no run open
        batches = [{"n": 1, "group": "minutes", "part": "", "status": "done", "files": [{"path": "/x/a.docx"}],
                    "result": {"written": 4, "duplicates": 1, "review": 0}},
                   {"n": 2, "group": "plans", "part": "1/2", "status": "started", "files": [], "result": {}},
                   {"n": 3, "group": "plans", "part": "2/2", "status": "pending", "files": [], "result": {}}]
        write(self.p("home", "kb", "work", "_intake-batches.json"),
              json.dumps({"schema": 1, "batches": batches, "final_step": "pending"}))
        p = self.server.get("/api/progress")[1]["progress"]
        self.assertEqual(len(p), 1)
        p = p[0]
        self.assertEqual((p["id"], p["batches"], p["done"], p["skipped"], p["current"], p["current_group"]),
                         ("work", 3, 1, 0, 2, "plans"))
        self.assertEqual((p["written"], p["duplicates"], p["review"], p["final_step"]), (4, 1, 0, "pending"))
        self.assertEqual(p["finished"], [{"n": 1, "group": "minutes", "part": "",
                                          "result": {"written": 4, "duplicates": 1, "review": 0}}])
        self.assertNotIn("/x/a.docx", json.dumps(p))  # counts, not file paths
        write(self.p("home", "kb", "work", "_intake-batches.json"), "{broken")
        self.assertEqual(self.server.get("/api/progress")[1], {"progress": []})

    def test_graph_of_a_registered_library(self):
        self.assertEqual(self.server.get("/api/graph?lib=work")[0], 404)
        result, out, _ = self.setup_library()
        self.assertEqual(result, "ok", out)
        status, g = self.server.get("/api/graph?lib=work")
        self.assertEqual(status, 200)
        self.assertEqual((g["label"], g["root"]), ("Work", self.p("home", "kb", "work")))
        self.assertIn("00_Status-Card", {n["id"] for n in g["nodes"]})
        self.assertTrue(all(n["new"] for n in g["nodes"] if n["kind"] == "summary"))  # written after the start
        self.assertEqual(self.server.get("/api/graph?lib=../etc")[0], 404)

    def test_skills_report_the_release_version(self):
        self.assertEqual(self.setup_library()[0], "ok")
        skills = self.server.get("/api/skills")[1]["skills"]
        kb = [x for x in skills if x["kb"]]
        self.assertEqual(len(kb), 3, skills)
        for x in kb:
            self.assertTrue(x["release"], x)
            self.assertEqual(x["version"], x["release"], x)  # just installed: up to date
        path = os.path.join(kb[0]["folder"], "SKILL.md")
        write(path, re.sub(r"(?m)^Version: .*$", "Version: 0.1.0", read(path)))
        x = next(y for y in self.server.get("/api/skills")[1]["skills"] if y["dir"] == kb[0]["dir"])
        self.assertEqual((x["version"], x["release"]), ("0.1.0", kb[0]["release"]))

    def test_quit(self):
        work = self.server.get("/api/state")[1]["work"]
        self.assertTrue(os.path.isdir(work))
        self.assertTrue(work.startswith(self.p("tmp")))
        self.assertEqual(self.server.post("/api/quit", {})[0], 200)
        self.assertEqual(self.server.proc.wait(10), 0)
        self.assertFalse(os.path.exists(work))  # the work folder goes with the client


class ChatEvents:
    """The page's conversation stream, read until an event that matches."""

    def __init__(self, server, after):
        self.c = http.client.HTTPConnection("127.0.0.1", server.port, timeout=30)
        self.c.request("GET", f"/api/chat/events?after={after}&t={server.token}")
        self.resp = self.c.getresponse()
        self.seen = []

    def until(self, test, what="event", timeout=30):
        end = time.time() + timeout
        while True:
            if time.time() > end:
                raise AssertionError(f"no {what} in {timeout}s: {self.seen}")
            line = self.resp.fp.readline().decode("utf-8")
            if not line:
                raise AssertionError(f"stream ended before {what}: {self.seen}")
            if line.startswith("data: "):
                ev = json.loads(line[6:])
                self.seen.append(ev)
                if test(ev):
                    return ev

    def close(self):
        self.c.close()


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class ChatTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        write(self.p("home", ".config", "opencode", "opencode.jsonc"), '{"model": "example/model-1"}\n')
        os.makedirs(self.p("bin"))
        write(self.p("bin", "opencode"), read(FAKE).replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
        os.chmod(self.p("bin", "opencode"), 0o700)
        self.log = self.p("log.jsonl")
        os.makedirs(self.p("tmp"))
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"), TMPDIR=self.p("tmp"),
                        PYTHONIOENCODING="utf-8", FAKE_OPENCODE_LOG=self.log,
                        PATH=self.p("bin") + os.pathsep + os.path.dirname(sys.executable))
        for k in ("KB_LIBRARIES", "LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE", "FAKE_OPENCODE_MODE"):
            self.env.pop(k, None)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def start(self, mode="", *args):
        if mode:
            self.env["FAKE_OPENCODE_MODE"] = mode
        s = Server(self.env, "--idle", "0", *args)
        self.addCleanup(s.stop)
        self.server = s
        status, r = s.post("/api/chat/start", {})
        self.assertEqual(status, 200, r)
        events = ChatEvents(s, 0)
        self.addCleanup(events.close)
        return events

    def calls(self):
        return [json.loads(x) for x in read(self.log).splitlines()] if os.path.exists(self.log) else []

    def ready(self):
        ev = self.start()
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        return ev

    def send(self, text, **kw):
        status, r = self.server.post("/api/chat/send", dict(kw, text=text))
        self.assertEqual(status, 200, r)

    def intake_library(self):
        # skills where OpenCode reads them, and a local work library
        ev = self.start("", "--agent", "opencode", "--preset", "work")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        result, out, _ = self.server.run("setup", [True, True, self.p("home", "kb", "work"), "team projects", "",
                                                   True, True, True])
        self.assertEqual(result, "ok", out)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready after setup", timeout=60)
        material = self.p("material")
        write(os.path.join(material, "Atlas weekly 1.md"), "# Weekly status\n\nRiverside Clinic moved to phase two.\n")
        write(os.path.join(material, "sub", "Atlas weekly 2.txt"), "Second week: the review is done.\n")
        write(os.path.join(material, "sub", "copy of week 1.md"),
              "# Weekly status\n\nRiverside Clinic moved to phase two.\n")  # the same content again
        write(os.path.join(material, ".hidden.md"), "not material\n")
        return ev, material

    def intake_until_done(self, timeout=90):
        end = time.time() + timeout
        while time.time() < end:
            run = self.server.get("/api/intake")[1]["run"]
            if run and run["state"] in ("done", "stopped"):
                return run
            time.sleep(0.3)
        raise AssertionError(f"intake not done: {run}")

    def test_intake_by_the_client(self):
        ev, material = self.intake_library()
        status, r = self.server.post("/api/intake", {"library": "work", "paths": [material]})
        self.assertEqual(status, 200, r)
        self.assertEqual(r["run"]["total"], 3)  # hidden files are left out
        # the intake's window takes no messages while it runs
        self.assertEqual(self.server.post("/api/chat/send", {"text": "hello", "win": r["run"]["win"]})[0], 409)
        run = self.intake_until_done()
        by_file = {it["file"]: it for it in run["items"]}
        self.assertEqual(by_file["Atlas weekly 1.md"]["status"], "written", run)
        self.assertEqual(by_file["Atlas weekly 2.txt"]["status"], "written", run)
        self.assertEqual(by_file["copy of week 1.md"]["status"], "duplicate", run)
        lib = self.p("home", "kb", "work")
        for it in run["items"]:
            if it["status"] == "written":
                self.assertTrue(os.path.isfile(os.path.join(lib, it["name"])), it)
        index = read(os.path.join(lib, "01_File-Index.md"))
        self.assertIn("Atlas weekly 1.md", index)
        self.assertIn("Atlas weekly 2.txt", index)
        done = ev.until(lambda e: e["type"] == "intake" and e["run"]["state"] == "done", "intake event")
        self.assertEqual(done["run"]["counts"], run["counts"])
        # the same folder again: everything is a duplicate, nothing is asked
        self.server.post("/api/intake", {"library": "work", "paths": [material]})
        again = self.intake_until_done()
        self.assertEqual(again["counts"], {"duplicate": 3}, again)

    def test_intake_asks_again_and_stops(self):
        self.env["FAKE_OPENCODE_INTAKE"] = "bad_once"
        _, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [os.path.join(material, "Atlas weekly 1.md")]})
        run = self.intake_until_done()
        self.assertEqual(run["items"][0]["status"], "written", run)  # the second answer was usable
        sent = [c for c in self.calls() if c.get("path", "").endswith("/prompt_async")]
        self.assertGreaterEqual(len(sent), 2)

    def test_intake_without_a_usable_answer(self):
        self.env["FAKE_OPENCODE_INTAKE"] = "never"
        _, material = self.intake_library()
        write(os.path.join(material, "scan.bin"), "\x00\x01\x02")
        self.server.post("/api/intake", {"library": "work", "paths": [os.path.join(material, "Atlas weekly 1.md"),
                                                                       os.path.join(material, "scan.bin")]})
        run = self.intake_until_done()
        self.assertEqual([it["status"] for it in run["items"]], ["failed", "manual"], run)
        self.assertIn("3", run["items"][0]["reason"])  # asked three times
        self.assertFalse(any(f.startswith("02_") for f in os.listdir(self.p("home", "kb", "work"))))

    def test_intake_stop_and_continue(self):
        self.env["FAKE_OPENCODE_INTAKE"] = "slow"
        _, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [material]})
        end = time.time() + 30
        while self.server.get("/api/intake")[1]["run"]["step"] != "ask" and time.time() < end:
            time.sleep(0.2)
        self.assertEqual(self.server.post("/api/intake/stop", {})[0], 200)
        run = self.intake_until_done()
        self.assertEqual(run["state"], "stopped")
        self.assertEqual(run["counts"], {"waiting": 3}, run)
        status, r = self.server.post("/api/intake", {"resume": True})
        self.assertEqual(status, 200, r)
        self.assertEqual(r["run"]["total"], 3)
        self.server.post("/api/intake/stop", {})
        self.intake_until_done()

    def test_intake_log_and_conversation_back(self):
        ev, material = self.intake_library()
        self.send("hello")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "echo: hello", "answer")
        self.send("PERM read " + self.p("home", "kb", "work", "00_Spec.md"))  # allowed by the client, and logged
        ev.until(lambda e: e["type"] == "auto", "auto")
        before = self.server.get("/api/chat/state")[1]["agent"]["session"]
        self.server.post("/api/intake", {"library": "work", "paths": [material]})
        run = self.intake_until_done()
        self.assertEqual(self.server.get("/api/chat/state")[1]["agent"]["session"], before)  # never left
        work = self.p("home", ".config", "evergreen-wiki", "intake", run["id"])
        self.assertEqual(run["log"], os.path.join(work, "intake.log"))
        text = read(run["log"])
        self.assertEqual(os.stat(run["log"]).st_mode & 0o777, 0o600)
        for part in ("run: prep.py scan", "exit 0", "decision: {", "written ->", "duplicate", "run " + run["id"] + " done"):
            self.assertIn(part, text)
        self.assertNotIn("Riverside Clinic moved to phase two", text)  # never the files' text
        logs = self.p("home", ".config", "evergreen-wiki", "logs")
        day = [f for f in os.listdir(logs) if f.startswith("kb-client-")]
        self.assertEqual(len(day), 1)
        self.assertEqual(os.stat(os.path.join(logs, day[0])).st_mode & 0o777, 0o600)
        self.assertIn("permission read allowed by the client (rule)", read(os.path.join(logs, day[0])))

    def test_intake_survives_the_client(self):
        self.env["FAKE_OPENCODE_INTAKE"] = "slow"
        _, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [material]})
        end = time.time() + 30
        while self.server.get("/api/intake")[1]["run"]["step"] != "ask" and time.time() < end:
            time.sleep(0.2)
        self.server.stop()  # the client dies in the middle of the run
        self.env["FAKE_OPENCODE_INTAKE"] = ""
        ev = self.start()
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        run = self.server.get("/api/intake")[1]["run"]
        self.assertEqual((run["state"], run["counts"]), ("stopped", {"waiting": 3}), run)
        status, r = self.server.post("/api/intake", {"resume": True})
        self.assertEqual(status, 200, r)
        run = self.intake_until_done()
        self.assertEqual(run["counts"], {"written": 2, "duplicate": 1}, run)

    def queue_rows(self):
        text = read(self.p("home", "kb", "work", "_Consolidation-Queue.md"))
        return [ln for ln in text.split("\n") if ln.startswith("|") and ".md" in ln.split("|")[1]]

    def test_intake_then_consolidation_unattended(self):
        self.env["FAKE_OPENCODE_CONSOLIDATE"] = "ask"
        ev, material = self.intake_library()
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": True})[0], 200)
        self.server.post("/api/intake", {"library": "work", "paths": [material]})
        run = self.intake_until_done()
        cons = run["consolidation"]
        self.assertEqual((run["state"], cons["state"]), ("done", "done"), run)
        self.assertEqual((cons["files"], cons["changes"], cons["queue"], cons["round"]), (2, 4, 0, 2), cons)
        self.assertEqual(self.queue_rows(), [])
        text = read(run["log"])
        self.assertIn("question answered as recommended", text)
        self.assertIn("Accept all (recommended)", text)
        sent = [c["body"]["parts"][0]["text"] for c in self.calls() if c.get("path", "").endswith("/prompt_async")]
        rounds = [x for x in sent if "consolidate_" in x]
        self.assertEqual(len(rounds), 2)
        self.assertTrue(all("unattended" in x for x in rounds), rounds)

    def test_consolidation_waits_for_a_person(self):
        self.env["FAKE_OPENCODE_CONSOLIDATE"] = "ask"
        ev, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [os.path.join(material, "Atlas weekly 1.md")]})
        q = ev.until(lambda e: e["type"] == "question", "the step-5 question", timeout=60)
        time.sleep(3)
        run = self.server.get("/api/intake")[1]["run"]
        self.assertEqual((run["state"], run["step"], run["consolidation"]["state"]), ("running", "consolidate", "running"))
        self.assertIn("a card waits for a person", read(run["log"]))
        status, _ = self.server.post("/api/chat/question", {"id": q["id"], "answers": [["Accept all (recommended)"]]})
        self.assertEqual(status, 200)
        run = self.intake_until_done()
        self.assertEqual((run["consolidation"]["state"], run["consolidation"]["files"]), ("done", 1), run)
        sent = [c["body"]["parts"][0]["text"] for c in self.calls() if c.get("path", "").endswith("/prompt_async")]
        self.assertTrue(any("At step 5 ask the user as usual" in x for x in sent))

    def test_consolidation_that_does_not_move(self):
        self.env["FAKE_OPENCODE_CONSOLIDATE"] = "stuck"
        _, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [os.path.join(material, "Atlas weekly 1.md")]})
        run = self.intake_until_done()
        cons = run["consolidation"]
        self.assertEqual((run["state"], cons["state"], cons["round"], cons["queue"]), ("done", "failed", 2, 1), cons)
        self.assertIn("2 rounds", cons["reason"])

    def test_consolidation_stopped_and_continued(self):
        self.env["FAKE_OPENCODE_CONSOLIDATE"] = "ask"
        ev, material = self.intake_library()
        self.server.post("/api/intake", {"library": "work", "paths": [os.path.join(material, "Atlas weekly 1.md")]})
        ev.until(lambda e: e["type"] == "question", "the step-5 question", timeout=60)
        self.server.post("/api/intake/stop", {})
        run = self.intake_until_done()
        self.assertEqual((run["state"], run["consolidation"]["state"]), ("stopped", "stopped"), run)
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": True})[0], 200)
        status, r = self.server.post("/api/intake", {"resume": True})
        self.assertEqual((status, r["run"]["total"]), (200, 0), r)
        run = self.intake_until_done()
        self.assertEqual((run["state"], run["consolidation"]["state"], run["consolidation"]["queue"]), ("done", "done", 0), run)
        self.assertEqual(self.server.post("/api/intake", {"resume": True})[0], 409)  # nothing is left

    def auto_library(self, mode=""):
        """A work library switched to automatic intake, with short times; returns (events, material, drop
        folder entry)."""
        self.env.update(KB_CLIENT_AUTO_POLL="1", KB_CLIENT_AUTO_SETTLE="1")
        if mode:
            self.env["FAKE_OPENCODE_INTAKE"] = mode
        ev, material = self.intake_library()
        status, r = self.server.post("/api/auto", {"library": "work", "on": True})
        self.assertEqual(status, 200, r)
        a = r["auto"]
        lib = self.p("home", "kb", "work")
        self.assertEqual(a["inbox"], os.path.join(lib, "_Inbox"))
        self.assertTrue(os.path.isdir(a["inbox"]) and os.path.isdir(a["not_filed"]))
        return ev, material, a

    def auto_until(self, test, what, timeout=90):
        end = time.time() + timeout
        run = None
        while time.time() < end:
            run = self.server.get("/api/intake")[1]["run"]
            if run and run.get("auto") and test(run):
                return run
            time.sleep(0.3)
        raise AssertionError(f"no automatic run {what}: {run}")

    def keep_originals(self, on):
        conf = self.p("home", "kb", "work", "_kb.json")
        data = json.loads(read(conf))
        data["sources"] = {"keep": on}
        write(conf, json.dumps(data))

    def test_automatic_intake(self):
        ev, material, a = self.auto_library()
        lib = self.p("home", "kb", "work")
        self.keep_originals(False)
        shutil.copy(os.path.join(material, "Atlas weekly 1.md"), a["inbox"])
        os.makedirs(os.path.join(a["inbox"], "sub"))
        shutil.copy(os.path.join(material, "sub", "Atlas weekly 2.txt"), os.path.join(a["inbox"], "sub"))
        shutil.copy(os.path.join(material, "sub", "copy of week 1.md"), a["inbox"])
        with open(os.path.join(a["inbox"], "scan.png"), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
        run = self.auto_until(lambda r: r["state"] == "done", "done")
        self.assertEqual(run["counts"], {"written": 2, "duplicate": 1, "manual": 1}, run)
        # the library keeps no originals: written files move to Filed, the duplicate is removed, the
        # picture waits in Not-filed; nothing is left at the top of the drop folder
        self.assertEqual(sorted(os.listdir(os.path.join(a["inbox"], "Filed"))), ["Atlas weekly 1.md", "Atlas weekly 2.txt"])
        self.assertEqual(os.listdir(a["not_filed"]), ["scan.png"])
        run = self.server.get("/api/intake")[1]["run"]
        manual = next(it for it in run["items"] if it["status"] == "manual")
        self.assertEqual(manual["source"], os.path.join(a["not_filed"], "scan.png"))
        self.assertEqual(sorted(os.listdir(a["inbox"])), ["Filed", "Not-filed", "sub"])
        self.assertEqual(os.listdir(os.path.join(a["inbox"], "sub")), [])
        for it in run["items"]:
            if it["status"] == "written":
                self.assertTrue(os.path.isfile(os.path.join(lib, it["name"])), it)
        # Allow everything was on for the run only
        self.assertTrue(any(e["type"] == "allow_all" and e["on"] for e in ev.seen) or
                        ev.until(lambda e: e["type"] == "allow_all" and e["on"], "allow all on"))
        ev.until(lambda e: e["type"] == "allow_all" and not e["on"], "allow all off again", timeout=30)
        self.assertFalse(self.server.get("/api/chat/state?win=" + run["win"])[1]["agent"]["allow_all"])
        state = self.server.get("/api/state")[1]
        auto = next(x for x in state["libraries"] if x["id"] == "work")["auto"]
        self.assertEqual((auto["on"], auto["manual"], auto["waiting"]), (True, 1, 0), auto)
        self.assertEqual((auto["last"]["written"], auto["last"]["duplicate"], auto["last"]["not_filed"]), (2, 1, 1))
        self.assertTrue(os.path.isfile(auto["last"]["log"]))
        self.assertIn("automatic intake from", read(auto["last"]["log"]))
        saved = json.loads(read(self.p("home", ".config", "evergreen-wiki", "auto-intake.json")))
        self.assertTrue(saved["libraries"]["work"]["on"])
        # the drop folder is not part of the graph
        g = self.server.get("/api/graph?lib=work")[1]
        self.assertFalse([n for n in g["nodes"] if n["path"].startswith("_Inbox")], g)
        # a file that is not new: nothing else runs; switched off, the folder stays and nothing is taken
        self.assertEqual(self.server.post("/api/auto", {"library": "work", "on": False})[1]["auto"]["on"], False)
        shutil.copy(os.path.join(material, "Atlas weekly 1.md"), os.path.join(a["inbox"], "again.md"))
        time.sleep(4)
        self.assertEqual(self.server.get("/api/intake")[1]["run"]["id"], run["id"])
        self.assertTrue(os.path.isfile(os.path.join(a["inbox"], "again.md")))

    def test_automatic_intake_removes_kept_originals(self):
        ev, material, a = self.auto_library()
        self.keep_originals(True)
        shutil.copy(os.path.join(material, "sub", "Atlas weekly 2.txt"), a["inbox"])
        run = self.auto_until(lambda r: r["state"] == "done", "done")
        self.assertEqual(run["counts"], {"written": 1}, run)
        self.assertEqual(sorted(os.listdir(a["inbox"])), ["Not-filed"])  # the copy is in Sources/
        self.assertTrue(os.listdir(self.p("home", "kb", "work", "Sources")))

    def test_automatic_intake_stops_when_allow_all_is_switched_off(self):
        ev, material, a = self.auto_library("slow")
        shutil.copy(os.path.join(material, "Atlas weekly 1.md"), a["inbox"])
        going = self.auto_until(lambda r: r["state"] == "running" and r["step"] == "ask", "asking")
        self.assertTrue(self.server.get("/api/chat/state?win=" + going["win"])[1]["agent"]["allow_all"])
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": False, "win": going["win"]})[0], 200)
        run = self.auto_until(lambda r: r["state"] == "stopped", "stopped")
        self.assertEqual(run["counts"], {"waiting": 1}, run)
        self.assertTrue(os.path.isfile(os.path.join(a["inbox"], "Atlas weekly 1.md")))  # left for later
        self.assertIn("Allow everything was switched off", read(run["log"]))
        # paused until a file that run did not have comes
        time.sleep(4)
        self.assertEqual(self.server.get("/api/intake")[1]["run"]["id"], run["id"])
        last = next(x for x in self.server.get("/api/state")[1]["libraries"] if x["id"] == "work")["auto"]["last"]
        self.assertEqual((last["state"], last["waiting"]), ("stopped", 1), last)

    def test_automatic_intake_refusals(self):
        self.ready()
        self.assertEqual(self.server.post("/api/auto", {"library": "nowhere", "on": True})[0], 400)

    def test_intake_prompt_keeps_the_text(self):
        for lang, t in intake_mod.PROMPT.items():
            item = t["item"]
            self.assertNotRegex(item.replace("不做脱敏或打码", "").replace("Do no masking or redaction", ""),
                                "脱敏|打码|[Mm]ask|[Rr]edact", lang)
            self.assertTrue("不做脱敏或打码" in item or "Do no masking or redaction" in item, lang)

    def test_answer_recommended(self):
        ag = agent.Agent.__new__(agent.Agent)
        sent = []
        ag.reply_question = lambda rid, answers: sent.append(answers) or True
        w = agent.Window("w1")
        ag.windows = {"w1": w}
        w.questions = {"q1": {"id": "q1", "questions": [
            {"options": [{"label": "Leave some out", "description": ""}, {"label": "全部采用（推荐）", "description": ""}],
             "custom": True},
            {"options": [{"label": "A", "description": ""}, {"label": "B", "description": "recommended"}], "custom": True},
            {"options": [{"label": "A", "description": ""}], "custom": True},
            {"options": [], "custom": True}, {"options": [], "custom": False}]}}
        self.assertEqual(ag.answer_recommended("q1", "go on"), [["全部采用（推荐）"], ["B"], ["A"], ["go on"], []])
        self.assertIsNone(ag.answer_recommended("q2", "go on"))

    def test_idle_waits_for_an_intake(self):
        app = kb_client.App.__new__(kb_client.App)
        stopped = []
        app.idle, app.job, app.agent, app.last_seen = 1, None, None, 0
        app.server = type("S", (), {"shutdown": lambda self: stopped.append(1)})()
        running = [True]
        app.intake = type("R", (), {"running": lambda self: running[0]})()
        app.auto = type("W", (), {"any_on": lambda self, libs: False})()
        import threading
        t = threading.Thread(target=app.idle_watch, daemon=True)
        t.start()
        time.sleep(2.5)
        self.assertEqual(stopped, [])
        running[0] = False
        auto_on = [True]  # a library switched to automatic intake keeps the client going too
        app.auto = type("W", (), {"any_on": lambda self, libs: auto_on[0]})()
        time.sleep(2.5)
        self.assertEqual(stopped, [])
        auto_on[0] = False
        t.join(10)
        time.sleep(0.2)
        self.assertEqual(stopped, [1])

    def test_old_logs_and_runs_are_removed(self):
        logs = self.p("home", ".config", "evergreen-wiki", "logs")
        old = os.path.join(logs, "kb-client-20000101.log")
        write(old, "x\n")
        os.utime(old, (time.time() - 8 * 86400,) * 2)
        runs = self.p("home", ".config", "evergreen-wiki", "intake")
        for name, state in (("done-old", "done"), ("stopped-old", "stopped")):
            path = os.path.join(runs, name, "intake-run.json")
            write(path, json.dumps({"run": {"state": state}}))
            os.utime(path, (time.time() - 8 * 86400,) * 2)
        self.start()
        self.assertFalse(os.path.exists(old))
        self.assertFalse(os.path.exists(os.path.join(runs, "done-old")))
        self.assertTrue(os.path.exists(os.path.join(runs, "stopped-old")))  # kept to be continued

    def test_intake_refusals(self):
        self.assertEqual(self.server_or_start().post("/api/intake", {"library": "work", "paths": ["relative"]})[0], 400)
        status, r = self.server.post("/api/intake", {"library": "work", "paths": ["/nowhere"]})
        self.assertEqual((status, r.get("reason")), (409, "intake_skills"), r)
        self.assertEqual(self.server.post("/api/intake", {"resume": True})[1].get("reason"), "intake_skills")

    def server_or_start(self):
        ev = self.ready()
        self.addCleanup(ev.close)
        return self.server

    def test_starts_without_a_model_in_its_settings(self):
        # the settings may come from elsewhere; whether OpenCode can be used shows when it starts
        os.remove(self.p("home", ".config", "opencode", "opencode.jsonc"))
        ev = self.ready()
        self.assertFalse(self.server.get("/api/state")[1]["agent"]["model"])
        self.send("hello")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "echo: hello", "answer")

    def test_recheck_finds_opencode_installed_later(self):
        program = self.p("bin", "opencode")
        os.rename(program, self.p("opencode.later"))
        s = Server(self.env, "--idle", "0")
        self.addCleanup(s.stop)
        self.server = s
        status, r = s.post("/api/chat/start", {})
        self.assertEqual((status, r["reason"]), (409, "no_program"))
        self.assertEqual(s.post("/api/chat/send", {"text": "hello"})[0], 409)
        self.assertEqual(s.post("/api/chat/recheck", {})[1]["reason"], "no_program")
        os.rename(self.p("opencode.later"), program)
        status, r = s.post("/api/chat/recheck", {})
        self.assertEqual(status, 200, r)
        self.assertEqual(s.get("/api/state")[1]["agent"]["program"], program)
        ev = ChatEvents(s, 0)
        self.addCleanup(ev.close)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")

    def test_recheck_after_simple_mode(self):
        ev = self.start("noserve1")  # the first serve fails, the next one works
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "simple", "simple")
        status, r = self.server.post("/api/chat/recheck", {})
        self.assertEqual(status, 200, r)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        self.send("hello")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "echo: hello", "answer")
        self.assertEqual([c["args"][0] for c in self.calls() if "args" in c], ["serve", "serve"])
        # while it is ready, a recheck changes nothing
        self.assertEqual(self.server.post("/api/chat/recheck", {})[0], 200)
        self.assertEqual(len([c for c in self.calls() if "args" in c]), 2)

    def test_conversation(self):
        ev = self.ready()
        start = self.calls()[0]
        self.assertEqual(start["args"][:2], ["serve", "--hostname=127.0.0.1"])
        self.assertEqual(start["cwd"], os.path.realpath(self.home))
        config = json.loads(start["config"])
        self.assertEqual(config["permission"]["edit"], "ask")
        self.assertEqual(config["permission"]["bash"], "ask")
        self.send("hello there")
        user = ev.until(lambda e: e["type"] == "part" and e["role"] == "user", "user text")
        self.assertEqual(user["text"], "hello there")
        ev.until(lambda e: e["type"] == "delta" and "echo" in e["delta"], "delta")
        answer = ev.until(lambda e: e["type"] == "part" and e["role"] == "assistant" and e["text"], "answer")
        self.assertEqual(answer["text"], "echo: hello there")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        st = self.server.get("/api/chat/state")[1]
        self.assertEqual([h["text"] for h in st["history"]], ["hello there", "echo: hello there"])
        session = st["agent"]["session"]
        # a new conversation, then the client started again picks the last one up
        self.assertEqual(self.server.post("/api/chat/new", {})[0], 200)
        ev.until(lambda e: e["type"] == "reset", "reset")
        new = self.server.get("/api/chat/state")[1]["agent"]["session"]
        self.assertNotEqual(new, session)
        self.assertEqual(self.server.get("/api/chat/state")[1]["history"], [])
        saved = json.loads(read(self.p("home", ".config", "evergreen-wiki", "kb-client.json")))
        win = self.server.get("/api/chat/state")[1]["agent"]["current"]
        self.assertEqual(saved, {"session": new, "always": {}, "current": win,
                                 "windows": [{"id": win, "session": new, "kind": "chat", "task": None, "title": ""}]})

    def test_setup_restarts_opencode(self):
        ev = self.ready()
        self.send("hello there")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        result, out, asked = self.server.run("setup", ["opencode", True, True, "work", self.p("home", "kb", "work"),
                                                       "team projects", "", True])
        self.assertEqual(result, "ok", out)
        self.assertEqual(asked[0]["default"], "opencode")  # the client suggests the agent it talks to
        self.assertTrue(os.path.isfile(self.p("home", ".config", "opencode", "skills", "kb-note", "SKILL.md")))
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "starting" and e.get("restart"), "restart")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready again")
        serves = [c for c in self.calls() if c.get("args", [])[:1] == ["serve"]]
        self.assertEqual(len(serves), 2)
        self.send("after the restart")
        ev.until(lambda e: e["type"] == "part" and e["role"] == "assistant" and e["text"] == "echo: after the restart",
                 "answer after the restart")

    def test_bad_requests(self):
        self.ready()
        s = self.server
        self.assertEqual(s.post("/api/chat/send", {"text": ""})[0], 400)
        self.assertEqual(s.post("/api/chat/send", {"text": "x" * 20001})[0], 400)
        self.assertEqual(s.post("/api/chat/send", {"text": "x", "material": ["relative"]})[0], 400)
        self.assertEqual(s.post("/api/chat/question", {"id": "x", "answers": "no"})[0], 400)
        self.assertEqual(s.post("/api/chat/permission", {"id": "unknown", "allow": True})[0], 409)
        self.assertEqual(s.get("/api/chat/state", token=False)[0], 403)

    def test_chat_first(self):
        work = self.p("home", "projects", "atlas")
        os.makedirs(work)
        work = os.path.realpath(work)  # the temporary folder may be under a link to a system folder (/var on macOS)
        ev = self.start("", "--chat-first")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        s = self.server
        self.assertTrue(s.get("/api/state")[1]["chat_first"])
        agent = s.get("/api/chat/state")[1]["agent"]
        self.assertEqual((agent["workdir"], agent["recent"]), ("", []))
        self.assertEqual([m["id"] for m in agent["models"]], ["example/model-1", "example/model-2"])
        # folders that cannot be the work folder
        for path, why in ((self.home, "too_wide"), (self.tmp, "too_wide"), ("/", "too_wide"), ("/etc", "system"),
                          (self.p("home", "missing"), "missing"), ("relative", "missing")):
            status, r = s.post("/api/chat/workdir", {"path": path})
            self.assertEqual((status, r.get("reason")), (400, why), path)
        # a work folder starts OpenCode there; editing inside it needs no card, outside it does
        status, r = s.post("/api/chat/workdir", {"path": work})
        self.assertEqual(status, 200, r)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "starting" and e.get("restart") == "workdir", "restart")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready in the work folder")
        self.assertEqual([c for c in self.calls() if "cwd" in c][-1]["cwd"], os.path.realpath(work))
        self.send("PERM edit " + os.path.join(work, "notes.txt"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        self.send("PERM edit " + self.p("home", "elsewhere.txt"))
        card = ev.until(lambda e: e["type"] in ("auto", "permission"))
        self.assertEqual(card["type"], "permission")
        s.post("/api/chat/permission", {"id": card["id"], "reply": "reject"})
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        # a model of OpenCode's settings goes with the message; another is refused
        self.send("hello", model="example/model-2")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        prompt = [c for c in self.calls() if c.get("path", "").endswith("/prompt_async")][-1]
        self.assertEqual(prompt["body"]["model"], {"providerID": "example", "modelID": "model-2"})
        self.assertEqual(s.post("/api/chat/send", {"text": "x", "model": "other/x"})[0], 400)
        # an edit step brings its diff
        self.send("EDIT")
        step = ev.until(lambda e: e["type"] == "part" and e.get("kind") == "tool", "edit step")
        self.assertIn("+new", step["diff"])
        ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
        # earlier conversations of the folder, and going back to one
        first = s.get("/api/chat/state")[1]["agent"]["session"]
        s.post("/api/chat/new", {})
        ev.until(lambda e: e["type"] == "reset", "reset")
        listed = s.post("/api/chat/sessions", {})[1]
        self.assertIn(first, [x["id"] for x in listed["sessions"]])
        self.assertEqual(s.post("/api/chat/open", {"session": "nope"})[0], 404)
        status, r = s.post("/api/chat/open", {"session": first})
        self.assertEqual(status, 200, r)
        st = s.get("/api/chat/state?win=" + r["win"])[1]
        self.assertEqual(st["agent"]["session"], first)
        self.assertIn("hello", [h.get("text") for h in st["history"]])
        saved = json.loads(read(self.p("home", ".config", "evergreen-wiki", "kb-client.json")))
        here = saved["windows_by_dir"][saved["workdir"]]
        self.assertEqual((saved["workdir"], saved["recent"], here["current"]),
                         (os.path.realpath(work), [os.path.realpath(work)], r["win"]))
        self.assertIn(first, [w["session"] for w in here["windows"]])

    def test_chat_first_requests_need_the_option(self):
        self.ready()
        s = self.server
        self.assertFalse(s.get("/api/state")[1]["chat_first"])
        for what in ("workdir", "sessions"):
            self.assertEqual(s.post("/api/chat/" + what, {})[0], 404, what)
        self.assertEqual(s.post("/api/chat/send", {"text": "x", "model": "example/model-1"})[0], 400)

    def test_permission_asked_and_answered(self):
        ev = self.ready()
        self.send("PERM edit " + self.p("elsewhere", "a.md"))
        card = ev.until(lambda e: e["type"] == "permission", "permission")
        self.assertEqual(card["permission"], "edit")
        self.assertEqual(len(self.server.get("/api/chat/state")[1]["agent"]["permissions"]), 1)
        self.assertEqual(self.server.post("/api/chat/permission", {"id": card["id"], "allow": False})[0], 200)
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: reject", "reply")
        self.assertEqual(self.server.get("/api/chat/state")[1]["agent"]["permissions"], [])

    def test_permission_always(self):
        ev = self.ready()
        self.send("PERM bash git status")
        card = ev.until(lambda e: e["type"] == "permission", "permission")
        self.assertEqual(card["always"], ["bash *"])
        self.assertEqual(self.server.post("/api/chat/permission", {"id": card["id"], "reply": "sometimes"})[0], 400)
        self.assertEqual(self.server.post("/api/chat/permission", {"id": card["id"], "reply": ["always"]})[0], 400)
        self.assertEqual(self.server.post("/api/chat/permission", {"id": card["id"], "reply": "always"})[0], 200)
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: always", "reply")
        self.assertEqual(self.server.get("/api/state")[1]["remembered"], 1)
        # the client keeps the answer: the same kind of command is answered without a card, also after the
        # client starts again, but never a command joined to another one
        self.send("PERM bash bash scripts/x.sh")
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        self.send("PERM bash bash a.sh; rm -r b")
        card = ev.until(lambda e: e["type"] in ("auto", "permission"))
        self.assertEqual(card["type"], "permission")
        self.server.post("/api/chat/permission", {"id": card["id"], "reply": "reject"})
        self.server.stop()
        ev = self.start()
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        self.assertEqual(self.server.get("/api/state")[1]["remembered"], 1)
        self.send("PERM bash bash other.sh")
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        # Clear forgets it and starts OpenCode anew
        self.assertEqual(self.server.post("/api/chat/forget", {})[0], 200)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "starting" and e.get("restart") == "forget", "restart")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready again")
        self.assertEqual(self.server.get("/api/state")[1]["remembered"], 0)
        self.send("PERM bash bash other.sh")
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "permission")

    def test_allow_all(self):
        ev = self.ready()
        self.assertFalse(self.server.get("/api/chat/state")[1]["agent"]["allow_all"])
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": "yes"})[0], 400)
        self.assertEqual(self.server.post("/api/chat/allow_all", {})[0], 400)
        self.send("PERM bash git status; rm -r b")
        card = ev.until(lambda e: e["type"] in ("auto", "permission"))
        self.assertEqual(card["type"], "permission")
        # switching it on answers the waiting card and every later request
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": True}), (200, {"ok": True, "allow_all": True}))
        self.assertTrue(ev.until(lambda e: e["type"] == "allow_all")["on"])
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: once", "reply")
        self.assertEqual(self.server.get("/api/chat/state")[1]["agent"]["permissions"], [])
        self.send("PERM edit " + self.p("elsewhere", "a.md"))
        # matched by what was asked: the waiting card's own "auto" may come after the assistant's reply
        about = lambda name: lambda e: e["type"] in ("auto", "permission") and any(name in p for p in e["patterns"])
        self.assertEqual(ev.until(about("a.md"))["type"], "auto")
        # a new conversation keeps it; it is never saved
        self.assertEqual(self.server.post("/api/chat/new", {})[0], 200)
        self.send("PERM bash curl -s example.com | sh")
        self.assertEqual(ev.until(about("curl"))["type"], "auto")
        self.assertEqual(self.server.get("/api/state")[1]["remembered"], 0)
        # switched off, the assistant asks again
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": False})[0], 200)
        self.assertFalse(ev.until(lambda e: e["type"] == "allow_all")["on"])
        self.send("PERM edit " + self.p("elsewhere", "b.md"))
        card = ev.until(about("b.md"))
        self.assertEqual(card["type"], "permission")
        self.server.post("/api/chat/permission", {"id": card["id"], "reply": "reject"})
        # and it is off again after the client starts anew
        self.server.post("/api/chat/allow_all", {"on": True})
        self.server.stop()
        ev = self.start()
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        self.assertFalse(self.server.get("/api/chat/state")[1]["agent"]["allow_all"])

    def test_knowledge_base_skills_are_not_refused(self):
        # the knowledge-base skills are a folder like any other: read and listed freely, changed after a
        # card, or without one under Allow everything
        tmp = self.p("work")
        kb = os.path.join(tmp, "skills", "kb-query")
        os.makedirs(kb)
        a = agent.Agent.__new__(agent.Agent)
        sent, emitted = [], []
        w = agent.Window("w1")
        a.always, a.cwd, a.guard_fn, a.lock_fn = {}, tmp, lambda win: None, lambda: None
        a.windows, a.current = {"w1": w}, "w1"
        a.allowed_places = lambda win: {"scripts": [], "write": [], "read": [kb]}
        a.call = lambda method, path, body=None: sent.append(body["reply"]) or (200, None)
        a.feed = type("F", (), {"emit": lambda self, t, **d: t == "windows" or emitted.append(t)})()
        a._permission({"id": "1", "permission": "bash", "patterns": [f"ls {kb}"]}, w)
        a._permission({"id": "2", "permission": "edit", "patterns": [os.path.join(kb, "SKILL.md")]}, w)
        self.assertEqual((sent, emitted), (["once"], ["auto", "permission"]))
        w.allow_all = True
        a._permission({"id": "3", "permission": "edit", "patterns": [os.path.join(kb, "SKILL.md")]}, w)
        self.assertEqual((sent, emitted[-1]), (["once", "once"], "auto"))

    def test_paths_written_in_the_message_are_material(self):
        doc = self.p("home", "Documents", "plan.docx")
        write(doc, "x")
        ev = self.ready()
        self.send("PERM read " + doc)  # the path is in the message itself; nothing chosen in the browser
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        self.send("PERM read " + self.p("home", "Documents", "other.docx"))  # not an existing file
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "permission")

    def test_read_only_commands_are_answered_by_the_client(self):
        material = self.p("home", "Documents", "minutes")
        os.makedirs(material)
        ev = self.ready()
        self.send(f"PERM bash ls {material} 2>/dev/null; head -n 5 {material}/a.md | wc -l", material=[material])
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")

    def test_permission_inside_the_material_is_answered_by_the_client(self):
        material = self.p("home", "Documents", "minutes")
        os.makedirs(material)
        ev = self.ready()
        self.send("PERM read " + os.path.join(material, "*"), material=[material])
        auto = ev.until(lambda e: e["type"] in ("auto", "permission"), "answer")
        self.assertEqual(auto["type"], "auto")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: once", "reply")
        # writing there is not allowed: only the library may be written to
        self.send("PERM edit " + os.path.join(material, "a.md"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "permission")

    def test_tool_step_names_the_stage_script(self):
        ev = self.ready()
        self.send("RUN cd /skills/kb-incremental && python3 scripts/convert.py a.docx out.md")
        step = ev.until(lambda e: e["type"] == "part" and e["kind"] == "tool", "tool step")
        self.assertEqual((step["script"], step["detail"]), ("convert", "Run a script"))

    def test_open_run_material_is_read_without_a_card(self):
        ev = self.ready()
        result, out, _ = self.server.run("setup", ["opencode", True, True, "work", self.p("home", "kb", "work"),
                                                   "team projects", "", True])
        self.assertEqual(result, "ok", out)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready after the restart")
        material = self.p("disk", "minutes")
        os.makedirs(material)
        plan = self.p("home", "kb", "work", "_intake-batches.json")

        def progress(status):
            write(plan, json.dumps({"schema": 1, "sources": [material], "final_step": "pending",
                                    "batches": [{"n": 1, "group": "minutes", "status": status, "files": [], "result": {}}]}))
        progress("pending")  # a run continued in a new conversation: the material was not chosen there
        self.send("PERM read " + os.path.join(material, "a.docx"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: once", "reply")
        progress("done")  # finished: its material is no longer allowed
        self.send("PERM read " + os.path.join(material, "b.docx"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "permission")

    def test_work_folder_is_written_without_a_card(self):
        ev = self.ready()
        work = self.server.get("/api/state")[1]["work"]
        self.send("PERM edit " + os.path.join(work, "out", "a.md"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "permission: once", "reply")
        self.send("PERM edit " + self.p("home", "a.md"))
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "permission")

    def test_question(self):
        ev = self.ready()
        self.send("QUESTION")
        q = ev.until(lambda e: e["type"] == "question", "question")
        self.assertEqual([o["label"] for o in q["questions"][0]["options"]], ["Work", "Life"])
        self.assertEqual(self.server.post("/api/chat/question", {"id": q["id"], "answers": [["Life"]]})[0], 200)
        ev.until(lambda e: e["type"] == "part" and e["text"] == 'answers: [["Life"]]', "answer")

    def test_stop(self):
        ev = self.ready()
        self.send("SLOW")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "busy")
        self.assertEqual(self.server.post("/api/chat/stop", {})[0], 200)
        ev.until(lambda e: e["type"] == "part" and e["text"] == "aborted", "aborted")

    def test_quit_stops_opencode(self):
        self.ready()
        pid = self.calls()[0]["pid"]
        self.assertEqual(self.server.post("/api/quit", {})[0], 200)
        self.assertEqual(self.server.proc.wait(15), 0)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            self.fail("opencode still runs")

    def test_simple_mode_without_the_interface(self):
        for mode in ("noapi", "noserve"):
            with self.subTest(mode=mode):
                ev = self.start(mode)
                st = ev.until(lambda e: e["type"] == "agent" and e["state"] != "starting", "state")
                self.assertEqual(st["state"], "simple")
                self.send("hello")
                out = ev.until(lambda e: e["type"] == "part" and e["role"] == "assistant", "output")
                self.assertEqual(out["text"].strip(), "run: hello")
                # opencode run keeps no conversation: one window only, write tasks go to it
                status, r = self.server.post("/api/chat/open", {})
                self.assertEqual((status, r.get("reason")), (409, "simple"), r)
                ev.until(lambda e: e["type"] == "status" and e["status"] == "idle", "idle")
                status, r = self.server.post("/api/chat/task", {"task": "lint", "text": "lint"})
                self.assertEqual((status, r["win"]), (200, out["win"]), r)
                self.assertEqual(len(self.chat()["agent"]["windows"]), 1)

    def test_subagent_permission_answered_by_the_client(self):
        material = self.p("home", "Documents", "minutes")
        os.makedirs(material)
        ev = self.ready()
        self.send("SUBAGENT read " + os.path.join(material, "*"), material=[material])
        auto = ev.until(lambda e: e["type"] in ("auto", "permission"), "answer")
        self.assertEqual((auto["type"], auto["child"]), ("auto", True))
        sub = ev.until(lambda e: e["type"] == "part" and e["text"].startswith("subagent"), "subagent")
        self.assertTrue(sub["child"])
        ev.until(lambda e: e["type"] == "part" and e["text"] == "done after the subagent", "answer")

    def test_subagent_permission_card(self):
        ev = self.ready()
        self.send("SUBAGENT edit " + self.p("elsewhere", "a.md"))
        card = ev.until(lambda e: e["type"] == "permission", "card")
        self.assertTrue(card["child"])
        self.assertEqual(self.server.post("/api/chat/permission", {"id": card["id"], "allow": True})[0], 200)
        sub = ev.until(lambda e: e["type"] == "part" and e["text"].startswith("subagent"), "subagent")
        self.assertEqual(sub["text"], "subagent: once")
        # the subagent going idle does not end the main conversation's work
        idle = [e for e in ev.seen if e["type"] == "status" and e["status"] == "idle"]
        self.assertEqual(idle, [])

    def test_reasoning_part(self):
        ev = self.ready()
        self.send("THINK")
        r = ev.until(lambda e: e["type"] == "part" and e["kind"] == "reasoning", "reasoning")
        self.assertEqual(r["text"], "pondering")

    def test_send_while_busy(self):
        ev = self.ready()
        self.send("SLOW")
        ev.until(lambda e: e["type"] == "status" and e["status"] == "busy")
        self.send("and this too")
        ev.until(lambda e: e["type"] == "part" and e["text"] == "echo: and this too", "second answer")
        self.server.post("/api/chat/stop", {})

    def test_terminal(self):
        write(self.p("bin", "x-terminal-emulator"),
              "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$FAKE_TERMINAL_LOG\"\n")
        os.chmod(self.p("bin", "x-terminal-emulator"), 0o700)
        self.env["FAKE_TERMINAL_LOG"] = self.p("terminal.txt")
        self.ready()
        self.assertEqual(self.server.post("/api/chat/terminal", {})[1]["reason"], "no_session")
        self.server.post("/api/chat/new", {})
        session = self.server.get("/api/chat/state")[1]["agent"]["session"]
        status, r = self.server.post("/api/chat/terminal", {})
        self.assertEqual((status, r["terminal"]), (200, "x-terminal-emulator"))
        for _ in range(50):
            if os.path.exists(self.p("terminal.txt")):
                break
            time.sleep(0.1)
        args = read(self.p("terminal.txt")).split("\n")
        self.assertEqual(args[0], "-e")
        self.assertTrue(args[1].endswith("opencode"))
        self.assertEqual(args[2], "--session=" + session)

    def test_start_timeout(self):
        ev = self.start("slow", "--start-timeout", "2")
        line = ev.until(lambda e: e["type"] == "agent" and e.get("line"), "output line")
        self.assertIn("refreshing", line["line"])
        st = ev.until(lambda e: e["type"] == "agent" and e["state"] != "starting", "state")
        self.assertEqual(st["state"], "simple")

    # ----- several conversation windows -----

    def chat(self, win=None):
        return self.server.get("/api/chat/state" + (f"?win={win}" if win else ""))[1]

    def texts(self, win):
        return [h.get("text") for h in self.chat(win)["history"]]

    def open_window(self, **body):
        status, r = self.server.post("/api/chat/open", body)
        self.assertEqual(status, 200, r)
        return r["win"]

    def busy(self, ev, win):
        ev.until(lambda e: e["type"] == "status" and e.get("win") == win and e["status"] != "idle", f"{win} busy")

    def idle(self, ev, win):
        ev.until(lambda e: e["type"] == "status" and e.get("win") == win and e["status"] == "idle", f"{win} idle")

    def test_windows_keep_conversations_apart(self):
        ev = self.ready()
        st = self.chat()["agent"]
        self.assertEqual(len(st["windows"]), 1)
        w1 = st["current"]
        w2 = self.open_window()
        self.assertNotEqual(w1, w2)
        self.assertEqual([w["id"] for w in self.chat()["agent"]["windows"]], [w1, w2])
        # the second window works while the first one is answered
        self.send("SLOW", win=w2)
        self.busy(ev, w2)
        self.send("hello", win=w1)
        answer = ev.until(lambda e: e["type"] == "part" and e.get("text") == "echo: hello", "answer")
        self.assertEqual(answer["win"], w1)
        self.idle(ev, w1)
        self.assertEqual(self.texts(w1), ["hello", "echo: hello"])
        self.assertEqual(self.texts(w2), ["SLOW"])
        by_id = {w["id"]: w for w in self.chat()["agent"]["windows"]}
        self.assertEqual((by_id[w1]["status"], by_id[w2]["status"]), ("idle", "busy"))
        self.assertEqual(by_id[w1]["title"], "t-" + by_id[w1]["session"])  # the title OpenCode gave it
        self.assertNotEqual(by_id[w1]["session"], by_id[w2]["session"])
        # Stop and New conversation act on the window they name only
        self.assertEqual(self.server.post("/api/chat/stop", {"win": w2})[0], 200)
        done = ev.until(lambda e: e["type"] == "part" and e.get("text") == "aborted", "aborted")
        self.assertEqual(done["win"], w2)
        self.assertEqual(self.server.post("/api/chat/new", {"win": w2})[0], 200)
        reset = ev.until(lambda e: e["type"] == "reset", "reset")
        self.assertEqual(reset["win"], w2)
        self.assertEqual(self.texts(w1), ["hello", "echo: hello"])
        self.assertEqual(self.texts(w2), [])
        self.assertEqual(self.server.post("/api/chat/send", {"text": "x", "win": "nowhere"})[0], 404)

    def test_window_limit_and_closing(self):
        ev = self.ready()
        first = self.chat()["agent"]["current"]
        wins = [first] + [self.open_window() for _ in range(7)]
        status, r = self.server.post("/api/chat/open", {})
        self.assertEqual((status, r.get("reason")), (409, "too_many"), r)
        # a window at work closes only when asked to stop it
        self.send("SLOW", win=wins[1])
        self.busy(ev, wins[1])
        status, r = self.server.post("/api/chat/close", {"win": wins[1]})
        self.assertEqual((status, r.get("reason")), (409, "busy"), r)
        sid = next(w["session"] for w in self.chat()["agent"]["windows"] if w["id"] == wins[1])
        self.assertEqual(self.server.post("/api/chat/close", {"win": wins[1], "stop": True})[0], 200)
        self.assertIn(f"/session/{sid}/abort", [c.get("path") for c in self.calls()])
        self.assertNotIn(wins[1], [w["id"] for w in self.chat()["agent"]["windows"]])
        self.assertEqual(self.server.post("/api/chat/close", {"win": wins[1]})[0], 404)
        # closing the last window leaves a new one
        for w in wins[2:]:
            self.assertEqual(self.server.post("/api/chat/close", {"win": w})[0], 200)
        self.assertEqual(self.server.post("/api/chat/close", {"win": first})[0], 200)
        left = self.chat()["agent"]["windows"]
        self.assertEqual(len(left), 1)
        self.assertNotEqual(left[0]["id"], first)

    def test_windows_come_back(self):
        self.env["FAKE_OPENCODE_STORE"] = self.p("conversations.json")
        ev = self.ready()
        w1 = self.chat()["agent"]["current"]
        self.send("hello", win=w1)
        self.idle(ev, w1)
        w2 = self.open_window()
        self.send("there", win=w2)
        self.idle(ev, w2)
        self.assertEqual(self.server.post("/api/chat/focus", {"win": w2})[0], 200)
        before = [(w["id"], w["session"]) for w in self.chat()["agent"]["windows"]]
        self.server.stop()
        ev = self.ready()
        st = self.chat()["agent"]
        self.assertEqual([(w["id"], w["session"]) for w in st["windows"]], before)
        self.assertEqual([w["title"] for w in st["windows"]], ["t-" + sid for _, sid in before])  # kept too
        self.assertEqual(st["current"], w2)
        self.assertEqual(self.texts(None), ["there", "echo: there"])  # the current window by default
        self.assertEqual(self.texts(w1), ["hello", "echo: hello"])

    def test_allow_all_is_per_window(self):
        ev = self.ready()
        w1 = self.chat()["agent"]["current"]
        w2 = self.open_window()
        self.assertEqual(self.server.post("/api/chat/allow_all", {"on": True, "win": w1}),
                         (200, {"ok": True, "allow_all": True}))
        self.assertEqual(ev.until(lambda e: e["type"] == "allow_all")["win"], w1)
        self.send("PERM edit " + self.p("elsewhere", "a.md"), win=w2)
        card = ev.until(lambda e: e["type"] in ("auto", "permission"))
        self.assertEqual((card["type"], card["win"]), ("permission", w2))
        self.assertFalse(self.chat(w2)["agent"]["allow_all"])
        self.assertEqual([c["id"] for c in self.chat(w2)["agent"]["permissions"]], [card["id"]])
        self.assertEqual(self.chat(w1)["agent"]["permissions"], [])
        self.server.post("/api/chat/permission", {"id": card["id"], "reply": "reject"})
        self.idle(ev, w2)
        self.send("PERM edit " + self.p("elsewhere", "b.md"), win=w1)
        self.assertEqual(ev.until(lambda e: e["type"] in ("auto", "permission"))["type"], "auto")

    def test_write_tasks_run_one_at_a_time(self):
        ev, _ = self.intake_library()
        s = self.server
        w1 = self.chat()["agent"]["current"]
        status, r = s.post("/api/chat/task", {"task": "lint", "library": "work", "text": "SLOW lint"})
        self.assertEqual(status, 200, r)
        tw = r["win"]
        self.assertNotEqual(tw, w1)
        self.busy(ev, tw)
        st = self.chat()["agent"]
        task_win = next(w for w in st["windows"] if w["id"] == tw)
        self.assertEqual((task_win["kind"], task_win["task"]), ("task", {"name": "lint", "library": "work"}))
        self.assertEqual(st["lock"], {"holder": "task", "win": tw, "task": "lint", "library": "work"})
        # no other write task, no intake and no step that changes libraries meanwhile
        status, r = s.post("/api/chat/task", {"task": "archive", "library": "work", "text": "archive"})
        self.assertEqual((status, r.get("reason")), (409, "locked"), r)
        status, r = s.post("/api/intake", {"library": "work", "paths": [self.p("material")]})
        self.assertEqual((status, r.get("reason")), (409, "locked"), r)
        self.assertEqual(s.post("/api/action", {"action": "rollback"})[0], 409)
        status, r = s.post("/api/action", {"action": "backup"})
        self.assertEqual(status, 200, r)  # backing up only reads the libraries
        s.post("/api/answer", {"job": r["job"], "cancel": True})
        self.assertEqual(s.post("/api/chat/task", {"task": "other", "text": "x"})[0], 400)
        # the other windows go on
        self.send("hello", win=w1)
        ev.until(lambda e: e["type"] == "part" and e.get("text") == "echo: hello", "answer")
        # the lock goes once the task window is idle with no card waiting
        s.post("/api/chat/stop", {"win": tw})
        self.idle(ev, tw)
        self.assertIsNone(self.chat()["agent"]["lock"])
        status, r = s.post("/api/chat/task", {"task": "archive", "library": "work", "text": "SLOW archive"})
        self.assertEqual(status, 200, r)
        tw2 = r["win"]
        self.busy(ev, tw2)
        # a message in a task window goes on with its task: refused while another one holds the lock
        status, r = s.post("/api/chat/send", {"text": "yes, go on", "win": tw})
        self.assertEqual((status, r.get("reason")), (409, "locked"), r)
        s.post("/api/chat/stop", {"win": tw2})
        self.idle(ev, tw2)
        self.send("SLOW go on", win=tw)
        self.busy(ev, tw)
        self.assertEqual(self.chat()["agent"]["lock"]["win"], tw)
        s.post("/api/chat/stop", {"win": tw})

    def test_library_writes_from_other_windows_ask_during_a_task(self):
        ev, _ = self.intake_library()
        s = self.server
        lib = self.p("home", "kb", "work")
        prep = self.p("home", ".config", "opencode", "skills", "kb-incremental", "scripts", "prep.py")
        find = self.p("home", ".config", "opencode", "skills", "kb-query", "scripts", "kbfind.py")
        w1 = self.chat()["agent"]["current"]
        s.post("/api/chat/allow_all", {"on": True, "win": w1})
        status, r = s.post("/api/chat/task", {"task": "lint", "library": "work", "text": "SLOW lint"})
        tw = r["win"]
        self.busy(ev, tw)

        def answer(text):
            self.send(text, win=w1)
            got = ev.until(lambda e: e["type"] in ("auto", "permission") and e.get("win") == w1, text)
            if got["type"] == "permission":
                s.post("/api/chat/permission", {"id": got["id"], "reply": "reject"})
            self.idle(ev, w1)
            return got["type"]

        # writing the library or running the intake skill's scripts asks, even with Allow everything on
        self.assertEqual(answer("PERM edit " + os.path.join(lib, "x.md")), "permission")
        self.assertEqual(answer(f"PERM bash python3 {prep} scan {lib}"), "permission")
        # reading it, looking things up and everything else does not
        self.assertEqual(answer("PERM read " + os.path.join(lib, "00_Spec.md")), "auto")
        self.assertEqual(answer(f"PERM bash python3 {find} Atlas"), "auto")
        self.assertEqual(answer("PERM edit " + self.p("elsewhere", "a.md")), "auto")
        # the task window itself writes as before
        self.send("PERM edit " + os.path.join(lib, "y.md"), win=tw)
        # once the task is done, the library is written without a card again
        s.post("/api/chat/stop", {"win": tw})
        self.idle(ev, tw)
        self.assertEqual(answer("PERM edit " + os.path.join(lib, "x.md")), "auto")

    def test_intake_runs_in_its_own_window(self):
        self.env["FAKE_OPENCODE_INTAKE"] = "slow"
        ev, material = self.intake_library()
        s = self.server
        w1 = self.chat()["agent"]["current"]
        self.send("hello", win=w1)
        self.idle(ev, w1)
        before = self.chat(w1)["agent"]["windows"][0]["session"]
        s.post("/api/chat/allow_all", {"on": True, "win": w1})
        status, r = s.post("/api/intake", {"library": "work", "paths": [material], "win": w1})
        self.assertEqual(status, 200, r)
        iw = r["run"]["win"]
        self.assertNotEqual(iw, w1)
        st = self.chat()["agent"]
        self.assertEqual(next(w for w in st["windows"] if w["id"] == iw)["kind"], "intake")
        self.assertEqual(st["lock"], {"holder": "intake", "win": iw})
        self.assertTrue(self.chat(iw)["agent"]["allow_all"])  # taken from the window it was started from
        self.busy(ev, iw)
        # the conversation of the other windows goes on; the intake window takes no messages
        self.send("during the intake", win=w1)
        ev.until(lambda e: e["type"] == "part" and e.get("text") == "echo: during the intake", "answer")
        status, r = s.post("/api/chat/send", {"text": "x", "win": iw})
        self.assertEqual((status, r.get("reason")), (409, "intake_running"), r)
        status, r = s.post("/api/chat/close", {"win": iw, "stop": True})
        self.assertEqual((status, r.get("reason")), (409, "intake_running"), r)
        status, r = s.post("/api/chat/task", {"task": "lint", "library": "work", "text": "lint"})
        self.assertEqual((status, r.get("reason")), (409, "locked"), r)
        s.post("/api/intake/stop", {})
        self.intake_until_done()
        self.assertEqual(next(w for w in self.chat()["agent"]["windows"] if w["id"] == w1)["session"], before)
        self.assertEqual(self.texts(w1)[:2], ["hello", "echo: hello"])
        # the intake window comes back after a restart only while its run can be continued
        self.server.stop()
        ev = self.ready()
        self.assertIn("intake", [w["kind"] for w in self.chat()["agent"]["windows"]])

    def test_automatic_intake_does_not_wait_for_other_windows(self):
        ev, material, a = self.auto_library()
        w1 = self.chat()["agent"]["current"]
        self.send("SLOW", win=w1)
        self.busy(ev, w1)
        shutil.copy(os.path.join(material, "Atlas weekly 1.md"), a["inbox"])
        run = self.auto_until(lambda r: r["state"] == "done", "done")
        self.assertEqual(run["counts"], {"written": 1}, run)
        self.assertNotEqual(run["win"], w1)
        self.assertFalse(self.chat(w1)["agent"]["allow_all"])  # switched on for the intake window only
        self.server.post("/api/chat/stop", {"win": w1})

    def test_chat_first_windows_per_folder(self):
        a, b = self.p("home", "projects", "a"), self.p("home", "projects", "b")
        os.makedirs(a)
        os.makedirs(b)
        a, b = os.path.realpath(a), os.path.realpath(b)
        self.env["FAKE_OPENCODE_STORE"] = self.p("conversations.json")
        ev = self.start("", "--chat-first")
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        s = self.server
        s.post("/api/chat/workdir", {"path": a})
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready in a")
        w1 = self.chat()["agent"]["current"]
        self.send("one", win=w1)
        self.idle(ev, w1)
        w2 = self.open_window()
        self.send("SLOW", win=w2)
        self.busy(ev, w2)
        # every window must be idle to change folders
        self.assertEqual(s.post("/api/chat/workdir", {"path": b})[0], 409)
        s.post("/api/chat/stop", {"win": w2})
        self.idle(ev, w2)
        in_a = [(w["id"], w["session"]) for w in self.chat()["agent"]["windows"]]
        self.assertEqual(s.post("/api/chat/workdir", {"path": b})[0], 200)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready in b")
        self.assertEqual(len(self.chat()["agent"]["windows"]), 1)
        self.assertEqual(s.post("/api/chat/workdir", {"path": a})[0], 200)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready in a again")
        self.assertEqual([(w["id"], w["session"]) for w in self.chat()["agent"]["windows"]], in_a)
        # an earlier conversation opens in a new window, or in the one that already has it
        sid1 = in_a[0][1]
        self.assertEqual(self.open_window(session=sid1), w1)
        s.post("/api/chat/new", {"win": w1})
        ev.until(lambda e: e["type"] == "reset" and e.get("win") == w1, "reset")
        w3 = self.open_window(session=sid1)
        self.assertNotIn(w3, (w1, w2))
        self.assertEqual(next(w for w in self.chat()["agent"]["windows"] if w["id"] == w3)["title"], "t-" + sid1)
        self.assertEqual(self.texts(w3), ["one", "echo: one"])
        self.assertEqual(s.post("/api/chat/open", {"session": "nope"})[0], 404)


@unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("bash"), "Linux desktops with bash")
class FindOpenCodeTest(unittest.TestCase):
    """OpenCode where a desktop session does not look: a common install folder, a ~/.bashrc function."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        write(os.path.join(self.home, ".config", "opencode", "opencode.jsonc"), '{"model": "example/model-1"}\n')
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=os.path.join(self.home, ".config"),
                        PYTHONIOENCODING="utf-8", PATH=os.path.dirname(sys.executable) + os.pathsep + "/usr/bin:/bin")
        for k in ("KB_LIBRARIES", "LANG", "LC_ALL", "KB_CLIENT_OPENCODE", "FAKE_OPENCODE_MODE", "BASH_ENV", "ENV"):
            self.env.pop(k, None)

    def fake(self, path):
        write(path, read(FAKE).replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
        os.chmod(path, 0o700)

    def start(self, *args):
        s = Server(self.env, "--idle", "0", *args)
        self.addCleanup(s.stop)
        return s

    def ready(self, s):
        self.assertEqual(s.post("/api/chat/start", {})[0], 200)
        ev = ChatEvents(s, 0)
        self.addCleanup(ev.close)
        ev.until(lambda e: e["type"] == "agent" and e["state"] == "ready", "ready")
        return ev

    def test_common_folder(self):
        self.fake(os.path.join(self.home, ".local", "bin", "opencode"))
        s = self.start()
        self.assertEqual(s.get("/api/state")[1]["agent"]["how"], "common")
        self.ready(s)

    def test_bashrc_function(self):
        self.fake(os.path.join(self.tmp, "hidden", "real-opencode"))
        write(os.path.join(self.home, ".bashrc"), 'opencode() { echo "settings refreshed"; "%s" "$@"; }\n'
              % os.path.join(self.tmp, "hidden", "real-opencode"))
        s = self.start()
        self.assertEqual(s.get("/api/state")[1]["agent"]["how"], "shell-function")
        ev = self.ready(s)
        self.assertTrue(any(e.get("line") == "settings refreshed" for e in ev.seen), ev.seen)

    def test_option_and_not_found(self):
        s = self.start()
        self.assertEqual(s.get("/api/state")[1]["agent"]["program"], "")
        self.assertEqual(s.post("/api/chat/start", {})[1]["reason"], "no_program")
        self.fake(os.path.join(self.tmp, "elsewhere", "oc"))
        s = self.start("--opencode", os.path.join(self.tmp, "elsewhere", "oc"))
        self.assertEqual(s.get("/api/state")[1]["agent"]["how"], "option")
        self.ready(s)


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class DecideTest(unittest.TestCase):
    """Which permission requests the client answers itself (agent.decide)."""

    def test_work_folder(self):
        work = os.path.join(self.tmp, "home", "projects", "atlas")
        os.makedirs(work)
        places = dict(self.places, edit=[work])
        for perm in ("edit", "write", "read", "list"):
            self.assertTrue(agent.decide(perm, [os.path.join(work, "src", "a.py")], places, work), perm)
            self.assertTrue(agent.decide(perm, ["src/a.py"], places, work), perm)
        self.assertFalse(agent.decide("edit", [os.path.join(self.tmp, "home", "b.py")], places, work))
        self.assertFalse(agent.decide("edit", [os.path.join(work, "a.py")], self.places, work))
        self.assertTrue(agent.decide("bash", [f"ls {work}"], places, work))
        self.assertFalse(agent.decide("bash", ["rm a.py"], places, work))

    def test_check_workdir(self):
        home = os.path.realpath(os.path.expanduser("~"))
        for path, why in (("", "missing"), ("rel", "missing"), ("/", "too_wide"), (home, "too_wide"),
                          (os.path.dirname(home), "too_wide"), ("/etc", "system"), ("/usr/share", "system")):
            with self.assertRaises(ValueError) as cm:
                agent.check_workdir(path)
            self.assertEqual(str(cm.exception), why, path)
        self.assertEqual(agent.check_workdir(self.lib), self.lib)

    def test_edit_diff(self):
        part = {"type": "tool", "tool": "edit", "id": "p", "messageID": "m",
                "state": {"status": "completed", "title": "a.py", "metadata": {"diff": "-a\n+b\n"}}}
        self.assertEqual(agent.part_event(part, "assistant")["diff"], "-a\n+b\n")
        self.assertNotIn("diff", agent.part_event(dict(part, tool="bash"), "assistant"))

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lib = os.path.join(self.tmp, "home", "kb", "work")
        self.mat = os.path.join(self.tmp, "disk", "minutes")
        self.skill = os.path.join(self.tmp, "home", ".config", "opencode", "skills", "kb-incremental")
        for d in (self.lib, self.mat, os.path.join(self.skill, "scripts")):
            os.makedirs(d)
        write(os.path.join(self.skill, "scripts", "batch_plan.py"), "")
        write(os.path.join(self.tmp, "home", "other.py"), "")
        os.symlink(os.path.join(self.tmp, "home"), os.path.join(self.lib, "out"))
        self.places = {"write": [self.lib], "read": [self.mat, self.skill],
                       "scripts": [os.path.join(self.skill, "scripts")]}
        self.cwd = os.path.join(self.tmp, "home")

    def ok(self, permission, *patterns):
        return agent.decide(permission, list(patterns), self.places, self.cwd)

    def test_writing(self):
        self.assertTrue(self.ok("edit", os.path.join(self.lib, "00_Spec.md")))
        self.assertTrue(self.ok("edit", "kb/work/notes/a.md"))  # relative to the home folder
        self.assertTrue(self.ok("edit", os.path.join(self.lib, "*")))
        self.assertFalse(self.ok("edit", os.path.join(self.mat, "a.md")))
        self.assertFalse(self.ok("edit", os.path.join(self.lib, "out", "x.md")))  # a link out of the library
        self.assertFalse(self.ok("edit", os.path.join(self.lib, "..", "x.md")))
        self.assertFalse(self.ok("edit", os.path.join(self.lib, "a.md"), "/etc/passwd"))
        self.assertFalse(self.ok("edit"))

    def test_reading(self):
        self.assertTrue(self.ok("read", os.path.join(self.mat, "a.docx")))
        self.assertTrue(self.ok("external_directory", os.path.join(self.mat, "*")))
        self.assertTrue(self.ok("read", os.path.join(self.skill, "SKILL.md")))
        self.assertFalse(self.ok("read", os.path.join(self.tmp, "home", "other.py")))
        self.assertFalse(self.ok("glob", "**/*.md"))  # the whole home folder
        self.assertFalse(self.ok("webfetch", "https://example.com"))

    def test_read_only_commands(self):
        lib, mat = self.lib, self.mat
        os.environ["KB_LIBRARIES"] = "x"
        for command in (f"ls {lib} 2>/dev/null; ls {mat}; echo \"$KB_LIBRARIES\"",
                        f"grep -rn 'a;b' {lib} | head -20", f"find {lib} -name '*.md' | wc -l",
                        f"cat {mat}/*.md", f"head -n 5 {lib}/a.md && tail {lib}/a.md",
                        f"test -f {lib}/a.md || echo missing", f"grep -l -e x {lib}/a.md",
                        f"stat {os.path.join(self.skill, 'SKILL.md')}"):
            with self.subTest(command=command):
                self.assertTrue(self.ok("bash", command))
        for command in (f"find {lib} -delete", f"find {lib} -exec rm {{}} ;", "ls /etc", "ls",
                        f"cat {lib}/a > {lib}/b", f"cat {lib}/a >> x", f"echo $(rm {lib}/a)", f"echo `id`",
                        f"ls {lib} &", f"ls {lib} |", "echo $SECRET", f"rm {lib}/a", "grep root /etc/passwd",
                        f"grep -r x", f"cd {lib} && ls", f"ls {lib}/../..", f"ls {lib}/out",
                        "cat ~/.ssh/id_rsa", f"(ls {lib})", f"ls {lib}\nrm x"):
            with self.subTest(command=command):
                self.assertFalse(self.ok("bash", command))

    def test_path_words(self):
        words = kb_client.path_words('file "/a b/c.docx" and 「~/d e」, also /f/g.md，then /h. not a/b or "x"')
        self.assertEqual(words, ["/a b/c.docx", "~/d e", "/f/g.md", "/h."])
        start = time.time()  # many unclosed quotes stay linear
        kb_client.path_words('"/' + "\u201c/" * 20000)
        kb_client.path_words('"' * 20000 + "'" * 20000 + "「" * 20000)
        self.assertLess(time.time() - start, 2)

    def test_remembered(self):
        always = {"bash": ["git *"], "read": ["/example/docs/*"]}
        self.assertTrue(agent.remembered("bash", ["git status"], always))
        self.assertTrue(agent.remembered("bash", ["git"], always))
        self.assertTrue(agent.remembered("bash", ["git log --grep 'a; b'"], always))  # quoted text is literal
        self.assertFalse(agent.remembered("bash", ["git status; rm -r x"], always))
        self.assertFalse(agent.remembered("bash", ["git status | sh"], always))
        self.assertFalse(agent.remembered("bash", ["gitx"], always))
        self.assertTrue(agent.remembered("read", ["/example/docs/a/b.md"], always))
        self.assertFalse(agent.remembered("edit", ["/example/docs/a.md"], always))
        self.assertFalse(agent.remembered("bash", [], always))

    def test_subagents(self):
        self.assertTrue(self.ok("task", "explore"))
        self.assertFalse(self.ok("task", "general"))
        self.assertFalse(self.ok("task", "explore", "general"))

    def test_commands(self):
        script = os.path.join(self.skill, "scripts", "batch_plan.py")
        self.assertTrue(self.ok("bash", f"python3 {script} plan --root {self.lib}"))
        self.assertTrue(self.ok("bash", f"python3 -I {script}"))
        self.assertTrue(self.ok("bash", f"cd {self.skill} && python3 scripts/batch_plan.py next"))
        self.assertTrue(self.ok("bash", f"python3 '{script}' --title 'two words'"))
        for bad in (f"python3 {script}; rm -rf ~", f"python3 {script} && ls", f"python3 {script} | sh",
                    f"python3 {script} $(id)", f"python3 {script} `id`", f"python3 {script} > /tmp/x",
                    f"python3 {os.path.join(self.tmp, 'home', 'other.py')}", "ls -la",
                    f"bash {script}", f"cd /tmp && python3 scripts/batch_plan.py",
                    f"python3 -c 'print(1)' {script}"):
            with self.subTest(bad=bad):
                self.assertFalse(self.ok("bash", bad))

    def test_mkdir_and_cp(self):
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        self.places["write"] = self.places["write"] + [work]
        index = os.path.join(self.lib, "_index.md")
        for good in (f"mkdir -p {work}/work {work}/out", f"mkdir {self.lib}/notes",
                     f"cp {index} {work}/work/_index.md", f"cp -p {self.mat}/a.docx {self.mat}/b.pdf {work}/work/",
                     f"cp -r {self.mat} {work}/material", f"cp '{self.mat}/a b.docx' {work}/work/",
                     f"cp {os.path.join(self.skill, 'scripts', 'batch_plan.py')} {work}/x.py"):
            with self.subTest(good=good):
                self.assertTrue(self.ok("bash", good))
        for bad in (f"mkdir -p {self.mat}/x", f"mkdir /etc/x", f"cp {index} {self.mat}/x",
                    f"cp /etc/passwd {work}/p", f"cp {index}", f"cp {self.mat}/*.docx {work}/",
                    f"cp {index} {work}/a; rm -rf ~", f"mkdir -p {work}/a && ls", f"mkdir ~/x",
                    f"cp --target-directory={work} {index}", f"mv {index} {work}/",
                    f"cp {index} {self.lib}/out/x"):  # a link out of the library
            with self.subTest(bad=bad):
                self.assertFalse(self.ok("bash", bad))

    def test_stage_script(self):
        for command, script in (("python3 /s/kb-incremental/scripts/convert.py a b", "convert"),
                                ('cd /s && python3 scripts/index_tool.py check w --orig "x"', "index_tool check"),
                                ("python3 -I '/a b/scripts/card_check.py' o n", "card_check"),
                                ("python3 scripts/batch_plan.py finish --plan p", "batch_plan finish"),
                                ("python3 scripts/assemble.py h.md b.md out/x.md", "assemble"),
                                ('python3 scripts/meta.py entities s.md --field "a=b"', "meta entities"),
                                ("python3 scripts/prep.py scan m.docx --library l --work w --n 1", "prep scan"),
                                ("python3 scripts/consolidate.py fill t.md h.md out/t.md", "consolidate fill"),
                                ("python3 scripts/meta.py --help", ""),
                                ("python3 scripts/batch_plan.py --help", ""), ("python3 other.py", ""),
                                ("ls scripts", "")):
            with self.subTest(command=command):
                self.assertEqual(agent.stage_script(command), script)

    def test_quoted_text(self):
        script = os.path.join(self.skill, "scripts", "batch_plan.py")
        for good in (f'python3 {script} add --kind topic --text "Projects: Atlas (new topic; a.docx)"',
                     f"python3 {script} add --text 'a | b & c > d'",
                     f'cd {self.skill} && python3 scripts/batch_plan.py add --text "x (y; z)"'):
            with self.subTest(good=good):
                self.assertTrue(self.ok("bash", good))
        for bad in (f'python3 {script} --text "$(id)"', f'python3 {script} --text "`id`"',
                    f'python3 {script} --text "a\\"; id; echo "', f'python3 {script} --text "open',
                    f'python3 {script} --text "a" ; id', f"python3 {script} --text 'a'|sh",
                    f'python3 {script} --text "line\nbreak"'):
            with self.subTest(bad=bad):
                self.assertFalse(self.ok("bash", bad))


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class GraphTest(unittest.TestCase):
    """The links between a library's files (kb_client.graph)."""

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lib = os.path.join(self.tmp, "lib")
        files = {
            "00_Spec.md": "Cite sources as basis: [[02_Example]].\n",
            "00_Status-Card.md": "- Release in May. basis: [[02_Plan]]\n- Owner. basis: [[02_Minutes|the minutes]]\n",
            "02_Plan.md": '---\nentities: ["[[Atlas]]"]\n---\nSee [[Riverside Clinic#Address]] and [[02_Plan]].\n',
            "02_Minutes.md": "---\ntype: topic\n---\nNo links.\n",
            "03_Atlas-Team.md": '---\ntype: "entity"\n---\nTeam page.\n',
            "Entities/Atlas.md": "---\ntype: entity\n---\n",
            "Archive/02_Plan_old20260101-0900.md": "[[Archived Link]]\n",
            "02_Plan_old20261001-1200.md": "[[Old Link]]\n",
            "_run-log_2026.md": "[[Log Link]]\n",
            "snapshot_00_Status-Card.md": "[[Snapshot Link]]\n",
            ".hidden/x.md": "[[Hidden Link]]\n",
            "notes.txt": "[[Text Link]]\n",
        }
        for rel, text in files.items():
            write(os.path.join(self.lib, rel), text)
        write(os.path.join(self.tmp, "outside", "secret.md"), "[[Outside Link]]\n")
        os.symlink(os.path.join(self.tmp, "outside"), os.path.join(self.lib, "out"))
        os.symlink(os.path.join(self.tmp, "outside", "secret.md"), os.path.join(self.lib, "02_Link.md"))
        old = time.time() - 3600
        for rel in ("00_Spec.md", "00_Status-Card.md", "02_Minutes.md", "03_Atlas-Team.md", "Entities/Atlas.md"):
            os.utime(os.path.join(self.lib, rel), (old, old))

    def test_nodes_and_links(self):
        g = kb_client.graph(self.lib, time.time() - 60)
        kinds = {n["id"]: n["kind"] for n in g["nodes"]}
        self.assertEqual(kinds, {"00_Spec": "summary", "00_Status-Card": "summary", "02_Plan": "topic",
                                 "02_Minutes": "topic", "03_Atlas-Team": "entity", "Atlas": "entity",
                                 "Riverside Clinic": "missing"})
        links = {(x["source"], x["target"]) for x in g["links"]}
        self.assertEqual(links, {("00_Status-Card", "02_Plan"), ("00_Status-Card", "02_Minutes"),
                                 ("02_Plan", "Atlas"), ("02_Plan", "Riverside Clinic")})
        nodes = {n["id"]: n for n in g["nodes"]}
        self.assertEqual([i for i, n in nodes.items() if n["new"]], ["02_Plan"])
        self.assertEqual((nodes["02_Plan"]["links"], nodes["Atlas"]["path"]), (3, os.path.join("Entities", "Atlas.md")))
        self.assertFalse(g["truncated"])
        self.assertNotIn(self.tmp, json.dumps(g))  # paths relative to the library

    def test_original_node(self):
        write(os.path.join(self.lib, "Sources", "02_Minutes.pdf"), "%PDF")
        write(os.path.join(self.lib, "Sources", "notes.md"), "[[Sources Link]]\n")  # never scanned
        write(os.path.join(self.lib, "02_Minutes.md"), '---\noriginal: "[[Sources/02_Minutes.pdf]]"\n---\nBody.\n')
        g = kb_client.graph(self.lib)
        nodes = {n["id"]: n for n in g["nodes"]}
        self.assertEqual((nodes["02_Minutes.pdf"]["kind"], nodes["02_Minutes.pdf"]["path"]),
                         ("original", os.path.join("Sources", "02_Minutes.pdf")))
        self.assertIn({"source": "02_Minutes", "target": "02_Minutes.pdf"}, g["links"])
        self.assertNotIn("notes", nodes)
        self.assertNotIn("Sources Link", nodes)

    def test_nothing_new_without_a_start_time(self):
        self.assertFalse(any(n["new"] for n in kb_client.graph(self.lib)["nodes"]))

    def test_node_limit(self):
        limit = kb_client.GRAPH_MAX_NODES
        self.addCleanup(setattr, kb_client, "GRAPH_MAX_NODES", limit)
        kb_client.GRAPH_MAX_NODES = 3
        g = kb_client.graph(self.lib)
        self.assertTrue(g["truncated"])
        self.assertLessEqual(len(g["nodes"]), 3)


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class IdleTest(unittest.TestCase):
    def test_stops_without_the_page(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        env = dict(os.environ, HOME=tmp, XDG_CONFIG_HOME=os.path.join(tmp, ".config"), PYTHONIOENCODING="utf-8")
        s = Server(env, "--idle", "1")
        self.addCleanup(s.stop)
        self.assertEqual(s.proc.wait(15), 0)


@unittest.skipIf(os.name == "nt", "desktop entries are for Linux desktops")
class DesktopEntryTest(unittest.TestCase):
    """Both double-click entries, at the top of the folder and in tools/kb-client, start kb_client.py."""

    def test_entries_reach_the_client(self):
        for entry in (os.path.join(ROOT, "kb-client.desktop"), os.path.join(os.path.dirname(TOOL), "kb-client.desktop")):
            with open(entry, encoding="utf-8") as f:
                line = next(x for x in f.read().splitlines() if x.startswith("Exec="))
            self.assertIn("exec python3 kb_client.py", line)
            args = shlex.split(line[len("Exec="):].replace("exec python3 kb_client.py", "test -f kb_client.py && pwd -P"))
            out = subprocess.run([entry if a == "%k" else a for a in args], capture_output=True, text=True, check=True)
            self.assertEqual(out.stdout.strip(), os.path.realpath(os.path.dirname(TOOL)), entry)



def skill_md(name, desc, version=""):
    return f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n" + (f"\nVersion: {version}\n" if version else "")


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class SkillsTest(unittest.TestCase):
    """The Skills section: listing, the lock on the knowledge-base skills, backup and restore, import, new."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.p("home")
        self.oc = self.p("home", ".config", "opencode", "skills")
        write(os.path.join(self.oc, "kb-query", "SKILL.md"), skill_md("kb-query", 'Answers from the library. "check my notes"', "1.16.0"))
        write(os.path.join(self.oc, "my-tool", "SKILL.md"), skill_md("my-tool", 'Does a thing. Use for "do the thing" or "thing please".'))
        write(os.path.join(self.p("home", ".claude", "skills", "my-tool", "SKILL.md")), skill_md("my-tool", "Older copy."))
        os.makedirs(self.p("tmp"))
        env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"), TMPDIR=self.p("tmp"),
                   PYTHONIOENCODING="utf-8", PATH=os.path.dirname(sys.executable))
        for k in ("KB_LIBRARIES", "LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
            env.pop(k, None)
        self.server = Server(env, "--idle", "0")
        self.addCleanup(self.server.stop)

    def p(self, *parts):
        return os.path.join(self.tmp, *parts)

    def skills(self):
        status, r = self.server.get("/api/skills")
        self.assertEqual(status, 200)
        return r["skills"]

    def test_list_groups_and_shadowing(self):
        sk = self.skills()
        self.assertEqual([(x["dir"], x["kb"], x["used"]) for x in sk],
                         [("kb-query", True, True), ("my-tool", False, True), ("my-tool", False, False)])
        self.assertEqual(sk[0]["version"], "1.16.0")
        self.assertEqual(sk[1]["triggers"], ["do the thing", "thing please"])
        self.assertEqual(sk[1]["agent"], "opencode")

    def test_knowledge_base_skills_are_backed_up_and_restored(self):
        res, out, _ = self.server.run("skill_backup", [], skill="kb-query")
        self.assertEqual(res, "ok", out)
        md = os.path.join(self.oc, "kb-query", "SKILL.md")
        before = read(md)
        write(md, "changed\n")
        when = os.listdir(self.p("home", ".config", "evergreen-wiki", "skill-backups", "kb-query"))[0]
        res, out, _ = self.server.run("skill_restore", [when, True], skill="kb-query")
        self.assertEqual(res, "ok", out)
        self.assertEqual(read(md), before)

    def test_backup_and_restore(self):
        res, out, _ = self.server.run("skill_backup", [], skill="my-tool")
        self.assertEqual(res, "ok", out)
        self.assertIn("skill-backups", out)
        md = os.path.join(self.oc, "my-tool", "SKILL.md")
        write(md, "changed\n")
        self.assertEqual(self.skills()[1]["backups"], 1)
        when = os.listdir(self.p("home", ".config", "evergreen-wiki", "skill-backups", "my-tool"))[0]
        res, out, asked = self.server.run("skill_restore", [when, True], skill="my-tool")
        self.assertEqual(res, "ok", out)
        self.assertIn("Does a thing", read(md))
        self.assertEqual(self.skills()[1]["backups"], 2)  # the changed version was kept too
        res, out, _ = self.server.run("skill_restore", [when, False], skill="my-tool")
        self.assertEqual(res, "stopped")

    def test_new_skill(self):
        res, out, _ = self.server.run("skill_new", ["weekly-report", "Writes the weekly report", True])
        self.assertEqual(res, "ok", out)
        self.assertIn("skill: weekly-report", out)
        text = read(os.path.join(self.oc, "weekly-report", "SKILL.md"))
        self.assertIn("name: weekly-report", text)
        self.assertIn("Writes the weekly report.", text)
        for name in ("weekly-report", "kb-note", "Bad Name"):
            res, out, _ = self.server.run("skill_new", [name])
            self.assertEqual(res, "stopped", name)

    def test_import_folder_and_zip(self):
        src = self.p("ext", "summarise")
        write(os.path.join(src, "SKILL.md"), skill_md("summarise", 'Summaries. "sum it up"'))
        write(os.path.join(src, "scripts", "x.py"), "print(1)\n")
        res, out, _ = self.server.run("skill_import", ["folder", src, True])
        self.assertEqual(res, "ok", out)
        self.assertTrue(os.path.isfile(os.path.join(self.oc, "summarise", "scripts", "x.py")))
        res, out, _ = self.server.run("skill_import", ["folder", src])
        self.assertEqual(res, "stopped")
        self.assertIn("exists already", out)
        import zipfile
        good, bad = self.p("good.zip"), self.p("bad.zip")
        with zipfile.ZipFile(good, "w") as z:
            z.writestr("notes-helper/SKILL.md", skill_md("notes-helper", "Helps."))
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("../evil/SKILL.md", skill_md("evil", "x"))
        res, out, _ = self.server.run("skill_import", ["zip", good, True])
        self.assertEqual(res, "ok", out)
        self.assertTrue(os.path.isfile(os.path.join(self.oc, "notes-helper", "SKILL.md")))
        res, out, _ = self.server.run("skill_import", ["zip", bad])
        self.assertEqual(res, "stopped")
        self.assertIn("outside", out)
        self.assertFalse(os.path.exists(self.p("evil")))


@unittest.skipUnless(os.name == "posix", "the client runs on Linux desktops")
class SkillCommandTest(unittest.TestCase):
    def test_skill_command_on_several_lines(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = os.path.join(tmp, "skills", "kb-incremental")
        lib = os.path.join(tmp, "lib")
        os.makedirs(os.path.join(kb, "scripts"))
        os.makedirs(lib)
        write(os.path.join(kb, "scripts", "batch_plan.py"), "")
        scripts = os.path.join(kb, "scripts")
        places = {"scripts": [scripts], "write": [lib], "read": [kb]}
        script = os.path.join(scripts, "batch_plan.py")
        joined = (f'python3 {script} plan \\\n  "{tmp}/inbox/Project Atlas" \\\n  --plan {lib}/_intake-batches.json \\\n'
                  f"  --library-root {lib} \\\n  --batch-files 5 2>&1")
        blank = f'python3 {script} plan \\\n\\\n  "{tmp}/inbox/Project Atlas" \\\n  --batch-files 5 2>&1'  # an empty continued line
        for cmd in (joined, blank, joined.replace("\n", "\r\n"), f"python3 {script} plan x 2>/dev/null",
                    f"python3 {script} plan x 2> /dev/null 2>&1"):
            self.assertTrue(agent.skill_command(cmd, [scripts], tmp), cmd)
            self.assertTrue(agent.decide("bash", [cmd], places, tmp), cmd)
        for cmd in (f"python3 {script} plan x 2>&1; rm -rf {kb}", f"python3 {script} plan x > {kb}/x",
                    f"python3 {script} plan x 2>{kb}/err", f"python3 {script} plan x 2>&1 | tee {kb}/x",
                    f"python3 {script} plan $(rm -rf {kb})"):
            self.assertFalse(agent.skill_command(cmd, [scripts], tmp), cmd)
            self.assertFalse(agent.decide("bash", [cmd], places, tmp), cmd)  # a card, not refused
        # listing or reading the skill folder is a read-only command like any other
        self.assertTrue(agent.decide("bash", [f"ls {kb}/"], places, tmp))
        self.assertTrue(agent.decide("bash", [f"cat {kb}/SKILL.md | head -5"], places, tmp))
        # inside quotes nothing is joined or dropped
        self.assertEqual(agent.plain_command("echo 'a \\\nb' '2>&1'"), "echo 'a \\\nb' '2>&1'")
        self.assertFalse(agent.skill_command(f"python3 {script} 'a \\\nb'", [scripts], tmp))
        self.assertEqual(agent.plain_command("a \\\nb 2>&1"), "a  b")


if __name__ == "__main__":
    unittest.main()
