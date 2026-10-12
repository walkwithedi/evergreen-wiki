#!/usr/bin/env python3
"""Plan and track intake of a large set of material in batches.

Before a large intake the assistant runs "plan" on the chosen folders or files. It lists
every file, sets aside what cannot be filed (unsupported types, files already in the
library by content hash, identical copies within the material) and cuts the rest into
batches: one batch per first-level subfolder, a subfolder over the limit split in file
name order, loose files of a chosen folder as a batch of their own, separately chosen
files as one more. A batch closes at --batch-files files or --batch-mb megabytes (defaults
from _kb.json intake). One batch means no batching: nothing is written.

With more than one batch the plan is saved as a JSON progress file (names.batch_plan,
default _intake-batches.json, in the library root for a local library). Later commands
read and update it, so a run can stop after any batch and go on in a new conversation.

Subcommands:
  plan    PATH [PATH ...] --plan FILE [--library-root DIR] [--index INDEX]
          [--batch-files N] [--batch-mb N] [--first GROUP ...] [--replace]
                                   inventory, batches and summary; writes FILE when > 1 batch
  status  --plan FILE              progress, pending summary work and the review list
  next    --plan FILE              the next pending batch: a header line, then "file: <path>" lines
  done    --plan FILE --batch N [--written N] [--duplicates N] [--review N]
  skip    --plan FILE --batch N    leave a batch out (its files stay where they are)
  add     --plan FILE --batch N --kind topic|entity|trigger|review --text TEXT [--file NAME]
                                   record work deferred to the final step, or an item to review
  finish  --plan FILE              mark the final step done; prints what was recorded and
                                   "result: archive the plan" or "result: keep the plan" (batches pending)
Exit codes: 0 ok; 1 next: no pending batch; 2 bad input or unreadable file;
3 plan: a plan with pending batches already exists (use status, or --replace).
Results go to stdout, logs to stderr.
"""
import argparse
import datetime
import hashlib
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402
import index_tool  # noqa: E402

log = logging.getLogger("batch_plan")
PLAN_SCHEMA = 1

# what intake can read, by extension (the converter's list first; see references/convert.md)
CONVERT_EXT = (".docx", ".pptx", ".xlsx", ".xlsm", ".pdf", ".eml")
LEGACY_EXT = (".doc", ".xls", ".ppt", ".msg", ".rtf", ".wps", ".et", ".dps")
TEXT_EXT = (".md", ".txt", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".log", ".yaml", ".yml")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".heic")
ARCHIVE_EXT = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz")
# files that are never material: editor lock files, system files
JUNK_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}
KINDS = ("topic", "entity", "trigger", "review")
LOOSE = "(loose files)"
CHOSEN = "(chosen files)"


def kind_of(name):
    n = name.lower()
    for kind, exts in (("convert", CONVERT_EXT), ("legacy", LEGACY_EXT), ("text", TEXT_EXT),
                       ("image", IMAGE_EXT)):
        if n.endswith(exts):
            return kind
    return "archive" if n.endswith(ARCHIVE_EXT) else "other"


def is_junk(name):
    return name.startswith((".", "~$")) or name.lower() in JUNK_NAMES


