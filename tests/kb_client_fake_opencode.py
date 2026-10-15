#!/usr/bin/env python3
"""A stand-in for `opencode` in the kb-client tests: `serve` answers the parts of the OpenCode 1.19 HTTP
interface the client uses and sends their events; `run <message>` prints an answer.

FAKE_OPENCODE_LOG: file that gets one JSON line per call (the arguments, OPENCODE_CONFIG_CONTENT, and
every request). FAKE_OPENCODE_MODE: "noserve" (serve exits at once), "noserve1" (only the first serve
exits at once; needs FAKE_OPENCODE_LOG), "noapi" (GET /permission is 404), "slow" (serve never says it
listens). Messages starting with PERM <permission> <pattern>, QUESTION or SLOW
make the session ask for a permission, ask a question or wait to be aborted; SUBAGENT <permission>
<pattern> starts a subagent session that asks for that permission; THINK sends reasoning first; RUN <command>
shows a finished bash step running that command; STEPS <n> gives one answer with n tool steps (the third
one failed); EDIT shows a finished edit step with a diff. A message naming a decision_<n>.json file is a
client intake turn: the head and decision files are written (FAKE_OPENCODE_INTAKE: bad_once, never, slow).
A message naming a consolidate_<r>.json file is a client consolidation round: one row leaves the library's
queue and the result file is written (FAKE_OPENCODE_CONSOLIDATE: "ask" asks the step-5 question first and
consolidates only when it is answered with Accept all, "stuck" changes nothing). GET /session lists the sessions with this
server's folder, their time and parent; GET /config/providers offers example/model-1 and example/model-2.
"""
import json
import os
import queue
import re
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = os.environ.get("FAKE_OPENCODE_LOG", "")
INTAKE_RE = re.compile(r"/[^\s，。）]+decision_\d+\.json")
CONSOLIDATE_RE = re.compile(r"/[^\s，。）]+consolidate_\d+\.json")
MODE = os.environ.get("FAKE_OPENCODE_MODE", "")


def note(**data):
    if LOG:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


