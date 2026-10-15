"""Intake driven by the client, for local libraries: the fixed steps of kb-incremental's fast intake
(references/fast.md) run here, the judgement steps go to the assistant with a fixed answer.

For each file, in order:
  1. prep.py scan (duplicate check by content hash, conversion, cleanup into <work>/body_<n>.md, card)
  2. the assistant, in a new conversation: masking and term fixes in the body file, the head file
     (metadata only) and a decision file <work>/decision_<n>.json:
     {"partition", "topic", "type", "title", "close_read", "same_version"}; checked here, asked again
     up to MAX_ASKS times with the reason when it is missing or wrong
  3. prep.py file (file name, index check, assembly); a file name already in the index goes back to
     the assistant, which decides between the next version (same_version) and another short title
  4. package.py preview --run and deliver: written into the library at once
A file that is a duplicate upload is skipped; one that cannot be converted (a scan, a picture) is
left for the user, who can hand it to the assistant afterwards. Delivery happens here, so an item is
"written" only when package.py deliver went through.

Events go to the conversation feed as type "intake" with the run's snapshot. Each run has its own work
folder under <state dir>/intake/<id>/ (outside the system temporary folder, which the client empties when
it stops): intake-run.json holds the run (saved at every change, so that a client started again shows an
interrupted run as stopped and can continue it) and intake.log what happened to each file (scripts and
their exit codes, the assistant's turns, the decisions and why one was not accepted; never a file's text).
A finished run's folder is removed after KEEP_DAYS days. When the run ends, the conversation goes back to
the one that was open before it. Standard library only.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time

log = logging.getLogger("kb_client.intake")

MAX_FILES = 2000  # files of one run, after folders are expanded
MAX_ASKS = 3  # the assistant's turns for one item (the first and two corrections)
ASK_TIMEOUT = 1200  # seconds for one turn of the assistant
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
1. Masking and term fixes in the body file {body}, following the library's _kb-params.md and spec; change only what needs it.
2. Write the head file {head}: metadata only, in the head format of the params; no key conclusions.
3. Decide the placement and write it into {decision} as one JSON object:
{{"partition": "two-digit partition", "topic": "topic", "type": "document type", "title": "short title", "close_read": true or false, "same_version": false}}
Do not run prep.py file or package.py, write no entity pages and change nothing in the library: the client assembles and writes the file. For a new topic, just use its name. If the body file is missing, answer "files missing" and stop: do not scan the original again or look in other folders. When the decision file is written, answer with one line.""",
        "name_hit": """A file with this name is in the library already:
{out}
Decide whether this item is the next version of that file (compare dates and content). If it is, set "same_version" to true in the decision file; if it is different material, choose a short title that tells them apart. Then write {decision} again.""",
        "retry": """The decision was not accepted: {why}
Correct it and write {decision} again (and {head} where needed).""",
    },
    "zh": {
        "item": """【客户端入库 第 {n}/{total} 项】知识库：{label}（{root}）
原文件：{source}
扫描结果：
{card}

请按 kb-incremental 技能快速入库（references/fast.md）「每一项」的第 2–4 步处理这一项，只做下面三件事：
1. 在正文文件 {body} 里做脱敏和术语修正（按知识库的 _kb-params.md 和规范），只改需要改的地方；
2. 写头文件 {head}：只写元数据（按参数里的头部格式），不写关键结论；
3. 决定放置，把结果写进 {decision}，内容是一个 JSON 对象：
{{"partition": "两位分区号", "topic": "主题", "type": "文档类型", "title": "短标题", "close_read": true 或 false, "same_version": false}}
不要运行 prep.py file、package.py，不新建实体页，也不要改知识库里的任何文件：组装和写入由客户端完成。需要新主题时直接写新主题名。如果正文文件不存在，直接回复「缺少文件」并停止，不要重新扫描原文件，也不要去别的文件夹里找。写好决定文件后回复一句话即可。""",
        "name_hit": """知识库里已有同名文件：
{out}
判断这一项是不是那个文件的新版本（对比日期和内容）。是新版本：把决定文件里的 "same_version" 设为 true；是不同的材料：换一个能区分开的短标题。然后重写 {decision}。""",
        "retry": """上一次的决定没有通过：{why}
请修正后重写 {decision}（需要时也改 {head}）。""",
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
           "convert": "no text could be read from it (a scan, a picture or an unknown format)"},
    "zh": {"no_decision": "决定文件不存在，或不是一个 JSON 对象",
           "field": "\"{k}\" 必须是不超过 {n} 个字符的非空文本",
           "flag": "\"{k}\" 只能是 true 或 false", "no_head": "头文件不存在或是空的",
           "no_body": "正文文件不存在或是空的", "stopped": "已停止",
           "timeout": "助手没有按时答复", "agent": "OpenCode 没有就绪",
           "asks": "答复 {n} 次后仍没有可用的决定", "scan": "扫描失败", "file": "组装失败",
           "preview": "写入前的检查没有通过", "deliver": "写进知识库时出错",
           "convert": "读不出文字（扫描件、图片或无法识别的格式）"},
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