def inside(path, root):
    if not root:
        return False
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def file_hash(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()[:16]  # same form as index_tool's source hash


def now_text():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def scan(paths, library_root):
    """[(group, rel, abs path)] in a stable order; library files and junk left out."""
    found, seen = [], set()
    for p in paths:
        p = os.path.abspath(os.path.expanduser(p))
        if not os.path.exists(p):
            raise kbconf.ConfigError(f"path not found: {p}")
        if inside(p, library_root):
            log.warning("skipped, inside the library: %s", p)
            continue
        if os.path.isfile(p):
            if not is_junk(os.path.basename(p)) and p not in seen:
                seen.add(p)
                found.append((CHOSEN, os.path.basename(p), p))
            continue
        base = os.path.basename(p.rstrip(os.sep)) or p
        for dirpath, dirs, files in os.walk(p):
            dirs[:] = sorted(d for d in dirs if not is_junk(d)
                             and not inside(os.path.join(dirpath, d), library_root))
            for f in sorted(files):
                full = os.path.join(dirpath, f)
                if is_junk(f) or full in seen or not os.path.isfile(full):
                    continue
                seen.add(full)
                rel = os.path.relpath(full, p).replace(os.sep, "/")  # same plan text on every system
                parts = rel.split("/")
                group = f"{base}/{parts[0]}" if len(parts) > 1 else f"{base}/{LOOSE}"
                found.append((group, f"{base}/{rel}", full))
    return found


def index_hashes(index):
    if not index:
        return {}
    if not os.path.isfile(index):
        log.warning("index not found, no hash check against the library: %s", index)
        return {}
    lines, rows = index_tool.parse(index)
    return {r[4]: r[1] for r in rows if r[4]}


def cut(files, max_files, max_bytes):
    """Split one group's files into batches by count and size; a big file gets a batch alone."""
    batches, cur, size = [], [], 0
    for f in files:
        if cur and (len(cur) >= max_files or size + f["size"] > max_bytes):
            batches.append(cur)
            cur, size = [], 0
        cur.append(f)
        size += f["size"]
    if cur:
        batches.append(cur)
    return batches


def build(paths, library_root, index, max_files, max_mb, first):
    known = index_hashes(index)
    groups, order = {}, []
    excluded = {"duplicates": [], "unsupported": [], "unreadable": []}
    hashes = {}
    for group, rel, full in scan(paths, library_root):
        kind = kind_of(full)
        if kind in ("archive", "other"):
            reason = "archive: unpack it first" if kind == "archive" else "file type intake cannot read"
            excluded["unsupported"].append({"path": full, "rel": rel, "reason": reason})
            continue
        try:
            size = os.path.getsize(full)
            h = file_hash(full)
        except OSError as e:
            excluded["unreadable"].append({"path": full, "rel": rel, "reason": str(e)})
            continue
        if h in known:
            excluded["duplicates"].append({"path": full, "rel": rel, "reason": f"already in the library as {known[h]}"})
            continue
        if h in hashes:
            excluded["duplicates"].append({"path": full, "rel": rel, "reason": f"same content as {hashes[h]}"})
            continue
        hashes[h] = rel
        if group not in groups:
            groups[group] = []
            order.append(group)
        groups[group].append({"path": full, "rel": rel, "size": size, "kind": kind, "hash": h})

    def rank(g):
        for i, f in enumerate(first):
            if g == f or g.split("/", 1)[-1] == f:
                return i
        return len(first)
    order.sort(key=lambda g: (rank(g), g == CHOSEN, g.endswith(LOOSE), g))
    batches = []
    for g in order:
        parts = cut(groups[g], max_files, max_mb * 1024 * 1024)
        for i, files in enumerate(parts, 1):
            batches.append({"n": len(batches) + 1, "group": g,
                            "part": f"{i}/{len(parts)}" if len(parts) > 1 else "",
                            "files": files, "status": "pending", "result": {}, "finished": ""})
    return {"schema": PLAN_SCHEMA, "created": now_text(), "updated": now_text(),
            "sources": [os.path.abspath(os.path.expanduser(p)) for p in paths],
            "library_root": os.path.abspath(os.path.expanduser(library_root)) if library_root else "",
            "limits": {"batch_files": max_files, "batch_mb": max_mb},
            "batches": batches, "excluded": excluded,
            "deferred": [], "final_step": "pending"}


def mb(n):
    return f"{n / 1048576:.1f} MB"


def batch_label(b):
    return b["group"] + (f" part {b['part']}" if b["part"] else "")


def print_plan(plan):
    batches = plan["batches"]
    files = [f for b in batches for f in b["files"]]
    print(f"files to file: {len(files)} ({mb(sum(f['size'] for f in files))})")
    groups = {}
    for b in batches:
        g = groups.setdefault(b["group"], {"files": 0, "size": 0, "kinds": {}, "batches": 0})
        g["batches"] += 1
        for f in b["files"]:
            g["files"] += 1
            g["size"] += f["size"]
            g["kinds"][f["kind"]] = g["kinds"].get(f["kind"], 0) + 1
    for name, g in groups.items():
        kinds = ", ".join(f"{k} {n}" for k, n in sorted(g["kinds"].items()))
        print(f"group: {name} | files {g['files']} | {mb(g['size'])} | {kinds} | batches {g['batches']}")
    ex = plan["excluded"]
    for key in ("duplicates", "unsupported", "unreadable"):
        print(f"left out, {key}: {len(ex[key])}")
        for e in ex[key][:20]:
            print(f"  {e['rel']}: {e['reason']}")
        if len(ex[key]) > 20:
            print(f"  ... {len(ex[key]) - 20} more (in the plan file)")
    lim = plan["limits"]
    print(f"batches: {len(batches)} (at most {lim['batch_files']} files or {lim['batch_mb']} MB each)")
    for b in batches:
        print(f"batch {b['n']}: {batch_label(b)} | {len(b['files'])} files | {mb(sum(f['size'] for f in b['files']))} | {b['status']}")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            plan = json.load(f)
    except OSError as e:
        raise kbconf.ConfigError(f"cannot read the plan {path}: {e}")
    except json.JSONDecodeError as e:
        raise kbconf.ConfigError(f"the plan {path} is not valid JSON: {e}")
    if not isinstance(plan, dict) or plan.get("schema") != PLAN_SCHEMA:
        raise kbconf.ConfigError(f"{path} is not a batch plan of schema {PLAN_SCHEMA}")
    return plan


def save(path, plan):
    plan["updated"] = now_text()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, path)
    log.info("plan saved: %s", path)


