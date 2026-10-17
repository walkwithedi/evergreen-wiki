#!/usr/bin/env python3
"""Build upload-ready skill zips (one top-level folder per zip, as claude.ai expects).

Usage:
  python3 scripts/build_skill.py                      all skills -> dist/<skill>-<version>.zip
  python3 scripts/build_skill.py kb-note kb-query     only these
  python3 scripts/build_skill.py --locale zh          descriptions from locales/zh/descriptions.json
  python3 scripts/build_skill.py --config my.json     bake a private registry into config/kb-libraries.json
  python3 scripts/build_skill.py --out-dir DIR

A zip built with --config holds your library locations: keep it private, never attach it
to a public release. The version is read from the "Version:" line of each SKILL.md.
"""
import argparse
import json
import logging
import os
import re
import sys
import zipfile

log = logging.getLogger("build_skill")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = ["kb-note", "kb-query", "kb-ingest"]
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_FILES = {".DS_Store"}


def skill_version(text):
    m = re.search(r"^Version: (\d+\.\d+\.\d+)\s*$", text, re.M)
    return m.group(1) if m else None


def replace_description(text, new):
    if "\n" in new or len(new) > 1024:
        raise ValueError("description must be one line of at most 1024 characters")
    out, n = re.subn(r"^description: .*$", lambda m: "description: " + new, text, count=1, flags=re.M)
    if n != 1:
        raise ValueError("no description line in front matter")
    return out


def build(name, out_dir, locale_desc, config_path):
    src = os.path.join(ROOT, "skills", name)
    with open(os.path.join(src, "SKILL.md"), encoding="utf-8") as f:
        skill_md = f.read()
    if not re.search(rf"^name: {re.escape(name)}$", skill_md, re.M):
        raise SystemExit(f"{name}: front matter name does not match the folder")
    ver = skill_version(skill_md)
    if not ver:
        raise SystemExit(f"{name}: no 'Version: X.Y.Z' line in SKILL.md")
    if locale_desc:
        skill_md = replace_description(skill_md, locale_desc[name])
    suffix = "-private" if config_path else ""
    loc = f"-{locale_desc['_locale']}" if locale_desc else ""
    dest = os.path.join(out_dir, f"{name}-{ver}{loc}{suffix}.zip")
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(src):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fn in sorted(filenames):
                if fn in SKIP_FILES or fn.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, fn)
                arc = os.path.join(name, os.path.relpath(full, src)).replace(os.sep, "/")
                if arc == f"{name}/SKILL.md":
                    z.writestr(arc, skill_md)
                else:
                    z.write(full, arc)
        if config_path:
            with open(config_path, encoding="utf-8") as f:
                json.load(f)  # fail early on invalid JSON
            z.write(config_path, f"{name}/config/kb-libraries.json")
    log.info("built %s (%d bytes)", dest, os.path.getsize(dest))
    print(f"built: {os.path.relpath(dest, ROOT)}")
    return ver


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("skills", nargs="*", default=SKILLS)
    ap.add_argument("--locale")
    ap.add_argument("--config")
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    locale_desc = None
    if a.locale:
        p = os.path.join(ROOT, "locales", a.locale, "descriptions.json")
        with open(p, encoding="utf-8") as f:
            locale_desc = json.load(f)
        locale_desc["_locale"] = a.locale
        missing = [s for s in a.skills if s not in locale_desc]
        if missing:
            raise SystemExit(f"{p} has no description for {missing}")
    if a.config:
        log.warning("baking a private registry into the zip; do not publish it")
    versions = {build(s, a.out_dir, locale_desc, a.config) for s in a.skills}
    if len(versions) > 1:
        log.warning("skills carry different versions: %s", sorted(versions))


if __name__ == "__main__":
    main()
