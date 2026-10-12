#!/usr/bin/env python3
"""Shared configuration loader for the evergreen-wiki skills.

Two levels of configuration:

  Registry (user level)   kb-libraries.json: which libraries exist and where they live.
  Library (per library)   _kb.json in the library root: label, language, timezone,
                          metadata mode, sensitivity, partitions and file/folder names.

Every name a skill or script uses (summary files, archive folder, "_old" suffix, ...)
comes from resolve_names(), so a library can keep its own names (for example Chinese
ones) while the skills stay generic.

Subcommands (results on stdout, logs on stderr):
  registry [--path FILE]                    print the resolved registry as JSON
  show     LIBRARY_ROOT_OR_KB_JSON          print the resolved library config as JSON
  names    LIBRARY_ROOT_OR_KB_JSON          print the resolved names, one "key: value" per line
  limits   --language LANG                  print the default Table D length limits for a language
  validate LIBRARY_ROOT_OR_KB_JSON          check _kb.json; exit 3 on problems

Only the Python 3 standard library is used. Python 3.8 or newer.
"""
import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

log = logging.getLogger("kbconf")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"

SCHEMA = 1
KB_JSON = "_kb.json"
PARAMS_FILE = "_kb-params.md"
REGISTRY_FILE = "kb-libraries.json"

# Default English names. A library overrides any of them through "names" in _kb.json.
DEFAULT_NAMES = {
    "spec": "00_Spec.md",
    "status_card": "00_Status-Card.md",
    "index": "01_File-Index.md",
    "open_items": "01_Open-Items.md",
    "changelog": "01_Change-Log.md",
    "glossary": "01_Glossary-Issues.md",
    "archive_dir": "Archive",
    "entities_dir": "Entities",
    "notes_dir": "Quick-Notes",
    "notes_done_dir": "Filed",
    "old_suffix": "_old",
    "snapshot_prefix": "snapshot_",
    "readme": "README.txt",
    "run_log_prefix": "_run-log_",
    "batch_plan": "_intake-batches.json",
    "note_marker": "Quick note:",
    "assistant_label": "Assistant",
    "user_label": "User",
}
SUMMARY_KEYS = ("spec", "status_card", "index", "open_items", "changelog", "glossary")

# Default Table D length limits by language: (heading demotion limit, file name limit).
# Chinese packs about twice the information per character, so it gets lower limits.
DEFAULT_LIMITS = {"zh": (55, 80), "ja": (55, 80), "ko": (60, 90)}
FALLBACK_LIMITS = (90, 120)

# Converting uploads to Markdown before intake (kb-incremental scripts/convert.py).
# enabled: off unless the library turns it on (new libraries from a preset do).
# image_limit: pictures in one batch that are read without asking.
# min_pdf_chars_per_page, min_chars_per_image: below these a file is read as the original.
CONVERT_DEFAULTS = {"enabled": False, "image_limit": 10, "min_pdf_chars_per_page": 200,
                    "min_chars_per_image": 100}

# Intake of many files at once (kb-incremental scripts/batch_plan.py): a batch closes at
# batch_files files or batch_mb megabytes; more than one batch turns batch mode on.
INTAKE_DEFAULTS = {"batch_files": 10, "batch_mb": 20}

DEFAULTS = {
    "schema": SCHEMA,
    "label": "",
    "preset": "",
    "language": "en",
    "timezone": "UTC",
    "metadata": "yaml",
    "sensitivity": {"enabled": False, "keep_last": 4},
    "partitions": {"max": 9, "topic_start": 2, "fallback": ""},
    "delivery": "",
    "convert": CONVERT_DEFAULTS,
    "intake": INTAKE_DEFAULTS,
    "names": {},
}
KNOWN_KEYS = set(DEFAULTS) | {"backend", "inbox", "notes"}


