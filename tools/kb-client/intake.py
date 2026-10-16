"""Intake driven by the client, for local libraries: the fixed steps of kb-incremental's fast intake
(references/fast.md) run here, the judgement steps go to the assistant with a fixed answer; then the
consolidation queue is worked through, a round at a time (references/consolidate.md).

For each file, in order:
  1. prep.py scan (duplicate check by content hash, conversion, cleanup into <work>/body_<n>.md, card)
  2. the assistant, in a new conversation: term fixes in the body file (no masking: the body stays as it
     is), the head file (metadata only) and a decision file <work>/decision_<n>.json:
     {"partition", "topic", "type", "title", "close_read", "same_version"}; checked here, asked again
     up to MAX_ASKS times with the reason when it is missing or wrong
  3. prep.py file (file name, index check, assembly); a file name already in the index goes back to
     the assistant, which decides between the next version (same_version) and another short title
  4. package.py preview --run and deliver: written into the library at once
A file that is a duplicate upload is skipped; one that cannot be converted (a scan, a picture) is
left for the user, who can hand it to the assistant afterwards. Delivery happens here, so an item is
"written" only when package.py deliver went through.

Then, while the library's consolidation queue has files: one consolidation round per new conversation,
the queue read again after each (consolidate.py list). It ends when the queue is empty, when it did not
get shorter in STUCK_ROUNDS rounds in a row, or after as many rounds as the queue had files plus
STUCK_ROUNDS (a round that does less than its share still counts as progress). With Allow
everything on, the round is unattended: the summary changes are all accepted, as the skill recommends.

A question card or permission card that waits during a turn: with Allow everything on, a question is
answered with its recommended option (permissions are allowed by the agent already); otherwise the card
waits for a person on the page, and the time it waits does not count against the turn's time limit.

Events go to the conversation feed as type "intake" with the run's snapshot. Each run has its own work
folder in its library, <library>/_Runtime/intake/<id>/ (outside the system temporary folder, which the
client empties when it stops, and outside the home folder, so a run survives either): intake-run.json holds the run (saved at every change, so that a client started again shows an
interrupted run as stopped and can continue it) and intake.log what happened to each file (scripts and
their exit codes, the assistant's turns, the decisions and why one was not accepted; never a file's text).
A finished run's folder is removed after KEEP_DAYS days. Runs that earlier versions kept under
<state dir>/intake/ are moved into their libraries once by migrate(). The run talks to the assistant in its own window
(the client's intake window, win), so the page's other conversations go on meanwhile. Standard library only.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time

import kb_manage

log = logging.getLogger("kb_client.intake")

MAX_FILES = 2000  # files of one run, after folders are expanded
MAX_ASKS = 3  # the assistant's turns for one item (the first and two corrections)
ASK_TIMEOUT = 1200  # seconds for one turn of the assistant
CONSOLIDATE_TIMEOUT = 3600  # seconds for one consolidation round
STUCK_ROUNDS = 2  # rounds in a row without a shorter queue end the consolidation
SCRIPT_TIMEOUT = 900  # seconds for one script run (conversion of a large file)
FIELD_MAX = 200
KEEP_DAYS = 7  # a finished run's work folder and log are kept this long
STATE = "intake-run.json"  # package.py uses run.json in the same folder
LOG = "intake.log"
# The lines of prep.py scan's card that say what happened without quoting the file (its opening text,
# headings and term hits are left out of the log)
SCAN_LOGGED = ("===", "Content hash", "Source name", "result:", "index:", "conversion:", "pictures:", "body:",
               "cleanup failed", "date:", "size:", "headings:", "terms: spec not found", "refused")
DECISION_FIELDS = ("partition", "topic", "type", "title")

PROMPT = {
    "en": {
        "item": """[Client intake {n}/{total}] Library: {label} ({root})
Original file: {source}
Scan card:
{card}

