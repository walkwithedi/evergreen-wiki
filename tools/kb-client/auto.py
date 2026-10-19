"""Automatic ingest: documents put in a library's drop folder are ingested by the client without asking.

A library with automatic ingest switched on has a drop folder in its root, _Drop (_待入库 in a Chinese
library); its name starts with an underscore, so the skills and the index skip it. Once the documents
there have not changed for STABLE seconds, the assistant is free and no other run goes on, they move to
a staging folder of the client's own and a run (ingest_run.Run) ingests them, every one of them with
cards, in windows where Allow everything is on and questions take their recommended answer. Decisions
the owner must take (new topics, new versions under another name, conflicts) still wait on the page.
When the run is done the documents move to _Filed/<date> (_已入库) and the ones that gave no source to
_Not filed (_未处理), both in the library root. While a library has it switched on, the client does not
stop when its page is closed.

Settings: <state dir>/auto/settings.json, {library id: true}. Python 3 standard library only.
"""
import json
import logging
import os
import shutil
import threading
import time

import ingest_run

log = logging.getLogger("kb_client.auto")

STABLE = int(os.environ.get("KB_AUTO_STABLE", "120"))  # seconds the drop folder must stay unchanged
TICK = 5
FOLDERS = {"en": ("_Drop", "_Filed", "_Not filed"), "zh": ("_待入库", "_已入库", "_未处理")}


def folders_for(root, lang):
    """(drop folder, filed folder, not-filed folder) of a library."""
    drop, filed, missing = FOLDERS["zh" if str(lang).startswith("zh") else "en"]
    return os.path.join(root, drop), os.path.join(root, filed), os.path.join(root, missing)


def drop_files(drop):
    """{path below the drop folder: (size, mtime)} of the documents in it."""
    out = {}
    for here, dirs, names in os.walk(drop):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for n in names:
            if n.startswith((".", "~$")) or not n.lower().endswith(ingest_run.MATERIAL_EXT):
                continue
            p = os.path.join(here, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out[os.path.relpath(p, drop)] = (st.st_size, st.st_mtime)
    return out


def free_path(path):
    base, ext = os.path.splitext(path)
    k = 1
    while os.path.exists(path):
        k += 1
        path = "%s (%d)%s" % (base, k, ext)
    return path


class Watcher:
    def __init__(self, app, state_dir):
        self.app = app
        self.folder = os.path.join(state_dir, "auto")
        self.settings_path = os.path.join(self.folder, "settings.json")
        self.seen = {}  # library id -> (files, since)
        self.runs = {}  # run id -> (library, staging folder, files)
        self.last = {}  # library id -> what the last automatic run did
        self.stop_flag = threading.Event()
        self.thread = None

    def settings(self):
        data = ingest_run.read_json(self.settings_path, {})
        return {k: bool(v) for k, v in data.items()} if isinstance(data, dict) else {}

    def any_on(self):
        return any(self.settings().values())

    def switch(self, lib, on):
        """Switches automatic ingest of a library; makes its drop folder when switched on."""
        s = self.settings()
        s[lib["id"]] = bool(on)
        os.makedirs(self.folder, exist_ok=True)
        ingest_run.write_json(self.settings_path, s)
        if on:
            os.makedirs(folders_for(lib["root"], self.lang_of(lib))[0], exist_ok=True)
        return self.state(lib)

    def lang_of(self, lib):
        cfg = ingest_run.read_json(os.path.join(lib["root"], "_kb.json"), {}) or {}
        return str(cfg.get("language", "en"))

    def state(self, lib):
        drop = folders_for(lib["root"], self.lang_of(lib))
        return {"on": self.settings().get(lib["id"], False), "drop": drop[0], "filed": drop[1], "not_filed": drop[2],
                "waiting": len(drop_files(drop[0])) if os.path.isdir(drop[0]) else 0,
                "last": self.last.get(lib["id"])}

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()

    def loop(self):
        while not self.stop_flag.wait(TICK):
            try:
                self.tick()
            except Exception:  # noqa: BLE001 - the watcher keeps going; the log says what happened
                log.exception("automatic ingest")

    def tick(self):
        self.finish()
        app = self.app
        ag = app.agent
        for lib_id, on in self.settings().items():
            if not on:
                continue
            lib = app.local_library(lib_id)
            if lib is None:
                continue
            drop = folders_for(lib["root"], self.lang_of(lib))[0]
            files = drop_files(drop) if os.path.isdir(drop) else {}
            if not files:
                self.seen.pop(lib_id, None)
                continue
            before = self.seen.get(lib_id)
            if before is None or before[0] != files:
                self.seen[lib_id] = (files, time.time())
                continue
            if time.time() - before[1] < STABLE or app.ingest_running() or ag is None or ag.state != "ready":
                continue
            if any(w.kind == "chat" and w.busy() for w in list(ag.windows.values())):
                continue
            self.begin(lib, drop, files)
            return

    def begin(self, lib, drop, files):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        staging = os.path.join(self.folder, lib["id"], stamp)
        for rel in files:
            dest = os.path.join(staging, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(os.path.join(drop, rel), dest)
        for here, dirs, names in os.walk(drop, topdown=False):   # the folders emptied by the move
            if here != drop and not os.listdir(here):
                os.rmdir(here)
        self.seen.pop(lib["id"], None)
        log.info("automatic ingest of %d documents into %s", len(files), lib["id"])
        run, why = self.app.start_ingest({"library": lib["id"], "material": staging, "rules": {"folders": []},
                                          "unattended": True})
        if run is None:
            log.warning("automatic ingest of %s not started: %s; the documents go back", lib["id"], why)
            self.put_back(staging, drop)
            return
        self.runs[run.id] = (lib, staging, list(files))

    def put_back(self, staging, drop):
        for here, _, names in os.walk(staging):
            for n in names:
                p = os.path.join(here, n)
                dest = free_path(os.path.join(drop, os.path.relpath(p, staging)))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(p, dest)
        shutil.rmtree(staging, ignore_errors=True)

    def finish(self):
        """Moves the documents of finished automatic runs out of the staging folder."""
        run = self.app.ingest
        if run is None or run.id not in self.runs or run.running():
            return
        lib, staging, files = self.runs.pop(run.id)
        if run.state != "done":
            self.put_back(staging, folders_for(lib["root"], self.lang_of(lib))[0])
            self.last[lib["id"]] = {"at": time.strftime("%Y-%m-%d %H:%M"), "state": run.state, "files": len(files)}
            return
        _, filed, not_filed = folders_for(lib["root"], self.lang_of(lib))
        missing = {m["rel"] for m in run.missing}
        day = time.strftime("%Y%m%d")
        for rel in files:
            src = os.path.join(staging, rel)
            if not os.path.exists(src):
                continue
            dest = free_path(os.path.join(not_filed if rel.replace(os.sep, "/") in missing else os.path.join(filed, day), rel))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(src, dest)
        shutil.rmtree(staging, ignore_errors=True)
        self.last[lib["id"]] = {"at": time.strftime("%Y-%m-%d %H:%M"), "state": "done", "files": len(files),
                                "not_filed": len(missing), "counts": run.snapshot()["counts"]}
        log.info("automatic ingest of %s done: %s", lib["id"], json.dumps(self.last[lib["id"]]))