def get_batch(plan, n):
    for b in plan["batches"]:
        if b["n"] == n:
            return b
    raise kbconf.ConfigError(f"no batch {n} in the plan (1 to {len(plan['batches'])})")


def pending(plan):
    return [b for b in plan["batches"] if b["status"] == "pending"]


def print_status(plan):
    bs = plan["batches"]
    done = [b for b in bs if b["status"] == "done"]
    skipped = [b for b in bs if b["status"] == "skipped"]
    left = pending(plan)
    print(f"batches: {len(bs)} | done {len(done)} | skipped {len(skipped)} | pending {len(left)}")
    files_done = sum(len(b["files"]) for b in done)
    files_left = sum(len(b["files"]) for b in left)
    print(f"files: done {files_done} | pending {files_left}")
    if left:
        print(f"next: batch {left[0]['n']} {batch_label(left[0])} ({len(left[0]['files'])} files)")
    print(f"final step: {plan['final_step']}")
    # items a final step already handled are kept in the file but no longer listed
    by_kind = {k: [d for d in plan["deferred"] if d["kind"] == k and not d.get("handled")] for k in KINDS}
    for k in KINDS:
        print(f"{k}: {len(by_kind[k])}")
        for d in by_kind[k]:
            name = f" [{d['file']}]" if d.get("file") else ""
            print(f"  batch {d['batch']}{name}: {d['text']}")


