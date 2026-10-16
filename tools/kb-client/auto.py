"""Unattended intake for local libraries: a library switched to automatic intake gets a drop folder at its
top (_Inbox, or _待入库 when the switch was turned on in Chinese; the underscore keeps it out of every
search), and the client files what is put there without anybody on the page.

  - The drop folders are looked at every POLL seconds. A file is taken once its size and time have not
    changed for SETTLE seconds, so that one still being copied waits. Hidden names and the folder's own
    two subfolders are left out.
  - A run starts only when nothing else is going: no intake run, no step, OpenCode ready and idle with no
    card waiting. OpenCode is started when it is not running yet. One library at a time, at most
    intake.MAX_FILES files a run.
  - The run is intake.Run with Allow everything switched on for its length: the files, then the
    consolidation queue, unattended. Allow everything goes back to off at the end when the run switched it
    on; switching it off during the run stops the run.
  - Each file is cleared from the drop folder as soon as it is done: written with its original copied into
    the library's sources folder, or a duplicate upload: removed; written without a copy there (the library
    keeps no originals, or the file is larger than the limit): moved to the Filed subfolder; a file that
    needs a person or failed: moved to the Not-filed subfolder, never tried again. A file left waiting (the
    run was stopped) stays where it is.
  - With no new file, a library whose consolidation queue still has files gets a consolidation-only run,
    until one ends without finishing (stuck, failed or stopped); new files lift that.
  - A run stopped by a person (Stop, or Allow everything switched off) pauses the library until a file
    that run did not have arrives, or the switch is turned off and on.

The switches, the folders and each library's last run (counts, time, log) are kept in
<state dir>/auto-intake.json, never in the library. Standard library only.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time

import intake as intake_mod

log = logging.getLogger("kb_client.auto")

# The times can be shortened for tests through the environment.
POLL = max(1, int(os.environ.get("KB_CLIENT_AUTO_POLL") or 60))  # seconds between looks at the drop folders
SETTLE = max(0, int(os.environ.get("KB_CLIENT_AUTO_SETTLE") or 120))  # seconds a file must stay unchanged
TICK = min(5, POLL)  # how often the watcher wakes (also to see Allow everything switched off)
SETTINGS = "auto-intake.json"
# drop folder, files that need a person, files written whose original the library does not keep
FOLDERS = {"en": ("_Inbox", "Not-filed", "Filed"), "zh": ("_待入库", "未处理", "已入库")}


class Settings:
    """auto-intake.json: {"libraries": {id: {"on", "inbox", "not_filed", "filed", "last"}}}."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            libs = data.get("libraries") if isinstance(data, dict) else None
        except (OSError, ValueError):
            libs = None
        self.libs = {str(k): v for k, v in libs.items() if isinstance(v, dict)} if isinstance(libs, dict) else {}

    def save(self):
        with self.lock:
            data = json.dumps({"libraries": self.libs}, ensure_ascii=False, indent=1)
        try:
            os.makedirs(os.path.dirname(self.path), mode=0o700, exist_ok=True)
            fd = os.open(self.path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(self.path + ".tmp", self.path)
        except OSError as e:
            log.warning("automatic intake settings not saved: %s", e)

    def get(self, lib_id):
        with self.lock:
            return dict(self.libs.get(lib_id) or {})

    def update(self, lib_id, **kw):
        with self.lock:
            self.libs.setdefault(lib_id, {}).update(kw)
        self.save()


def folders_for(root, lang):
    inbox, not_filed, filed = FOLDERS.get(lang, FOLDERS["en"])
    top = os.path.join(root, inbox)
    return {"inbox": top, "not_filed": os.path.join(top, not_filed), "filed": os.path.join(top, filed)}


def inbox_files(entry):
    """The files in a drop folder (subfolders walked, hidden names and its two subfolders left out), with
    (size, mtime); at most intake.MAX_FILES."""
    out = {}
    skip = {os.path.realpath(entry.get("not_filed", "")), os.path.realpath(entry.get("filed", ""))}
    for here, dirs, files in os.walk(entry["inbox"]):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and os.path.realpath(os.path.join(here, d)) not in skip)
        for f in sorted(files):
            if f.startswith("."):
                continue
            p = os.path.join(here, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out[p] = (st.st_size, st.st_mtime)
            if len(out) >= intake_mod.MAX_FILES:
                return out
    return out


def count_files(folder):
    try:
        return sum(1 for _, _, files in os.walk(folder) for f in files if not f.startswith("."))
    except OSError:
        return 0


def free_name(folder, name):
    """name in folder, or "stem (2).ext" and on when it is taken."""
    stem, ext = os.path.splitext(name)
    path, n = os.path.join(folder, name), 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{stem} ({n}){ext}")
        n += 1
    return path


def clear_item(item, entry):
    """Takes a finished file out of the drop folder (see the module text); returns (what was done:
    removed, filed, not_filed, or "" when the file stays; where it went, or "")."""
    src, status = item["source"], item["status"]
    if status == "duplicate" or (status == "written" and item.get("kept")):
        os.remove(src)
        return "removed", ""
    if status in ("written", "manual", "failed"):
        key = "filed" if status == "written" else "not_filed"
        os.makedirs(entry[key], exist_ok=True)
        dest = free_name(entry[key], os.path.basename(src))
        shutil.move(src, dest)
        return key, dest
    return "", ""


def queue_waiting(scripts, root, queue_name):
    """True when the library's consolidation queue has files (consolidate.py list); False when it has none
    or cannot be read."""
    queue = os.path.join(root, queue_name)
    if not os.path.isfile(queue):
        return False
    try:
        p = subprocess.run([sys.executable, os.path.join(scripts, "consolidate.py"), "list", queue, "--limit", "1"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                           errors="replace", timeout=60, stdin=subprocess.DEVNULL,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    except (OSError, subprocess.TimeoutExpired):
        return False
    for ln in p.stdout.split("\n"):
        if p.returncode == 0 and ln.startswith("queue: "):
            try:
                return int(ln.split()[1]) > 0
            except (IndexError, ValueError):
                return False
    return False


class Watcher:
    """The thread that looks at the drop folders and starts the runs. app is the kb_client.App: its
    libraries, its agent, its current intake run and start_intake."""

    def __init__(self, app, state_dir, lang):
        self.app = app
        self.lang = lang if lang in FOLDERS else "en"
        self.settings = Settings(os.path.join(state_dir, SETTINGS))
        self.seen = {}  # path -> (size, mtime, unchanged since)
        self.paused = {}  # library id -> the files of a run a person stopped
        self.cons_done = set()  # libraries whose consolidation-only run ended without finishing
        self.run = None  # the automatic run going on
        self.turned_on = False  # whether that run switched Allow everything on
        self.last_look = 0.0
        self.thread = None
        self.stopping = threading.Event()

    # ----- the switch -----

    def on_libraries(self, libs):
        """The local libraries (kb_client.libraries()) switched on that exist on this computer."""
        return [lib for lib in libs if lib["root"] and lib["exists"] and self.settings.get(lib["id"]).get("on")]

    def any_on(self, libs):
        return bool(self.on_libraries(libs))

    def switch(self, lib, on):
        """Turns automatic intake on or off for a local library; making its drop folders when it is turned
        on (an earlier library's folders are kept). Returns its state for the page."""
        entry = self.settings.get(lib["id"])
        if on:
            if not entry.get("inbox") or not os.path.realpath(entry["inbox"]).startswith(os.path.realpath(lib["root"]) + os.sep):
                entry.update(folders_for(lib["root"], self.lang))
            for key in ("inbox", "not_filed"):
                os.makedirs(entry[key], exist_ok=True)
        self.paused.pop(lib["id"], None)
        self.cons_done.discard(lib["id"])
        self.settings.update(lib["id"], on=bool(on), inbox=entry.get("inbox", ""), not_filed=entry.get("not_filed", ""),
                             filed=entry.get("filed", ""))
        log.info("automatic intake %s for %s (%s)", "on" if on else "off", lib["id"], entry.get("inbox", ""))
        return self.lib_state(lib)

    def lib_state(self, lib):
        """What a library card shows: {on, inbox, not_filed, waiting (files in the drop folder), manual
        (files in Not-filed), last}."""
        e = self.settings.get(lib["id"])
        if not e:
            return {"on": False}
        waiting = len(inbox_files(e)) if e.get("on") and os.path.isdir(e.get("inbox", "")) else 0
        return {"on": bool(e.get("on")), "inbox": e.get("inbox", ""), "not_filed": e.get("not_filed", ""),
                "waiting": waiting, "manual": count_files(e.get("not_filed", "")), "last": e.get("last") or None}

    # ----- the thread -----

    def start(self):
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while not self.stopping.wait(TICK):
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - the watcher keeps going; the log says what happened
                log.exception("automatic intake")

    def tick(self):
        run = self.run
        if run is not None and run.running():
            ag = run.agent
            if run.state == "running" and ag is not None and not ag.allow_all:
                run.note("Allow everything was switched off: the automatic run stops")
                log.info("automatic intake %s: Allow everything switched off, stopping", run.id)
                run.stop()
            return
        now = time.time()
        if now - self.last_look < POLL:
            return
        self.last_look = now
        app = self.app
        libs = self.on_libraries(app.libraries())
        ready = {}
        current = set()
        for lib in libs:
            entry = self.settings.get(lib["id"])
            if not os.path.isdir(entry.get("inbox", "")):
                continue
            files = inbox_files(entry)
            for p, sig in files.items():
                current.add(p)
                old = self.seen.get(p)
                if old is None or old[:2] != sig:
                    self.seen[p] = (sig[0], sig[1], now)
                elif now - old[2] >= SETTLE:
                    ready.setdefault(lib["id"], []).append(p)
        for p in list(self.seen):
            if p not in current:
                del self.seen[p]
        if not libs or not app.idle_for_intake():
            return
        ag = app.agent
        if ag is None:
            if ready or any(lib["id"] not in self.cons_done for lib in libs):
                log.info("automatic intake: starting OpenCode")
                app.start_agent()
            return
        if ag.state != "ready" or ag.status != "idle" or ag.questions or ag.permissions:
            return
        for lib in libs:
            files = ready.get(lib["id"]) or []
            stopped = self.paused.get(lib["id"])
            if stopped is not None:
                if not set(files) - stopped:
                    continue
                del self.paused[lib["id"]]
            if files:
                self.cons_done.discard(lib["id"])
                self.begin(lib, files)
                return
        for lib in libs:
            if lib["id"] in self.cons_done or lib["id"] in self.paused:
                continue
            scripts = app.intake_scripts()
            if scripts and queue_waiting(scripts, lib["root"], app.queue_name(lib["root"])):
                self.begin(lib, [])
                return
            self.cons_done.add(lib["id"])  # nothing to do until new files come

    def begin(self, lib, files):
        ag = self.app.agent
        self.turned_on = not ag.allow_all
        if self.turned_on:
            ag.set_allow_all(True)
        run, why = self.app.start_intake(lib["id"], [], auto={"sources": files[:intake_mod.MAX_FILES],
                                                              "item_done": self.item_done, "ended": self.ended})
        if run is None:
            log.info("automatic intake for %s not started: %s", lib["id"], why)
            self.restore_allow_all(ag)
            return
        self.run = run
        run.note(f"automatic intake from {self.settings.get(lib['id']).get('inbox')}: {len(files)} files")
        log.info("automatic intake %s: %d files into %s", run.id, len(files), lib["id"])

    def restore_allow_all(self, ag):
        if self.turned_on and ag is not None and ag.allow_all:
            ag.set_allow_all(False)
        self.turned_on = False

    # ----- what a run reports -----

    def item_done(self, run, item):
        entry = self.settings.get(run.lib["id"])
        try:
            what, dest = clear_item(item, entry)
        except OSError as e:
            run.note(f"item {item['n']} not cleared from the drop folder: {e}")
            return
        if what:
            run.note(f"item {item['n']} {item['file']}: {what.replace('_', ' ')}")
            self.seen.pop(item["source"], None)
        if dest:
            run.set(item, source=dest)  # the panel hands a file that needs a person over from where it is now

    def ended(self, run):
        self.restore_allow_all(run.agent)
        snap = run.snapshot()
        c, cons = snap["counts"], snap["consolidation"]
        last = {"at": time.strftime("%Y-%m-%d %H:%M"), "state": snap["state"], "written": c.get("written", 0),
                "duplicate": c.get("duplicate", 0), "not_filed": c.get("manual", 0) + c.get("failed", 0),
                "waiting": c.get("waiting", 0), "consolidation": cons.get("state", ""),
                "consolidated": cons.get("files", 0), "reason": cons.get("reason", ""), "log": snap["log"]}
        self.settings.update(run.lib["id"], last=last)
        if snap["state"] == "stopped":
            self.paused[run.lib["id"]] = {it["source"] for it in snap["items"]}
        if cons.get("state") != "done":
            self.cons_done.add(run.lib["id"])
        self.last_look = 0.0  # look again at once: more files may be waiting
        log.info("automatic intake %s %s: %s", run.id, snap["state"], json.dumps(last, ensure_ascii=False))
