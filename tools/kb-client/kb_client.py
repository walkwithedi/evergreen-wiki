#!/usr/bin/env python3
"""Knowledge base client: the evergreen-wiki installer and its backup, rollback, move and uninstall
commands as a page in the browser, served from this computer.

  python3 kb_client.py          start the local server and open the page in the default browser
Options: --lang en|zh (default: the system language), --port N (default: a free port), --no-browser
(print the address only), --idle SECONDS (stop after that long without the page; 0 never; default 120),
--start-timeout SECONDS (wait that long for OpenCode to start; default 90), --opencode PATH (the
OpenCode program to use; also KB_CLIENT_OPENCODE; default: found on PATH, in a common install folder
or through the interactive shell), --log-level (default from LOG_LEVEL); for set up, --agent answers
that question in advance and --descriptions FILE replaces the skill descriptions (as install.py).

The server listens on 127.0.0.1 only and answers only requests that carry the token in the address it
opens, so other pages in the browser cannot use it. The questions, previews and checks are the ones of
install.py and kb_manage.py: a step runs in a worker thread, its questions go to the page and wait for
the answer, and what it prints is streamed to the page. The conversation on the page goes to an OpenCode
server this client starts on 127.0.0.1 (agent.py); the page never talks to OpenCode itself. The folder
browser only lists folders. The Skills section lists the skills OpenCode reads and manages them
(skills_admin.py: backup before an edit, restore, import, a new skill from a template); the
knowledge-base skills are upgraded by their own step (install.upgrade). Material is ingested in the
conversation, with the kb-ingest skill. Otherwise this file writes nothing but the current
conversation's id. Python 3 standard library only.
"""
import argparse
import getpass
import json
import logging
import os
import queue
import re
import secrets
import signal
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import install  # noqa: E402
import kb_manage  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent as agent_mod  # noqa: E402
import skills_admin  # noqa: E402

log = logging.getLogger("kb_client")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
ACTIONS = ("setup", "backup", "rollback", "move", "uninstall", "batch",
           "skill_backup", "skill_restore", "skill_import", "skill_new", "skill_upgrade")
LANGS = ("en", "zh")
MAX_BODY = 64 * 1024
# Steps and chat requests a client started with --simple refuses (and its page hides): the ones that move,
# remove or roll back libraries and skills, change skills, or forget permission answers.
SIMPLE_REFUSED = {"rollback", "move", "uninstall", "skill_backup", "skill_restore", "skill_import", "skill_new",
                  "forget"}
CHAT_ACTIONS = {name: name for name in ("start", "recheck", "send", "new", "stop", "permission", "question", "terminal", "forget",
                                         "allow_all", "workdir", "sessions", "open", "close", "focus")}
CHAT_FIRST_ACTIONS = ("workdir", "sessions")  # only with --chat-first
# steps that change libraries, holding the write lock; an upgrade can set one up and writes the knowledge-base line
WRITE_STEPS = ("setup", "rollback", "move", "uninstall", "skill_upgrade")
RESTART_STEPS = ("setup", "skill_upgrade")  # OpenCode is restarted after these, to read the skills again
MAX_TEXT = 20000  # characters of one message from the page
MAX_PATHS = 200  # material paths sent with one message
MAX_ENTRIES = 2000  # entries listed per folder; the page says when a folder holds more
STATIC = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
          "style.css": "text/css; charset=utf-8"}

