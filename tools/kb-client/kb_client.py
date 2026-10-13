#!/usr/bin/env python3
"""Knowledge base client: the evergreen-wiki installer and its backup, rollback, move and uninstall
commands as a page in the browser, served from this computer.

  python3 kb_client.py          start the local server and open the page in the default browser
Options: --lang en|zh (default: the system language), --port N (default: a free port), --no-browser
(print the address only), --idle SECONDS (stop after that long without the page; 0 never; default 120),
--log-level (default from LOG_LEVEL); for set up, --agent and --preset life|work answer those questions
in advance and --descriptions FILE replaces the skill descriptions (as install.py).

The server listens on 127.0.0.1 only and answers only requests that carry the token in the address it
opens, so other pages in the browser cannot use it. The questions, previews and checks are the ones of
install.py and kb_manage.py: a step runs in a worker thread, its questions go to the page and wait for
the answer, and what it prints is streamed to the page. The folder browser only lists folders; nothing
in this file writes outside what the installer writes. Python 3 standard library only.
"""
import argparse
import getpass
import json
import logging
import os
import queue
import re
import secrets
import shutil
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import install  # noqa: E402
import kb_manage  # noqa: E402

log = logging.getLogger("kb_client")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
ACTIONS = ("setup", "backup", "rollback", "move", "uninstall")
LANGS = ("en", "zh")
MAX_BODY = 64 * 1024
MAX_ENTRIES = 2000  # entries listed per folder; the page says when a folder holds more
STATIC = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
          "style.css": "text/css; charset=utf-8"}

MSG = {
    "en": {
        "move_pick": "Which library should be moved?",
        "move_none": "No registered library on this computer can be moved.",
        "move_to": "Choose the folder to move the library into. The library keeps its folder name.",
        "busy": "Another step is still running.",
        "started": "Knowledge base client: {url}",
        "stopped": "Knowledge base client stopped.",
    },
    "zh": {
        "move_pick": "要移动哪个知识库？",
        "move_none": "本机没有可以移动的已登记知识库。",
        "move_to": "选择要把知识库移到哪个文件夹里。知识库的文件夹名不变。",
        "busy": "还有一个步骤在运行。",
        "started": "知识库客户端：{url}",
        "stopped": "知识库客户端已停止。",
    },
}


class Cancelled(Exception):
    """The page cancelled the running step."""


class Job:
    """One step (set up, back up, ...) running in a worker thread. Events are numbered from 1 and kept
    for the life of the job, so a page that reconnects gets everything it missed."""

    def __init__(self, action):
        self.id = secrets.token_hex(4)
        self.action = action
        self.events = []
        self.cond = threading.Condition()
        self.answers = queue.Queue()
        self.asking = None  # number of the question waiting for its answer
        self.done = False
        self.thread = None

    def emit(self, etype, **data):
        with self.cond:
            ev = dict(data, type=etype, seq=len(self.events) + 1)
            if etype == "ask":
                self.asking = ev["seq"]  # before the page can see the question
            self.events.append(ev)
            self.cond.notify_all()
            return ev["seq"]

    def since(self, seq, timeout):
        """Events after seq, waiting up to timeout seconds for one."""
        with self.cond:
            if len(self.events) <= seq and not self.done:
                self.cond.wait(timeout)
            return self.events[seq:]

    def ask(self, kind, prompt, **data):
        seq = self.emit("ask", kind=kind, prompt=prompt, **data)
        while True:
            got_seq, value = self.answers.get()
            if got_seq is None or got_seq == seq:
                self.asking = None
                self.emit("answered", of=seq)  # a page that replays the events skips this question
                if got_seq is None:  # cancel
                    raise KeyboardInterrupt
                return value

    def answer(self, seq, value):
        if self.done or self.asking != seq:
            return False
        self.answers.put((seq, value))
        return True

    def cancel(self):
        self.answers.put((None, None))


class WebAsker:
    """The ask, yes and choose of install.Asker, answered on the page. Calling the object with a language
    returns it in that language, so it serves as the asker factory install.py and kb_manage.py take.
    Cancelling on the page raises KeyboardInterrupt, which both treat as "cancelled"."""

    def __init__(self, job, lang):
        self.job = job
        self.lang = lang

    def __call__(self, lang):
        self.lang = lang
        return self

    def ask(self, prompt, default="", kind=None):
        value = self.job.ask("folder" if kind == "folder" else "text", prompt, default=default)
        value = value.strip() if isinstance(value, str) else ""
        return value or default

    def yes(self, prompt, default=True):
        value = self.job.ask("yes", prompt, default=bool(default))
        return value if isinstance(value, bool) else bool(default)

    def choose(self, prompt, options, default):
        opts = [{"value": str(v), "text": str(t)} for v, t in options]
        values = [o["value"] for o in opts]
        value = self.job.ask("choose", prompt, options=opts, default=str(default))
        return value if value in values else default


