#!/usr/bin/env python3
"""Check and deliver the output of an intake run.

Output directory layout (the only accepted shape):
  OUT/*.md, OUT/README.txt        knowledge files, summary files and the readme
  OUT/<entities_dir>/*.md         entity pages (optional, no deeper folders)
  OUT/<sources_dir>/*             copies of originals, any format, named after their topic files
                                  (optional, preview and deliver only: a local library that keeps
                                  originals; zip and the Drive preview refuse the folder)

When a topic file gets a new version, the originals kept for its old version (<sources_dir>/<stem>.*)
move to the archive folder with it, unless the run delivers a copy under exactly the same name,
which is archived the usual way.

Subcommands:
  zip      OUT DEST.zip --library LIB
           Drive backend: check the output and pack it into one zip for the user to upload.
  preview  OUT --library LIB --plan plan.json
           Local backend, round 1: list what will be written and which existing files will
           move to the archive folder. Nothing is changed.
  deliver  --plan plan.json
           Local backend, round 2 (after the user confirms): re-check every target, archive
           the old version (<stem><old_suffix><YYYYMMDDHHMMSS><ext>), copy the new one in,
           keep the readme in the archive folder and write a run log there.
  remote-preview OUT --library KB_JSON --existing existing.json --plan plan.json
           Drive backend, round 1: the same preview for a library this script cannot reach.
           existing.json lists the copies already in the library with each output name:
           [{"rel": "<name or entities_dir/name>", "id": "<file id>", "modified": "<time>"}].
           The plan says, for each file, which copies move to the archive folder under which
           name, and then which file to write; the assistant carries it out with the connector.
  remote-log --plan plan.json --results results.json
           Drive backend, round 2: print the run log (and its file name) from the results
           {"<rel>": "ok" | "<error>"}, for the assistant to write into the archive folder.

LIB is the library root (or its _kb.json); every name comes from its "names", the time
stamps from its "timezone" and the file name limit from --max-name-len (Table D).
Results on stdout, logs on stderr. Exit codes: 0 ok, 2 bad input, 3 check failed, 4 I/O error.
"""
import argparse
import json
import logging
import os
import shutil
import sys
import zipfile
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("package")


def check_output(out, names, max_len, allow_sources=False):
    """Return (files, errors). files = list of (relative path, absolute path)."""
    errors, files = [], []
    if not os.path.isdir(out):
        return [], [f"output directory not found: {out}"]
    ent, src = names["entities_dir"], names["sources_dir"]
    for entry in sorted(os.listdir(out)):
        p = os.path.join(out, entry)
        if os.path.isdir(p):
            if entry == src and not allow_sources:
                errors.append(f"{src}/ (originals) is delivered only into a local library that keeps originals")
                continue
            if entry not in (ent, src):
                errors.append(f"folder not allowed in the output: {entry} (only {ent}/ and {src}/)")
                continue
            for sub in sorted(os.listdir(p)):
                sp = os.path.join(p, sub)
                if os.path.isdir(sp):
                    errors.append(f"{entry}/ must not contain folders: {sub}")
                else:
                    files.append((f"{entry}/{sub}", sp))
        else:
            files.append((entry, p))
    rel = [r for r, _ in files]
    if names["index"] not in rel:
        errors.append(f"missing {names['index']} (every run rewrites it)")
    if names["readme"] not in rel:
        errors.append(f"missing {names['readme']}")
    for r, p in files:
        b = os.path.basename(r)
        if names["old_suffix"] in b or b.startswith(names["snapshot_prefix"]) or b.startswith("_"):
            errors.append(f"file that must not be delivered: {r}")
        elif r.startswith(src + "/"):  # an original: any format, kept as it is
            if not os.path.getsize(p):
                errors.append(f"empty file: {r}")
            log.info("included: %s (%d bytes)", r, os.path.getsize(p))
            continue
        elif not (b.lower().endswith(".md") or r == names["readme"]):
            errors.append(f"only .md files and {names['readme']} may be delivered: {r}")
        try:
            with open(p, encoding="utf-8") as f:
                if not f.read().strip():
                    errors.append(f"empty file: {r}")
        except UnicodeDecodeError:
            errors.append(f"not UTF-8: {r}")
        if max_len and len(b) > max_len:
            log.warning("file name longer than %d characters (%d): %s", max_len, len(b), b)
        log.info("included: %s (%d bytes)", r, os.path.getsize(p))
    return files, errors


