"""OpenCode behind the knowledge base client: starts `opencode serve` on 127.0.0.1, keeps one current
conversation, passes its events to the page and answers permission requests the client may answer itself.

Only this module talks to OpenCode; the page talks to kb_client.py. The interface used is the one of
OpenCode 1.19 (checked at start: GET /session and GET /permission must answer): POST /session,
GET /session/{id}/message, POST /session/{id}/prompt_async, POST /session/{id}/abort, GET /event,
POST /permission/{id}/reply, POST /question/{id}/reply and /reject. When the server does not start or
the interface is missing, a simple mode runs `opencode run <message>` once per message instead.
Python 3 standard library only.
"""
import http.client
import json
import logging
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from urllib.parse import quote

log = logging.getLogger("kb_client.agent")
LISTEN_RE = re.compile(r"opencode server listening on (https?://)?(127\.0\.0\.1|localhost):(\d+)")
GLOB_CHARS = "*?[{"
SHELL_CHARS = set(";|&`$<>(){}\n\r\\")
PYTHONS = ("python3", "python")
FEED_KEEP = 5000  # events kept for a page that reconnects; older ones come back through the history
# Every action of the OpenCode this client starts asks first; the client answers what it may itself.
ASK_ALL = {"permission": {name: "ask" for name in (
    "read", "edit", "glob", "grep", "list", "bash", "task", "external_directory", "webfetch", "websearch",
    "lsp", "skill")}}
# The skills load their own instructions; reading a skill is never a question for the user.
ASK_ALL["permission"]["skill"] = "allow"


# ---------- which requests the client answers itself ----------

def real(path):
    return os.path.realpath(os.path.normpath(path))