def utf8_stdio():
    """Windows consoles default to a legacy code page; library names may be CJK."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def setup_logging(level):
    utf8_stdio()
    logging.basicConfig(level=level, format=LOG_FORMAT, stream=sys.stderr)


def add_log_args(ap):
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="default: environment variable LOG_LEVEL, else INFO")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise ConfigError(f"cannot read {path}: {e}")
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path} is not valid JSON: {e}")


class ConfigError(Exception):
    pass


def registry_candidates():
    """Places the registry is looked for, in order. Project instructions come first
    but are read by the model, not by this script."""
    out = []
    env = os.environ.get("KB_LIBRARIES")
    if env:
        out.append(os.path.expanduser(env))
    if os.name == "nt" and os.environ.get("APPDATA"):
        out.append(os.path.join(os.environ["APPDATA"], "kb", REGISTRY_FILE))
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    out.append(os.path.join(base, "kb", REGISTRY_FILE))
    here = os.path.dirname(os.path.abspath(__file__))
    out.append(os.path.join(os.path.dirname(here), "config", REGISTRY_FILE))
    return out


def load_registry(path=None):
    paths = [path] if path else registry_candidates()
    for p in paths:
        if p and os.path.isfile(p):
            log.info("registry: %s", p)
            reg = load_json(p)
            problems = check_registry(reg)
            for msg in problems:
                log.warning("registry: %s", msg)
            reg["_path"] = p
            return reg
        log.debug("no registry at %s", p)
    raise ConfigError("no registry found; looked in: " + ", ".join(p for p in paths if p))


def check_registry(reg):
    problems = []
    if not isinstance(reg, dict):
        return ["registry must be a JSON object"]
    if reg.get("schema") != SCHEMA:
        problems.append(f"schema should be {SCHEMA}, got {reg.get('schema')!r}")
    libs = reg.get("libraries")
    if not isinstance(libs, list) or not libs:
        problems.append("libraries must be a non-empty list")
        return problems
    seen = set()
    for i, lib in enumerate(libs):
        where = f"libraries[{i}]"
        if not isinstance(lib, dict):
            problems.append(f"{where} must be an object")
            continue
        lid = lib.get("id")
        if not lid or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(lid)):
            problems.append(f"{where}.id must be lowercase letters, digits and hyphens")
        if lid in seen:
            problems.append(f"{where}.id {lid!r} is used twice")
        seen.add(lid)
        b = lib.get("backend") or {}
        if b.get("type") not in ("gdrive", "local"):
            problems.append(f"{where}.backend.type must be gdrive or local")
        if not b.get("root"):
            problems.append(f"{where}.backend.root is required")
        if not lib.get("scope"):
            problems.append(f"{where}.scope is empty; the assistant uses it to route questions")
    prefs = reg.get("preferences", {})
    if prefs and prefs.get("output") not in (None, "markdown", "plain"):
        problems.append("preferences.output must be markdown or plain")
    return problems


def find_kb_json(path):
    path = os.path.expanduser(path)
    if os.path.isdir(path):
        path = os.path.join(path, KB_JSON)
    return path


def merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve_names(names_override=None):
    names = dict(DEFAULT_NAMES)
    for k, v in (names_override or {}).items():
        if k.endswith("_key"):
            names[k] = v
        elif k in DEFAULT_NAMES:
            names[k] = v
        else:
            log.warning("unknown name key ignored: %s", k)
    for k in SUMMARY_KEYS:
        names.setdefault(k + "_key", search_key(names[k]))
    return names


def search_key(file_name):
    """Partial string used to find a summary file: '00_Status-Card.md' -> 'Status-Card'."""
    stem = re.sub(r"\.md$", "", file_name, flags=re.I)
    return re.sub(r"^\d+_", "", stem)


def load_library(path):
    p = find_kb_json(path)
    raw = load_json(p)
    cfg = merge(DEFAULTS, raw)
    cfg["names"] = resolve_names(raw.get("names"))
    cfg["_path"] = p
    for msg in validate(raw):
        log.warning("%s: %s", p, msg)
    return cfg


def validate(raw):
    problems = []
    if not isinstance(raw, dict):
        return ["_kb.json must be a JSON object"]
    if raw.get("schema") != SCHEMA:
        problems.append(f"schema should be {SCHEMA}, got {raw.get('schema')!r}")
    for k in raw:
        if k not in KNOWN_KEYS:
            problems.append(f"unknown key {k!r}")
    if raw.get("metadata", "yaml") not in ("yaml", "text"):
        problems.append("metadata must be yaml or text")
    if raw.get("delivery", "") not in ("", "zip", "direct"):
        problems.append("delivery must be zip or direct")
    problems += check_convert(raw.get("convert", {}))
    problems += check_intake(raw.get("intake", {}))
    part = raw.get("partitions", {})
    mx, ts = part.get("max", 9), part.get("topic_start", 2)
    if not (isinstance(mx, int) and isinstance(ts, int) and 0 < ts <= mx <= 99):
        problems.append("partitions needs integers with 0 < topic_start <= max <= 99")
    fb = part.get("fallback", "")
    if fb and not (re.fullmatch(r"\d{2}", str(fb)) and ts <= int(fb) <= mx):
        problems.append("partitions.fallback must be a two-digit topic partition inside the range")
    problems += check_timezone(raw.get("timezone", "UTC"))
    names = raw.get("names", {})
    for k in names:
        if not (k in DEFAULT_NAMES or (k.endswith("_key") and k[:-4] in SUMMARY_KEYS)):
            problems.append(f"unknown names key {k!r}")
    return problems


def check_convert(conv):
    if not isinstance(conv, dict):
        return ["convert must be an object such as {\"enabled\": true}"]
    problems = []
    for k, v in conv.items():
        if k not in CONVERT_DEFAULTS:
            problems.append(f"unknown convert key {k!r}")
        elif k == "enabled" and not isinstance(v, bool):
            problems.append("convert.enabled must be true or false")
        elif k != "enabled" and not (isinstance(v, int) and not isinstance(v, bool) and v >= 0):
            problems.append(f"convert.{k} must be a whole number of 0 or more")
    return problems


def check_intake(intake):
    if not isinstance(intake, dict):
        return ["intake must be an object such as {\"batch_files\": 10}"]
    problems = []
    for k, v in intake.items():
        if k not in INTAKE_DEFAULTS:
            problems.append(f"unknown intake key {k!r}")
        elif not (isinstance(v, int) and not isinstance(v, bool) and v >= 1):
            problems.append(f"intake.{k} must be a whole number of 1 or more")
    return problems


class TimezoneUnavailable(ConfigError):
    """The name may be fine, but this Python cannot resolve IANA names
    (3.8 has no zoneinfo; Windows has no system timezone database)."""


def check_timezone(name):
    """Validate the spelling only, so a config checks the same on every system."""
    if name in (None, "", "UTC", "Z") or re.fullmatch(r"[+-]\d{2}:?\d{2}", str(name)):
        return []
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_+-]*(/[A-Za-z0-9_+-]+){0,2}", str(name)):
        return [f"timezone {name!r} is neither an IANA name nor an offset like +08:00"]
    try:
        tzinfo(name)
    except TimezoneUnavailable:
        pass
    except ConfigError as e:
        return [str(e)]
    return []


def tzinfo(name):
    """IANA name or a fixed offset such as +08:00 / UTC."""
    if name in (None, "", "UTC", "Z"):
        return timezone.utc
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", name)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        return timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    try:
        import zoneinfo  # Python 3.9+
    except ImportError:
        raise TimezoneUnavailable(f"timezone {name!r} needs Python 3.9+; use a fixed offset like +08:00")
    try:
        return zoneinfo.ZoneInfo(name)
    except Exception:
        if not zoneinfo.available_timezones():
            raise TimezoneUnavailable(f"this system has no timezone database for {name!r} "
                                      "(usual on Windows); use a fixed offset like +08:00")
        raise ConfigError(f"unknown timezone {name!r}")


def now(tz_name):
    return datetime.now(tzinfo(tz_name))


def default_limits(language):
    lang = (language or "en").split("-")[0].lower()
    return DEFAULT_LIMITS.get(lang, FALLBACK_LIMITS)


def default_delivery(cfg, backend_type):
    """direct for every backend; zip only when set, or when a Drive library has its own inbox script."""
    if cfg.get("delivery"):
        return cfg["delivery"]
    return "zip" if backend_type == "gdrive" and cfg.get("inbox") else "direct"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    add_log_args(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("registry"); p.add_argument("--path")
    for c in ("show", "names", "validate"):
        p = sub.add_parser(c); p.add_argument("library")
    p = sub.add_parser("limits"); p.add_argument("--language", required=True)
    a = ap.parse_args()
    setup_logging(a.log_level)
    try:
        if a.cmd == "registry":
            reg = load_registry(a.path)
            print(json.dumps(reg, ensure_ascii=False, indent=2))
        elif a.cmd == "show":
            print(json.dumps(load_library(a.library), ensure_ascii=False, indent=2))
        elif a.cmd == "names":
            for k, v in load_library(a.library)["names"].items():
                print(f"{k}: {v}")
        elif a.cmd == "limits":
            h, f = default_limits(a.language)
            print(f"heading: {h}\nfilename: {f}")
        elif a.cmd == "validate":
            p = find_kb_json(a.library)
            problems = validate(load_json(p))
            for msg in problems:
                print(f"problem: {msg}")
            print("result: " + ("failed" if problems else "ok"))
            if problems:
                sys.exit(3)
    except ConfigError as e:
        log.error("%s", e)
        print(f"error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()
