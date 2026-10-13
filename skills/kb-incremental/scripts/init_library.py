#!/usr/bin/env python3
"""Create a new library from a preset, register it and make it visible to the assistant.

One definition of first-time setup, used by init mode (references/init.md) and by the
interactive installer (install.py), so both create exactly the same files.

Subcommands (results on stdout, logs on stderr):
  defaults  [--preset P] [--language L]       suggested label, id, scope, timezone and language
  plan      --root DIR --preset P [options]   preview of what write would create; exit 3 if refused
  write     --root DIR --preset P [options]   create the library (local folder)
  render    --out DIR  --preset P [options]   write the same files into DIR for upload (Drive)
  register  --registry FILE --id ID --label L --scope S --type local|gdrive --root R [--dry-run]
  instructions --registry FILE [--language L] [--file F [--apply]] [--project-block]
            print the instructions line, or update it in F, or print a block to paste
            into claude.ai Project instructions (the line plus the registry)
  instructions --drive-folder ID [--language L]
            print the one line for claude.ai Project instructions when the registry lives in
            Google Drive (kb-libraries.json in that folder); it never changes when libraries are added

Options for plan/write/render: --label --id --scope --language --timezone --sensitivity on|off --date.
Missing options take the values printed by defaults.

Exit codes: 0 ok, 2 bad input, 3 refused (folder holds Markdown files, id already used).
Only the Python 3 standard library is used. Python 3.8 or newer.
"""
import argparse
import json
import locale
import logging
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("init_library")
PRESETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "presets")
PRESETS = ("life", "work")
LANGUAGES = ("en", "zh")

# Suggested label and scope per preset and language. The scope is what routes requests
# between libraries, so the user is always asked to confirm or change it.
PRESET_DEFAULTS = {
    "life": {"en": ("Life", "me and my family: IDs, health, insurance, money, home"),
             "zh": ("生活", "我和家人：证件、健康、保险、财务、住房")},
    "work": {"en": ("Work", "work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports"),
             "zh": ("工作", "工作目标与计划、项目与事务、会议与决策、制度流程、报表等工作资料")},
}

# The line that tells the assistant the libraries exist. The prefix is how an existing
# line is found again, so a second run updates it instead of adding another.
LINE_PREFIX = {"en": "I keep knowledge bases: ", "zh": "我有知识库："}
LINE_TAIL = {
    "en": ". For questions about these, use kb-query before searching code or answering from memory; "
          "to save something, use kb-note. At the start of a conversation, if a library holds an unfinished "
          "batch intake, ask whether to continue it.",
    "zh": "。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note。"
          "新对话开始时，如知识库有未完成的分批入库，先提醒是否继续。",
}
# One line for a registry kept in Google Drive. The "registry: ..." part is what the skills
# look for (references/config.md), so it stays in English in every language.
DRIVE_LINE = {
    "en": "I keep knowledge bases; their list and scopes are in Google Drive "
          "(registry: Google Drive folder {folder}, file kb-libraries.json). For questions my knowledge "
          "bases may answer, use kb-query before searching code or answering from memory; to save something, use kb-note.",
    "zh": "我有知识库，库的清单与范围在 Google Drive 里（registry: Google Drive folder {folder}, file kb-libraries.json）。"
          "可能记在知识库里的问题，先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note。",
}
REGISTRY_HEADING = {"en": "Knowledge base registry (kb-libraries.json):", "zh": "知识库注册表（kb-libraries.json）："}


class Refused(Exception):
    pass


def lang_key(language):
    return "zh" if (language or "").lower().startswith("zh") else "en"


def detect_language():
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(var)
        if v:
            return lang_key(v)
    try:
        v = locale.getlocale()[0] or ""
    except ValueError:
        v = ""
    return "zh" if v.lower().startswith(("zh", "chinese")) else "en"


def detect_timezone():
    """IANA name where the system says it, else the current fixed offset (no DST)."""
    tz = os.environ.get("TZ", "").lstrip(":")
    if tz and not kbconf.check_timezone(tz):
        return tz
    try:
        target = os.path.realpath("/etc/localtime")
        m = re.search(r"zoneinfo/(.+)$", target)
        if m and not kbconf.check_timezone(m.group(1)):
            return m.group(1)
    except OSError:
        pass
    try:
        with open("/etc/timezone", encoding="utf-8") as f:
            tz = f.read().strip()
        if tz and not kbconf.check_timezone(tz):
            return tz
    except OSError:
        pass
    off = time.localtime().tm_gmtoff or 0
    if off == 0:
        return "UTC"
    sign = "+" if off > 0 else "-"
    off = abs(off) // 60
    return f"{sign}{off // 60:02d}:{off % 60:02d}"


