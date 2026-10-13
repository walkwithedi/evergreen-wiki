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
        self.env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=self.p("home", ".config"),
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

    def test_needs_opencode_and_a_model(self):
        os.remove(self.p("home", ".config", "opencode", "opencode.jsonc"))
        s = Server(self.env, "--idle", "0")
        self.addCleanup(s.stop)
        status, r = s.post("/api/chat/start", {})
        self.assertEqual((status, r["reason"]), (409, "no_model"))
        self.assertEqual(s.post("/api/chat/send", {"text": "hello"})[0], 409)
        self.assertEqual(s.get("/api/chat/state")[1]["agent"]["state"], "off")

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
        self.assertEqual(saved, {"session": new})

    def test_bad_requests(self):
        self.ready()
        s = self.server
        self.assertEqual(s.post("/api/chat/send", {"text": ""})[0], 400)
        self.assertEqual(s.post("/api/chat/send", {"text": "x" * 20001})[0], 400)
        self.assertEqual(s.post("/api/chat/send", {"text": "x", "material": ["relative"]})[0], 400)
        self.assertEqual(s.post("/api/chat/question", {"id": "x", "answers": "no"})[0], 400)
        self.assertEqual(s.post("/api/chat/permission", {"id": "unknown", "allow": True})[0], 409)
        self.assertEqual(s.get("/api/chat/state", token=False)[0], 403)

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


if __name__ == "__main__":
    unittest.main()