def cmd_plan(a):
    cfg = kbconf.load_library(a.library_root) if a.library_root else {}
    intake = cfg.get("intake", kbconf.INTAKE_DEFAULTS)
    max_files = a.batch_files or intake["batch_files"]
    max_mb = a.batch_mb or intake["batch_mb"]
    if max_files < 1 or max_mb < 1:
        raise kbconf.ConfigError("--batch-files and --batch-mb must be 1 or more")
    if os.path.exists(a.plan) and not a.replace:
        old = load(a.plan)
        if pending(old):
            print(f"existing plan: {a.plan}")
            print_status(old)
            print("result: a plan with pending batches exists; continue it, or pass --replace to start over")
            return 3
    plan = build(a.paths, a.library_root, a.index, max_files, max_mb, a.first or [])
    print_plan(plan)
    if not plan["batches"]:
        print("result: nothing to file")
    elif len(plan["batches"]) == 1:
        print("result: one batch, no batching needed; file it as usual (no plan written)")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(a.plan)), exist_ok=True)
        save(a.plan, plan)
        print(f"result: plan written to {a.plan}")
    return 0


def cmd_status(a):
    print_status(load(a.plan))
    return 0


def cmd_next(a):
    plan = load(a.plan)
    left = pending(plan)
    if not left:
        print(f"result: no pending batch; final step {plan['final_step']}")
        return 1
    b = left[0]
    print(f"batch: {b['n']}/{len(plan['batches'])} | {batch_label(b)} | {len(b['files'])} files")
    for f in b["files"]:
        if os.path.isfile(f["path"]):
            print(f"file: {f['path']}")
        else:
            print(f"missing: {f['path']}")
    return 0


def cmd_done(a, status="done"):
    plan = load(a.plan)
    b = get_batch(plan, a.batch)
    b["status"] = status
    b["finished"] = now_text()
    if status == "done":
        b["result"] = {"written": a.written, "duplicates": a.duplicates, "review": a.review}
        plan["final_step"] = "pending"  # new material since a "finish intake": the summary step is due again
    save(a.plan, plan)
    left = pending(plan)
    print(f"batch {b['n']}: {status} | pending {len(left)}")
    return 0


def cmd_add(a):
    plan = load(a.plan)
    get_batch(plan, a.batch)
    text = " ".join(a.text.split())
    if not text:
        raise kbconf.ConfigError("--text is empty")
    plan["deferred"].append({"batch": a.batch, "kind": a.kind, "text": text, "file": a.file or ""})
    save(a.plan, plan)
    print(f"recorded: {a.kind}, batch {a.batch}")
    return 0


def cmd_finish(a):
    plan = load(a.plan)
    left = pending(plan)
    if left:
        print(f"warning: {len(left)} batches still pending; they stay in the plan")
    plan["final_step"] = "done"
    print_status(plan)
    for d in plan["deferred"]:
        d["handled"] = True
    save(a.plan, plan)
    print("result: keep the plan (batches pending)" if left else "result: archive the plan")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("paths", nargs="+")
    p.add_argument("--plan", required=True)
    p.add_argument("--library-root")
    p.add_argument("--index", help="the library's file index, for the content-hash check")
    p.add_argument("--batch-files", type=int)
    p.add_argument("--batch-mb", type=int)
    p.add_argument("--first", action="append", help="group to put first (repeatable, in this order)")
    p.add_argument("--replace", action="store_true")
    for c in ("status", "next", "finish"):
        sub.add_parser(c).add_argument("--plan", required=True)
    for c in ("done", "skip"):
        p = sub.add_parser(c)
        p.add_argument("--plan", required=True)
        p.add_argument("--batch", type=int, required=True)
        if c == "done":
            for k in ("written", "duplicates", "review"):
                p.add_argument(f"--{k}", type=int, default=0)
    p = sub.add_parser("add")
    p.add_argument("--plan", required=True)
    p.add_argument("--batch", type=int, required=True)
    p.add_argument("--kind", choices=KINDS, required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--file")
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    handlers = {"plan": cmd_plan, "status": cmd_status, "next": cmd_next, "done": cmd_done,
                "skip": lambda x: cmd_done(x, "skipped"), "add": cmd_add, "finish": cmd_finish}
    try:
        sys.exit(handlers[a.cmd](a))
    except kbconf.ConfigError as e:
        log.error("%s", e)
        print(f"error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