def defaults(preset=None, language=None):
    language = lang_key(language or detect_language())
    out = {"language": language, "timezone": detect_timezone()}
    if preset:
        label, scope = PRESET_DEFAULTS[preset][language]
        kb = load_preset_kb(preset)
        out.update({"preset": preset, "id": preset, "label": label, "scope": scope,
                    "sensitivity": kb["sensitivity"]["enabled"],
                    "convert": kb.get("convert", {}).get("enabled", False)})
    return out


def load_preset_kb(preset):
    if preset not in PRESETS:
        raise kbconf.ConfigError(f"unknown preset {preset!r}; choose one of {', '.join(PRESETS)}")
    return kbconf.load_json(os.path.join(PRESETS_DIR, preset, kbconf.KB_JSON))


def preset_file(preset, language, *rel):
    """A preset text file in the library language: <preset>/<language>/... when the preset
    has that translation, else the English file in <preset>/. _kb.json is shared."""
    local = os.path.join(PRESETS_DIR, preset, lang_key(language), *rel)
    return local if os.path.isfile(local) else os.path.join(PRESETS_DIR, preset, *rel)


def settings(a):
    """Fill missing options from defaults; returns a plain dict."""
    d = defaults(a.preset, a.language)
    s = {k: getattr(a, k, None) for k in ("preset", "label", "id", "scope", "language", "timezone")}
    for k, v in s.items():
        if not v:
            s[k] = d[k]
    sens = getattr(a, "sensitivity", None)
    s["sensitivity"] = d["sensitivity"] if sens is None else sens == "on"
    conv = getattr(a, "convert", None)
    s["convert"] = d["convert"] if conv is None else conv == "on"
    s["date"] = getattr(a, "date", None) or datetime.now(local_tz(s["timezone"])).strftime("%Y-%m-%d")
    problems = kbconf.check_timezone(s["timezone"])
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", s["id"]):
        problems.append("id must be lowercase letters, digits and hyphens")
    if not s["scope"].strip():
        problems.append("scope is empty; it decides which library a request belongs to")
    if problems:
        raise kbconf.ConfigError("; ".join(problems))
    return s


def local_tz(name):
    try:
        return kbconf.tzinfo(name)
    except kbconf.ConfigError:
        return None  # system local time; the date is all that is needed