Handle this item with steps 2 to 4 of "Each item" in the kb-incremental skill's fast intake (references/fast.md), and do only these three things:
1. Term fixes in the body file {body}, following the library's _kb-params.md and spec; change only what needs it. Do no masking or redaction: the body stays as it is.
2. Write the head file {head}: metadata only, in the head format of the params; no key conclusions.
3. Decide the placement and write it into {decision} as one JSON object:
{{"partition": "two-digit partition", "topic": "topic", "type": "document type", "title": "short title", "close_read": true or false, "same_version": false}}
Do not run prep.py file or package.py, write no entity pages and change nothing in the library: the client assembles and writes the file. For a new topic, just use its name. If the body file is missing, answer "files missing" and stop: do not scan the original again or look in other folders. When the decision file is written, answer with one line.""",
        "name_hit": """A file with this name is in the library already:
{out}
Decide whether this item is the next version of that file (compare dates and content). If it is, set "same_version" to true in the decision file; if it is different material, choose a short title that tells them apart. Then write {decision} again.""",
        "retry": """The decision was not accepted: {why}
Correct it and write {decision} again (and {head} where needed).""",
        "consolidate": """[Client consolidation, round {r}] Library: {label} ({root})
Do one round of consolidation with the kb-incremental skill (references/consolidate.md): the steps before the first round, then this one round only. Use {work} as the work folder. {mode}
Stop when this round is delivered and do not go on with the next one: the client starts it in a new conversation. Last, write this round's result into {result} as one JSON object:
{{"files": files consolidated, "changes": summary changes applied}}
and answer with one line. An empty queue: write {{"files": 0, "changes": 0}} and stop.""",
        "unattended": """This run is unattended (Allow everything is on): at step 5 do not ask; take the recommended "Accept all" and note "unattended, all accepted" in the readme. Wherever else a choice comes up, go on with the recommended option instead of waiting for an answer.""",
        "attended": "At step 5 ask the user as usual.",
        "fallback": "Go on as you judge best.",
    },
    "zh": {
        "item": """【客户端入库 第 {n}/{total} 项】知识库：{label}（{root}）
原文件：{source}
扫描结果：
{card}

请按 kb-incremental 技能快速入库（references/fast.md）「每一项」的第 2–4 步处理这一项，只做下面三件事：
1. 在正文文件 {body} 里做术语修正（按知识库的 _kb-params.md 和规范），只改需要改的地方；不做脱敏或打码，正文保持原样；
2. 写头文件 {head}：只写元数据（按参数里的头部格式），不写关键结论；
3. 决定放置，把结果写进 {decision}，内容是一个 JSON 对象：
{{"partition": "两位分区号", "topic": "主题", "type": "文档类型", "title": "短标题", "close_read": true 或 false, "same_version": false}}
不要运行 prep.py file、package.py，不新建实体页，也不要改知识库里的任何文件：组装和写入由客户端完成。需要新主题时直接写新主题名。如果正文文件不存在，直接回复「缺少文件」并停止，不要重新扫描原文件，也不要去别的文件夹里找。写好决定文件后回复一句话即可。""",
        "name_hit": """知识库里已有同名文件：
{out}
判断这一项是不是那个文件的新版本（对比日期和内容）。是新版本：把决定文件里的 "same_version" 设为 true；是不同的材料：换一个能区分开的短标题。然后重写 {decision}。""",
        "retry": """上一次的决定没有通过：{why}
请修正后重写 {decision}（需要时也改 {head}）。""",
        "consolidate": """【客户端整合 第 {r} 轮】知识库：{label}（{root}）
