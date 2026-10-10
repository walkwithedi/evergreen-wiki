#!/usr/bin/env python3
"""Archive older copies of same-name files: preview, local execution and run log.

Rule: inside one folder, files with exactly the same .md name are versions of one
document. The newest (by modified time) stays; every older copy moves to the archive
folder and is renamed  <stem><old_suffix><YYYYMMDDHHMMSS><ext>  (one second apart).
Nothing is ever deleted.

Used by the Drive backend, where several files may share one name. A local folder
cannot hold two files with the same name, so the local backend archives the old version
at delivery time instead (package.py deliver), with the same naming and log format.

Subcommands:
  plan   --files candidates.json --base-time "YYYY-MM-DD HH:MM:SS" --folder-name NAME
         --scope TEXT --out plan.json
         Group by (folder, name); conflicts (equal modified times, or modified-time and
         created-time disagree on the newest) are reported and left alone.
  log    --plan plan.json --results results.json --end-time "YYYY-MM-DD HH:MM:SS" --out log.txt
         Write the run log and print the log file name to store in the archive folder.

Common options: --tz (IANA name or +HH:MM, from _kb.json "timezone"), --old-suffix,
--snapshot-prefix, --log-prefix (names.old_suffix / snapshot_prefix / run_log_prefix).
The assistant performs the moves itself and writes results.json ({"id": "ok" or error}).
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("archive")
TZ = timezone.utc


def parse_ts(s):
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def short(dt):
    return dt.strftime("%m-%d %H:%M")


def size_text(v):
    return "unknown" if v is None else str(v)


def size_note(same):
    if same is None:
        return "  size unknown (search result had no fileSize)"
    return "  same size (possibly a repeated upload)" if same else "  different size (content likely differs)"


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.error("cannot read JSON %s: %s", path, e)
        sys.exit(2)


def dump_json(obj, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def cmd_plan(a):
    files = load_json(a.files)
    if isinstance(files, dict) and "files" in files:
        files = files["files"]
    log.info("read %d candidate files", len(files))
    base = datetime.strptime(a.base_time, "%Y-%m-%d %H:%M:%S")
    groups, skipped = {}, 0
    for f in files:
        t = f.get("title", "")
        if not t.lower().endswith(".md"):
            log.debug("skip non-.md: %s", t); skipped += 1; continue
        if a.old_suffix in t or t.startswith(a.snapshot_prefix) or t.startswith("_"):
            log.warning("file that should not be in the main folder, skipped: %s", t); skipped += 1; continue
        groups.setdefault((f.get("parentId", ""), t), {})[f["id"]] = f
    log.info("%d distinct .md names, %d skipped", len(groups), skipped)

    items, conflicts, seq = [], [], 0
    folders = sorted({k[0] for k in groups})
    for key in sorted(groups):
        parent, title = key
        fs = list(groups[key].values())
        if len(fs) < 2:
            continue
        by_mod = sorted(fs, key=lambda f: parse_ts(f["modifiedTime"]), reverse=True)
        by_cre = sorted(fs, key=lambda f: parse_ts(f["createdTime"]), reverse=True)
        keep = by_mod[0]
        reason = None
        if parse_ts(by_mod[0]["modifiedTime"]) == parse_ts(by_mod[1]["modifiedTime"]):
            reason = "the two newest copies have the same modified time"
        elif by_cre[0]["id"] != keep["id"]:
            reason = "newest by modified time and newest by created time differ (an upload tool may have kept local times)"
        if reason:
            log.warning("conflict: %s: %s", title, reason)
            conflicts.append({"title": title, "parent": parent, "reason": reason, "files": fs})
            continue
        group = {"title": title, "parent": parent, "keep": keep, "archive": []}
        for f in by_mod[1:]:
            stamp = (base + timedelta(seconds=seq)).strftime("%Y%m%d%H%M%S")
            seq += 1
            stem, ext = os.path.splitext(title)
            new_title = f"{stem}{a.old_suffix}{stamp}{ext}"
            a_size, k_size = f.get("fileSize"), keep.get("fileSize")
            same = None if a_size is None or k_size is None else str(a_size) == str(k_size)
            group["archive"].append(dict(f, new_title=new_title, same_size=same))
            log.info("to archive: %s (id=%s) -> %s", title, f["id"], new_title)
        items.append(group)

    plan = {"folder_name": a.folder_name, "scope": a.scope, "base_time": a.base_time,
            "candidate_count": len(files), "groups": items, "conflicts": conflicts}
    dump_json(plan, a.out)
    log.info("plan written: %s", a.out)

    n_arch = sum(len(g["archive"]) for g in items)
    print("=== Preview ===")
    print(f"Library: {a.folder_name}")
    print(f"Time: {a.base_time}")
    print(f"Scope: {a.scope}")
    print(f".md names checked: {len(groups)}")
    print(f"Names with several copies: {len(items) + len(conflicts)}")
    print(f"Older copies to archive: {n_arch}")
    print()
    for k, g in enumerate(items, 1):
        kp = g["keep"]
        print(f"{k}. {g['title']}" + (f" (folder {g['parent']})" if len(folders) > 1 else ""))
        print(f"  keep    | modified {short(parse_ts(kp['modifiedTime']))} | {size_text(kp.get('fileSize'))} bytes | id={kp['id']}")
        for f in g["archive"]:
            print(f"  archive | modified {short(parse_ts(f['modifiedTime']))} | {size_text(f.get('fileSize'))} bytes | id={f['id']} -> {f['new_title']}")
            print(size_note(f["same_size"]))
    if conflicts:
        print()
        print("Needs a human decision (not handled this time):")
        for c in conflicts:
            print(f"  {c['title']}: {c['reason']}")
            for f in c["files"]:
                print(f"    modified {short(parse_ts(f['modifiedTime']))} | created {short(parse_ts(f['createdTime']))} | {size_text(f.get('fileSize'))} bytes | id={f['id']}")
    if n_arch == 0 and not conflicts:
        print("No same-name copies; nothing to archive.")


def cmd_log(a):
    plan = load_json(a.plan)
    results = load_json(a.results)
    end = datetime.strptime(a.end_time, "%Y-%m-%d %H:%M:%S")
    lines = ["=== Run ===", f"Library: {plan['folder_name']}", f"Time: {plan['base_time']}", "",
             f"Scope: {plan['scope']}"]
    groups = plan["groups"]
    n_arch = sum(len(g["archive"]) for g in groups)
    lines += [f"Names with several copies: {len(groups) + len(plan['conflicts'])}",
              f"Older copies to archive: {n_arch}", ""]
    ok = fail = 0
    for k, g in enumerate(groups, 1):
        kp = g["keep"]
        lines.append(f"{k}. {g['title']}")
        lines.append(f"  keep    | modified {short(parse_ts(kp['modifiedTime']))} | {size_text(kp.get('fileSize'))} bytes | id={kp['id']}")
        for f in g["archive"]:
            r = results.get(f["id"])
            if r == "ok":
                ok += 1
                lines.append(f"  archive | modified {short(parse_ts(f['modifiedTime']))} | {size_text(f.get('fileSize'))} bytes | id={f['id']} -> {f['new_title']}")
            else:
                fail += 1
                lines.append(f"  failed  | id={f['id']} | {r or 'not executed'}")
                log.error("archive failed: %s id=%s: %s", g["title"], f["id"], r or "not executed")
            lines.append(size_note(f["same_size"]))
    for c in plan["conflicts"]:
        lines.append(f"Needs a human decision (not handled): {c['title']}: {c['reason']}")
    lines += ["", f"Archived {ok}, failed {fail}.", "", "=== End ==="]
    with open(a.out, "w", encoding="utf-8", newline="\n") as fo:
        fo.write("\n".join(lines) + "\n")
    name = f"{a.log_prefix}{end.strftime('%Y%m%d_%H%M%S')}.txt"
    log.info("log written: %s (store it in the archive folder as %s)", a.out, name)
    print(f"Log file name: {name}")
    print(f"Archived {ok}, failed {fail}.")


def main():
    global TZ
    names = kbconf.DEFAULT_NAMES
    ap = argparse.ArgumentParser(description="Archive older same-name copies")
    ap.add_argument("-v", "--verbose", action="store_true", help="same as --log-level DEBUG")
    kbconf.add_log_args(ap)
    ap.add_argument("--tz", default="UTC", help="library timezone: IANA name or +HH:MM")
    ap.add_argument("--old-suffix", default=names["old_suffix"])
    ap.add_argument("--snapshot-prefix", default=names["snapshot_prefix"])
    ap.add_argument("--log-prefix", default=names["run_log_prefix"])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--files", required=True); p.add_argument("--base-time", required=True)
    p.add_argument("--folder-name", required=True); p.add_argument("--scope", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("log")
    p.add_argument("--plan", required=True); p.add_argument("--results", required=True)
    p.add_argument("--end-time", required=True); p.add_argument("--out", required=True)
    a = ap.parse_args()
    kbconf.setup_logging("DEBUG" if a.verbose else a.log_level)
    try:
        TZ = kbconf.tzinfo(a.tz)
    except kbconf.ConfigError as e:
        log.error("%s", e)
        sys.exit(2)
    log.info("subcommand: %s, timezone %s", a.cmd, a.tz)
    {"plan": cmd_plan, "log": cmd_log}[a.cmd](a)


if __name__ == "__main__":
    main()
