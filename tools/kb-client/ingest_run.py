"""Ingest runs driven by the client, for local libraries: the scripts of kb-ingest do every fixed step, the
assistant only writes cards, one source at a time, in a window of its own.

A run takes one material folder. plan() lists its documents and marks the important ones by the rules
the user chose (folders below the material folder, documents changed on or after a date); the user
confirms the list, then Run.main() goes through the steps:

  convert   doc2kb_core.py --batch <material> --kb-batch: the run's batch files (the folders below the
            material folder become the sources' folders in the library)
  versions  ingest.py versions: sources already in the library (same content), groups of same-named
            sources, possible older versions under another name. Groups and candidates wait for the
            owner's decisions (ingest.py pending write; the page's Waiting for confirmation).
  file      the sources that are not important are filed without cards (ingest.py file --sources):
            they can be searched and quoted at once, and get their cards later (Backfill)
  cards     the important sources, and every source that replaces one in the library, get cards: per
            batch file a new conversation, per source one message; quote_check.py check checks them and
            a rejected card is sent back once with the reason
  decide    new topics and conflicts with the old versions wait for the owner's decisions
  write     ingest.py entities --apply, file --cards, pages

Each run keeps its state in <state dir>/ingest/<id>/run.json, written at every change, so that a client
started again shows an interrupted run as stopped and Continue picks it up where it was; run.log says
what happened (scripts with exit codes, the assistant's turns; never a document's text). Finished runs
are removed after KEEP_DAYS days.

Backfill writes the cards of sources filed without them while the assistant is idle: the important ones
first (the rules of the run that filed them), newest first; it gives way as soon as a conversation window
gets busy, and can be paused. Sources whose cards name new topics wait for the owner's decisions; the
others are written at once (ingest.py backfill, quote_check.py check, entities --apply, add-cards, pages).

Python 3 standard library only.
"""
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time

log = logging.getLogger("kb_client.ingest")

STATE = "run.json"
LOG = "run.log"
KEEP_DAYS = 7
MAX_FILES = 20000  # documents of one material folder
ASK_TIMEOUT = 1200  # seconds for one turn of the assistant
SCRIPT_TIMEOUT = 3600  # seconds for one script run (converting a large folder)
PARALLEL_MAX = 4
POLL = 3  # seconds between looks at a decisions file
IDLE_GRACE = int(os.environ.get("KB_BACKFILL_IDLE", "60"))  # seconds every window must be idle before backfill starts
MATERIAL_EXT = (".docx", ".pptx", ".xlsx", ".xlsm", ".pdf", ".eml", ".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz")

PROMPT = {
    "en": {
        "cards": """[Client ingest {n}/{total}] Library: {label}
Batch file: {batch}
Write the cards of source {sid} ({name}) in that batch file, following the kb-ingest skill's references/extract.md ({extract}); the library's topics are listed in {topics}.
Write them to {out}, one JSON object per line, nothing else in the file. Only this one source; do not read the other sources.
Run no scripts and change nothing in the library: the client checks and files the cards. When the file is written, answer with one line.""",
        "retry": """{k} of the cards in {out} did not pass the quote check:
{reasons}
Write these cards once more, following "Fixing a rejected card" in references/extract.md, to {out} (replace its content; only the corrected cards). Then answer with one line.""",
        "fallback": "Go on as you judge best.",
    },
    "zh": {
        "cards": """【客户端入库 第 {n}/{total} 份】知识库：{label}
批文件：{batch}
请按 kb-ingest 技能的 references/extract.md（{extract}）为这个批文件里的来源 {sid}（{name}）写卡片；知识库的主题列表在 {topics}。
写进 {out}，每行一个 JSON 对象，文件里不写别的内容。只写这一份来源，不要读其他来源。
不要运行任何脚本，也不要改知识库里的文件：卡片由客户端核对和归档。写好后回复一句话即可。""",
        "retry": """{out} 里有 {k} 张卡片没有通过引文核对：
{reasons}
请按 references/extract.md「Fixing a rejected card」重写这些卡片，写进 {out}（覆盖原内容，只写改过的卡片），然后回复一句话即可。""",
        "fallback": "按你的判断继续。",
    },
}
WHY = {
    "en": {"stopped": "stopped", "timeout": "the assistant did not answer in time", "agent": "OpenCode is not ready",
           "convert": "no text could be read (a scan, a picture, an unsupported format) or the same file as another",
           "no_cards": "no card passed the quote check", "script": "a script failed: {what}",
           "busy": "a conversation needed the assistant", "changed": "the library file changed meanwhile"},
    "zh": {"stopped": "已停止", "timeout": "助手没有按时答复", "agent": "OpenCode 没有就绪",
           "convert": "读不出文字（扫描件、图片、不支持的格式），或与另一份文件完全相同",
           "no_cards": "没有卡片通过引文核对", "script": "脚本出错：{what}",
           "busy": "对话需要助手，先让出", "changed": "库里的文件在此期间改动了"},
}


class Stopped(Exception):
    pass


def _lang(lang):
    return lang if lang in PROMPT else "en"


def write_json(path, data):
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- choosing material