请用 kb-incremental 技能做一轮整合（references/consolidate.md）：先做「第一轮之前」的准备，然后只做这一轮。工作文件夹用 {work}。{mode}
这一轮送达后就停下，不要接着做下一轮：下一轮由客户端在新对话里发起。最后把这一轮的结果写进 {result}，内容是一个 JSON 对象：
{{"files": 整合的文件数, "changes": 采用的状态卡等改动条数}}
然后回复一句话即可。队列为空时，写入 {{"files": 0, "changes": 0}} 并停止。""",
        "unattended": """这是无人值守的运行（已全部允许）：第 5 步不要提问，按推荐直接「全部采用」，并在说明文件里注明「无人值守，全部采用」；其他需要选择的地方也按推荐项继续，不要等待回答。""",
        "attended": "第 5 步照常请用户选择。",
        "fallback": "按你的判断继续。",
    },
}

WHY = {
    "en": {"no_decision": "the decision file is missing or is not one JSON object",
           "field": "\"{k}\" must be a non-empty text of at most {n} characters",
           "flag": "\"{k}\" must be true or false", "no_head": "the head file is missing or empty",
           "no_body": "the body file is missing or empty", "stopped": "stopped",
           "timeout": "the assistant did not answer in time", "agent": "OpenCode is not ready",
           "asks": "no usable decision after {n} answers", "scan": "scan failed", "file": "assembly failed",
           "preview": "the delivery check failed", "deliver": "writing into the library failed",
           "convert": "no text could be read from it (a scan, a picture or an unknown format)",
           "stuck": "the consolidation queue did not get shorter in {n} rounds in a row (changes not accepted, or the "
                    "round was not delivered); say \"consolidate\" in the conversation to go on",
           "rounds": "the consolidation took more rounds than the queue has files; say \"consolidate\" in the "
                     "conversation to go on"},
    "zh": {"no_decision": "决定文件不存在，或不是一个 JSON 对象",
           "field": "\"{k}\" 必须是不超过 {n} 个字符的非空文本",
           "flag": "\"{k}\" 只能是 true 或 false", "no_head": "头文件不存在或是空的",
           "no_body": "正文文件不存在或是空的", "stopped": "已停止",
           "timeout": "助手没有按时答复", "agent": "OpenCode 没有就绪",
           "asks": "答复 {n} 次后仍没有可用的决定", "scan": "扫描失败", "file": "组装失败",
           "preview": "写入前的检查没有通过", "deliver": "写进知识库时出错",
           "convert": "读不出文字（扫描件、图片或无法识别的格式）",
           "stuck": "整合队列连续 {n} 轮没有变少（改动没有采用，或这一轮没有送达）；可以在对话里说「整合」接着做",
           "rounds": "整合的轮数超过了队列里的文件数；可以在对话里说「整合」接着做"},
}


class Stopped(Exception):
    pass


def expand(paths, library_root):
    """The files of paths (folders walked, hidden names and the library itself skipped), in order and
    without repeats; at most MAX_FILES."""
    out, seen = [], set()
    lib = os.path.realpath(library_root)

    def add(p):
        r = os.path.realpath(p)
        if r in seen or r == lib or r.startswith(lib + os.sep):
            return
        seen.add(r)
        out.append(p)

    for p in paths:
        if os.path.isfile(p):
            add(p)
        elif os.path.isdir(p):
            for d, dirs, files in os.walk(p):
                dirs[:] = sorted(x for x in dirs if not x.startswith("."))
                for f in sorted(files):
                    if not f.startswith("."):
                        add(os.path.join(d, f))
                if len(out) >= MAX_FILES:
                    break
        if len(out) >= MAX_FILES:
            break
    return out[:MAX_FILES]


def read_decision(path, head, body, lang):
    """(decision, "") when the assistant's answer is usable, else (None, why)."""
    w = WHY[lang]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None, w["no_decision"]
    if not isinstance(data, dict):
        return None, w["no_decision"]
    out = {}
    for k in DECISION_FIELDS:
        v = data.get(k)
        if not isinstance(v, str) or not v.strip() or len(v.strip()) > FIELD_MAX:
            return None, w["field"].format(k=k, n=FIELD_MAX)
        out[k] = v.strip()
    for k in ("close_read", "same_version"):
        v = data.get(k, False)
        if not isinstance(v, bool):
            return None, w["flag"].format(k=k)
        out[k] = v
    for p, why in ((head, "no_head"), (body, "no_body")):
        try:
            if os.path.getsize(p) == 0:
                return None, w[why]
        except OSError:
            return None, w[why]
    return out, ""


class _Closed:
    allow_all, questions, permissions, session = False, {}, {}, None


_NO_WINDOW = _Closed()