class World:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}  # id -> [{"info", "parts"}]
        self.meta = {}  # id -> {"parentID", "time"}
        self.clients = []
        self.bad = set()  # decision files answered wrongly once (FAKE_OPENCODE_INTAKE bad_once)
        self.waits = {}  # permission or question id -> (threading.Event, [reply])
        self.aborts = {}
        self.n = 0

    def next(self, prefix):
        with self.lock:
            self.n += 1
            return f"{prefix}{self.n}"

    def emit(self, etype, **props):
        ev = {"id": self.next("e"), "type": etype, "properties": props}
        for q in list(self.clients):
            q.put(ev)

    def message(self, sid, role, text):
        mid = self.next("m")
        info = {"id": mid, "sessionID": sid, "role": role}
        part = {"id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "text", "text": text}
        self.sessions[sid].append({"info": info, "parts": [part]})
        self.emit("message.updated", sessionID=sid, info=info)
        if role == "assistant" and len(text) > 3:
            self.emit("message.part.updated", sessionID=sid, part=dict(part, text=""), time=0)
            self.emit("message.part.delta", sessionID=sid, messageID=mid, partID=part["id"], field="text",
                      delta=text)
        self.emit("message.part.updated", sessionID=sid, part=part, time=0)

    def wait_for(self, rid, timeout=20):
        ev, box = self.waits[rid]
        ev.wait(timeout)
        return box[0] if box else None

    def turn(self, sid, text):
        self.message(sid, "user", text)
        self.emit("session.status", sessionID=sid, status={"type": "busy"})
        words = text.split()
        if words[0] == "PERM":
            rid = self.next("per")
            self.waits[rid] = (threading.Event(), [])
            self.emit("permission.asked", id=rid, sessionID=sid, permission=words[1], patterns=[" ".join(words[2:])],
                      metadata={}, always=[words[1] + " *"])
            got = self.wait_for(rid)
            self.emit("permission.replied", sessionID=sid, requestID=rid, reply=got)
            self.message(sid, "assistant", f"permission: {got}")
        elif words[0] == "QUESTION":
            rid = self.next("que")
            self.waits[rid] = (threading.Event(), [])
            self.emit("question.asked", id=rid, sessionID=sid, questions=[
                {"question": "Which library?", "header": "Library",
                 "options": [{"label": "Work", "description": "the work library"},
                             {"label": "Life", "description": "the life library"}]}])
            got = self.wait_for(rid)
            self.emit("question.replied", sessionID=sid, requestID=rid, answers=got)
            self.message(sid, "assistant", f"answers: {json.dumps(got)}")
        elif words[0] == "SUBAGENT":
            child = self.next("ses")
            self.sessions[child] = []
            self.meta[child] = {"parentID": sid, "time": {"created": time.time(), "updated": time.time()}}
            self.emit("session.created", info={"id": child, "parentID": sid, "title": "explore"})
            rid = self.next("per")
            self.waits[rid] = (threading.Event(), [])
            self.emit("permission.asked", id=rid, sessionID=child, permission=words[1],
                      patterns=[" ".join(words[2:])], metadata={}, always=[])
            got = self.wait_for(rid)
            self.emit("permission.replied", sessionID=child, requestID=rid, reply=got)
            self.emit("session.status", sessionID=child, status={"type": "idle"})  # only the child is idle
            self.message(child, "assistant", f"subagent: {got}")
            self.message(sid, "assistant", "done after the subagent")
        elif words[0] == "THINK":
            mid = self.next("m")
            info = {"id": mid, "sessionID": sid, "role": "assistant"}
            self.emit("message.updated", sessionID=sid, info=info)
            self.emit("message.part.updated", sessionID=sid, time=0, part={
                "id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "reasoning", "text": "pondering"})
            for part in ({"type": "text", "text": "let me look"},
                         {"type": "tool", "tool": "read", "callID": "c1",
                          "state": {"status": "completed", "input": {"filePath": "/x/a.md"}, "output": "",
                                    "title": "a.md", "metadata": {}, "time": {"start": 0, "end": 0}}},
                         {"type": "text", "text": "the answer"}):
                self.emit("message.part.updated", sessionID=sid, time=0,
                          part=dict(part, id=self.next("p"), sessionID=sid, messageID=mid))
        elif words[0] == "RUN":
            mid = self.next("m")
            info = {"id": mid, "sessionID": sid, "role": "assistant"}
            self.emit("message.updated", sessionID=sid, info=info)
            self.emit("message.part.updated", sessionID=sid, time=0, part={
                "id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "tool", "tool": "bash",
                "callID": "c2", "state": {"status": "completed", "input": {"command": text[4:]}, "output": "",
                                          "title": "Run a script", "metadata": {}, "time": {"start": 0, "end": 0}}})
        elif words[0] == "STEPS":
            mid = self.next("m")
            info = {"id": mid, "sessionID": sid, "role": "assistant"}
            parts = []
            for k in range(int(words[1])):
                tool, status = ("read", "completed") if k % 2 else ("bash", "error" if k == 2 else "completed")
                parts.append({"id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "tool", "tool": tool,
                              "callID": f"s{k}", "state": {"status": status, "input": {"filePath": f"/x/{k}.md"},
                                                           "output": "", "title": f"step {k}", "metadata": {},
                                                           "error": "failed" if status == "error" else None,
                                                           "time": {"start": 0, "end": 0}}})
            parts.append({"id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "text",
                          "text": "steps done"})
            self.sessions[sid].append({"info": info, "parts": parts})
            self.emit("message.updated", sessionID=sid, info=info)
            for part in parts:
                self.emit("message.part.updated", sessionID=sid, part=part, time=0)
        elif words[0] == "EDIT":
            mid = self.next("m")
            info = {"id": mid, "sessionID": sid, "role": "assistant"}
            part = {"id": self.next("p"), "sessionID": sid, "messageID": mid, "type": "tool", "tool": "edit",
                    "callID": "e1", "state": {"status": "completed", "input": {"filePath": "notes.txt"}, "output": "",
                                              "title": "notes.txt", "time": {"start": 0, "end": 0},
                                              "metadata": {"diff": "--- notes.txt\n+++ notes.txt\n-old\n+new\n"}}}
            self.sessions[sid].append({"info": info, "parts": [part]})
            self.emit("message.updated", sessionID=sid, info=info)
            self.emit("message.part.updated", sessionID=sid, part=part, time=0)
        elif words[0] == "SLOW":
            ev = self.aborts.setdefault(sid, threading.Event())
            ev.clear()
            self.message(sid, "assistant", "aborted" if ev.wait(20) else "slow done")
        elif CONSOLIDATE_RE.search(text):
            self.message(sid, "assistant", self.consolidate(text, sid))
        elif INTAKE_RE.search(text):
            self.message(sid, "assistant", self.intake(text, sid))
        else:
            self.message(sid, "assistant", "echo: " + text)
        self.emit("session.status", sessionID=sid, status={"type": "idle"})

    def consolidate(self, text, sid):
        """A client consolidation round: the first row of the queue named by the library root leaves it."""
        result = CONSOLIDATE_RE.search(text).group(0)
        mode = os.environ.get("FAKE_OPENCODE_CONSOLIDATE", "")
        root = re.search(r"(?:Library|知识库)[:：][^(（]*[(（](.+?)[)）]\n", text).group(1)
        files = 0
        if mode == "ask":
            rid = self.next("que")
            self.waits[rid] = (threading.Event(), [])
            self.emit("question.asked", id=rid, sessionID=sid, questions=[
                {"question": "Apply these changes?", "header": "Changes",
                 "options": [{"label": "Leave some out first", "description": ""},
                             {"label": "Accept all (recommended)", "description": ""},
                             {"label": "Cancel the round", "description": ""}]}])
            got = self.wait_for(rid, 60)
            self.emit("question.replied", sessionID=sid, requestID=rid, answers=got)
            if not (got and got[0] and got[0][0].startswith("Accept all")):
                mode = "stuck"
        if mode != "stuck":
            queue = os.path.join(root, "_Consolidation-Queue.md")
            with open(queue, encoding="utf-8") as f:
                lines = f.read().split("\n")
            for i, ln in enumerate(lines):
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if ln.strip().startswith("|") and cells[0].endswith(".md"):
                    del lines[i]
                    files = 1
                    break
            with open(queue, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        with open(result, "w", encoding="utf-8") as f:
            json.dump({"files": files, "changes": 2 * files}, f)
        return "round done"

    def intake(self, text, sid):
        """A client intake turn: writes the head file and the decision file the message names. The title
        is the original file's name; a name-hit message makes it the next version. FAKE_OPENCODE_INTAKE:
        "bad_once" writes an unusable decision the first time for each item, "never" writes nothing,
        "slow" waits until the turn is aborted."""
        decision = INTAKE_RE.search(text).group(0)
        head = re.sub(r"decision_(\d+)\.json$", r"head_\1.md", decision)
        mode = os.environ.get("FAKE_OPENCODE_INTAKE", "")
        if mode == "never":
            return "thinking about it"
        if mode == "slow":  # waits to be stopped
            ev = self.aborts.setdefault(sid, threading.Event())
            ev.clear()
            return "aborted" if ev.wait(20) else "slow done"
        if mode == "bad_once" and decision not in self.bad:
            self.bad.add(decision)
            with open(decision, "w", encoding="utf-8") as f:
                f.write('{"partition": ""}')
            return "decided"
        orig = re.search(r"(?:Original file|原文件)[:：]\s*(.+)", text)
        title = os.path.splitext(os.path.basename(orig.group(1).strip()))[0] if orig else ""
        prev = {}
        if os.path.isfile(decision):
            try:
                with open(decision, encoding="utf-8") as f:
                    prev = json.load(f)
            except ValueError:
                prev = {}
        title = title or prev.get("title") or "Item"
        same = bool(prev.get("same_version")) or "next version of that file" in text or "新版本" in text and "同名" in text
        with open(head, "w", encoding="utf-8") as f:
            f.write("> Source: " + title + "\n")
        with open(decision, "w", encoding="utf-8") as f:
            json.dump({"partition": "02", "topic": "Atlas", "type": "Report", "title": title,
                       "close_read": False, "same_version": same}, f)
        return "decided"
        self.emit("session.idle", sessionID=sid)


WORLD = World()


class Server(ThreadingHTTPServer):
    """No reverse lookup of the host name when binding: it can wait for a DNS timeout on some systems."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def reply(self, code, data=None):
        body = b"" if data is None else json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        note(method="GET", path=self.path)
        parts = self.path.strip("/").split("/")
        if self.path == "/event":
            q = queue.Queue()
            WORLD.clients.append(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            try:
                self.wfile.write(b'data: {"type": "server.connected", "properties": {}}\n\n')
                self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=5)
                        self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except OSError:
                WORLD.clients.remove(q)
            return None
        if self.path == "/session":
            return self.reply(200, [dict({"id": k, "title": "t-" + k, "directory": os.getcwd()}, **WORLD.meta.get(k, {}))
                                    for k in WORLD.sessions])
        if self.path == "/config/providers":
            return self.reply(200, {"providers": [{"id": "example", "models": {
                "model-1": {"name": "Model One"}, "model-2": {"name": "Model Two"}}}], "default": {"example": "model-1"}})
        if self.path == "/permission":
            return self.reply(404 if MODE == "noapi" else 200, [])
        if len(parts) == 2 and parts[0] == "session":
            return self.reply(200 if parts[1] in WORLD.sessions else 404, {"id": parts[1]})
        if len(parts) == 3 and parts[0] == "session" and parts[2] == "message":
            return self.reply(200, WORLD.sessions.get(parts[1], []))
        return self.reply(404, {})

    def do_POST(self):
        body = self.body()
        note(method="POST", path=self.path, body=body)
        parts = self.path.strip("/").split("/")
        if self.path == "/session":
            sid = WORLD.next("ses")
            WORLD.sessions[sid] = []
            WORLD.meta[sid] = {"time": {"created": time.time(), "updated": time.time()}}
            return self.reply(200, {"id": sid})
        if len(parts) == 3 and parts[0] == "session" and parts[2] == "prompt_async":
            text = body["parts"][0]["text"]
            threading.Thread(target=WORLD.turn, args=(parts[1], text), daemon=True).start()
            return self.reply(204)
        if len(parts) == 3 and parts[0] == "session" and parts[2] == "abort":
            WORLD.aborts.setdefault(parts[1], threading.Event()).set()
            return self.reply(200, True)
        if len(parts) == 3 and parts[0] in ("permission", "question") and parts[2] in ("reply", "reject"):
            if parts[1] not in WORLD.waits:
                return self.reply(404, {})
            ev, box = WORLD.waits[parts[1]]
            box.append(body.get("reply") or body.get("answers") or "rejected")
            ev.set()
            return self.reply(200, True)
        return self.reply(404, {})


def main():
    args = sys.argv[1:]
    note(args=args, config=os.environ.get("OPENCODE_CONFIG_CONTENT", ""), cwd=os.getcwd(), pid=os.getpid())
    if args[:1] == ["run"]:
        print("run: " + " ".join(args[1:]), flush=True)
        return 0
    if args[:1] != ["serve"]:
        return 2
    print("refreshing the model settings", flush=True)
    if MODE == "noserve":
        return 1
    if MODE == "noserve1" and not os.path.exists(LOG + ".once"):
        with open(LOG + ".once", "w", encoding="utf-8"):
            return 1
    server = Server(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    if MODE == "slow":
        time.sleep(60)
    print(f"opencode server listening on http://127.0.0.1:{server.server_address[1]}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