class Output:
    """Stands in for sys.stdout: what a job's thread prints goes to its page, everything else to the
    real stream."""

    def __init__(self, real):
        self.real = real
        self.per_thread = threading.local()

    def write(self, s):
        job = getattr(self.per_thread, "job", None)
        if job is None:
            return self.real.write(s)
        if s:
            job.emit("out", text=s)
        return len(s)

    def flush(self):
        self.real.flush()

    def __getattr__(self, name):
        return getattr(self.real, name)


class App:
    def __init__(self, lang, options, idle):
        self.lang = lang
        self.options = options
        self.idle = idle
        self.token = secrets.token_urlsafe(24)
        self.job = None
        self.lock = threading.Lock()
        self.last_seen = time.time()
        self.output = None
        self.server = None

    # ---------- steps ----------

    def start(self, action, lib_id=None):
        with self.lock:
            if self.job and not self.job.done:
                return None
            job = Job(action)
            self.job = job
        job.thread = threading.Thread(target=self.run, args=(job, lib_id), daemon=True)
        job.thread.start()
        return job

    def run(self, job, lib_id):
        if self.output:
            self.output.per_thread.job = job
        asker = WebAsker(job, self.lang)
        result = "ok"
        try:
            if run_action(job.action, asker, self.lang, self.options, lib_id):
                result = "stopped"  # kb_manage printed why: cancelled, refused or failed
        except KeyboardInterrupt:
            print(install.MSG[self.lang]["cancelled"])
            result = "cancelled"
        except SystemExit as e:  # the wizard exits after printing why
            result = "ok" if e.code in (None, 0) else "stopped"
        except Exception as e:  # shown on the page; the server keeps running
            log.exception("step %s failed", job.action)
            print(f"{type(e).__name__}: {e}")
            result = "error"
        finally:
            if self.output:
                self.output.per_thread.job = None
            with job.cond:
                job.done = True
                job.events.append({"type": "end", "result": result, "seq": len(job.events) + 1})
                job.cond.notify_all()

    # ---------- state ----------

    def state(self):
        job = self.job
        return {
            "lang": self.lang,
            "home": os.path.expanduser("~"),
            "libraries": libraries(),
            "skills": skills_installed(),
            "agent": agent_status(),
            "backups": len(kb_manage.list_backups()),
            "registry": kb_manage.registry_path(),
            "job": None if job is None else {"id": job.id, "action": job.action, "done": job.done},
        }

    def idle_watch(self):
        while self.idle:
            time.sleep(min(5, self.idle))
            busy = self.job is not None and not self.job.done
            if not busy and time.time() - self.last_seen > self.idle:
                log.info("no page for %s seconds, stopping", self.idle)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return


def run_action(action, asker, lang, options, lib_id=None):
    """Runs one step; returns the exit code of kb_manage (0 when it went through), None for set up."""
    m = MSG[lang]
    if action == "setup":
        install.wizard(asker, lang, options.get("agent"), options.get("preset"), options.get("descriptions"))
        return None
    if action == "move":
        libs = [(i, label, root) for i, label, root in kb_manage.registered_libs()
                if kb_manage.lib_check(root, install.MANAGE_DEFAULTS) is None]
        if not libs:
            print(m["move_none"])
            return 0
        ids = [i for i, _, _ in libs]
        if lib_id not in ids:
            q = asker(lang)
            lib_id = q.choose(m["move_pick"], [(i, f"{label}  {root}") for i, label, root in libs], ids[0])
        parent = asker(lang).ask(m["move_to"], kind="folder")
        return kb_manage.main(["move", lib_id, "--to", parent, "--lang", lang], asker, install.MANAGE_DEFAULTS)
    return kb_manage.main([action, "--lang", lang], asker, install.MANAGE_DEFAULTS)


# ---------- what the page shows ----------

