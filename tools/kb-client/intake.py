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

Events go to the conversation feed as type "intake" with the run's snapshot. Standard library only.
"""
import json
import logging
import os
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
Do not run prep.py file or package.py, write no entity pages and change nothing in the library: the client assembles and writes the file. For a new topic, just use its name. When the decision file is written, answer with one line.""",
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
不要运行 prep.py file、package.py，不新建实体页，也不要改知识库里的任何文件：组装和写入由客户端完成。需要新主题时直接写新主题名。写好决定文件后回复一句话即可。""",
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

    def __init__(self, agent, lib, sources, scripts, work, lang, run_id):
        self.agent = agent
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

    # ----- the page -----

    def snapshot(self):
        with self.lock:
            counts = {}
            for it in self.items:
                counts[it["status"]] = counts.get(it["status"], 0) + 1
            return {"id": self.id, "library": self.lib["id"], "label": self.lib["label"], "root": self.lib["root"],
                    "state": self.state, "step": self.step, "total": len(self.items), "counts": counts,
                    "items": [dict(it) for it in self.items]}

    def emit(self):
        self.agent.feed.emit("intake", run=self.snapshot())

    def set(self, item, **kw):
        with self.lock:
            item.update(kw)
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
        self.emit()
        try:
            for item in self.items:
                if self.stop_flag.is_set():
                    break
                self.one(item)
        except Exception:  # shown on the page as a failed item; the client keeps running
            log.exception("intake run %s", self.id)
        finally:
            with self.lock:
                self.state = "stopped" if self.stop_flag.is_set() else "done"
                self.step = ""
                for it in self.items:
                    if it["status"] == "working":
                        it["status"], it["reason"] = "waiting", WHY[self.lang]["stopped"]
            self.emit()

    def script(self, *args):
        cmd = [sys.executable, os.path.join(self.scripts, args[0])] + [str(x) for x in args[1:]]
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                               errors="replace", timeout=SCRIPT_TIMEOUT, env=env, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return 124, "timeout"
        except OSError as e:
            return 2, str(e)
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
            raise Stopped(WHY[self.lang]["agent"])
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
                        return
                elif ev["type"] == "agent" and ev.get("state") in ("failed", "simple"):
                    raise Stopped(WHY[self.lang]["agent"])
        try:
            ag.stop()
        except (OSError, RuntimeError):
            log.debug("nothing to stop")
        raise Stopped(WHY[self.lang]["timeout"])


def tail(text, lines=4):
    return " / ".join(ln.strip() for ln in (text or "").strip().split("\n")[-lines:] if ln.strip())[:600]
