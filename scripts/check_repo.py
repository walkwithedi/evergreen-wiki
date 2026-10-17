#!/usr/bin/env python3
"""Repository consistency checks run in CI (and locally before a commit).

  1. SKILL.md front matter: name matches the folder; description is one line of at most
     1024 characters; every skill has the same "Version: X.Y.Z".
  2. Locale descriptions: every skill has one, and each holds the same number of quoted
     trigger phrases as the English description ("..." vs 「...」).
  3. Environment-bound words (tool names, sandbox paths) appear only in the backend and
     environment references, never in SKILL.md or other references.
  4. No library file name is hard-coded in scripts: names come from kbconf.
  5. Presets and the sample library pass kbconf validation; preset placeholders are present.
  6. Plugin manifests are valid JSON and carry the skills version.
Exit code 1 on any problem.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "shared", "scripts"))
import kbconf  # noqa: E402

SKILLS = ["kb-note", "kb-query", "kb-incremental", "kb-ingest"]
ENV_WORDS = ["search_files", "read_file_content", "download_file_content", "create_file", "update_file",
             "get_file_metadata", "present_files", "/home/claude", "/mnt/user-data", "application/vnd.google-apps"]
ENV_ALLOWED = {"backend-gdrive.md", "backend-local.md", "environment.md"}
problems = []


def bad(msg):
    problems.append(msg)
    print(f"problem: {msg}")


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def check_skills():
    versions = {}
    descs = {}
    for s in SKILLS:
        t = read(os.path.join(ROOT, "skills", s, "SKILL.md"))
        m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", t)
        if not m:
            bad(f"{s}: front matter must be exactly name and description")
            continue
        if m.group(1) != s:
            bad(f"{s}: name {m.group(1)!r} does not match folder")
        if len(m.group(2)) > 1024:
            bad(f"{s}: description longer than 1024 characters")
        descs[s] = m.group(2)
        v = re.search(r"^Version: (\d+\.\d+\.\d+)$", t, re.M)
        versions[s] = v.group(1) if v else None
        if not v:
            bad(f"{s}: no 'Version: X.Y.Z' line")
    if len(set(versions.values())) > 1:
        bad(f"skills carry different versions: {versions}")
    for p in glob.glob(os.path.join(ROOT, "locales", "*", "descriptions.json")):
        loc = json.loads(read(p))
        for s in SKILLS:
            if s not in loc:
                bad(f"{os.path.relpath(p, ROOT)}: no description for {s}")
                continue
            en = len(re.findall(r'"[^"]+"', descs.get(s, "")))
            other = len(re.findall(r"「[^」]+」|\"[^\"]+\"|“[^”]+”", loc[s]))
            if en != other:
                bad(f"{os.path.relpath(p, ROOT)}: {s} has {other} trigger phrases, English has {en}")
            if len(loc[s]) > 1024:
                bad(f"{os.path.relpath(p, ROOT)}: {s} description too long")
    return next(iter(versions.values()), None)


def check_env_words():
    for p in glob.glob(os.path.join(ROOT, "skills", "*", "**", "*.md"), recursive=True):
        if os.path.basename(p) in ENV_ALLOWED:
            continue
        t = read(p)
        for w in ENV_WORDS:
            if w in t:
                bad(f"{os.path.relpath(p, ROOT)}: environment-bound word {w!r} (move it to a backend/environment reference)")


def check_hardcoded_names():
    names = [v for k, v in kbconf.DEFAULT_NAMES.items() if k in kbconf.SUMMARY_KEYS or k.endswith("_dir")]
    for p in glob.glob(os.path.join(ROOT, "skills", "*", "scripts", "*.py")):
        if os.path.basename(p) == "kbconf.py":
            continue
        t = read(p)
        for n in names:
            if re.search(r"[\"']" + re.escape(n) + r"[\"']", t):
                bad(f"{os.path.relpath(p, ROOT)}: hard-coded library name {n!r}; use kbconf names")


def check_libraries():
    presets = glob.glob(os.path.join(ROOT, "skills", "kb-incremental", "assets", "presets", "*"))
    for d in presets + [os.path.join(ROOT, "examples", "sample-life-kb")]:
        rel = os.path.relpath(d, ROOT)
        for msg in kbconf.validate(json.loads(read(os.path.join(d, "_kb.json")))):
            bad(f"{rel}/_kb.json: {msg}")
        for f in ("_kb-params.md", "00_Spec.md"):
            if not os.path.isfile(os.path.join(d, f)):
                bad(f"{rel}: missing {f}")
    # translated presets (<preset>/<language>/) replace the text files, so they need the same set
    translated = [t for d in presets for t in glob.glob(os.path.join(d, "*")) if os.path.isdir(t)
                  and os.path.basename(t) != "summary"]
    for d in translated:
        if not os.path.isfile(os.path.join(d, "_kb-params.md")):
            bad(f"{os.path.relpath(d, ROOT)}: missing _kb-params.md")
    for d in presets + translated:
        spec = read(os.path.join(d, "00_Spec.md"))
        for ph in ("{{DATE}}", "{{HEADING_LIMIT}}", "{{FILENAME_LIMIT}}"):
            if ph not in spec:
                bad(f"{os.path.relpath(d, ROOT)}/00_Spec.md: placeholder {ph} missing")
        for k in kbconf.SUMMARY_KEYS:
            if k != "spec" and not os.path.isfile(os.path.join(d, "summary", kbconf.DEFAULT_NAMES[k])):
                bad(f"{os.path.relpath(d, ROOT)}/summary: missing {kbconf.DEFAULT_NAMES[k]}")


def check_manifests(version):
    for p in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        full = os.path.join(ROOT, p)
        if not os.path.isfile(full):
            bad(f"missing {p}")
            continue
        try:
            data = json.loads(read(full))
        except json.JSONDecodeError as e:
            bad(f"{p}: invalid JSON: {e}")
            continue
        vers = [data.get("version")] if "plugins" not in data else [x.get("version") for x in data["plugins"]]
        if version and any(v != version for v in vers):
            bad(f"{p}: version {vers} differs from skills {version}")


def main():
    version = check_skills()
    check_env_words()
    check_hardcoded_names()
    check_libraries()
    check_manifests(version)
    print("result: " + (f"{len(problems)} problems" if problems else "ok"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