def libraries():
    path = kb_manage.registry_path()
    reg = kb_manage.read_json(path, {})
    out = []
    for lib in reg.get("libraries", []) if isinstance(reg, dict) else []:
        backend = lib.get("backend") or {}
        kind = backend.get("type", "local")
        root = backend.get("root", "") if kind == "local" else ""
        root = kb_manage.norm(root) if root else ""
        out.append({"id": lib.get("id", ""), "label": lib.get("label") or lib.get("id", ""),
                    "scope": lib.get("scope", ""), "type": kind, "root": root,
                    "exists": bool(root) and os.path.isdir(root),
                    "movable": bool(root) and kb_manage.lib_check(root, install.MANAGE_DEFAULTS) is None})
    return out


def skills_installed():
    """[{agent, folder, skills}] for every known skills folder holding one of the skills."""
    out = []
    for target, (folder, _) in sorted(install.TARGETS.items()):
        have = [s for s in kb_manage.SKILLS if os.path.isfile(os.path.join(folder, s, "SKILL.md"))]
        if have:
            out.append({"agent": target, "name": install.AGENT_NAMES.get(target, target),
                        "folder": folder, "skills": have})
    return out


def strip_jsonc(text):
    """Comments (// and /* */) and trailing commas removed, strings left alone, for json.loads."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def agent_status():
    """OpenCode on this computer: the program, and whether its settings name a model."""
    folder = install.AGENT_HOMES["opencode"]
    status = {"program": shutil.which("opencode") or "", "config": "", "model": False, "error": ""}
    for name in ("opencode.jsonc", "opencode.json"):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        status["config"] = path
        try:
            with open(path, encoding="utf-8") as f:
                data = json.loads(strip_jsonc(f.read()) or "{}")
            status["model"] = bool(isinstance(data, dict) and (data.get("model") or data.get("provider")))
        except (OSError, ValueError) as e:
            status["error"] = str(e)
        break
    return status


def places():
    """Starting points of the folder browser: the home folder and mounted removable media."""
    home = os.path.expanduser("~")
    out = [{"path": home, "kind": "home"}]
    user = getpass.getuser()
    for base in (os.path.join("/media", user), os.path.join("/run", "media", user), "/media", "/mnt"):
        if not os.path.isdir(base):
            continue
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for name in names:
            p = os.path.join(base, name)
            if os.path.isdir(p) and os.path.ismount(p) and all(x["path"] != p for x in out):
                out.append({"path": p, "kind": "media"})
    return out


def browse_root(path, roots):
    """The starting point that holds path (both real paths), or None: the browser stays inside them."""
    for root in roots:
        if path == root or path.startswith(root.rstrip(os.sep) + os.sep):
            return root
    return None


def list_folder(path, hidden=False, nearest=False):
    """The entries of one folder inside the home folder or a mounted drive, folders first. Raises
    ValueError for a path that is not an absolute, existing folder there; with nearest, a missing folder
    is replaced by its nearest existing parent (a folder typed in an answer is often not made yet).
    Reads only."""
    if not path or not os.path.isabs(os.path.expanduser(path)):
        raise ValueError("not an absolute path")
    path = os.path.realpath(os.path.expanduser(path))
    roots = [os.path.realpath(p["path"]) for p in places()]
    root = browse_root(path, roots)
    if root is None:
        raise ValueError("outside the home folder and the mounted drives")
    while nearest and path != root and not os.path.isdir(path):
        path = os.path.dirname(path)
    if not os.path.isdir(path):
        raise ValueError("not a folder")
    entries = []
    with os.scandir(path) as it:
        for e in it:
            if not hidden and e.name.startswith("."):
                continue
            try:
                is_dir = e.is_dir()
                size = 0 if is_dir else e.stat().st_size
            except OSError:
                continue
            entries.append({"name": e.name, "dir": is_dir, "size": size})
    entries.sort(key=lambda x: (not x["dir"], x["name"].lower()))
    parent = os.path.dirname(path) if path != root else ""
    return {"path": path, "parent": parent,
            "entries": entries[:MAX_ENTRIES], "more": max(0, len(entries) - MAX_ENTRIES)}


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "kb-client"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    def host_ok(self):
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def token_ok(self, query):
        given = self.headers.get("X-Token") or (query.get("t") or [""])[0]
        return secrets.compare_digest(given, self.app.token)

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def guard(self):
        """(path, query) when the request may go on; else the error was sent and None returned."""
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        if not self.host_ok():
            self.send(403, {"error": "host"})
            return None
        if url.path.startswith("/api/") and not self.token_ok(query):
            self.send(403, {"error": "token"})
            return None
        self.app.last_seen = time.time()
        return url.path, query

    def do_GET(self):
        g = self.guard()
        if g is None:
            return None
        path, query = g
        if path == "/api/state":
            return self.send(200, self.app.state())
        if path == "/api/places":
            return self.send(200, {"places": places()})
        if path == "/api/fs":
            try:
                return self.send(200, list_folder((query.get("path") or [""])[0],
                                                  (query.get("hidden") or [""])[0] == "1",
                                                  (query.get("nearest") or [""])[0] == "1"))
            except (ValueError, OSError) as e:
                return self.send(400, {"error": str(e)})
        if path == "/api/events":
            return self.events(query)
        return self.static(path)

    def do_POST(self):
        g = self.guard()
        if g is None:
            return None
        path, _ = g
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send(415, {"error": "json only"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self.send(413, {"error": "too large"})
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            return self.send(400, {"error": "bad json"})
        if path == "/api/action":
            action = body.get("action")
            if action not in ACTIONS:
                return self.send(400, {"error": "unknown action"})
            job = self.app.start(action, body.get("library"))
            if job is None:
                return self.send(409, {"error": MSG[self.app.lang]["busy"]})
            return self.send(200, {"job": job.id})
        if path == "/api/answer":
            job = self.app.job
            if job is None or job.id != body.get("job"):
                return self.send(404, {"error": "no such job"})
            if body.get("cancel"):
                job.cancel()
                return self.send(200, {"ok": True})
            ok = job.answer(body.get("seq"), body.get("value"))
            return self.send(200 if ok else 409, {"ok": ok})
        if path == "/api/quit":
            self.send(200, {"ok": True})
            job = self.app.job
            if job and not job.done:
                job.cancel()
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return None
        return self.send(404, {"error": "not found"})

    def events(self, query):
        """Server-sent events of the current job, from the event after Last-Event-ID (or ?after=)."""
        job = self.app.job
        if job is None or job.id != (query.get("job") or [""])[0]:
            return self.send(404, {"error": "no such job"})
        try:
            seq = int(self.headers.get("Last-Event-ID") or (query.get("after") or ["0"])[0])
        except ValueError:
            seq = 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                evs = job.since(seq, 15)
                if not evs:
                    self.wfile.write(b": keep-alive\n\n")
                for ev in evs:
                    seq = ev["seq"]
                    data = json.dumps(ev, ensure_ascii=False)
                    self.wfile.write(f"id: {seq}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.app.last_seen = time.time()
                if evs and evs[-1]["type"] == "end":
                    return None
        except (BrokenPipeError, ConnectionResetError):
            log.debug("event stream closed by the page")
        return None

    def static(self, path):
        """Only the page's own files, by fixed name and type."""
        name = "index.html" if path == "/" else path[1:]
        for known, ctype in STATIC.items():
            if name == known:
                with open(os.path.join(WEB, known), "rb") as f:
                    return self.send(200, f.read(), ctype)
        return self.send(404, {"error": "not found"})