def build_files(s):
    """Return [(relative path, text)] for a new library, and the folders to create."""
    kb = load_preset_kb(s["preset"])
    kb.update({"label": s["label"], "preset": s["preset"], "language": s["language"], "timezone": s["timezone"]})
    kb["sensitivity"] = dict(kb["sensitivity"], enabled=bool(s["sensitivity"]))
    kb["convert"] = dict(kb.get("convert", {}), enabled=bool(s.get("convert", False)))
    problems = kbconf.validate(kb)
    if problems:
        raise kbconf.ConfigError("generated _kb.json: " + "; ".join(problems))
    names = kbconf.resolve_names(kb.get("names"))
    heading, filename = kbconf.default_limits(s["language"])
    fill = {"{{DATE}}": s["date"], "{{HEADING_LIMIT}}": str(heading), "{{FILENAME_LIMIT}}": str(filename)}

    def filled(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for k, v in fill.items():
            text = text.replace(k, v)
        return text

    def src(*rel):
        return preset_file(s["preset"], s["language"], *rel)

    files = [(kbconf.KB_JSON, json.dumps(kb, ensure_ascii=False, indent=2) + "\n"),
             (kbconf.PARAMS_FILE, filled(src(kbconf.PARAMS_FILE))),
             (names["spec"], filled(src(kbconf.DEFAULT_NAMES["spec"])))]
    for k in kbconf.SUMMARY_KEYS:
        if k != "spec":
            files.append((names[k], filled(src("summary", kbconf.DEFAULT_NAMES[k]))))
    folders = [names["archive_dir"], names["notes_dir"]]
    if kb.get("metadata", "yaml") == "yaml":
        folders.append(names["entities_dir"])
    return files, folders


def check_root(root):
    """A new library needs an empty folder or a new one; any Markdown file means an existing library."""
    if os.path.exists(root) and not os.path.isdir(root):
        raise Refused(f"{root} is a file, not a folder")
    if os.path.isdir(root):
        md = sorted(n for n in os.listdir(root) if n.lower().endswith(".md") or n == kbconf.KB_JSON)
        if md:
            raise Refused(f"{root} already holds {', '.join(md[:3])}{' ...' if len(md) > 3 else ''}; "
                          "it looks like an existing library. Ask the assistant to set it up instead "
                          "(init mode, existing-library branch), which never overwrites files.")


def plan_text(root, s, files, folders):
    lines = [f"Library: {s['label']} (id {s['id']}) | preset {s['preset']} | {root}",
             f"Scope: {s['scope']}",
             f"Language: {s['language']} | timezone: {s['timezone']} | "
             f"sensitivity and masking: {'on' if s['sensitivity'] else 'off'} | "
             f"convert uploads to Markdown: {'on' if s.get('convert') else 'off'}",
             "Files:"]
    lines += [f"  {p}" for p, _ in files]
    lines.append("Folders: " + ", ".join(folders))
    return "\n".join(lines)


def write_files(root, files, folders):
    os.makedirs(root, exist_ok=True)
    for rel, text in files:
        p = os.path.join(root, rel)
        with open(p, "x", encoding="utf-8", newline="\n") as f:
            f.write(text)
        log.info("wrote %s", p)
    for d in folders:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    missing = [rel for rel, _ in files if not os.path.isfile(os.path.join(root, rel))]
    if missing:
        raise kbconf.ConfigError("not written: " + ", ".join(missing))


def create_library(root, s):
    root = os.path.abspath(os.path.expanduser(root))
    check_root(root)
    files, folders = build_files(s)
    write_files(root, files, folders)
    return root, files, folders


# Registry and instructions line

def registry_path(path=None):
    """The registry to write: the given path, else the first existing candidate, else the user file."""
    if path:
        return os.path.abspath(os.path.expanduser(path))
    cands = kbconf.registry_candidates()[:-1]  # the last one lives inside a private skill build
    for p in cands:
        if os.path.isfile(p):
            return p
    return cands[0]


def load_registry_or_new(path, language=None):
    if os.path.isfile(path):
        return kbconf.load_json(path)
    reg = {"schema": kbconf.SCHEMA, "preferences": {}, "libraries": []}
    if language:
        reg["preferences"]["language"] = language
    return reg


def registry_entry(lib_id, label, scope, backend_type, root):
    if backend_type == "local":
        root = os.path.abspath(os.path.expanduser(root))
        home = os.path.expanduser("~")
        if root.startswith(home + os.sep):
            root = "~" + root[len(home):].replace(os.sep, "/")
    return {"id": lib_id, "label": label, "scope": scope, "backend": {"type": backend_type, "root": root}}


def add_to_registry(path, entry, language=None, dry_run=False):
    reg = load_registry_or_new(path, language)
    libs = reg.setdefault("libraries", [])
    if any(lib.get("id") == entry["id"] for lib in libs):
        raise Refused(f"id {entry['id']!r} is already in {path}; choose another id")
    root = entry["backend"]["root"]
    for lib in libs:
        if (lib.get("backend") or {}).get("root") == root:
            raise Refused(f"{root} is already registered as {lib.get('id')!r} in {path}")
    libs.append(entry)
    problems = kbconf.check_registry(reg)
    if problems:
        raise kbconf.ConfigError("; ".join(problems))
    if not dry_run:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    return reg


def instructions_line(reg, language=None):
    language = lang_key(language or reg.get("preferences", {}).get("language"))
    sep, lp, rp = ("；", "（", "）") if language == "zh" else ("; ", " (", ")")
    libs = sep.join(f"{lib['label']}{lp}{lib['scope']}{rp}" for lib in reg.get("libraries", []))
    return LINE_PREFIX[language] + libs + LINE_TAIL[language]


def is_our_line(line):
    """Both forms (libraries listed, or registry in Drive) start with the same words."""
    return any(line.lstrip().startswith(p.strip().rstrip(":：")) for p in LINE_PREFIX.values())


def drive_line(folder, language=None):
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,}", folder or ""):
        raise kbconf.ConfigError(f"not a Drive folder ID: {folder!r}")
    return DRIVE_LINE[lang_key(language)].format(folder=folder)