class Run:
    """One intake run in a thread. items: [{n, source, file, status, name, reason}] with status waiting,
    working, written, duplicate, manual, failed."""

    def __init__(self, agent, lib, sources, scripts, work, lang, run_id, win="", hooks=None):
        self.agent = agent
        # an automatic run's (auto.Watcher): item_done(run, item) once a file is done, ended(run) at the end
        self.hooks = hooks or {}
        self.auto = bool(hooks)
        self.win = win  # the agent's window this run talks in
        self.lib = lib  # {"id", "label", "root"}
        self.scripts = scripts  # the installed kb-incremental's scripts folder
        self.work = work
        self.lang = lang if lang in PROMPT else "en"
        self.id = run_id
        self.items = [{"n": i, "source": s, "file": os.path.basename(s), "status": "waiting", "name": "",
                       "reason": ""} for i, s in enumerate(sources, 1)]
        self.state = "running"  # running, stopping, done, stopped
        self.step = ""  # scan, ask, file, write: what the current item is at
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.names = None
        self.conf = None
        self.started = time.time()
        # the consolidation after the files: state "", running, done, stopped or failed
        self.cons = {"state": "", "round": 0, "rounds": 0, "queue": 0, "files": 0, "changes": 0, "reason": ""}

    @classmethod
    def restore(cls, work):
        """The run saved in work, as a client started again sees it: what was running is stopped, the file
        being worked on waits again. None when there is no readable run there."""
        try:
            with open(os.path.join(work, STATE), encoding="utf-8") as f:
                data = json.load(f)
            snap = data["run"]
            run = cls(None, data["lib"], [], data["scripts"], work, data["lang"], snap["id"], data.get("win", ""))
            run.items = [dict(it) for it in snap["items"]]
            run.started = data.get("started", 0)
            run.auto = bool(data.get("auto"))
            run.cons.update(snap.get("consolidation") or {})
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if snap["state"] in ("running", "stopping"):
            run.interrupted = True
            for it in run.items:
                if it["status"] == "working":
                    it["status"], it["reason"] = "waiting", ""
            run.state = "stopped"
            if run.cons["state"] == "running":
                run.cons["state"] = "stopped"
        else:
            run.state = snap["state"]
        return run

    interrupted = False  # restored from a run that was going when the client stopped
    # ----- the page -----

    def snapshot(self):
        with self.lock:
            counts = {}
            for it in self.items:
                counts[it["status"]] = counts.get(it["status"], 0) + 1
            return {"id": self.id, "library": self.lib["id"], "label": self.lib["label"], "root": self.lib["root"],
                    "auto": self.auto, "win": self.win, "state": self.state, "step": self.step, "total": len(self.items), "counts": counts,
                    "items": [dict(it) for it in self.items], "consolidation": dict(self.cons),
                    "log": os.path.join(self.work, LOG)}

    def emit(self):
        snap = self.snapshot()
        self.save(snap)
        if self.agent is not None:
            self.agent.feed.emit("intake", run=snap)
            self.agent.emit_windows()  # the write lock follows the run

    def save(self, snap):
        data = {"run": snap, "lib": self.lib, "scripts": self.scripts, "lang": self.lang, "win": self.win,
                "started": self.started, "auto": self.auto}
        path = os.path.join(self.work, STATE)
        try:
            fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(path + ".tmp", path)
        except OSError as e:
            log.warning("intake %s not saved: %s", self.id, e)

    def note(self, text):
        """One line in this run's intake.log (only the owner can read it)."""
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(text).replace("\r", "") + "\n"
        try:
            fd = os.open(os.path.join(self.work, LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            log.warning("intake log not written: %s", e)

    def set(self, item, **kw):
        with self.lock:
            item.update(kw)
        if "status" in kw and kw["status"] != "working":
            self.note(f"item {item['n']} {item['file']}: {kw['status']}" + (f" -> {kw['name']}" if kw.get("name") else "")
                      + (f" ({kw['reason']})" if kw.get("reason") else ""))
        self.emit()

    # ----- running -----

    def start(self):
        self.thread = threading.Thread(target=self.main, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()
        with self.lock:
            if self.state == "running":
                self.state = "stopping"
        try:
            self.agent.stop(self.win)
        except (OSError, RuntimeError, KeyError):
            log.debug("nothing to stop")
        self.emit()

    def running(self):
        return self.state in ("running", "stopping")

    def left(self):
        """What a stopped run leaves to continue: (the files not reached, whether consolidation is left)."""
        sources = [it["source"] for it in self.items if it["status"] == "waiting"]
        return sources, self.state == "stopped" and self.cons["state"] not in ("done", "failed")

    def main(self):
        self.note(f"run {self.id}: {len(self.items)} files into {self.lib['label']} ({self.lib['root']}); "
                  f"scripts {self.scripts}; Python {sys.version.split()[0]}")
        self.emit()
        try:
            for item in self.items:
                if self.stop_flag.is_set():
                    break
                self.one(item)
                if "item_done" in self.hooks and item["status"] != "waiting":
                    self.hooks["item_done"](self, item)
            if not self.stop_flag.is_set():
                self.consolidate()
        except Exception as e:  # shown on the page as a failed item; the client keeps running
            log.exception("intake run %s", self.id)
            self.note(f"error: {type(e).__name__}: {e}")
        finally:
            with self.lock:
                self.state = "stopped" if self.stop_flag.is_set() else "done"
                self.step = ""
                if self.cons["state"] == "running":
                    self.cons["state"] = "stopped" if self.stop_flag.is_set() else "failed"
                for it in self.items:
                    if it["status"] == "working":
                        it["status"], it["reason"] = "waiting", WHY[self.lang]["stopped"]
            self.note(f"run {self.id} {self.state}: " + ", ".join(f"{k} {v}" for k, v in sorted(self.snapshot()["counts"].items())))
            self.emit()
            if "ended" in self.hooks:
                self.hooks["ended"](self)

    def script(self, *args):
        cmd = [sys.executable, os.path.join(self.scripts, args[0])] + [str(x) for x in args[1:]]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.note("run: " + " ".join(str(x) for x in args))
        began = time.time()
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                               errors="replace", timeout=SCRIPT_TIMEOUT, env=env, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            self.note(f"  timed out after {SCRIPT_TIMEOUT} s")
            return 124, "timeout"
        except OSError as e:
            self.note(f"  could not run: {e}")
            return 2, str(e)
        self.note(f"  exit {p.returncode} in {time.time() - began:.1f} s")
        for name, text in (("out", p.stdout), ("err", p.stderr)):
            lines = [ln for ln in (text or "").rstrip("\n").split("\n") if ln.strip()]
            if args[0] == "prep.py" and args[1] == "scan" and name == "out":
                lines = [ln for ln in lines if ln.startswith(SCAN_LOGGED)]  # the card's other lines quote the text
            for ln in lines[-20:]:
                self.note(f"  {name}| {ln[:400]}")
        if p.returncode and p.stderr:
            log.info("%s exit %s: %s", args[0], p.returncode, p.stderr.strip()[-500:])
        return p.returncode, p.stdout

    def library_conf(self):
        if self.conf is None:
            sys.path.insert(0, self.scripts)
            try:
                import kbconf  # the installed skill's own copy
                self.conf = kbconf.load_library(self.lib["root"])
            except Exception:  # noqa: BLE001 - a library prep.py refuses shows there
                self.conf = {}
            finally:
                if sys.path and sys.path[0] == self.scripts:
                    sys.path.pop(0)
        return self.conf

    def library_names(self):
        if self.names is None:
            self.names = self.library_conf().get("names") or {}
        return self.names

    def one(self, item):
        w = WHY[self.lang]
        n, src, root = item["n"], item["source"], self.lib["root"]
        p = {k: os.path.join(self.work, f"{k}_{n}.{ext}") for k, ext in
             (("body", "md"), ("head", "md"), ("decision", "json"), ("plan", "json"))}
        self.set(item, status="working", reason="")
        self.step = "scan"
        self.emit()
        code, card = self.script("prep.py", "scan", src, "--library", root, "--work", self.work, "--n", n)
        if code == 3 and "duplicate upload by content hash" in card:
            self.set(item, status="duplicate")
            return
        if code:
            self.set(item, status="failed", reason=f"{w['scan']}: {tail(card)}")
            return
        if not os.path.isfile(p["body"]) or "read the original" in card:
            self.set(item, status="manual", reason=w["convert"])
            return
        if self.stop_flag.is_set():
            return
        t = PROMPT[self.lang]
        fill = dict(n=n, total=len(self.items), label=self.lib["label"], root=root, source=src, card=card.strip(),
                    body=p["body"], head=p["head"], decision=p["decision"])
        message = t["item"].format(**fill)
        new, last = True, ""
        for _ in range(MAX_ASKS):
            self.step = "ask"
            self.emit()
            try:
                self.ask(message, [src, p["body"], p["head"], p["decision"]], new)
            except Stopped as e:
                self.set(item, status="waiting" if self.stop_flag.is_set() else "failed", reason=str(e))
                return
            new = False
            d, why = read_decision(p["decision"], p["head"], p["body"], self.lang)
            self.note(f"item {n} decision: {json.dumps(d, ensure_ascii=False)}" if d else f"item {n} decision not accepted: {why}")
            if d is None:
                last = why
                message = t["retry"].format(why=why, **fill)
                continue
            self.step = "file"
            self.emit()
            args = ["prep.py", "file", "--n", n, "--library", root, "--work", self.work,
                    "--partition", d["partition"], "--topic", d["topic"], "--type", d["type"], "--title", d["title"],
                    "--orig", item["file"], "--source", src, "--backend", "local"]
            args += ["--close-read"] if d["close_read"] else []
            args += ["--same-version"] if d["same_version"] else []
            code, out = self.script(*args)
            if code == 3 and "File name: HIT" in out:
                last = tail(out)
                message = t["name_hit"].format(out=out.strip(), **fill)
                continue
            if code and "refused:" in out:  # the library or this computer, not the answer: asking again cannot help
                self.set(item, status="failed", reason=f"{w['file']}: {tail(out)}")
                return
            if code:
                last = f"{w['file']}: {tail(out)}"
                message = t["retry"].format(why=last, **fill)
                continue
            self.deliver(item, n, p["plan"])
            return
        self.set(item, status="failed", reason=w["asks"].format(n=MAX_ASKS) + (f" ({last})" if last else ""))

    def deliver(self, item, n, plan):
        w = WHY[self.lang]
        self.step = "write"
        self.emit()
        out_dir = os.path.join(self.work, f"out_{n}")
        code, out = self.script("package.py", "preview", out_dir, "--library", self.lib["root"], "--plan", plan,
                                "--run", os.path.join(self.work, "run.json"))
        if code:
            self.set(item, status="failed", reason=f"{w['preview']}: {tail(out)}")
            return
        code, out = self.script("package.py", "deliver", "--plan", plan)
        if code:
            self.set(item, status="failed", reason=f"{w['deliver']}: {tail(out)}")
            return
        names = self.library_names()
        skip = {names.get("index"), names.get("consolidation_queue"), names.get("readme")}
        written = sorted(f for f in os.listdir(out_dir) if f.endswith(".md") and f not in skip)
        # kept: the original's copy is in the library's sources folder (a library that keeps originals)
        sources = names.get("sources_dir") or "Sources"
        try:
            copies = os.listdir(os.path.join(out_dir, sources))
        except OSError:
            copies = []
        kept = bool(copies) and all(os.path.isfile(os.path.join(self.lib["root"], sources, f)) for f in copies)
        self.set(item, status="written", name=written[0] if written else "", kept=kept)

    def queue_length(self):
        """Files in the library's consolidation queue (consolidate.py list); 0 when there is no queue."""
        name = self.library_names().get("consolidation_queue") or "_Consolidation-Queue.md"
        queue = os.path.join(self.lib["root"], name)
        if not os.path.isfile(queue):
            return 0
        code, out = self.script("consolidate.py", "list", queue, "--limit", 1)
        for ln in (out or "").split("\n"):
            if code == 0 and ln.startswith("queue: "):
                try:
                    return int(ln.split()[1])
                except (IndexError, ValueError):
                    break
        return None

    def cset(self, **kw):
        with self.lock:
            self.cons.update(kw)
        self.emit()

    def consolidate(self):
        """Consolidation rounds until the queue is empty, each in a new conversation."""
        w, t = WHY[self.lang], PROMPT[self.lang]
        q = self.queue_length()
        if q is None:
            self.cset(state="failed", reason=w["scan"])
            return
        if q == 0:
            self.note("consolidation: the queue is empty")
            self.cset(state="done", queue=0)
            return
        intake = self.library_conf().get("intake") or {}
        per = intake.get("consolidate_files") if isinstance(intake.get("consolidate_files"), int) else 10
        per = max(1, per)
        rounds = -(-q // per)
        self.note(f"consolidation: {q} files in the queue, {per} a round")
        self.step = "consolidate"
        self.cset(state="running", round=0, rounds=rounds, queue=q, files=0, changes=0, reason="")
        stuck, most = 0, q + STUCK_ROUNDS
        while q > 0:
            r = self.cons["round"] + 1
            if r > most:
                self.cset(state="failed", reason=w["rounds"])
                return
            unattended = self.window().allow_all
            work = os.path.join(self.work, f"consolidate_{r}")
            result = os.path.join(self.work, f"consolidate_{r}.json")
            os.makedirs(work, mode=0o700, exist_ok=True)
            self.cset(round=r, rounds=max(rounds, r))
            self.note(f"consolidation round {r} ({'unattended' if unattended else 'the user decides'})")
            text = t["consolidate"].format(r=r, label=self.lib["label"], root=self.lib["root"], work=work,
                                           result=result, mode=t["unattended" if unattended else "attended"])
            try:
                self.ask(text, [], True, CONSOLIDATE_TIMEOUT)
            except Stopped as e:
                self.cset(state="stopped" if self.stop_flag.is_set() else "failed", reason=str(e))
                return
            got = read_result(result)
            left = self.queue_length()
            if left is None:
                left = q
            stuck = 0 if left < q else stuck + 1
            self.note(f"consolidation round {r}: queue {q} -> {left}; reported {json.dumps(got)}")
            with self.lock:
                self.cons["files"] += max(0, q - left)
                self.cons["changes"] += got.get("changes", 0)
                self.cons["queue"] = left
                self.cons["rounds"] = r + -(-left // per)  # the estimate, from what is left
            self.emit()
            q = left
            if stuck >= STUCK_ROUNDS:
                self.cset(state="failed", reason=w["stuck"].format(n=STUCK_ROUNDS))
                return
            if self.stop_flag.is_set():
                self.cset(state="stopped", reason=w["stopped"])
                return
        self.cset(state="done")

    def window(self):
        """The agent's window this run talks in (a stand-in when it was closed meanwhile)."""
        w = self.agent.windows.get(self.win) if self.agent is not None else None
        return w if w is not None else _NO_WINDOW

    def waiting_cards(self):
        """Answers the question cards waiting (Allow everything on); True while a card waits for a person."""
        ag, w = self.agent, self.window()
        questions = list(w.questions.values())
        if w.allow_all:
            for q in questions:
                answers = ag.answer_recommended(q["id"], PROMPT[self.lang]["fallback"])
                self.note(f"  question answered as recommended: {json.dumps(answers, ensure_ascii=False)[:300]}")
            return False
        return bool(questions or w.permissions)

    def ask(self, text, material, new, timeout=ASK_TIMEOUT):
        """One turn of the assistant: text in a new conversation (or the item's own), until it is idle. The
        time a card waits for a person does not count against timeout."""
        ag = self.agent
        if ag.state != "ready":
            self.note(f"assistant not ready ({ag.state})")
            raise Stopped(WHY[self.lang]["agent"])
        began = time.time()
        self.note(("new conversation, " if new else "same conversation, ") + f"message of {len(text)} characters")
        seq = ag.feed.last()
        try:
            if new:
                ag.new(self.win)
            ag.send(text, material, win=self.win)
        except (OSError, RuntimeError, ValueError, KeyError) as e:
            log.warning("intake message not sent: %s", type(e).__name__)
            raise Stopped(WHY[self.lang]["agent"])
        busy, deadline, waited = False, time.time() + timeout, None
        while time.time() < deadline:
            if self.stop_flag.is_set():
                raise Stopped(WHY[self.lang]["stopped"])
            if self.waiting_cards():  # the time left stands still while a card waits
                if waited is None:
                    waited = max(5.0, deadline - time.time())
                    self.note("  a card waits for a person on the page")
                deadline = time.time() + waited
            else:
                waited = None
            for ev in ag.feed.since(seq, 2):
                seq = ev["seq"]
                if ev.get("win") not in (None, self.win):
                    continue  # another window's conversation
                if ev["type"] == "status":
                    if ev["status"] != "idle":
                        busy = True
                    elif busy:
                        self.note(f"  assistant done in {time.time() - began:.0f} s (conversation {self.window().session})")
                        return
                elif ev["type"] == "agent" and ev.get("state") in ("failed", "simple"):
                    self.note(f"  assistant {ev.get('state')}: {ev.get('reason', '')}")
                    raise Stopped(WHY[self.lang]["agent"])
                elif ev["type"] == "error":
                    self.note(f"  error from OpenCode: {str(ev.get('text', ''))[:300]}")
                elif ev["type"] in ("auto", "permission"):
                    what = " | ".join(ev.get("patterns") or [])[:200]
                    self.note(f"  {'allowed' if ev['type'] == 'auto' else 'card'}: {ev.get('permission')} {what}")
        self.note(f"  no answer in {timeout} s")
        try:
            ag.stop(self.win)
        except (OSError, RuntimeError, KeyError):
            log.debug("nothing to stop")
        raise Stopped(WHY[self.lang]["timeout"])


def read_result(path):
    """{"files", "changes"} from a round's result file; {} when it is missing or unusable."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in ("files", "changes") and isinstance(v, int) and 0 <= v < 100000}


def run_dirs(roots):
    """The run folders (with a saved run) under each of roots."""
    out = []
    for root in roots:
        try:
            names = os.listdir(root)
        except OSError:
            continue
        out += [os.path.join(root, d) for d in names if os.path.isfile(os.path.join(root, d, STATE))]
    return out


def latest(roots):
    """The most recent run saved under any of roots (Run.restore), or None."""
    dirs = run_dirs(roots)
    for d in sorted(dirs, key=lambda d: os.path.getmtime(os.path.join(d, STATE)), reverse=True):
        run = Run.restore(d)
        if run is not None:
            return run
    return None


def clean(roots, keep_days=KEEP_DAYS):
    """Removes the work folders of finished runs older than keep_days days; stopped ones stay to be continued."""
    for path in run_dirs(roots):
        state = os.path.join(path, STATE)
        try:
            old = time.time() - os.path.getmtime(state) > keep_days * 86400
            with open(state, encoding="utf-8") as f:
                done = json.load(f)["run"]["state"] == "done"
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if old and done:
            shutil.rmtree(path, ignore_errors=True)


def migrate(old_root, dest_of):
    """Moves the run folders of earlier versions (<state dir>/intake/<id>/) into their libraries:
    dest_of(library id) is that library's intake folder, or None while the library is not here. A folder is
    copied, compared and only then removed; one that cannot go yet stays for the next start. Returns the
    number moved."""
    try:
        names = sorted(os.listdir(old_root))
    except OSError:
        return 0
    moved = left = 0
    for name in names:
        src = os.path.join(old_root, name)
        try:
            with open(os.path.join(src, STATE), encoding="utf-8") as f:
                lib_id = json.load(f)["lib"]["id"]
            dest_root = dest_of(str(lib_id))
            if not dest_root:
                left += 1
                continue
            dest = os.path.join(dest_root, name)
            if not os.path.exists(dest):
                os.makedirs(dest_root, mode=0o700, exist_ok=True)
                tmp = dest + ".moving"
                shutil.rmtree(tmp, ignore_errors=True)
                shutil.copytree(src, tmp, symlinks=True)
                os.rename(tmp, dest)
            if kb_manage.diff_trees(src, dest):
                log.warning("intake run %s: the copy in %s differs; the old folder stays", name, dest_root)
                left += 1
                continue
            shutil.rmtree(src)
            moved += 1
        except (OSError, ValueError, KeyError, TypeError) as e:
            log.warning("intake run %s not moved: %s", name, e)
            left += 1
    if not left:
        try:
            os.rmdir(old_root)
        except OSError:
            pass
    if moved or left:
        log.info("intake runs moved into the libraries: %d, left for the next start: %d", moved, left)
    return moved


def tail(text, lines=4):
    return " / ".join(ln.strip() for ln in (text or "").strip().split("\n")[-lines:] if ln.strip())[:600]
