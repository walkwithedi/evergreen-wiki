#!/usr/bin/env python3
"""Repository consistency checks run in CI (and locally before a commit).

  1. SKILL.md front matter: name matches the folder; description is one line of at most
     1024 characters; every skill has the same "Version: X.Y.Z".
  2. Locale descriptions: every skill has one, and each holds the same number of quoted
     trigger phrases as the English description ("..." vs 「...」).
  3. Environment-bound words (tool names, sandbox paths) appear only in the backend and
     environment references, never in SKILL.md or other references.
  4. No library file name is hard-coded in scripts: names come from kbconf.
  5. Presets and the sample library pass kbconf validation (schema 2); presets hold the spec with its
     {{DATE}} placeholder and the status card, in every translation.
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

SKILLS = ["kb-note", "kb-query", "kb-ingest"]
ENV_WORDS = ["search_files", "read_file_content", "download_file_content", "create_file", "update_file",
             "get_file_metadata", "present_files", "/home/claude", "/mnt/user-data", "application/vnd.google-apps"]
ENV_ALLOWED = {"backend-local.md", "environment.md"}
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
    presets = glob.glob(os.path.join(ROOT, "skills", "kb-ingest", "assets", "presets", "*"))
    sample = os.path.join(ROOT, "examples", "sample-work-kb")
    for d in presets + [sample]:
        rel = os.path.relpath(d, ROOT)
        if not os.path.isfile(os.path.join(d, "_kb.json")):
            bad(f"{rel}: missing _kb.json")
            continue
        for msg in kbconf.validate(json.loads(read(os.path.join(d, "_kb.json")))):
            bad(f"{rel}/_kb.json: {msg}")
    # translated presets (<preset>/<language>/) replace the text files, so they need the same set
    translated = [t for d in presets for t in glob.glob(os.path.join(d, "*")) if os.path.isdir(t)
                  and os.path.basename(t) != "summary"]
    for d in presets + translated:
        rel = os.path.relpath(d, ROOT)
        spec = os.path.join(d, kbconf.DEFAULT_NAMES["spec"])
        if not os.path.isfile(spec):
            bad(f"{rel}: missing {kbconf.DEFAULT_NAMES['spec']}")
        elif "{{DATE}}" not in read(spec):
            bad(f"{rel}/{kbconf.DEFAULT_NAMES['spec']}: placeholder {{{{DATE}}}} missing")
        if not os.path.isfile(os.path.join(d, "summary", kbconf.DEFAULT_NAMES["status_card"])):
            bad(f"{rel}/summary: missing {kbconf.DEFAULT_NAMES['status_card']}")


def main():
    check_skills()
    check_env_words()
    check_hardcoded_names()
    check_libraries()
    print("result: " + (f"{len(problems)} problems" if problems else "ok"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