def upsert_line(text, line):
    """Replace our existing line, or append it; every other line stays as it is.
    Returns (new text, 'added' | 'updated' | 'unchanged')."""
    lines = text.split("\n")
    for i, old in enumerate(lines):
        if is_our_line(old):
            if old.strip() == line:
                return text, "unchanged"
            lines[i] = line
            return "\n".join(lines), "updated"
    body = text.rstrip("\n")
    return (body + "\n\n" if body else "") + line + "\n", "added"


def update_instructions_file(path, line, dry_run=False):
    path = os.path.expanduser(path)
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    new, what = upsert_line(text, line)
    if what != "unchanged" and not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
    return what


def project_block(reg, language=None):
    language = lang_key(language or reg.get("preferences", {}).get("language"))
    clean = {k: v for k, v in reg.items() if not k.startswith("_")}
    return (instructions_line(reg, language) + "\n\n" + REGISTRY_HEADING[language] + "\n"
            + json.dumps(clean, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    kbconf.add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("defaults")
    p.add_argument("--preset", choices=PRESETS)
    p.add_argument("--language")
    for c in ("plan", "write", "render"):
        p = sub.add_parser(c)
        p.add_argument("--out" if c == "render" else "--root", required=True)
        p.add_argument("--preset", required=True, choices=PRESETS)
        for opt in ("label", "id", "scope", "language", "timezone", "date"):
            p.add_argument("--" + opt)
        p.add_argument("--sensitivity", choices=["on", "off"])
        p.add_argument("--convert", choices=["on", "off"])
    p = sub.add_parser("register")
    p.add_argument("--registry")
    for opt in ("id", "label", "scope", "root"):
        p.add_argument("--" + opt, required=True)
    p.add_argument("--type", required=True, choices=["local", "gdrive"])
    p.add_argument("--language")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("instructions")
    p.add_argument("--registry")
    p.add_argument("--drive-folder")
    p.add_argument("--language")
    p.add_argument("--file")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--project-block", action="store_true")
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    try:
        if a.cmd == "defaults":
            print(json.dumps(defaults(a.preset, a.language), ensure_ascii=False, indent=2))
        elif a.cmd in ("plan", "write"):
            s = settings(a)
            root = os.path.abspath(os.path.expanduser(a.root))
            check_root(root)
            files, folders = build_files(s)
            print(plan_text(root, s, files, folders))
            if a.cmd == "write":
                write_files(root, files, folders)
                print(f"result: written {len(files)} files and {len(folders)} folders")
        elif a.cmd == "render":
            s = settings(a)
            out = os.path.abspath(os.path.expanduser(a.out))
            check_root(out)
            files, folders = build_files(s)
            write_files(out, files, [])
            print(plan_text(out, s, files, folders))
            print(f"result: rendered {len(files)} files; create the folders in the library: {', '.join(folders)}")
        elif a.cmd == "register":
            path = registry_path(a.registry)
            entry = registry_entry(a.id, a.label, a.scope, a.type, a.root)
            add_to_registry(path, entry, lang_key(a.language) if a.language else None, a.dry_run)
            print(f"registry: {path}")
            print(json.dumps(entry, ensure_ascii=False))
            print("result: " + ("would add" if a.dry_run else "added"))
        elif a.cmd == "instructions" and a.drive_folder:
            print(drive_line(a.drive_folder, a.language))
        elif a.cmd == "instructions":
            path = registry_path(a.registry)
            reg = kbconf.load_json(path)
            if a.project_block:
                print(project_block(reg, a.language))
                return
            line = instructions_line(reg, a.language)
            print(line)
            if a.file:
                what = update_instructions_file(a.file, line, dry_run=not a.apply)
                print(f"{'' if a.apply else 'would be '}{what}: {os.path.expanduser(a.file)}")
    except Refused as e:
        print(f"refused: {e}")
        sys.exit(3)
    except kbconf.ConfigError as e:
        log.error("%s", e)
        print(f"error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