def serve(app, port, open_browser):
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    app.server = server
    url = f"http://127.0.0.1:{server.server_address[1]}/?t={app.token}"
    print(MSG[app.lang]["started"].format(url=url), flush=True)
    if open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    if app.idle:
        threading.Thread(target=app.idle_watch, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:  # Ctrl+C in the terminal window stops the client like Quit
        log.info("stopped from the terminal")
    finally:
        server.server_close()
    print(MSG[app.lang]["stopped"], flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", choices=LANGS)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--idle", type=int, default=120, metavar="SECONDS")
    ap.add_argument("--agent", choices=sorted(install.TARGETS))
    ap.add_argument("--preset", choices=["life", "work"])
    ap.add_argument("--descriptions", metavar="FILE")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    if a.descriptions:
        try:
            install.load_descriptions(a.descriptions)
        except (OSError, ValueError) as e:
            ap.error(str(e))
    if a.idle < 0:
        ap.error("--idle must be 0 or more")
    il = kb_manage.init_library()
    il.kbconf.utf8_stdio()
    lang = a.lang or il.detect_language()
    lang = lang if lang in LANGS else "en"
    # Answers on the page are typed like answers in a terminal opened in the home folder: a relative
    # folder is taken from there, never from wherever the program was started.
    os.chdir(os.path.expanduser("~"))
    app = App(lang, {"agent": a.agent, "preset": a.preset, "descriptions": a.descriptions}, a.idle)
    app.output = Output(sys.stdout)
    sys.stdout = app.output
    serve(app, a.port, not a.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