def plan(material, rules, library_root):
    """The documents of a material folder and which of them are important: {"material", "total",
    "important", "folders": [{folder, files}], "files": [{rel, modified, important}], "rules", "other"}.
    rules: {"folders": [folders below the material folder; empty for all], "since": "YYYY-MM-DD" or ""}.
    The client hands over a folder found through its folder browser's places (kb_client.walk_to). Refuses
    a folder inside the library and one with more than MAX_FILES documents."""
    material = os.path.realpath(os.path.expanduser(material))
    if not os.path.isdir(material):
        raise ValueError("not a folder: %s" % material)
    root = os.path.realpath(library_root)
    if material == root or material.startswith(root + os.sep) or root.startswith(material + os.sep):
        raise ValueError("the material folder and the library folder must be apart")
    rules = check_rules(rules)
    files, other, folders = [], 0, {}
    for here, dirs, names in os.walk(material):
        dirs[:] = sorted(d for d in dirs if not d.startswith((".", "__MACOSX")))
        for n in sorted(names):
            if n.startswith((".", "~$")):
                continue
            full = os.path.join(here, n)
            rel = os.path.relpath(full, material).replace(os.sep, "/")
            if not n.lower().endswith(MATERIAL_EXT):
                other += 1
                continue
            try:
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            day = datetime.date.fromtimestamp(mtime).isoformat()
            files.append({"rel": rel, "modified": day, "important": important(rel, day, rules)})
            top = rel.split("/")[0] if "/" in rel else ""
            folders[top] = folders.get(top, 0) + 1
            if len(files) > MAX_FILES:
                raise ValueError("more than %d documents in %s: choose a smaller folder" % (MAX_FILES, material))
    return {"material": material, "total": len(files), "important": sum(1 for f in files if f["important"]),
            "folders": [{"folder": k, "files": v} for k, v in sorted(folders.items())], "files": files,
            "rules": rules, "other": other}


def check_rules(rules):
    rules = rules if isinstance(rules, dict) else {}
    folders = [str(f).strip("/").replace("\\", "/") for f in rules.get("folders") or [] if str(f).strip("/")]
    since = str(rules.get("since") or "")
    if since and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        raise ValueError("since must be YYYY-MM-DD")
    return {"folders": folders, "since": since}


def important(rel, day, rules):
    """True when a document (path below the material folder, last-modified day) matches the rules."""
    if rules["folders"] and not any(rel == f or rel.startswith(f + "/") for f in rules["folders"]):
        return False
    return not (rules["since"] and day and day[:10] < rules["since"])


# ---------------------------------------------------------------- a run