class Run:
    """One intake run in a thread. items: [{n, source, file, status, name, reason}] with status waiting,
    working, written, duplicate, manual, failed."""

    def __init__(self, agent, lib, sources, scripts, work, lang, run_id, back_to=""):
        self.agent = agent
        self.back_to = back_to  # the conversation open before the run, opened again when it ends
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
        self.started = time.time()

    @classmethod
    def restore(cls, work):
        """The run saved in work, as a client started again sees it: what was running is stopped, the file
        being worked on waits again. None when there is no readable run there."""
        try:
            with open(os.path.join(work, STATE), encoding="utf-8") as f:
                data = json.load(f)
            snap = data["run"]
            run = cls(None, data["lib"], [], data["scripts"], work, data["lang"], snap["id"], data.get("back_to", ""))
            run.items = [dict(it) for it in snap["items"]]
            run.started = data.get("started", 0)
        except (OSError, ValueError, KeyError, TypeError):
            return None
        if snap["state"] in ("running", "stopping"):
            run.interrupted = True
            for it in run.items:
                if it["status"] == "working":
                    it["status"], it["reason"] = "waiting", ""
            run.state = "stopped"
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
                    "state": self.state, "step": self.step, "total": len(self.items), "counts": counts,
                    "items": [dict(it) for it in self.items], "log": os.path.join(self.work, LOG)}

    def emit(self):
        snap = self.snapshot()
        self.save(snap)
        if self.agent is not None:
            self.agent.feed.emit("intake", run=snap)

    def save(self, snap):
        data = {"run": snap, "lib": self.lib, "scripts": self.scripts, "lang": self.lang, "back_to": self.back_to,
                "started": self.started}
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
            self.agent.stop()
        except (OSError, RuntimeError):
            log.debug("nothing to stop")
        self.emit()

    def running(self):
        return self.state in ("running", "stopping")

    def main(self):
        self.note(f"run {self.id}: {len(self.items)} files into {self.lib['label']} ({self.lib['root']}); "
                  f"scripts {self.scripts}; Python {sys.version.split()[0]}")
        self.emit()
        try:
            for item in self.items:
                if self.stop_flag.is_set():
                    break
                self.one(item)
        except Exception as e:  # shown on the page as a failed item; the client keeps running
            log.exception("intake run %s", self.id)
            self.note(f"error: {type(e).__name__}: {e}")
        finally:
            with self.lock:
                self.state = "stopped" if self.stop_flag.is_set() else "done"
                self.step = ""
                for it in self.items:
                    if it["status"] == "working":
                        it["status"], it["reason"] = "waiting", WHY[self.lang]["stopped"]
            self.note(f"run {self.id} {self.state}: " + ", ".join(f"{k} {v}" for k, v in sorted(self.snapshot()["counts"].items())))
            self.emit()
            self.go_back()

    def go_back(self):
        """Opens the conversation that was open before the run, so that no file's conversation is the one
        picked up later."""
        ag = self.agent
        if ag is None or ag.state != "ready":
            return
        for _ in range(30):  # the last turn may still be ending
            try:
                ag.use_session(self.back_to)
                self.note(f"conversation back to {self.back_to or 'a new one'}")
                return
            except RuntimeError:
                time.sleep(1)
            except OSError as e:
                self.note(f"conversation not changed back: {e}")
                return

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

    def library_names(self):
        if self.names is None:
            sys.path.insert(0, self.scripts)
            try:
                import kbconf  # the installed skill's own copy
                self.names = kbconf.load_library(self.lib["root"])["names"]
            except Exception:  # noqa: BLE001 - a library prep.py refuses shows there
                self.names = {}
            finally:
                if sys.path and sys.path[0] == self.scripts:
                    sys.path.pop(0)
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
        self.set(item, status="written", name=written[0] if written else "")

    def ask(self, text, material, new):
        """One turn of the assistant: text in a new conversation (or the item's own), until it is idle."""
        ag = self.agent
        if ag.state != "ready":
            self.note(f"assistant not ready ({ag.state})")
            raise Stopped(WHY[self.lang]["agent"])
        began = time.time()
        self.note(("new conversation, " if new else "same conversation, ") + f"message of {len(text)} characters")
        seq = ag.feed.last()
        try:
            if new:
                ag.new()
            ag.send(text, material)
        except (OSError, RuntimeError, ValueError) as e:
            log.warning("intake message not sent: %s", type(e).__name__)
            raise Stopped(WHY[self.lang]["agent"])
        busy, deadline = False, time.time() + ASK_TIMEOUT
        while time.time() < deadline:
            if self.stop_flag.is_set():
                raise Stopped(WHY[self.lang]["stopped"])
            for ev in ag.feed.since(seq, 2):
                seq = ev["seq"]
                if ev["type"] == "status":
                    if ev["status"] != "idle":
                        busy = True
                    elif busy:
                        self.note(f"  assistant done in {time.time() - began:.0f} s (conversation {ag.session})")
                        return
                elif ev["type"] == "agent" and ev.get("state") in ("failed", "simple"):
                    self.note(f"  assistant {ev.get('state')}: {ev.get('reason', '')}")
                    raise Stopped(WHY[self.lang]["agent"])
                elif ev["type"] == "error":
                    self.note(f"  error from OpenCode: {str(ev.get('text', ''))[:300]}")
                elif ev["type"] in ("auto", "permission"):
                    what = " | ".join(ev.get("patterns") or [])[:200]
                    self.note(f"  {'allowed' if ev['type'] == 'auto' else 'card'}: {ev.get('permission')} {what}")
        self.note(f"  no answer in {ASK_TIMEOUT} s")
        try:
            ag.stop()
        except (OSError, RuntimeError):
            log.debug("nothing to stop")
        raise Stopped(WHY[self.lang]["timeout"])


def latest(root):
    """The most recent run saved under root (Run.restore), or None."""
    try:
        dirs = [os.path.join(root, d) for d in os.listdir(root)]
    except OSError:
        return None
    dirs = [d for d in dirs if os.path.isfile(os.path.join(d, STATE))]
    for d in sorted(dirs, key=lambda d: os.path.getmtime(os.path.join(d, STATE)), reverse=True):
        run = Run.restore(d)
        if run is not None:
            return run
    return None


def clean(root, keep_days=KEEP_DAYS):
    """Removes the work folders of finished runs older than keep_days days; stopped ones stay to be continued."""
    try:
        names = os.listdir(root)
    except OSError:
        return
    for d in names:
        path = os.path.join(root, d)
        state = os.path.join(path, STATE)
        try:
            old = time.time() - os.path.getmtime(state) > keep_days * 86400
            with open(state, encoding="utf-8") as f:
                done = json.load(f)["run"]["state"] == "done"
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if old and done:
            shutil.rmtree(path, ignore_errors=True)


def tail(text, lines=4):
    return " / ".join(ln.strip() for ln in (text or "").strip().split("\n")[-lines:] if ln.strip())[:600]