MSG = {
    "en": {
        "move_pick": "Which library should be moved?",
        "move_none": "No registered library on this computer can be moved.",
        "move_to": "Choose the folder to move the library into. The library keeps its folder name.",
        "batch_src": "Choose the folder with the documents to turn into batch files (Word, Excel, PowerPoint, PDF, mail). They are only read.",
        "batch_lib": "Which library are they for? Its settings give the size of a batch.",
        "batch_no_lib": "none yet (20,000 characters per batch)",
        "batch_out": "Choose the folder for the batch files. It stays after the client is closed, so the files can be copied and uploaded.",
        "batch_no_src": "{path} is not a folder.",
        "batch_not_empty": "{path} is not empty; choose a new or empty folder.",
        "batch_in_library": "{path} is inside the library {lib}; batch files go outside every library.",
        "batch_in_src": "{path} is inside the material folder; choose a folder outside it.",
        "batch_failed": "The converter stopped (exit code {code}); its output is above.",
        "batch_done": "{n} batch file(s) in {path}.",
        "pending_said": "The decisions for ingest run {run} in the {lib} library are saved; go on with that run.",
        "busy": "Another step is still running.",
        "simple": "This version of the client does not offer this.",
        "workdir_missing": "Choose an existing folder.",
        "workdir_too_wide": "Choose a folder inside your home folder or elsewhere, not the home folder itself or a folder holding it.",
        "workdir_system": "A system folder cannot be the work folder.",
        "chat_busy": "The assistant is still working; try again when it is done.",
        "no_program": "OpenCode was not found on this computer.",
        "not_ready": "The conversation is not ready yet.",
        "locked": "Another task that writes the libraries is running; wait until it is done.",
        "too_many": "Eight windows are open; close one first.",
        "window_busy": "The assistant is still working in this window.",
        "no_window": "That window is closed.",
        "confirm": "Write the library as previewed above?",
        "write": "Write",
        "change": "Change an item first",
        "cancel": "Cancel",
        "which_item": "Which item should be changed?",
        "started": "Knowledge base client: {url}",
        "stopped": "Knowledge base client stopped.",
    },
    "zh": {
        "move_pick": "要移动哪个知识库？",
        "move_none": "本机没有可以移动的已登记知识库。",
        "move_to": "选择要把知识库移到哪个文件夹里。知识库的文件夹名不变。",
        "batch_src": "选择放文档的文件夹（Word、Excel、PowerPoint、PDF、邮件），要转成批文件。文档只读不改。",
        "batch_lib": "这些材料要入哪个知识库？批的大小按它的设置定。",
        "batch_no_lib": "还没有（每批 20000 字符）",
        "batch_out": "选择批文件放在哪个文件夹。客户端关闭后仍保留，可以拷走上传。",
        "batch_no_src": "{path} 不是文件夹。",
        "batch_not_empty": "{path} 不是空文件夹，请选新的或空的文件夹。",
        "batch_in_library": "{path} 在知识库「{lib}」里面；批文件要放在所有知识库之外。",
        "batch_in_src": "{path} 在材料文件夹里面，请选材料文件夹以外的地方。",
        "batch_failed": "转换器中途停止（退出码 {code}），输出见上方。",
        "batch_done": "已在 {path} 生成 {n} 个批文件。",
        "pending_said": "知识库「{lib}」第 {run} 轮入库的决定已保存，请接着完成这一轮。",
        "busy": "还有一个步骤在运行。",
        "simple": "这个版本的客户端不提供这一项。",
        "workdir_missing": "请选择一个已有的文件夹。",
        "workdir_too_wide": "请选择家目录里或其他位置的某个文件夹，不能是家目录本身或包含家目录的文件夹。",
        "workdir_system": "系统文件夹不能作为工作文件夹。",
        "chat_busy": "助手还在处理，等它处理完再试。",
        "no_program": "本机没有找到 OpenCode。",
        "not_ready": "对话还没有准备好。",
        "locked": "另一个写知识库的任务正在运行，等它结束再试。",
        "too_many": "已经开了 8 个窗口，先关掉一个。",
        "window_busy": "助手还在这个窗口里处理。",
        "no_window": "这个窗口已经关闭。",
        "confirm": "按上面的预览写入知识库吗？",
        "write": "写入",
        "change": "先修改某一项",
        "cancel": "取消",
        "which_item": "修改哪一项？",
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

    def confirm(self, prompt, items, can_write=True):
        """The answer to a preview as install.confirm takes it: "" to write, "n" to cancel, or the number
        of the item to change. The page shows the choices instead of the terminal's typed answer."""
        m = MSG[self.lang]
        opts = ([("write", m["write"])] if can_write else []) + [("change", m["change"]), ("cancel", m["cancel"])]
        what = self.choose(m["confirm"], opts, opts[0][0])
        if what == "write":
            return ""
        if what == "cancel":
            return "n"
        return self.choose(m["which_item"], [(str(i), f"{i}. {name}") for i, name in enumerate(items, 1)], "1")


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
    def __init__(self, lang, options, idle, start_timeout=90):
        self.lang = lang
        self.options = options
        self.idle = idle
        self.start_timeout = start_timeout
        self.agent = None
        self.started = time.time()  # files changed after this count as new in the graph
        # The skills' work folder for this client: outside every library (mkdtemp makes it private), so
        # that their copies and output files are written there without a permission card each time.
        self.work = tempfile.mkdtemp(prefix="kb-client-work-")
        self.token = secrets.token_urlsafe(24)
        self.job = None
        self.lock = threading.Lock()
        self.last_seen = time.time()
        self.output = None
        self.server = None

    # ---------- steps ----------

    def start(self, action, lib_id=None):
        """(the step's Job, None), or (None, why): "busy" while another step runs, "locked" for a step that
        changes libraries while another one holds the lock."""
        with self.lock:
            if self.job and not self.job.done:
                return None, "busy"
            if action in WRITE_STEPS and self.write_lock() is not None:
                return None, "locked"
            job = Job(action)
            self.job = job
        job.thread = threading.Thread(target=self.run, args=(job, lib_id), daemon=True)
        job.thread.start()
        self.windows_changed()
        return job, None

    def run(self, job, lib_id):
        log.info("step %s started", job.action)
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
            log.info("step %s ended: %s", job.action, result)
        self.windows_changed()
        if job.action in RESTART_STEPS and result == "ok" and self.agent is not None:
            self.agent.restart()  # so that the conversation uses the skills and the instructions line just written

    # ---------- state ----------

    def state(self):
        job = self.job
        return {
            "lang": self.lang,
            "simple": bool(self.options.get("simple")),
            "chat_first": bool(self.options.get("chat_first")),
            "home": os.path.expanduser("~"),
            "libraries": libraries(),
            "skills": skills_installed(),
            "agent": agent_status(),
            "backups": len(kb_manage.list_backups()),
            "registry": kb_manage.registry_path(),
            "work": self.work,
            "log_dir": log_folder(),
            "opencode_skills": opencode_skills(),
            "kb_skills": kb_skills(),
            "instructions": instructions_line(),
            "pdftotext": bool(shutil.which("pdftotext")),
            "remembered": self.remembered(),
            "job": None if job is None else {"id": job.id, "action": job.action, "done": job.done},
        }

    # ---------- the conversation ----------

    def start_agent(self):
        """The Agent, started on first use; None and the reason when OpenCode is not found. Whether
        OpenCode can be used shows when it starts: a missing model only warns (its settings may come
        from elsewhere)."""
        with self.lock:
            if self.agent is None:
                if not agent_status()["program"]:
                    return None, "no_program"
                self.agent = agent_mod.Agent(OPENCODE["program"], os.path.expanduser("~"), self.places,
                                             os.path.join(kb_manage.state_dir(), "kb-client.json"),
                                             self.start_timeout, chat_first=bool(self.options.get("chat_first")))
                self.agent.lock_fn = self.write_lock
                self.agent.guard_fn = self.guard
        self.agent.start()
        return self.agent, None

    def remembered(self):
        """How many Always allow answers the client keeps (agent.remembered)."""
        if self.agent is not None:
            return self.agent.remembered_count()
        data = kb_manage.read_json(os.path.join(kb_manage.state_dir(), "kb-client.json"), {})
        always = data.get("always") if isinstance(data, dict) else None
        return sum(len(v) for v in always.values() if isinstance(v, list)) if isinstance(always, dict) else 0

    def recheck(self):
        """Looks for OpenCode again, the way the client did when it started, then starts it, or starts it
        anew after it failed or fell back to simple mode. None and the reason when it is still not found."""
        prog = find_opencode(self.options.get("opencode") or "")
        if not prog:
            return None, "no_program"
        if self.agent is None:
            return self.start_agent()
        self.agent.retry(prog)
        return self.agent, None

    # ---------- the write lock ----------

    def write_lock(self):
        """Who holds the write lock, or None: {"holder": "step", "action"} for a step that changes libraries."""
        job = self.job
        if job is not None and not job.done and job.action in WRITE_STEPS:
            return {"holder": "step", "action": job.action}
        return None

    def guard(self, win):
        """For agent.touches: the libraries and the knowledge-base skills' folders, while a step holds the
        write lock; None otherwise."""
        lock = self.write_lock()
        if lock is None or lock.get("win") == win:
            return None
        roots = [lib["root"] for lib in libraries() if lib["root"] and lib["exists"]]
        scripts = [f["folder"] for f in kb_skills()["found"] if f["name"] in ("kb-ingest", "kb-note")]
        return {"roots": roots, "scripts": scripts}

    def windows_changed(self):
        if self.agent is not None:
            self.agent.emit_windows()

    def places(self):
        pl = agent_places()
        pl["write"] = pl["write"] + [self.work] if os.path.isdir(self.work) else pl["write"]
        return pl

    def idle_watch(self):
        while self.idle:
            time.sleep(min(5, self.idle))
            busy = self.job is not None and not self.job.done
            busy = busy or (self.agent is not None and self.agent.status != "idle")
            if not busy and time.time() - self.last_seen > self.idle:
                log.info("no page for %s seconds, stopping", self.idle)
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return


def run_action(action, asker, lang, options, lib_id=None):
    """Runs one step; returns the exit code of kb_manage (0 when it went through), None for set up and
    the upgrade.
    For the skill steps lib_id is the skill's folder name."""
    m = MSG[lang]
    if action == "skill_upgrade":
        # each skill where OpenCode reads it now; a missing one goes to OpenCode's own folder
        places = {x["name"]: os.path.dirname(x["folder"]) for x in kb_skills()["found"]}
        install.upgrade(asker, lang, places, skills_admin.own_folder(), instructions_file(),
                        options.get("descriptions"))
        return None
    if action.startswith("skill_"):
        try:
            return skill_action(action, asker(lang), lang, lib_id)
        except skills_admin.Refused as e:
            print(str(e))
            return 1
    if action == "batch":
        q = asker(lang)
        return batch_step(q, lang, getattr(q, "job", None))
    if action == "setup":
        install.wizard(asker, lang, options.get("agent"), options.get("descriptions"), agent_default="opencode")
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


BATCH_RE = re.compile(r"_b\d{2,}\.md$")


def _inside(path, folder):
    path, folder = os.path.realpath(path), os.path.realpath(folder)
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def batch_step(q, lang, job=None):
    """Build batch files for kb-ingest with doc2kb: the material folder, the library whose settings give
    the batch size, a new or empty output folder outside every library. 0 when done, 1 when refused."""
    m = MSG[lang]
    src = q.ask(m["batch_src"], kind="folder")
    if not src or not os.path.isdir(src):
        print(m["batch_no_src"].format(path=src))
        return 1
    libs = [x for x in libraries() if x["root"] and x["exists"]]
    lib_id = q.choose(m["batch_lib"], [(x["id"], "%s  %s" % (x["label"], x["root"])) for x in libs]
                      + [("", m["batch_no_lib"])], libs[0]["id"] if libs else "")
    base = os.path.join(os.path.expanduser("~"), "kb-batches",
                        "%s_%s" % (os.path.basename(os.path.normpath(src)) or "material", time.strftime("%Y%m%d")))
    default, k = base, 1
    while os.path.exists(default) and os.listdir(default):
        k += 1
        default = "%s_%d" % (base, k)
    out = os.path.abspath(q.ask(m["batch_out"], default=default, kind="folder"))
    if os.path.isdir(out) and os.listdir(out):
        print(m["batch_not_empty"].format(path=out))
        return 1
    for x in libs:
        if _inside(out, x["root"]):
            print(m["batch_in_library"].format(path=out, lib=x["label"]))
            return 1
    if _inside(out, src):
        print(m["batch_in_src"].format(path=out))
        return 1
    cmd = [sys.executable, os.path.join(kb_manage.SCRIPTS, "doc2kb_core.py"), "--batch", src, "-o", out, "--kb-batch"]
    root = next((x["root"] for x in libs if x["id"] == lib_id), None)
    if root:
        cmd += ["--library", root]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                            errors="replace", env=env)
    for line in proc.stdout:
        print(line, end="")
    code = proc.wait()
    if code != 0:
        print(m["batch_failed"].format(code=code))
        return 1
    files = sorted(f for f in os.listdir(out) if BATCH_RE.search(f)) if os.path.isdir(out) else []
    print(m["batch_done"].format(n=len(files), path=out))
    if job is not None:
        job.emit("batch", out=out, files=files)
    return 0


def pending_runs():
    """({"runs": [...], "review": [...]}) for the page: ingest runs of local libraries waiting for the owner's
    decisions, and status-card items marked for review."""
    ing = ingest_module()
    runs, review = [], []
    for lib in libraries():
        if not (lib["root"] and lib["exists"]):
            continue
        folder = os.path.join(lib["root"], ing.PENDING_DIR)
        for fname in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            run = fname[:-5]
            if not fname.endswith(".json") or fname.endswith(".decisions.json") or not ing.RUN_RE.match(run):
                continue
            if os.path.isfile(os.path.join(folder, run + ".decisions.json")):
                continue
            try:
                with open(os.path.join(folder, fname), encoding="utf-8") as f:
                    pend = json.load(f)
            except (OSError, ValueError) as e:
                log.info("cannot read %s: %s", fname, e)
                continue
            runs.append({"library": lib["id"], "label": lib["label"], "run": run, "pending": pend})
        card = os.path.join(lib["root"], library_names(lib["root"])["status_card"])
        try:
            with open(card, encoding="utf-8") as f:
                lines = f.read().split("\n")
        except OSError:
            lines = []
        for line in lines:
            if "\u23f3" in line and ing.ITEM_RE.match(line):
                review.append({"library": lib["id"], "label": lib["label"], "item": ing.MARK_RE.sub("", line).strip()})
    return {"runs": runs, "review": review}


def ingest_module():
    kb_manage.init_library()  # puts kb-ingest's scripts on the path
    import ingest
    return ingest


def skill_action(action, q, lang, name):
    """The skill steps of the Skills section; 0 when done, 1 when cancelled."""
    sm = skills_admin.MSG[lang]
    if action == "skill_backup":
        print(sm["backed_up"].format(name=name, path=skills_admin.backup(name, lang)))
        return 0
    if action == "skill_restore":
        skill = skills_admin.find(name, lang)
        found = skills_admin.backups(name)
        if not found:
            raise skills_admin.Refused(sm["no_backups"].format(name=name))
        when = q.choose(sm["pick_backup"].format(name=name), [(b, b) for b in found], found[0])
        if not q.yes(sm["restore_confirm"].format(folder=skill["folder"], when=when), default=False):
            print(sm["cancelled"])
            return 1
        skills_admin.restore(name, when, lang)
        print(sm["restored"].format(name=name, when=when))
        return 0
    if action == "skill_new":
        new = q.ask(sm["new_name"]).strip().lower()
        skills_admin.taken(new, lang)
        purpose = q.ask(sm["new_purpose"]).strip()
        if not purpose:
            print(sm["cancelled"])
            return 1
        path = os.path.join(skills_admin.own_folder(), new)
        if not q.yes(sm["new_confirm"].format(path=path)):
            print(sm["cancelled"])
            return 1
        print(sm["created"].format(path=skills_admin.create(new, purpose, lang)))
        print(f"skill: {new}")
        return 0
    # skill_import
    kind = q.choose(sm["source_kind"], [("folder", sm["from_folder"]), ("zip", sm["from_zip"])], "folder")
    with tempfile.TemporaryDirectory(prefix="kb-client-skill-") as tmp:
        if kind == "zip":
            src = skills_admin.unpack_zip(q.ask(sm["zip_path"]).strip(), tmp, lang)
        else:
            src = q.ask(sm["pick_folder"], kind="folder")
        top, info, n, size = skills_admin.check_folder(src, lang)
        new = os.path.basename(top) if kind == "folder" or top != tmp else info["name"]
        new = new if skills_admin.NAME_RE.fullmatch(new or "") else info["name"]
        skills_admin.taken(new, lang)
        dest = os.path.join(skills_admin.own_folder(), new)
        print(sm["preview"].format(name=new, desc=info["description"][:300], n=n, size=max(1, size // 1024),
                                   dest=dest))
        if not q.yes(sm["import_confirm"]):
            print(sm["cancelled"])
            return 1
        skills_admin.install_copy(top, new)
    print(sm["imported"].format(name=new, dest=dest))
    return 0


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


GRAPH_MAX_NODES = 2000
GRAPH_MAX_READ = 1024 * 1024  # bytes read of one file
LINK_RE = re.compile(r"\[\[([^\[\]|#\n]+)(?:#[^\[\]|\n]*)?(?:\|[^\[\]\n]*)?\]\]")
ENTITY_TYPE_RE = re.compile(r"^type:\s*[\"']?entity[\"']?\s*$", re.M)
STAMP_RE = re.compile(r"\d{8}")


def library_names(root):
    il = kb_manage.init_library()
    try:
        return il.kbconf.load_library(root)["names"]
    except Exception as e:  # an incomplete library falls back to the default names
        log.info("cannot read the settings of %s: %s", root, e)
        return il.kbconf.resolve_names()


def graph(root, since=0.0):
    """The links between the Markdown files of a library, for the graph on the page. Skips what the skills
    skip when searching (the archive folder, names starting with an underscore or the snapshot prefix, old
    versions with a time stamp), links leading out of the library and hidden folders. Nodes are file names
    without .md: kind entity (in the entities folder or type: entity), summary (the spec and the summary
    files), topic (any other file), original (a copy in the sources folder that a file links to) or missing
    (linked to, no such file). new: changed since `since`."""
    names = library_names(root)
    summaries = {names[k].lower() for k in ("spec", "status_card", "index", "open_items", "changelog", "glossary")}
    real_root = os.path.realpath(root)
    files, truncated = [], False
    for here, dirs, fnames in os.walk(real_root):
        rel_here = os.path.relpath(here, real_root)
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_"))
                         and not (rel_here == "." and d in (names["archive_dir"], names["sources_dir"]))
                         and os.path.realpath(os.path.join(here, d)).startswith(real_root + os.sep))
        for f in sorted(fnames):
            if not f.lower().endswith(".md") or f.startswith(("_", ".", names["snapshot_prefix"])):
                continue
            stem = f[:-3]
            if names["old_suffix"] in stem and STAMP_RE.search(stem.split(names["old_suffix"])[-1]):
                continue
            full = os.path.join(here, f)
            if not os.path.realpath(full).startswith(real_root + os.sep):
                continue
            if len(files) >= GRAPH_MAX_NODES:
                truncated = True
                break
            files.append((stem, os.path.relpath(full, real_root), full))
    nodes, edges = {}, set()
    for stem, rel, full in files:
        try:
            with open(full, encoding="utf-8", errors="replace") as fh:
                text = fh.read(GRAPH_MAX_READ)
            mtime = os.path.getmtime(full)
        except OSError as e:
            log.info("cannot read %s: %s", rel, e)
            continue
        top = rel.split(os.sep)[0]
        if top == names["entities_dir"] or ENTITY_TYPE_RE.search(text.split("\n---", 1)[0] if text.startswith("---") else ""):
            kind = "entity"
        elif (stem + ".md").lower() in summaries:
            kind = "summary"
        else:
            kind = "topic"
        nodes.setdefault(stem, {"id": stem, "kind": kind, "path": rel, "new": mtime >= since > 0})
        if (stem + ".md").lower() == names["spec"].lower():
            continue  # the spec's links are examples of the rules, not links between files
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            target = target[:-3] if target.lower().endswith(".md") else target
            target = target.rsplit("/", 1)[-1]
            if target and target != stem:
                edges.add((stem, target))
    for _, target in sorted(edges):
        if target not in nodes:
            if len(nodes) >= GRAPH_MAX_NODES:
                truncated = True
                continue
            kept = os.path.join(real_root, names["sources_dir"], target)
            if "." in target and os.path.isfile(kept):  # an original kept in the sources folder
                nodes[target] = {"id": target, "kind": "original", "path": os.path.join(names["sources_dir"], target),
                                 "new": os.path.getmtime(kept) >= since > 0}
            else:
                nodes[target] = {"id": target, "kind": "missing", "path": "", "new": False}
    links = [{"source": a, "target": b} for a, b in sorted(edges) if a in nodes and b in nodes]
    degree = {}
    for e in links:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1
    for n in nodes.values():
        n["links"] = degree.get(n["id"], 0)
    return {"nodes": list(nodes.values()), "links": links, "truncated": truncated}


def agent_places():
    """Where OpenCode may act without asking (agent.decide): write in the registered local libraries;
    read also the skills and the agent's own settings; run the skills' scripts."""
    write = [lib["root"] for lib in libraries() if lib["root"] and lib["exists"]]
    skills = [os.path.join(s["folder"], name) for s in skills_installed() for name in s["skills"]]
    read = skills + [install.AGENT_HOMES["opencode"], os.path.dirname(kb_manage.registry_path())]
    read = [p for p in read if os.path.isdir(p)]
    return {"write": write, "read": read,
            "scripts": [os.path.join(p, "scripts") for p in skills if os.path.isdir(os.path.join(p, "scripts"))]}


def skills_installed():
    """[{agent, folder, skills}] for every known skills folder holding one of the skills."""
    out = []
    for target, (folder, _) in sorted(install.TARGETS.items()):
        have = [s for s in kb_manage.SKILLS if os.path.isfile(os.path.join(folder, s, "SKILL.md"))]
        if have:
            out.append({"agent": target, "name": install.AGENT_NAMES.get(target, target),
                        "folder": folder, "skills": have})
    return out


# The skills folders OpenCode reads besides its own (its Claude Code and .agents compatibility).
OPENCODE_SKILL_AGENTS = ("opencode", "claude-code", "agents")


def skill_version(folder):
    """The Version: line of a SKILL.md, or ""."""
    try:
        with open(os.path.join(folder, "SKILL.md"), encoding="utf-8", errors="replace") as f:
            for line in f.read(8192).split("\n"):
                if line.startswith("Version:"):
                    return line.split(":", 1)[1].strip()
    except OSError:  # unreadable: the skill is still listed, without a version
        return ""
    return ""


def kb_skills():
    """The knowledge-base skills where OpenCode reads them, the only skills the status line counts:
    {"ok", "found": [{name, folder, version}], "missing": [names], "checked": [folders]}. Each skill is
    taken from the first folder in OpenCode's order that holds it."""
    checked = [install.TARGETS[a][0] for a in OPENCODE_SKILL_AGENTS if a in install.TARGETS]
    found, missing = [], []
    for name in kb_manage.SKILLS:
        where = next((os.path.join(f, name) for f in checked if os.path.isfile(os.path.join(f, name, "SKILL.md"))), "")
        if where:
            found.append({"name": name, "folder": where, "version": skill_version(where)})
        else:
            missing.append(name)
    return {"ok": not missing, "found": found, "missing": missing, "checked": checked}


def opencode_skills():
    """True when the folders OpenCode reads hold every knowledge-base skill."""
    return kb_skills()["ok"]


def instructions_file():
    """The instructions file an upgrade refreshes the knowledge-base line in: OpenCode's AGENTS.md, or
    Claude Code's CLAUDE.md while OpenCode has no AGENTS.md and reads that one with the line in it."""
    own = install.INSTRUCTION_FILES["opencode"][0]
    claude = install.INSTRUCTION_FILES["claude-code"][0]
    if not os.path.isfile(own) and kb_manage.has_our_line(claude):
        return claude
    return own


def instructions_line():
    """True when the instructions OpenCode reads name the libraries: its AGENTS.md, or Claude Code's
    CLAUDE.md while there is no AGENTS.md (OpenCode reads that one then)."""
    path, _ = install.INSTRUCTION_FILES["opencode"]
    if os.path.isfile(path):
        return kb_manage.has_our_line(path)
    return kb_manage.has_our_line(install.INSTRUCTION_FILES["claude-code"][0])


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


OPENCODE = {"program": None}  # agent.Program, looked up once at start (find_opencode)


def find_opencode(explicit=""):
    OPENCODE["program"] = agent_mod.find_opencode(explicit)
    log.info("opencode: %s (%s)", OPENCODE["program"].describe() or "not found", OPENCODE["program"].how)
    return OPENCODE["program"]


def agent_status():
    """OpenCode on this computer: how it is run, and whether its settings name a model."""
    folder = install.AGENT_HOMES["opencode"]
    prog = OPENCODE["program"] or find_opencode()
    status = {"program": prog.describe(), "how": prog.how, "config": "", "model": False, "error": ""}
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


QUOTES = {'"': '"', "'": "'", "「": "」", "“": "”"}
BARE_PATH_RE = re.compile(r"(?<![^\s:：，,（(])[~/][^\s\"'“”「」，。；、）)]*")


def path_words(text):
    """The quoted parts that start with / or ~ (they may hold spaces), then the unquoted words that do.
    Linear in the length of the text: each kind of quote is searched forward only."""
    out, i, closed = [], 0, set()
    while i < len(text):
        c = text[i]
        if c in QUOTES and c not in closed:
            j = text.find(QUOTES[c], i + 1)
            if j < 0:
                closed.add(c)  # no closing quote of this kind further on
            elif j > i + 1 and text[i + 1] in "~/":
                out.append(text[i + 1:j])
                i = j + 1
                continue
        i += 1
    return out + BARE_PATH_RE.findall(text)


def text_paths(text):
    """Absolute paths (or ~/ ones) written in a message that name existing files or folders in the home
    folder or on a mounted drive, so that reading them needs no card. Quoted paths may hold spaces; at most
    MAX_PATHS."""
    out = []
    for raw in path_words(text or ""):
        raw = raw.rstrip(".,;:。，；：")
        path = known_path(raw)
        if not path or path in out:
            continue
        out.append(path)
        if len(out) >= MAX_PATHS:
            break
    return out


def known_path(raw):
    """The existing folder or file a typed path names, built by walk_to from the folder listings of the home
    folder or a mounted drive (never by testing the typed text itself); "" when there is none."""
    try:
        folder, _ = walk_to(raw)
        return folder
    except (ValueError, OSError):
        pass
    want = os.path.normpath(os.path.expanduser(raw))
    try:
        folder, _ = walk_to(os.path.dirname(want))
        name = os.path.basename(want)
        with os.scandir(folder) as it:
            found = [e.name for e in it if e.name == name and e.is_file()]
    except (ValueError, OSError):
        return ""
    return os.path.join(folder, found[0]) if found else ""


def walk_to(path, nearest=False):
    """(folder, starting point) for an absolute path inside the home folder or a mounted drive. The folder
    is built from the starting point one name at a time, each name taken from the folder listing, and its
    real path must stay inside the starting point's, so links out of it are refused too. With nearest,
    the walk stops at the last existing folder (a folder typed in an answer is often not made yet)."""
    if not path or not os.path.isabs(os.path.expanduser(path)):
        raise ValueError("not an absolute path")
    want = os.path.normpath(os.path.expanduser(path))
    for place in places():
        root = os.path.normpath(place["path"])
        if want != root and not want.startswith(root.rstrip(os.sep) + os.sep):
            continue
        folder = root
        for name in [x for x in want[len(root):].split(os.sep) if x]:
            try:
                found = [e.name for e in os.scandir(folder) if e.name == name and e.is_dir()]
            except OSError:
                found = []
            if not found:
                if nearest:
                    break
                raise ValueError("not a folder")
            folder = os.path.join(folder, found[0])
        real, real_root = os.path.realpath(folder), os.path.realpath(root)
        if real != real_root and not real.startswith(real_root.rstrip(os.sep) + os.sep):
            raise ValueError("outside the home folder and the mounted drives")
        return folder, root
    raise ValueError("outside the home folder and the mounted drives")


def list_folder(path, hidden=False, nearest=False):
    """The entries of one folder inside the home folder or a mounted drive, folders first (walk_to).
    Reads only."""
    path, root = walk_to(path, nearest)
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
        if path == "/api/graph":
            lib_id = (query.get("lib") or [""])[0]
            lib = next((x for x in libraries() if x["id"] == lib_id and x["root"] and x["exists"]), None)
            if lib is None:
                return self.send(404, {"error": "library"})
            return self.send(200, dict(graph(lib["root"], self.app.started), label=lib["label"], root=lib["root"]))
        if path == "/api/pending":
            return self.send(200, pending_runs())
        if path == "/api/skills":
            return self.send(200, {"skills": skills_admin.list_skills(), "folder": skills_admin.own_folder()})
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
        if path == "/api/chat/state":
            return self.chat_state((query.get("win") or [""])[0])
        if path == "/api/chat/events":
            return self.chat_events(query)
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
            if action in SIMPLE_REFUSED and self.app.options.get("simple"):
                return self.send(403, {"error": MSG[self.app.lang]["simple"]})
            arg = body.get("skill") if action.startswith("skill_") else body.get("library")
            job, why = self.app.start(action, arg if isinstance(arg, str) else None)
            if job is None:
                return self.send(409, {"error": MSG[self.app.lang][why], "reason": why})
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
        if path == "/api/pending":
            return self.pending_post(body)
        if path.startswith("/api/chat/"):
            return self.chat_post(path[len("/api/chat/"):], body)
        if path == "/api/quit":
            log.info("stopping: Quit on the page")
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

    # ----- the conversation -----

    def chat_state(self, win=""):
        """The agent as the page shows the window win (the current one when not given), with its history."""
        ag = self.app.agent
        if ag is None:
            return self.send(200, {"agent": {"state": "off"}, "seq": 0, "history": []})
        if win and win not in ag.windows:
            return self.send(404, {"error": MSG[self.app.lang]["no_window"], "reason": "no_window"})
        seq = ag.feed.last()  # before the history, so nothing falls between the two
        try:
            history = ag.history(win or None)
        except OSError as e:
            log.warning("history: %s", e)
            history = []
        return self.send(200, {"agent": ag.snapshot(win or None), "seq": seq, "history": history})

    def chat_events(self, query):
        ag = self.app.agent
        if ag is None:
            return self.send(404, {"error": "not started"})
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
                evs = ag.feed.since(seq, 15)
                if not evs:
                    self.wfile.write(b": keep-alive\n\n")
                for ev in evs:
                    seq = ev["seq"]
                    data = json.dumps(ev, ensure_ascii=False)
                    self.wfile.write(f"id: {seq}\ndata: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.app.last_seen = time.time()
        except (BrokenPipeError, ConnectionResetError):
            log.debug("chat stream closed by the page")
        return None

    def pending_post(self, body):
        """The owner's decisions for a pending ingest run: checked, written next to the pending file, and
        said in the current conversation window when the assistant is there."""
        ing = ingest_module()
        lib = next((x for x in libraries() if x["id"] == body.get("library") and x["root"] and x["exists"]), None)
        if lib is None:
            return self.send(404, {"error": "no such library"})
        try:
            path, dpath = ing.pending_paths(lib["root"], body.get("run") if isinstance(body.get("run"), str) else "")
        except ValueError as e:
            return self.send(400, {"error": str(e)})
        if not os.path.isfile(path):
            return self.send(404, {"error": "no such run"})
        if os.path.exists(dpath):
            return self.send(409, {"error": "already decided"})
        decisions = body.get("decisions")
        try:
            with open(path, encoding="utf-8") as f:
                pend = json.load(f)
        except (OSError, ValueError) as e:
            return self.send(409, {"error": str(e)})
        problems = ing.check_decisions(pend, decisions) if isinstance(decisions, dict) else ["decisions"]
        if problems:
            return self.send(400, {"error": "decisions", "problems": problems})
        with open(dpath, "w", encoding="utf-8") as f:
            json.dump(decisions, f, ensure_ascii=False, indent=1)
        text = MSG[self.app.lang]["pending_said"].format(run=pend.get("run") or body["run"], lib=lib["label"])
        said = False
        ag = self.app.agent
        if ag is not None and ag.state in ("ready", "simple"):
            try:
                ag.send(text)
                said = True
            except (RuntimeError, ValueError) as e:
                log.info("could not say the decisions: %s", e)
        return self.send(200, {"ok": True, "said": said, "text": text})

    def chat_post(self, path_part, body):
        what = CHAT_ACTIONS.get(path_part)  # a fixed name from here on, never the request's own text
        if what is None:
            return self.send(404, {"error": "not found"})
        m = MSG[self.app.lang]
        if what in SIMPLE_REFUSED and self.app.options.get("simple"):
            return self.send(403, {"error": m["simple"]})
        if what in CHAT_FIRST_ACTIONS and not self.app.options.get("chat_first"):
            return self.send(404, {"error": "not found"})
        if what in ("start", "recheck"):
            ag, why = self.app.start_agent() if what == "start" else self.app.recheck()
            if ag is None:
                return self.send(409, {"error": m[why], "reason": why})
            return self.send(200, {"agent": ag.snapshot()})
        ag = self.app.agent
        if ag is None or ag.state not in ("ready", "simple"):
            return self.send(409, {"error": m["not_ready"]})
        wid = body.get("win") or None
        if wid is not None and (not isinstance(wid, str) or wid not in ag.windows):
            return self.send(404, {"error": m["no_window"], "reason": "no_window"})
        w = ag.window(wid) if what not in ("permission", "question", "open", "workdir", "sessions", "forget") else None
        try:
            if what == "send":
                text, material = body.get("text"), body.get("material") or []
                if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
                    return self.send(400, {"error": "text"})
                if not isinstance(material, list) or len(material) > MAX_PATHS or \
                        not all(isinstance(x, str) and os.path.isabs(x) for x in material):
                    return self.send(400, {"error": "material"})
                model = body.get("model") or ""
                if not isinstance(model, str) or (model and not self.app.options.get("chat_first")):
                    return self.send(400, {"error": "model"})
                try:
                    ag.send(text.strip(), material + text_paths(text), model, win=w.id)
                except ValueError:
                    return self.send(400, {"error": "model"})
                return self.send(200, {"ok": True})
            if what == "workdir":
                try:
                    return self.send(200, {"ok": True, "workdir": ag.set_workdir(body.get("path"))})
                except ValueError as e:
                    return self.send(400, {"error": m.get("workdir_" + str(e), m["workdir_missing"]), "reason": str(e)})
                except RuntimeError:
                    return self.send(409, {"error": m["chat_busy"]})
            if what == "sessions":
                return self.send(200, {"sessions": ag.sessions(), "current": ag.session,
                                       "open": {x.session: x.id for x in ag.windows.values() if x.session}})
            if what == "open":
                session = body.get("session")
                if session is not None and not self.app.options.get("chat_first"):
                    return self.send(400, {"error": "session"})
                try:
                    return self.send(200, {"ok": True, "win": ag.open(session)})
                except LookupError:
                    return self.send(404, {"error": "no such conversation"})
                except agent_mod.Refused as e:
                    return self.send(409, {"error": m.get(e.reason, m["not_ready"]), "reason": e.reason})
            if what == "close":
                try:
                    ag.close(w.id, body.get("stop") is True)
                except agent_mod.Refused:
                    return self.send(409, {"error": m["window_busy"], "reason": "busy"})
                return self.send(200, {"ok": True, "current": ag.current})
            if what == "focus":
                ag.focus(w.id)
                return self.send(200, {"ok": True})
            if what == "new":
                ag.new(w.id)
                return self.send(200, {"ok": True, "session": w.session})
            if what == "forget":
                ag.forget()
                return self.send(200, {"ok": True})
            if what == "allow_all":
                if not isinstance(body.get("on"), bool):
                    return self.send(400, {"error": "on"})
                ag.set_allow_all(body["on"], w.id)
                return self.send(200, {"ok": True, "allow_all": w.allow_all})
            if what == "stop":
                ag.stop(w.id)
                return self.send(200, {"ok": True})
            if what == "terminal":
                try:
                    return self.send(200, {"ok": True, "terminal": ag.open_terminal(w.id)})
                except RuntimeError as e:
                    return self.send(409, {"error": str(e), "reason": "no_terminal" if "terminal" in str(e) else "no_session"})
            if what == "permission":
                reply = body.get("reply")
                if reply is None:
                    reply = "once" if body.get("allow") is True else "reject"
                if not isinstance(reply, str) or reply not in agent_mod.REPLIES:
                    return self.send(400, {"error": "reply"})
                ok = ag.reply_permission(str(body.get("id", "")), agent_mod.REPLIES[reply])
                return self.send(200 if ok else 409, {"ok": ok})
            if what == "question":
                answers = body.get("answers")
                if answers is not None and not (isinstance(answers, list) and all(
                        isinstance(a, list) and all(isinstance(x, str) for x in a) for a in answers)):
                    return self.send(400, {"error": "answers"})
                ok = ag.reply_question(str(body.get("id", "")), answers)
                return self.send(200 if ok else 409, {"ok": ok})
        except RuntimeError:
            return self.send(409, {"error": m["not_ready"]})
        except OSError as e:
            log.warning("chat %s failed: %s", what, type(e).__name__)
            return self.send(502, {"error": " ".join(str(e).split())[:300]})
        return self.send(404, {"error": "not found"})

    def static(self, path):
        """Only the page's own files, by fixed name and type."""
        name = "index.html" if path == "/" else path[1:]
        for known, ctype in STATIC.items():
            if name == known:
                with open(os.path.join(WEB, known), "rb") as f:
                    return self.send(200, f.read(), ctype)
        return self.send(404, {"error": "not found"})


class LocalServer(ThreadingHTTPServer):
    """No reverse lookup of the host name when binding: on some systems it waits for a DNS timeout
    before the page can open, and the server only ever answers on 127.0.0.1."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]


LOG_KEEP_DAYS = 7


def log_folder():
    return os.path.join(kb_manage.state_dir(), "logs")


def open_log_file(level):
    """Logs also go to <state dir>/logs/kb-client-YYYYMMDD.log (only the owner can read it), at INFO or the
    level asked for when that is lower; log files older than LOG_KEEP_DAYS days are removed. Returns the
    path, or "" when it cannot be written."""
    folder = log_folder()
    try:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if f.startswith("kb-client-") and f.endswith(".log") and \
                    time.time() - os.path.getmtime(p) > LOG_KEEP_DAYS * 86400:
                os.remove(p)
        path = os.path.join(folder, time.strftime("kb-client-%Y%m%d.log"))
        os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600))
        os.chmod(path, 0o600)
        handler = logging.FileHandler(path, encoding="utf-8")
    except OSError as e:
        log.warning("no log file: %s", e)
        return ""
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(min(logging.INFO, getattr(logging, level)))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(min(root.level, handler.level))
    return path


def serve(app, port, open_browser):
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = LocalServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    app.server = server
    url = f"http://127.0.0.1:{server.server_address[1]}/?t={app.token}"
    print(MSG[app.lang]["started"].format(url=url), flush=True)
    if open_browser:
        threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()
    if app.idle:
        threading.Thread(target=app.idle_watch, daemon=True).start()
    def on_term(signum, frame):  # another program asked the client to stop: stop the same way as Quit
        log.info("stopping: signal %s", signum)
        threading.Thread(target=server.shutdown, daemon=True).start()
    try:
        signal.signal(signal.SIGTERM, on_term)
    except (ValueError, OSError):  # not the main thread, or no such signal here
        log.debug("SIGTERM not handled")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:  # Ctrl+C in the terminal window stops the client like Quit
        log.info("stopping: Ctrl+C in the terminal")
    finally:
        server.server_close()
        if app.agent:
            app.agent.shutdown()
        shutil.rmtree(app.work, ignore_errors=True)
    print(MSG[app.lang]["stopped"], flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lang", choices=LANGS)
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--idle", type=int, default=120, metavar="SECONDS")
    ap.add_argument("--start-timeout", type=int, default=90, metavar="SECONDS")
    ap.add_argument("--opencode", default=os.environ.get("KB_CLIENT_OPENCODE", ""), metavar="PATH")
    ap.add_argument("--agent", choices=sorted(install.TARGETS))
    ap.add_argument("--descriptions", metavar="FILE")
    ap.add_argument("--chat-first", action="store_true",
                    help="open on the conversation with the knowledge base folded away; a work folder can be chosen")
    ap.add_argument("--simple", action="store_true",
                    help="hide and refuse moving, uninstalling, rolling back and changing skills")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    logging.getLogger().handlers[0].setLevel(a.log_level)
    path = open_log_file(a.log_level)
    log.info("kb-client started (Python %s, %s), log %s", sys.version.split()[0], " ".join(sys.argv[1:]), path or "none")
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
    find_opencode(a.opencode)
    app = App(lang, {"agent": a.agent, "descriptions": a.descriptions, "opencode": a.opencode,
               "simple": a.simple, "chat_first": a.chat_first},
              a.idle, a.start_timeout)
    app.output = Output(sys.stdout)
    sys.stdout = app.output
    serve(app, a.port, not a.no_browser)
    return 0


if __name__ == "__main__":
    sys.exit(main())