class Run:
    """One ingest run in a thread. items: one per source of the batch files, {sid, name, path, batch,
    important, status, cards, reason}; status waiting, filed (without cards), working, carded, duplicate,
    older (filed to the archive as an older version), failed, empty (no text: not filed). missing: documents of the plan that gave
    no source."""

    def __init__(self, app, lib, material, rules, scripts, work, lang, run_id, parallel=1, unattended=False):
        self.app = app  # the client: .agent (agent.Agent), .run_changed()
        self.lib = lib  # {"id", "label", "root"}
        self.material = material
        self.rules = check_rules(rules)
        self.scripts = scripts  # the installed kb-ingest's scripts folder
        self.work = work
        self.lang = _lang(lang)
        self.id = run_id
        self.parallel = max(1, min(PARALLEL_MAX, int(parallel or 1)))
        self.unattended = unattended
        self.items = []
        self.missing = []
        self.step = ""
        self.state = "running"  # running, stopping, waiting (decisions), done, stopped, failed
        self.done = []  # steps finished, for Continue
        self.reason = ""
        self.pending = ""  # the run name the owner's decisions are waited for under
        self.summary = {}
        self.started = time.time()
        self.stop_flag = threading.Event()
        self.lock = threading.RLock()
        self.thread = None
        self.windows = []

    # ----- saving and the page -----

    @classmethod
    def restore(cls, app, work):
        data = read_json(os.path.join(work, STATE))
        if not isinstance(data, dict):
            return None
        try:
            run = cls(app, data["lib"], data["material"], data["rules"], data["scripts"], work, data["lang"],
                      data["id"], data.get("parallel", 1), data.get("unattended", False))
            for k in ("items", "missing", "step", "state", "done", "reason", "pending", "summary", "started"):
                setattr(run, k, data[k])
        except (KeyError, TypeError, ValueError):
            return None
        if run.state in ("running", "stopping"):
            run.state = "stopped"
            for it in run.items:
                if it["status"] == "working":
                    it["status"] = "waiting"
        return run

    def snapshot(self):
        with self.lock:
            counts = {}
            for it in self.items:
                counts[it["status"]] = counts.get(it["status"], 0) + 1
            return {"id": self.id, "library": self.lib["id"], "label": self.lib["label"], "material": self.material,
                    "rules": self.rules, "state": self.state, "step": self.step, "reason": self.reason,
                    "pending": self.pending, "total": len(self.items), "counts": counts, "items": list(self.items),
                    "missing": list(self.missing), "summary": dict(self.summary), "parallel": self.parallel,
                    "windows": list(self.windows), "unattended": self.unattended,
                    "log": os.path.join(self.work, LOG), "started": self.started}

    def save(self):
        with self.lock:
            data = {k: getattr(self, k) for k in ("lib", "material", "rules", "scripts", "lang", "id", "parallel",
                                                  "unattended", "items", "missing", "step", "state", "done",
                                                  "reason", "pending", "summary", "started")}
        try:
            write_json(os.path.join(self.work, STATE), data)
        except OSError as e:
            log.warning("ingest run %s not saved: %s", self.id, e)

    def changed(self):
        self.save()
        self.app.run_changed(self)

    def note(self, text):
        line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(text).replace("\r", "") + "\n"
        try:
            fd = os.open(os.path.join(self.work, LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            log.warning("ingest log not written: %s", e)

    def set(self, it, **kw):
        with self.lock:
            it.update(kw)
        if kw.get("status") not in (None, "working"):
            self.note("%s %s: %s%s" % (it["sid"], it["path"], it["status"], " (%s)" % kw["reason"] if kw.get("reason") else ""))
        self.changed()

    # ----- running -----

    def start(self):
        self.stop_flag.clear()
        with self.lock:
            self.state, self.reason = "running", ""
        self.thread = threading.Thread(target=self.main, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()
        with self.lock:
            if self.state in ("running", "waiting"):
                self.state = "stopping" if self.state == "running" else "stopped"
        ag = self.app.agent
        for wid in list(self.windows):
            try:
                ag.stop(wid)
            except (OSError, RuntimeError, KeyError, AttributeError):
                log.debug("nothing to stop in %s", wid)
        self.changed()

    def running(self):
        return self.state in ("running", "stopping", "waiting")

    def main(self):
        self.note("run %s: %s into %s (%s); rules %s; scripts %s; Python %s" % (
            self.id, self.material, self.lib["label"], self.lib["root"], json.dumps(self.rules, ensure_ascii=False),
            self.scripts, sys.version.split()[0]))
        self.changed()
        try:
            for name in ("convert", "versions", "file", "cards", "decide", "write"):
                if name in self.done:
                    continue
                if self.stop_flag.is_set():
                    raise Stopped(WHY[self.lang]["stopped"])
                with self.lock:
                    self.step = name
                self.changed()
                getattr(self, "step_" + name)()
                with self.lock:
                    self.done.append(name)
                self.changed()
            with self.lock:
                self.state, self.step = "done", ""
        except Stopped as e:
            with self.lock:
                self.state, self.reason = "stopped", str(e)
        except Exception as e:  # shown on the page; the client keeps running
            log.exception("ingest run %s", self.id)
            self.note("error: %s: %s" % (type(e).__name__, e))
            with self.lock:
                self.state, self.reason = "failed", str(e)
        finally:
            with self.lock:
                for it in self.items:
                    if it["status"] == "working":
                        it["status"] = "waiting"
            for wid in list(self.windows):
                try:
                    self.app.agent.drop_window(wid)
                except (AttributeError, KeyError):
                    log.debug("window %s already gone", wid)
            with self.lock:
                self.windows = []
            self.note("run %s %s%s" % (self.id, self.state, ": " + self.reason if self.reason else ""))
            self.changed()

    # ----- scripts -----

    def script(self, *args, ok=(0,)):
        """Runs a kb-ingest script; returns its output. Raises RuntimeError for an exit code not in ok."""
        cmd = [sys.executable, os.path.join(self.scripts, args[0])] + [str(x) for x in args[1:]]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", LOG_LEVEL="WARNING")
        self.note("run: " + " ".join(os.path.basename(str(x)) if os.sep in str(x) else str(x) for x in args))
        began = time.time()
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                               errors="replace", timeout=SCRIPT_TIMEOUT, env=env, stdin=subprocess.DEVNULL)
        except (subprocess.TimeoutExpired, OSError) as e:
            self.note("  could not finish: %s" % type(e).__name__)
            raise RuntimeError(WHY[self.lang]["script"].format(what=args[0]))
        self.note("  exit %d in %.1f s" % (p.returncode, time.time() - began))
        for ln in [x for x in (p.stderr or "").strip().split("\n") if x.strip()][-10:]:
            self.note("  err| " + ln[:400])
        if p.returncode not in ok:
            raise RuntimeError(WHY[self.lang]["script"].format(what="%s %s" % (args[0], args[1] if len(args) > 1 else "")))
        self.last_exit = p.returncode
        return p.stdout

    def path(self, *parts):
        return os.path.join(self.work, *parts)

    def batches(self):
        folder = self.path("batches")
        return sorted(os.path.join(folder, n) for n in os.listdir(folder)
                      if re.search(r"_b\d+\.md$", n)) if os.path.isdir(folder) else []

    # ----- steps -----

    def step_convert(self):
        shutil.rmtree(self.path("batches"), ignore_errors=True)
        self.script("doc2kb_core.py", "--batch", self.material, "-o", self.path("batches"), "--kb-batch",
                    "--library", self.lib["root"])
        batches = self.batches()
        sys.path.insert(0, self.scripts)
        try:
            import kb_batch
            import kbconf
        finally:
            sys.path.remove(self.scripts)
        items, seen = [], set()
        for b in batches:
            with open(b, encoding="utf-8") as f:
                text = f.read()
            table = kb_batch.sources_table(text)
            for sec in kb_batch.parse(text):
                if sec["sid"] in seen:
                    continue
                seen.add(sec["sid"])
                t = table.get(sec["sid"], {})
                folder = kbconf.rel_folder(t.get("path", ""))
                name = os.path.splitext(sec["name"])[0] + ".md"
                day = (t.get("modified") or "")[:10]
                has_text = bool(re.search(r"\^%s\d+" % kb_batch.anchor_prefix(sec["sid"]), text_of(text, sec["sid"])))
                items.append({"sid": sec["sid"], "name": name, "path": "%s/%s" % (folder, name) if folder else name,
                              "rel": t.get("path", ""), "batch": os.path.basename(b),
                              "status": "waiting" if has_text else "empty", "cards": 0,
                              "reason": "" if has_text else WHY[self.lang]["convert"],
                              "important": important(t.get("path", ""), day, self.rules)})
        listed = {it["rel"] for it in items}
        missing = [{"rel": it["rel"], "reason": it["reason"]} for it in items if it["status"] == "empty"]
        for p in plan(self.material, {"folders": [], "since": ""}, self.lib["root"])["files"]:
            if p["rel"] not in listed and not any(r.startswith(p["rel"] + "/") for r in listed):
                missing.append({"rel": p["rel"], "reason": WHY[self.lang]["convert"]})
        with self.lock:
            self.items, self.missing = items, missing
        self.note("converted: %d sources in %d batch files, %d documents gave none" % (len(items), len(batches), len(missing)))

    def step_versions(self):
        args = ["ingest.py", "versions", *self.batches(), "--library", self.lib["root"]]
        if os.path.isfile(self.path("groups.json")):
            args += ["--groups", self.path("groups.json")]
        got = json.loads(self.script(*args))
        write_json(self.path("versions.json"), got)
        by_path = {it["path"]: it for it in self.items}
        for d in got["duplicates"]:
            it = by_path.get(d["source"])
            if it:
                self.set(it, status="duplicate", reason=d["existing"])
        if (got["groups"] or got["candidates"]) and not os.path.isfile(self.path("decided-versions")):
            self.wait_for_decisions("v", versions=self.path("versions.json"))
            out = json.loads(self.script("ingest.py", "pending", "read", "--library", self.lib["root"],
                                         "--run", self.pending, "--work", self.path("decisions-v")))
            shutil.copy(out["groups"], self.path("groups.json"))
            write_json(self.path("replaces.json"), out["replaces"])
            self.script("ingest.py", "pending", "done", "--library", self.lib["root"], "--run", self.pending)
            with open(self.path("decided-versions"), "w", encoding="utf-8") as f:
                f.write(self.pending)
            with self.lock:
                self.pending = ""
            got = json.loads(self.script("ingest.py", "versions", *self.batches(), "--library", self.lib["root"],
                                         "--groups", self.path("groups.json")))
            write_json(self.path("versions.json"), got)
        # a group goes together; a source that replaces one in the library gets cards in this run
        replaces = read_json(self.path("replaces.json"), [])
        new_of = {p.split("=", 1)[0] for p in replaces}
        names = {it["name"] for it in self.items}
        same = set(got["same_name"]) | new_of
        grouped = {g["name"] for g in got["groups"]}
        with self.lock:
            for it in self.items:
                if it["name"] in same or (it["name"] in grouped and any(
                        x["important"] for x in self.items if x["name"] == it["name"])):
                    it["important"] = True
        self.note("versions: %d same names, %d candidates, %d groups, %d duplicates (%d names)" % (
            len(got["same_name"]), len(got["candidates"]), len(got["groups"]), len(got["duplicates"]), len(names)))

    def common_args(self, items):
        """--groups and the --replaces pairs whose new source is one of items."""
        out = []
        if os.path.isfile(self.path("groups.json")):
            out += ["--groups", self.path("groups.json")]
        names = {it["name"] for it in items}
        for pair in read_json(self.path("replaces.json"), []):
            if pair.split("=", 1)[0] in names:
                out += ["--replaces", pair]
        return out

    def file_without_cards(self, items, status):
        """Files items without cards (ingest.py file --sources); a member of a group that was not filed as
        current went to the archive as an older version."""
        if not items:
            return
        out = json.loads(self.script("ingest.py", "file", *self.batches(), "--library", self.lib["root"],
                                     "--sources", ",".join(it["sid"] for it in items), *self.common_args(items)))
        written = set(out["sources"])
        for it in items:
            folder = it["path"].rsplit("/", 1)[0] + "/" if "/" in it["path"] else ""
            same = it["path"] in written or any(w.startswith(folder) and w.endswith("_" + it["name"]) for w in written)
            self.set(it, status=status if same else "older")
        self.summary["filed"] = self.summary.get("filed", 0) + len(out["sources"])

    def step_file(self):
        self.file_without_cards([it for it in self.items if not it["important"] and it["status"] == "waiting"], "filed")

    def step_cards(self):
        todo = [it for it in self.items if it["important"] and it["status"] in ("waiting", "working")]
        if not todo:
            return
        os.makedirs(self.path("cards"), exist_ok=True)
        self.script("ingest.py", "topics", "--library", self.lib["root"], "--out", self.path("topics.txt"))
        by_batch = {}
        for it in todo:
            by_batch.setdefault(it["batch"], []).append(it)
        queue = list(by_batch.values())
        qlock = threading.Lock()
        errors = []

        def worker(k):
            wkey = "%s-%d" % (self.id, k)
            asker = Asker(self, wkey, "%s · %s" % (TAB[self.lang], self.lib["label"]))
            while not self.stop_flag.is_set():
                with qlock:
                    if not queue:
                        return
                    group = queue.pop(0)
                try:
                    asker.new()
                    for it in group:
                        if self.stop_flag.is_set():
                            return
                        self.cards_of(it, asker, len(todo))
                except Stopped as e:
                    errors.append(e)
                    return
                except Exception as e:  # noqa: BLE001 - the other workers go on; reported below
                    log.exception("cards worker")
                    errors.append(e)
                    return

        threads = [threading.Thread(target=worker, args=(k,), daemon=True) for k in range(1, self.parallel + 1)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if self.stop_flag.is_set():
            raise Stopped(WHY[self.lang]["stopped"])
        if errors:
            raise errors[0] if isinstance(errors[0], Stopped) else RuntimeError(str(errors[0]))

    def cards_of(self, it, asker, total):
        """Cards for one source: written by the assistant, checked, sent back once; the accepted ones go to
        cards/<sid>.accepted.jsonl."""
        p = PROMPT[self.lang]
        out = self.path("cards", it["sid"] + ".jsonl")
        acc, rep = self.path("cards", it["sid"] + ".accepted.jsonl"), self.path("cards", it["sid"] + ".report.json")
        self.set(it, status="working")
        n = sum(1 for x in self.items if x["status"] in ("carded", "failed") and x["important"]) + 1
        extract = os.path.join(os.path.dirname(self.scripts), "references", "extract.md")
        batch = self.path("batches", it["batch"])
        asker.ask(p["cards"].format(n=n, total=total, label=self.lib["label"], batch=batch, sid=it["sid"],
                                    name=it["name"], extract=extract, topics=self.path("topics.txt"), out=out))
        accepted = self.check(out, acc, rep, it["sid"])
        report = read_json(rep, {})
        if report.get("rejected"):
            reasons = "\n".join("- %s: %s" % (json.dumps(r.get("card"), ensure_ascii=False)[:200], r.get("reason"))
                                for r in report["rejected"][:20])
            retry, acc2, rep2 = (self.path("cards", it["sid"] + x) for x in (".retry.jsonl", ".accepted2.jsonl", ".report2.json"))
            asker.ask(p["retry"].format(k=len(report["rejected"]), out=retry, reasons=reasons))
            accepted += self.check(retry, acc2, rep2, it["sid"])
            with open(acc, "a", encoding="utf-8") as f:
                for c in read_lines(acc2):
                    f.write(c + "\n")
        self.set(it, status="carded" if accepted else "failed", cards=accepted,
                 reason="" if accepted else WHY[self.lang]["no_cards"])

    def check(self, cards, acc, rep, sid):
        """quote_check.py check of one source's cards; returns how many were accepted."""
        lines = [ln for ln in read_lines(cards) if ln.strip()]
        mine = []
        for ln in lines:
            try:
                c = json.loads(ln)
            except ValueError:
                mine.append(ln)
                continue
            if isinstance(c, dict) and str(c.get("source", "")).strip().upper() in ("", sid):
                c["source"] = sid
                mine.append(json.dumps(c, ensure_ascii=False))
        with open(cards, "w", encoding="utf-8") as f:
            f.write("".join(x + "\n" for x in mine))
        self.script("quote_check.py", "check", cards, *self.batches(), "--accepted", acc, "--report", rep,
                    "--topics", self.path("topics.txt"), ok=(0, 3))
        return len([x for x in read_lines(acc) if x.strip()])

    def accepted(self):
        out = []
        for it in self.items:
            if it["status"] == "carded":
                out += [x for x in read_lines(self.path("cards", it["sid"] + ".accepted.jsonl")) if x.strip()]
        return out

    def step_decide(self):
        carded = [it for it in self.items if it["important"] and it["status"] == "carded"]
        if not carded:
            return
        with open(self.path("accepted.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(x + "\n" for x in self.accepted()))
        new_topics = []
        for it in carded:
            for name in ("report", "report2"):
                for t in (read_json(self.path("cards", "%s.%s.json" % (it["sid"], name)), {}) or {}).get("new_topics", []):
                    if t not in new_topics:
                        new_topics.append(t)
        write_json(self.path("report.json"), {"new_topics": new_topics})
        ents = self.script("ingest.py", "entities", self.path("accepted.jsonl"), "--library", self.lib["root"])
        with open(self.path("entities.json"), "w", encoding="utf-8") as f:
            f.write(ents)
        conf = self.script("ingest.py", "conflicts", *self.batches(), "--cards", self.path("accepted.jsonl"),
                           "--library", self.lib["root"], "--sources", ",".join(it["sid"] for it in carded),
                           *self.common_args(carded))
        with open(self.path("conflicts.json"), "w", encoding="utf-8") as f:
            f.write(conf)
        if not (new_topics or json.loads(conf)):
            return
        self.wait_for_decisions("t", report=self.path("report.json"), entities=self.path("entities.json"),
                                conflicts=self.path("conflicts.json"))
        out = json.loads(self.script("ingest.py", "pending", "read", "--library", self.lib["root"],
                                     "--run", self.pending, "--work", self.path("decisions-t")))
        if out["add_topics"]:
            self.script("ingest.py", "add-topic", "--library", self.lib["root"],
                        *sum([["--topic", t] for t in out["add_topics"]], []))
        for old, new in out["retopic"].items():
            self.script("ingest.py", "retopic", self.path("accepted.jsonl"), "--from", old, "--to", new)
        shutil.copy(out["entity_map"], self.path("entity-map.json"))
        shutil.copy(out["restore"], self.path("restore.json"))

    def step_write(self):
        failed = [it for it in self.items if it["important"] and it["status"] == "failed"]
        carded = [it for it in self.items if it["important"] and it["status"] == "carded"]
        self.file_without_cards(failed, "failed")  # filed all the same; Backfill tries their cards again
        if not carded:
            return
        acc = self.path("accepted.jsonl")
        emap = ["--map", self.path("entity-map.json")] if os.path.isfile(self.path("entity-map.json")) else []
        self.script("ingest.py", "entities", acc, "--library", self.lib["root"], "--apply", *emap)
        restore = ["--restore", self.path("restore.json")] if os.path.isfile(self.path("restore.json")) else []
        out = json.loads(self.script("ingest.py", "file", *self.batches(), "--cards", acc, "--library", self.lib["root"],
                                     "--sources", ",".join(it["sid"] for it in carded), *self.common_args(carded),
                                     *restore))
        if out["topics"]:
            self.script("ingest.py", "pages", "--library", self.lib["root"], *sum([["--topic", t] for t in out["topics"]], []))
        if self.pending:
            self.script("ingest.py", "pending", "done", "--library", self.lib["root"], "--run", self.pending)
            with self.lock:
                self.pending = ""
        self.summary.update(carded=len(out["sources"]), archived=len(out["archived"]), topics=len(out["topics"]),
                            review=len(out["review"]))

    # ----- the owner's decisions -----

    def wait_for_decisions(self, tag, **files):
        """Writes the pending file (ingest.py pending write) unless it is there, then waits for the
        decisions file the page writes."""
        run = "%s-%s" % (self.id, tag)
        pend = os.path.join(self.lib["root"], "_pending", run + ".json")
        dec = os.path.join(self.lib["root"], "_pending", run + ".decisions.json")
        if not os.path.isfile(pend):
            args = ["ingest.py", "pending", "write", "--library", self.lib["root"], "--run", run]
            for k, v in files.items():
                args += ["--" + k, v]
            self.script(*args)
        with self.lock:
            self.pending, self.state = run, "waiting"
        self.changed()
        while not os.path.isfile(dec):
            if self.stop_flag.wait(POLL):
                raise Stopped(WHY[self.lang]["stopped"])
        with self.lock:
            self.state = "running"
        self.changed()


TAB = {"en": "Ingest", "zh": "入库"}


def text_of(batch_text, sid):
    """The section (all parts) of one source in a batch file's text."""
    return "\n".join(m.group(0) for m in re.finditer(r"^# %s .*?(?=^# S\d{2,} |\Z)" % re.escape(sid), batch_text, re.M | re.S))


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n").split("\n")
    except OSError:
        return []


class Asker:
    """One window of the assistant for a run's cards: new() starts a conversation, ask() waits for the turn."""

    def __init__(self, run, key, label):
        self.run, self.key, self.label = run, key, label
        self.win = None

    def window(self):
        ag = self.run.app.agent
        w = ag.ingest_window(self.key, self.label)
        if w.id not in self.run.windows:
            with self.run.lock:
                self.run.windows.append(w.id)
            w.allow_all = w.allow_all or self.run.unattended
        self.win = w.id
        return w

    def new(self):
        ag = self.run.app.agent
        if ag is None or ag.state != "ready":
            raise Stopped(WHY[self.run.lang]["agent"])
        w = self.window()
        ag.new(w.id)

    def ask(self, text, timeout=ASK_TIMEOUT):
        """One turn: text in the window, until it is idle. A question card is answered with its recommended
        option while Allow everything is on in the window; the time a card waits for a person does not count."""
        run, ag = self.run, self.run.app.agent
        if ag is None or ag.state != "ready":
            raise Stopped(WHY[run.lang]["agent"])
        w = self.window()
        seq = ag.feed.last()
        began = time.time()
        run.note("  %s: message of %d characters" % (w.id, len(text)))
        try:
            ag.send(text, win=w.id)
        except (OSError, RuntimeError, ValueError, KeyError) as e:
            run.note("  not sent: %s" % type(e).__name__)
            raise Stopped(WHY[run.lang]["agent"])
        busy, deadline, waited = True, time.time() + timeout, None
        while time.time() < deadline:
            if run.stop_flag.is_set():
                raise Stopped(WHY[run.lang]["stopped"])
            if getattr(run, "gives_way", False) and (run.busy_chat() or run.state == "paused"):
                try:
                    ag.stop(w.id)
                except (OSError, RuntimeError, KeyError):
                    log.debug("nothing to stop in %s", w.id)
                raise Stopped(WHY[run.lang]["busy"])
            if w.questions and w.allow_all:
                for q in list(w.questions.values()):
                    got = ag.answer_recommended(q["id"], PROMPT[run.lang]["fallback"])
                    run.note("  question answered as recommended: %s" % json.dumps(got, ensure_ascii=False)[:200])
            if w.questions or w.permissions:
                if waited is None:
                    waited = max(5.0, deadline - time.time())
                deadline = time.time() + waited
            else:
                waited = None
            for ev in ag.feed.since(seq, 2):
                seq = ev["seq"]
                if ev.get("win") not in (None, w.id):
                    continue
                if ev["type"] == "status":
                    busy = ev["status"] != "idle"
                elif ev["type"] == "agent" and ev.get("state") in ("failed", "simple"):
                    raise Stopped(WHY[run.lang]["agent"])
            if not busy and w.status == "idle" and not (w.questions or w.permissions):
                run.note("  done in %.0f s" % (time.time() - began))
                return
        try:
            ag.stop(w.id)
        except (OSError, RuntimeError, KeyError):
            log.debug("nothing to stop in %s", w.id)
        raise Stopped(WHY[run.lang]["timeout"])


# ---------------------------------------------------------------- runs on disk

def runs_root(state_dir):
    return os.path.join(state_dir, "ingest")


def latest(app, root):
    """The most recent run saved under root, or None."""
    try:
        dirs = [os.path.join(root, d) for d in os.listdir(root)]
    except OSError:
        return None
    dirs = [d for d in dirs if os.path.isfile(os.path.join(d, STATE))]
    for d in sorted(dirs, key=lambda d: os.path.getmtime(os.path.join(d, STATE)), reverse=True):
        run = Run.restore(app, d)
        if run is not None:
            return run
    return None


def clean(root, keep_days=KEEP_DAYS):
    """Removes the folders of finished runs older than keep_days days; stopped ones stay to be continued."""
    try:
        names = os.listdir(root)
    except OSError:
        return
    for d in names:
        path = os.path.join(root, d)
        data = read_json(os.path.join(path, STATE))
        if not isinstance(data, dict) or data.get("state") != "done":
            continue
        try:
            old = time.time() - os.path.getmtime(os.path.join(path, STATE)) > keep_days * 86400
        except OSError:
            continue
        if old:
            shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------- backfill

class Backfill:
    """Writes the cards of a library's sources filed without them while the assistant is idle. One per
    library; state: off, idle (waiting for the assistant), working, paused, waiting (new topics), done."""

    def __init__(self, app, lib, scripts, work, lang, rules=None):
        self.app, self.lib, self.scripts, self.work = app, lib, scripts, work
        self.lang = _lang(lang)
        self.rules = check_rules(rules or {})
        self.state = "off"
        self.left = 0
        self.current = ""
        self.written = 0
        self.held = []  # sources whose cards wait for decisions on new topics
        self.stop_flag = threading.Event()
        self.thread = None
        self.lock = threading.RLock()
        self.windows = []
        self.unattended = False
        self.id = "backfill-" + lib["id"]
        self.gives_way = True  # Asker stops its turn when a conversation gets busy or it is paused
        self.items = []
        os.makedirs(work, exist_ok=True)
        saved = read_json(os.path.join(work, STATE), {}) or {}
        self.held = [x for x in saved.get("held", []) if isinstance(x, dict)]
        self.written = int(saved.get("written", 0) or 0)

    def snapshot(self):
        with self.lock:
            return {"library": self.lib["id"], "state": self.state, "left": self.left, "current": self.current,
                    "written": self.written, "held": len(self.held), "rules": self.rules}

    def save(self):
        try:
            write_json(os.path.join(self.work, STATE), {"held": self.held, "written": self.written})
        except OSError as e:
            log.warning("backfill state not saved: %s", e)

    def changed(self):
        self.save()
        self.app.run_changed(self)

    def note(self, text):
        Run.note(self, text)

    def set(self, it, **kw):
        it.update(kw)

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            with self.lock:
                if self.state == "paused":
                    self.state = "idle"
            self.changed()
            return
        self.stop_flag.clear()
        with self.lock:
            self.state = "idle"
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.changed()

    def pause(self):
        with self.lock:
            self.state = "paused"
        for wid in list(self.windows):
            try:
                self.app.agent.stop(wid)
            except (OSError, RuntimeError, KeyError, AttributeError):
                log.debug("nothing to stop in %s", wid)
        self.changed()

    def off(self):
        self.stop_flag.set()
        self.pause()
        with self.lock:
            self.state = "off"
        self.changed()

    def busy_chat(self):
        """True while a conversation window works or a card waits there."""
        ag = self.app.agent
        return ag is not None and any(w.kind == "chat" and w.busy() for w in list(ag.windows.values()))

    def order(self, uncarded):
        """The sources to do: important first (the rules), then newest first."""
        return [p for p, _ in sorted(uncarded, key=lambda r: (
            0 if important(r[0], (r[1] or "")[:10], self.rules) else 1, -_day_n(r[1]), r[0]))]

    def loop(self):
        quiet_since = time.time()
        while not self.stop_flag.is_set():
            if self.stop_flag.wait(2):
                return
            with self.lock:
                if self.state == "paused":
                    continue
            if self.busy_chat() or self.app.ingest_running():
                quiet_since = time.time()
                continue
            if time.time() - quiet_since < IDLE_GRACE:
                continue
            ag = self.app.agent
            if ag is None or ag.state != "ready":
                continue
            todo = self.todo()
            with self.lock:
                self.left = len(todo)
            if not todo:
                with self.lock:
                    self.state = "done"
                self.changed()
                continue
            self.one(todo[0])
            self.release_held()

    def todo(self):
        sys.path.insert(0, self.scripts)
        try:
            import kbconf
            import kbindex
            cfg = kbconf.load_library(self.lib["root"])
            ix = kbindex.open_index(self.lib["root"], cfg)
            try:
                rows = ix.uncarded()
            finally:
                ix.close()
        finally:
            sys.path.remove(self.scripts)
        held = {h["path"] for h in self.held}
        return [p for p in self.order(rows) if p not in held]

    def one(self, path):
        with self.lock:
            self.state, self.current = "working", path
        self.changed()
        work = os.path.join(self.work, "src")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        self.work_dir = work
        try:
            out = Run.script(self, "ingest.py", "backfill", "--library", self.lib["root"], "-o", work, "--source", path)
            batch = out.strip().split("\n")[-1]
            Run.script(self, "ingest.py", "topics", "--library", self.lib["root"], "--out", os.path.join(work, "topics.txt"))
            asker = Asker(self, self.id, "%s · %s" % (BACKFILL_TAB[self.lang], self.lib["label"]))
            asker.new()
            p = PROMPT[self.lang]
            cards = os.path.join(work, "cards.jsonl")
            extract = os.path.join(os.path.dirname(self.scripts), "references", "extract.md")
            asker.ask(p["cards"].format(n=self.written + 1, total=self.written + self.left, label=self.lib["label"],
                                        batch=batch, sid="S01", name=path.rsplit("/", 1)[-1], extract=extract,
                                        topics=os.path.join(work, "topics.txt"), out=cards))
            acc, rep = os.path.join(work, "accepted.jsonl"), os.path.join(work, "report.json")
            Run.script(self, "quote_check.py", "check", cards, batch, "--accepted", acc, "--report", rep,
                       "--topics", os.path.join(work, "topics.txt"), ok=(0, 3))
            report = read_json(rep, {}) or {}
            if not [x for x in read_lines(acc) if x.strip()]:
                self.note("%s: no card passed" % path)
                self.held.append({"path": path, "failed": True})
                return
            if report.get("new_topics"):
                keep = os.path.join(self.work, "held", "%d" % len(self.held))
                shutil.rmtree(keep, ignore_errors=True)
                shutil.copytree(work, keep)
                self.held.append({"path": path, "dir": keep, "batch": os.path.join(keep, os.path.basename(batch)),
                                  "new_topics": report["new_topics"]})
                self.note("%s: waits for decisions on %s" % (path, ", ".join(report["new_topics"])))
                self.write_pending()
                return
            self.write_cards(batch, acc)
        except Stopped as e:
            self.note("%s: %s" % (path, e))
        finally:
            with self.lock:
                if self.state == "working":
                    self.state = "idle"
                self.current = ""
            self.changed()

    def write_cards(self, batch, acc):
        Run.script(self, "ingest.py", "entities", acc, "--library", self.lib["root"], "--apply")
        out = json.loads(Run.script(self, "ingest.py", "add-cards", batch, "--cards", acc, "--library", self.lib["root"]))
        if out["topics"]:
            Run.script(self, "ingest.py", "pages", "--library", self.lib["root"], *sum([["--topic", t] for t in out["topics"]], []))
        with self.lock:
            self.written += len(out["sources"])

    def pending_name(self):
        return self.id

    def write_pending(self):
        topics = []
        for h in self.held:
            for t in h.get("new_topics", []):
                if t not in topics:
                    topics.append(t)
        rep = os.path.join(self.work, "pending-report.json")
        write_json(rep, {"new_topics": topics})
        dec = os.path.join(self.lib["root"], "_pending", self.pending_name() + ".decisions.json")
        if os.path.isfile(dec):
            return
        Run.script(self, "ingest.py", "pending", "write", "--library", self.lib["root"], "--run", self.pending_name(),
                   "--report", rep)

    def release_held(self):
        """Once the owner decided on the new topics, applies them and writes the held sources' cards."""
        dec = os.path.join(self.lib["root"], "_pending", self.pending_name() + ".decisions.json")
        if not self.held or not os.path.isfile(dec):
            return
        work = os.path.join(self.work, "decisions")
        out = json.loads(Run.script(self, "ingest.py", "pending", "read", "--library", self.lib["root"],
                                    "--run", self.pending_name(), "--work", work))
        if out["add_topics"]:
            Run.script(self, "ingest.py", "add-topic", "--library", self.lib["root"],
                       *sum([["--topic", t] for t in out["add_topics"]], []))
        for h in list(self.held):
            if h.get("failed"):
                continue
            acc = os.path.join(h["dir"], "accepted.jsonl")
            for old, new in out["retopic"].items():
                Run.script(self, "ingest.py", "retopic", acc, "--from", old, "--to", new)
            try:
                self.write_cards(h["batch"], acc)
            except RuntimeError as e:
                self.note("%s: %s" % (h["path"], e))
            self.held.remove(h)
        Run.script(self, "ingest.py", "pending", "done", "--library", self.lib["root"], "--run", self.pending_name())
        self.changed()


BACKFILL_TAB = {"en": "Cards", "zh": "补抽卡片"}


def _day_n(day):
    digits = re.sub(r"\D", "", day or "")[:8]
    return int(digits) if digits else 0