def load_names(lib):
    try:
        cfg = kbconf.load_library(lib)
    except kbconf.ConfigError as e:
        log.error("%s", e)
        sys.exit(2)
    return cfg


def cmd_zip(a):
    cfg = load_names(a.library)
    files, errors = check_output(a.out, cfg["names"], a.max_name_len)
    for e in errors:
        print(f"Error: {e}")
    if errors:
        print("Result: check failed, nothing packed")
        sys.exit(3)
    dest = os.path.abspath(a.dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for r, p in files:
                z.write(p, r)
    except OSError as e:
        log.error("zip failed: %s", e)
        sys.exit(4)
    n_ent = sum(1 for r, _ in files if "/" in r)
    print(f"Packed: {dest}, {len(files) - n_ent} root files, {n_ent} entity pages")


def cmd_preview(a):
    cfg = load_names(a.library)
    names = cfg["names"]
    root = os.path.dirname(cfg["_path"])
    files, errors = check_output(a.out, names, a.max_name_len, allow_sources=True)
    for e in errors:
        print(f"Error: {e}")
    if errors:
        print("Result: check failed, nothing planned")
        sys.exit(3)
    stamp0 = kbconf.now(cfg["timezone"]).replace(microsecond=0)
    items, seq = [], 0
    for r, p in files + stale_originals(root, names, files):
        if r == names["readme"]:
            continue
        target = os.path.join(root, *r.split("/"))
        item = {"rel": r, "src": os.path.abspath(p) if p else None, "target": target,
                "src_size": os.path.getsize(p) if p else 0, "exists": os.path.exists(target)}
        if item["exists"]:
            st = os.stat(target)
            stem, ext = os.path.splitext(os.path.basename(target))
            stamp = (stamp0 + timedelta(seconds=seq)).strftime("%Y%m%d%H%M%S")
            seq += 1
            item.update(old_size=st.st_size, old_mtime=st.st_mtime,
                        archive_as=f"{stem}{names['old_suffix']}{stamp}{ext}")
        items.append(item)
    plan = {"library": cfg.get("label") or os.path.basename(root), "root": root,
            "archive_dir": os.path.join(root, names["archive_dir"]),
            "readme": os.path.abspath(os.path.join(a.out, names["readme"])),
            "timezone": cfg["timezone"], "log_prefix": names["run_log_prefix"],
            "base_time": stamp0.strftime("%Y-%m-%d %H:%M:%S"), "items": items}
    with open(a.plan, "w", encoding="utf-8", newline="\n") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    new = [i for i in items if not i["exists"]]
    upd = [i for i in items if i["exists"]]
    print("=== Preview ===")
    print(f"Library: {plan['library']} ({root})")
    print(f"New files: {len(new)}")
    for i in new:
        print(f"  + {i['rel']}")
    print(f"New versions (old copy goes to {names['archive_dir']}/): {len(upd)}")
    for i in upd:
        what = "old" if i["src"] else "old original, no new copy"
        print(f"  ~ {i['rel']}  {what} -> {names['archive_dir']}/{i['archive_as']}")
    print(f"Plan written to {a.plan}. Nothing has changed yet.")


def stale_originals(root, names, files):
    """Originals in the library that go to the archive folder with this run: those of a topic file that
    gets a new version, and those of a delivered original's topic under another extension. A copy under
    exactly a delivered name is left out here: it is archived as that name's old version. Returns
    [(relative path, None)]."""
    src = names["sources_dir"]
    folder = os.path.join(root, src)
    if not os.path.isdir(folder):
        return []
    rel = {r for r, _ in files}
    updated = {os.path.splitext(r)[0] for r in rel if "/" not in r and r.lower().endswith(".md")
               and os.path.isfile(os.path.join(root, r))}
    delivered = {os.path.splitext(r.split("/", 1)[1])[0] for r in rel if r.startswith(src + "/")}
    out = []
    for name in sorted(os.listdir(folder)):
        r = f"{src}/{name}"
        stem = os.path.splitext(name)[0]
        if r in rel or not os.path.isfile(os.path.join(folder, name)):
            continue
        if stem in updated or stem in delivered:
            out.append((r, None))
    return out


def archive_names(stamp0, seq, base, old_suffix, count):
    """Archive names for COUNT old copies of BASE, one second apart from stamp0 + seq."""
    stem, ext = os.path.splitext(base)
    out = []
    for k in range(count):
        stamp = (stamp0 + timedelta(seconds=seq + k)).strftime("%Y%m%d%H%M%S")
        out.append(f"{stem}{old_suffix}{stamp}{ext}")
    return out


def cmd_remote_preview(a):
    cfg = load_names(a.library)
    names = cfg["names"]
    files, errors = check_output(a.out, names, a.max_name_len)
    try:
        with open(a.existing, encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError("existing must be a JSON list")
    except (OSError, ValueError) as e:
        errors.append(f"cannot read {a.existing}: {e}")
        existing = []
    for e in errors:
        print(f"Error: {e}")
    if errors:
        print("Result: check failed, nothing planned")
        sys.exit(3)
    copies = {}
    for c in existing:
        copies.setdefault(c.get("rel"), []).append(c)
    stamp0 = kbconf.now(cfg["timezone"]).replace(microsecond=0)
    items, seq = [], 0
    for r, p in files:
        if r == names["readme"]:
            continue
        old = sorted(copies.get(r, []), key=lambda c: str(c.get("modified", "")))
        names_for = archive_names(stamp0, seq, os.path.basename(r), names["old_suffix"], len(old))
        seq += len(old)
        items.append({"rel": r, "src": os.path.abspath(p), "folder": "entities" if "/" in r else "root",
                      "archive": [{"id": c.get("id"), "archive_as": n} for c, n in zip(old, names_for)]})
    plan = {"library": cfg.get("label") or "library", "backend": "gdrive",
            "archive_dir": names["archive_dir"], "entities_dir": names["entities_dir"],
            "readme": os.path.abspath(os.path.join(a.out, names["readme"])),
            "timezone": cfg["timezone"], "log_prefix": names["run_log_prefix"],
            "base_time": stamp0.strftime("%Y-%m-%d %H:%M:%S"), "items": items}
    with open(a.plan, "w", encoding="utf-8", newline="\n") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    new = [i for i in items if not i["archive"]]
    upd = [i for i in items if i["archive"]]
    print("=== Preview ===")
    print(f"Library: {plan['library']} (Google Drive)")
    print(f"New files: {len(new)}")
    for i in new:
        print(f"  + {i['rel']}")
    print(f"New versions (old copy goes to {names['archive_dir']}/): {len(upd)}")
    for i in upd:
        for o in i["archive"]:
            print(f"  ~ {i['rel']}  old -> {names['archive_dir']}/{o['archive_as']}")
    print(f"Plan written to {a.plan}. Nothing has changed yet.")


def cmd_remote_log(a):
    try:
        with open(a.plan, encoding="utf-8") as f:
            plan = json.load(f)
        with open(a.results, encoding="utf-8") as f:
            results = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.error("cannot read plan or results: %s", e)
        sys.exit(2)
    lines = ["=== Delivery ===", f"Library: {plan['library']} (Google Drive)", f"Time: {plan['base_time']}", ""]
    ok = fail = 0
    for i in plan["items"]:
        res = results.get(i["rel"], "not done")
        if res == "ok":
            ok += 1
            for o in i["archive"]:
                lines.append(f"  archive | {i['rel']} -> {o['archive_as']}")
            lines.append(f"  write   | {i['rel']}")
        else:
            fail += 1
            lines.append(f"  failed  | {i['rel']} | {res}")
    end = kbconf.now(plan["timezone"]).strftime("%Y%m%d_%H%M%S")
    lines += ["", f"Written {ok}, failed {fail}.", "", "=== End ==="]
    print("\n".join(lines))
    print(f"Run log file name: {plan['log_prefix']}{end}.txt")
    print(f"Readme file name: _delivery_{end}_README.txt")
    if fail:
        sys.exit(3)


def cmd_deliver(a):
    try:
        with open(a.plan, encoding="utf-8") as f:
            plan = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.error("cannot read plan: %s", e)
        sys.exit(2)
    arch = plan["archive_dir"]
    os.makedirs(arch, exist_ok=True)
    lines = ["=== Delivery ===", f"Library: {plan['library']}", f"Time: {plan['base_time']}", ""]
    ok = fail = 0
    for i in plan["items"]:
        target, rel = i["target"], i["rel"]
        try:
            if i["src"] and (not os.path.isfile(i["src"]) or os.path.getsize(i["src"]) != i["src_size"]):
                raise RuntimeError("output file changed after preview")
            if i["exists"]:
                if not os.path.isfile(target):
                    raise RuntimeError("target disappeared after preview")
                st = os.stat(target)
                if st.st_size != i["old_size"] or st.st_mtime != i["old_mtime"]:
                    raise RuntimeError("target changed after preview")
                dst = os.path.join(arch, i["archive_as"])
                if os.path.exists(dst):
                    raise RuntimeError(f"archive name already used: {i['archive_as']}")
                shutil.move(target, dst)
                lines.append(f"  archive | {rel} -> {i['archive_as']}")
            elif os.path.exists(target):
                raise RuntimeError("a file with this name appeared after preview")
            if not i["src"]:  # an old original whose topic file moved on: archived only
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(i["src"], target)
            lines.append(f"  write   | {rel}")
            ok += 1
        except (OSError, RuntimeError) as e:
            fail += 1
            lines.append(f"  failed  | {rel} | {e}")
            log.error("%s: %s", rel, e)
    end = kbconf.now(plan["timezone"]).strftime("%Y%m%d_%H%M%S")
    if os.path.isfile(plan["readme"]):
        shutil.copy2(plan["readme"], os.path.join(arch, f"_delivery_{end}_README.txt"))
    lines += ["", f"Written {ok}, failed {fail}.", "", "=== End ==="]
    log_name = f"{plan['log_prefix']}{end}.txt"
    with open(os.path.join(arch, log_name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"Run log: {os.path.basename(arch)}/{log_name}")
    if fail:
        sys.exit(3)


def main():
    ap = argparse.ArgumentParser(description="Check and deliver intake output")
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("zip"); p.add_argument("out"); p.add_argument("dest")
    p.add_argument("--library", required=True); p.add_argument("--max-name-len", type=int, default=0)
    p = sub.add_parser("preview"); p.add_argument("out"); p.add_argument("--library", required=True)
    p.add_argument("--plan", required=True); p.add_argument("--max-name-len", type=int, default=0)
    p = sub.add_parser("deliver"); p.add_argument("--plan", required=True)
    p = sub.add_parser("remote-preview"); p.add_argument("out"); p.add_argument("--library", required=True)
    p.add_argument("--existing", required=True); p.add_argument("--plan", required=True)
    p.add_argument("--max-name-len", type=int, default=0)
    p = sub.add_parser("remote-log"); p.add_argument("--plan", required=True); p.add_argument("--results", required=True)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    log.info("subcommand: %s", a.cmd)
    {"zip": cmd_zip, "preview": cmd_preview, "deliver": cmd_deliver,
     "remote-preview": cmd_remote_preview, "remote-log": cmd_remote_log}[a.cmd](a)


if __name__ == "__main__":
    main()