def inside(path, root):
    path, root = real(path), real(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def pattern_path(pattern, cwd):
    """The folder or file a permission pattern stands for: the part before the first wildcard, taken
    from cwd when relative. "" for an empty pattern."""
    p = os.path.expanduser(str(pattern).strip())
    if not p:
        return ""
    cut = min([p.index(c) for c in GLOB_CHARS if c in p] or [len(p)])
    if cut < len(p):
        p = p[:cut]
        p = p if p.endswith(os.sep) else os.path.dirname(p)
    p = p or "."
    return real(p if os.path.isabs(p) else os.path.join(cwd, p))


def skill_command(command, script_dirs, cwd):
    """True for `python3 [-I|-B|-u] <script>.py args` (optionally after one `cd <folder> &&`) whose script
    lies in one of script_dirs, with no other shell syntax at all."""
    cmd = str(command).strip()
    m = re.fullmatch(r"cd\s+(\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s*&&\s*(.*)", cmd, re.S)
    where = cwd
    if m:
        where = os.path.join(cwd, os.path.expanduser(m.group(1).strip("'\"")))
        cmd = m.group(2)
    if not cmd or SHELL_CHARS & set(cmd):
        return False
    try:
        words = shlex.split(cmd)
    except ValueError:
        return False
    if not words or os.path.basename(words[0]) not in PYTHONS:
        return False
    rest = words[1:]
    while rest and rest[0] in ("-I", "-B", "-u"):
        rest = rest[1:]
    if not rest or not rest[0].endswith(".py"):
        return False
    script = os.path.join(where, os.path.expanduser(rest[0]))
    return os.path.isfile(script) and any(inside(script, d) for d in script_dirs)


def decide(permission, patterns, places, cwd):
    """True when the client answers "once" itself. places: {"write": [...], "read": [...],
    "scripts": [...]} as real folder paths. Writing only inside a registered library; reading also in the
    chosen material, the skills and the agent's own settings; commands only the skills' own scripts.
    Everything else, and anything that cannot be read clearly, goes to the user."""
    patterns = [p for p in (patterns or []) if str(p).strip()]
    if not patterns:
        return False
    if permission == "bash":
        return all(skill_command(p, places.get("scripts", []), cwd) for p in patterns)
    if permission in ("edit", "write"):
        roots = places.get("write", [])
    elif permission in ("read", "list", "glob", "grep", "external_directory"):
        roots = places.get("write", []) + places.get("read", []) + places.get("scripts", [])
    else:
        return False
    for p in patterns:
        path = pattern_path(p, cwd)
        if not path or not any(inside(path, r) for r in roots):
            return False
    return True


# ---------- events for the page ----------

class Feed:
    """Numbered events for the page, kept for reconnects (the last FEED_KEEP)."""

    def __init__(self):
        self.cond = threading.Condition()
        self.events = []
        self.first = 1  # number of events[0]

    def emit(self, etype, **data):
        with self.cond:
            seq = self.first + len(self.events)
            self.events.append(dict(data, type=etype, seq=seq))
            if len(self.events) > FEED_KEEP:
                drop = len(self.events) - FEED_KEEP
                self.events = self.events[drop:]
                self.first += drop
            self.cond.notify_all()
            return seq

    def last(self):
        with self.cond:
            return self.first + len(self.events) - 1

    def since(self, seq, timeout):
        with self.cond:
            if self.first + len(self.events) - 1 <= seq:
                self.cond.wait(timeout)
            start = max(0, seq + 1 - self.first)
            return self.events[start:]


def part_event(part, role):
    """What the page needs of one message part: text, or a tool step in one line. None for the rest."""
    kind = part.get("type")
    base = {"messageID": part.get("messageID", ""), "partID": part.get("id", ""), "role": role}
    if kind == "text" and not part.get("synthetic") and not part.get("ignored"):
        return dict(base, kind="text", text=str(part.get("text", "")))
    if kind == "tool":
        state = part.get("state") or {}
        detail = state.get("title") or ""
        if not detail:
            inp = state.get("input") or {}
            detail = str(inp.get("command") or inp.get("filePath") or inp.get("path") or inp.get("pattern") or "")
        return dict(base, kind="tool", tool=str(part.get("tool", "")), status=str(state.get("status", "")),
                    detail=detail[:300], error=str(state.get("error", ""))[:300])
    return None


# ---------- OpenCode ----------

class Agent:
    """state: off, starting, ready, simple (opencode run per message), failed."""

    def __init__(self, program, cwd, places, state_file, start_timeout=90):
        self.program = program
        self.cwd = cwd
        self.places = places  # callable returning {"write", "read", "scripts"} without the material
        self.state_file = state_file
        self.start_timeout = start_timeout
        self.feed = Feed()
        self.lock = threading.RLock()
        self.state = "off"
        self.reason = ""
        self.output = []  # last lines OpenCode printed while starting
        self.proc = None
        self.port = None
        self.session = None
        self.status = "idle"
        self.material = []  # paths chosen for the current conversation's intake
        self.roles = {}  # messageID -> role
        self.permissions = {}  # pending, id -> event
        self.questions = {}
        self.run_proc = None  # simple mode
        self.stopping = False

    # ----- start and stop -----

    def start(self):
        with self.lock:
            if self.state != "off":
                return
            self.state = "starting"
        self.feed.emit("agent", state="starting")
        threading.Thread(target=self._start, daemon=True).start()

    def _start(self):
        env = dict(os.environ, OPENCODE_CONFIG_CONTENT=json.dumps(ASK_ALL))
        try:
            self.proc = subprocess.Popen([self.program, "serve", "--hostname=127.0.0.1", "--port=0"],
                                         cwd=self.cwd, env=env, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace",
                                         start_new_session=True)
        except OSError as e:
            self._simple(f"opencode serve: {e}")
            return
        found = threading.Event()
        threading.Thread(target=self._read_output, args=(found,), daemon=True).start()
        if not found.wait(self.start_timeout) or self.port is None:
            self._kill()
            self._simple("opencode serve did not start")
            return
        try:
            for path in ("/session", "/permission"):
                code, _ = self.call("GET", path)
                if code != 200:
                    raise OSError(f"GET {path} answered {code}")
        except (OSError, ValueError) as e:
            self._kill()
            self._simple(f"opencode serve: {e}")
            return
        with self.lock:
            self.state = "ready"
        threading.Thread(target=self._events, daemon=True).start()
        self._resume()
        self.feed.emit("agent", state="ready", session=self.session)

    def _read_output(self, found):
        for line in self.proc.stdout:
            line = line.rstrip("\n")
            log.debug("opencode: %s", line)
            self.output = (self.output + [line])[-20:]
            if not found.is_set():
                self.feed.emit("agent", state="starting", line=line[:300])
                m = LISTEN_RE.search(line)
                if m:
                    self.port = int(m.group(3))
                    found.set()
        found.set()  # the program ended

    def _simple(self, reason):
        log.warning("simple mode: %s", reason)
        with self.lock:
            self.state = "simple"
            self.reason = reason
        self.feed.emit("agent", state="simple", reason=reason, output="\n".join(self.output[-10:]))

    def _kill(self):
        proc = self.proc
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:  # the process group has ended meanwhile
                    log.debug("opencode had already stopped")

    def shutdown(self):
        self.stopping = True
        self._kill()
        rp = self.run_proc
        if rp and rp.poll() is None:
            try:
                os.killpg(rp.pid, signal.SIGTERM)
            except OSError:  # the run has ended meanwhile
                log.debug("opencode run had already stopped")

    # ----- talking to OpenCode -----

    def call(self, method, path, body=None, timeout=30):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            data = None if body is None else json.dumps(body).encode("utf-8")
            c.request(method, path, body=data, headers={"Content-Type": "application/json"} if data else {})
            r = c.getresponse()
            raw = r.read()
            try:
                return r.status, json.loads(raw) if raw else None
            except ValueError:
                return r.status, None
        finally:
            c.close()

    def _events(self):
        while not self.stopping:
            try:
                c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=None)
                c.request("GET", "/event", headers={"Accept": "text/event-stream"})
                r = c.getresponse()
                for raw in r.fp:
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        try:
                            ev = json.loads(line[5:].strip())
                        except ValueError:
                            continue
                        if isinstance(ev, dict):
                            self._handle(ev)
                c.close()
            except (OSError, http.client.HTTPException) as e:
                log.debug("event stream: %s", e)
            if self.proc and self.proc.poll() is not None:
                with self.lock:
                    self.state = "failed"
                    self.reason = "opencode stopped"
                self.feed.emit("agent", state="failed", reason=self.reason,
                               output="\n".join(self.output[-10:]))
                return
            time.sleep(1)

    def _handle(self, ev):
        kind = ev.get("type", "")
        p = ev.get("properties") or {}
        sid = p.get("sessionID") or (p.get("info") or {}).get("sessionID") or (p.get("part") or {}).get("sessionID")
        if sid != self.session:
            return
        if kind == "message.updated":
            info = p.get("info") or {}
            self.roles[info.get("id", "")] = info.get("role", "assistant")
            err = info.get("error")
            if err:
                self.feed.emit("error", text=str((err.get("data") or {}).get("message") or err.get("name") or err))
        elif kind == "message.part.updated":
            part = p.get("part") or {}
            pe = part_event(part, self.roles.get(part.get("messageID", ""), "assistant"))
            if pe:
                self.feed.emit("part", **pe)
        elif kind == "message.part.delta":
            if p.get("field") == "text":
                self.feed.emit("delta", messageID=p.get("messageID", ""), partID=p.get("partID", ""),
                               role=self.roles.get(p.get("messageID", ""), "assistant"), delta=str(p.get("delta", "")))
        elif kind == "session.status":
            self._set_status((p.get("status") or {}).get("type", "idle"))
        elif kind == "session.idle":
            self._set_status("idle")
        elif kind == "session.error":
            err = p.get("error") or {}
            self.feed.emit("error", text=str((err.get("data") or {}).get("message") or err.get("name") or "error"))
        elif kind == "permission.asked":
            self._permission(p)
        elif kind == "permission.replied":
            rid = p.get("requestID") or p.get("id") or ""
            if self.permissions.pop(rid, None) is not None:
                self.feed.emit("permission_done", id=rid)
        elif kind == "question.asked":
            q = {"id": p.get("id", ""), "questions": [
                {"question": str(x.get("question", "")), "header": str(x.get("header", "")),
                 "multiple": bool(x.get("multiple")), "custom": x.get("custom", True) is not False,
                 "options": [{"label": str(o.get("label", "")), "description": str(o.get("description", ""))}
                             for o in x.get("options") or []]}
                for x in p.get("questions") or []]}
            self.questions[q["id"]] = q
            self.feed.emit("question", **q)
        elif kind in ("question.replied", "question.rejected"):
            rid = p.get("requestID") or p.get("id") or ""
            if self.questions.pop(rid, None) is not None:
                self.feed.emit("question_done", id=rid)

    def _set_status(self, status):
        self.status = status
        self.feed.emit("status", status=status)

    def allowed_places(self):
        pl = self.places()
        return {"write": [real(x) for x in pl.get("write", [])],
                "read": [real(x) for x in pl.get("read", []) + self.material],
                "scripts": [real(x) for x in pl.get("scripts", [])]}

    def _permission(self, p):
        rid = p.get("id", "")
        perm = str(p.get("permission", ""))
        patterns = [str(x) for x in p.get("patterns") or []]
        if decide(perm, patterns, self.allowed_places(), self.cwd):
            try:
                self.call("POST", f"/permission/{quote(rid, safe='')}/reply", {"reply": "once"})
                self.feed.emit("auto", permission=perm, patterns=patterns[:5])
                return
            except OSError as e:
                log.warning("automatic reply failed: %s", e)
        ev = {"id": rid, "permission": perm, "patterns": patterns[:20]}
        self.permissions[rid] = ev
        self.feed.emit("permission", **ev)

    # ----- the conversation -----

    def _load_saved(self):
        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("session") if isinstance(data, dict) else None
        except (OSError, ValueError):
            return None

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp = self.state_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"session": self.session}, f)
            os.replace(tmp, self.state_file)
        except OSError as e:
            log.warning("cannot save the conversation: %s", e)

    def _resume(self):
        sid = self._load_saved()
        if sid and re.fullmatch(r"[\w-]{1,100}", sid):
            try:
                code, _ = self.call("GET", f"/session/{sid}")
                if code == 200:
                    self.session = sid
                    return
            except OSError:  # OpenCode cannot say; a new conversation starts with the first message
                log.debug("saved conversation %s not found", sid)
        self.session = None

    def ensure_session(self):
        if self.session:
            return self.session
        code, data = self.call("POST", "/session", {"title": "Knowledge base"})
        if code != 200 or not isinstance(data, dict) or not data.get("id"):
            raise OSError(f"POST /session answered {code}")
        self.session = str(data["id"])
        self._save()
        return self.session

    def new(self):
        with self.lock:
            self.material = []
            self.permissions.clear()
            self.questions.clear()
            self.roles.clear()
            self.status = "idle"
            if self.state == "ready":
                self.session = None
                self.ensure_session()
        self.feed.emit("reset", session=self.session)

    def history(self):
        """The current conversation as part events, for a page that opens or reconnects."""
        if self.state != "ready" or not self.session:
            return []
        code, data = self.call("GET", f"/session/{self.session}/message")
        out = []
        for msg in data if code == 200 and isinstance(data, list) else []:
            info = msg.get("info") or {}
            role = info.get("role", "assistant")
            self.roles[info.get("id", "")] = role
            for part in msg.get("parts") or []:
                pe = part_event(part, role)
                if pe:
                    out.append(pe)
        return out

    def send(self, text, material=()):
        for path in material:
            if os.path.isabs(path) and path not in self.material:
                self.material.append(path)
        if self.state == "simple":
            return self._run(text)
        if self.state != "ready":
            raise RuntimeError("not ready")
        sid = self.ensure_session()
        code, _ = self.call("POST", f"/session/{sid}/prompt_async", {"parts": [{"type": "text", "text": text}]})
        if code not in (200, 204):
            raise OSError(f"prompt answered {code}")
        return None

    def stop(self):
        if self.state == "simple":
            rp = self.run_proc
            if rp and rp.poll() is None:
                os.killpg(rp.pid, signal.SIGTERM)
            return
        if self.state == "ready" and self.session:
            self.call("POST", f"/session/{self.session}/abort")

    def reply_permission(self, rid, allow):
        if rid not in self.permissions:
            return False
        code, _ = self.call("POST", f"/permission/{quote(rid, safe='')}/reply",
                            {"reply": "once" if allow else "reject"})
        if code in (200, 204):
            self.permissions.pop(rid, None)
            self.feed.emit("permission_done", id=rid)
            return True
        return False

    def reply_question(self, rid, answers):
        if rid not in self.questions:
            return False
        q = quote(rid, safe="")
        if answers is None:
            code, _ = self.call("POST", f"/question/{q}/reject")
        else:
            code, _ = self.call("POST", f"/question/{q}/reply", {"answers": answers})
        if code in (200, 204):
            self.questions.pop(rid, None)
            self.feed.emit("question_done", id=rid)
            return True
        return False

    # ----- simple mode -----

    def _run(self, text):
        with self.lock:
            if self.run_proc and self.run_proc.poll() is None:
                raise RuntimeError("busy")
            mid = "run-" + str(time.time_ns())
            self.feed.emit("part", messageID=mid + "-u", partID=mid + "-u", role="user", kind="text", text=text)
            self.run_proc = subprocess.Popen([self.program, "run", text], cwd=self.cwd, stdin=subprocess.DEVNULL,
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace", start_new_session=True)
        threading.Thread(target=self._run_output, args=(self.run_proc, mid), daemon=True).start()

    def _run_output(self, proc, mid):
        self._set_status("busy")
        text = ""
        for line in proc.stdout:
            text += line
            self.feed.emit("part", messageID=mid, partID=mid, role="assistant", kind="text", text=text)
        proc.wait()
        self._set_status("idle")

    def snapshot(self):
        return {"state": self.state, "reason": self.reason, "session": self.session, "status": self.status,
                "output": "\n".join(self.output[-10:]) if self.state in ("simple", "failed") else "",
                "permissions": list(self.permissions.values()), "questions": list(self.questions.values())}
