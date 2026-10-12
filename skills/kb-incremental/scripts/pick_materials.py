#!/usr/bin/env python3
"""Let the user pick intake material or a library folder in a desktop dialog (local libraries).

Material (default): used when the user asks for intake without naming a path or uploading
files. A first dialog asks whether to pick a folder or files; the second is the matching
file chooser (files: several at once). With --library-root it opens in the material folder
next to the library (<library>-待整理 or <library>-inbox) when one exists.
Library (--library): used when no library is registered or a new library needs a place. One
folder chooser; the assistant then checks the folder and goes on with init mode.
The dialogs come from zenity and need a graphical session.

stdout: one chosen path per line (a folder, or each file).
Exit codes:
  0  paths printed
  3  no dialog possible (no graphical session or no zenity): ask the user for the path
  4  the user cancelled: ask whether to go on, and for the path if so
  5  no answer within --timeout seconds: ask the user for the path
stderr: log lines.
Usage: python3 pick_materials.py [--library | --library-root DIR] [--start DIR] [--timeout 100]
                                 [--language en|zh]
Keep --timeout below the agent's limit for a shell command.
"""
import argparse
import logging
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kbconf  # noqa: E402

log = logging.getLogger("pick_materials")
NO_DIALOG, CANCELLED, TIMED_OUT = 3, 4, 5
ZENITY_TIMEOUT = 5  # zenity's exit code when --timeout runs out
TEXT = {
    "en": {"title": "Choose material for the knowledge base", "ask": "What do you want to file?",
           "col": "Choice", "folder": "A folder (everything in it)", "files": "Files (select several with Ctrl)",
           "library": "Choose the knowledge base folder (an existing library, or an empty folder for a new one)"},
    "zh": {"title": "选择要入库的材料", "ask": "要入库的是什么？",
           "col": "选项", "folder": "一个文件夹（其中的全部文件）", "files": "文件（按住 Ctrl 可多选）",
           "library": "选择知识库文件夹（已有的库，或用来新建库的空文件夹）"},
}
# material folders kept next to a library, tried in this order
MATERIAL_SUFFIXES = ("-待整理", "-inbox")


def language(arg):
    if arg:
        return "zh" if arg.lower().startswith("zh") else "en"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        v = os.environ.get(var)
        if v:
            return "zh" if v.lower().startswith("zh") else "en"
    return "en"


def dialog_possible():
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        log.info("no graphical session (DISPLAY and WAYLAND_DISPLAY unset)")
        return False
    if not shutil.which("zenity"):
        log.info("zenity not found")
        return False
    return True


def zenity(args, timeout):
    """Run one zenity dialog; returns (exit code, stdout)."""
    cmd = ["zenity", "--timeout", str(timeout)] + args
    log.debug("run %s", cmd)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)
    return p.returncode, p.stdout


def material_start(library_root):
    """The material folder next to a library, if one exists."""
    root = os.path.abspath(os.path.expanduser(library_root)).rstrip(os.sep)
    for suffix in MATERIAL_SUFFIXES:
        if os.path.isdir(root + suffix):
            return root + suffix
    return None


def choose_folder(start, title, timeout):
    rc, out = zenity(["--file-selection", "--directory", "--title", title,
                      "--filename", os.path.join(start, "")], timeout)
    if rc == ZENITY_TIMEOUT:
        return TIMED_OUT, []
    if rc != 0:
        return CANCELLED, []
    paths = [p for p in out.splitlines() if p.strip()][:1]
    return (0, paths) if paths else (CANCELLED, [])


def pick(start, timeout, lang):
    t = TEXT[lang]
    rc, out = zenity(["--list", "--radiolist", "--title", t["title"], "--text", t["ask"],
                      "--column", t["col"], "--column", "key", "--column", t["title"],
                      "--hide-column", "2", "--print-column", "2", "--hide-header",
                      "TRUE", "folder", t["folder"], "FALSE", "files", t["files"]], timeout)
    if rc == ZENITY_TIMEOUT:
        return TIMED_OUT, []
    if rc != 0:
        return CANCELLED, []
    kind = out.strip().split("|")[0] or "folder"
    args = ["--file-selection", "--title", t["title"], "--filename", os.path.join(start, "")]
    if kind == "folder":
        args.append("--directory")
    else:
        args += ["--multiple", "--separator", "\n"]
    rc, out = zenity(args, timeout)
    if rc == ZENITY_TIMEOUT:
        return TIMED_OUT, []
    if rc != 0:
        return CANCELLED, []
    paths = [p for p in out.splitlines() if p.strip()]
    return (0, paths) if paths else (CANCELLED, [])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--library", action="store_true", help="choose a library folder instead of material")
    mode.add_argument("--library-root", help="the library being filled: open in the material folder next to it")
    ap.add_argument("--start", help="folder the chooser opens in (default: home)")
    ap.add_argument("--timeout", type=int, default=100, help="seconds to wait for each dialog (default 100)")
    ap.add_argument("--language", help="en or zh (default: from the locale)")
    kbconf.add_log_args(ap)
    a = ap.parse_args()
    kbconf.setup_logging(a.log_level)
    if not dialog_possible():
        return NO_DIALOG
    start = a.start or (a.library_root and material_start(a.library_root)) or "~"
    start = os.path.abspath(os.path.expanduser(start))
    timeout, lang = max(1, a.timeout), language(a.language)
    if a.library:
        rc, paths = choose_folder(start, TEXT[lang]["library"], timeout)
    else:
        rc, paths = pick(start, timeout, lang)
    for p in paths:
        print(p)
    log.info("result %d, %d path(s)", rc, len(paths))
    return rc


if __name__ == "__main__":
    sys.exit(main())
