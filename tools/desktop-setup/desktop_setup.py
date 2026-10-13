#!/usr/bin/env python3
"""Knowledge base setup in dialogs: the evergreen-wiki installer and its backup, rollback, move and
uninstall commands for people who do not use a terminal.

  python3 desktop_setup.py                 a menu: set up (skills, a library, the knowledge-base line),
                                           back up, roll back, move a library, uninstall
Options: --ui zenity|tty (default: dialogs when zenity and a graphical session are there, else
questions in the terminal; EVERGREEN_SETUP_UI sets the same), --lang en|zh, --log-level; for set up,
--agent and --preset life|work answer those questions in advance and --descriptions FILE replaces the
skill descriptions (as install.py).

The questions, previews and checks are the ones of install.py and kb_manage.py: this file only puts
dialogs behind the same ask, yes and choose calls. What those print is collected and shown in the next
dialog, so every preview is seen before its question. Python 3 standard library only.
"""
import argparse
import html
import io
import logging
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import install  # noqa: E402
import kb_manage  # noqa: E402

log = logging.getLogger("desktop_setup")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
LONG_TEXT = 12  # lines; longer output gets its own scrollable dialog before the question

MSG = {
    "en": {
        "title": "Knowledge base setup",
        "menu": "What would you like to do?",
        "setup": "Set up: install the skills, set up a library, tell your agent (also adds a library later)",
        "backup": "Back up the installed skills, the knowledge-base line and the registry",
        "rollback": "Roll back to a backup",
        "move": "Move a library to another folder",
        "uninstall": "Uninstall",
        "quit": "Quit",
        "move_pick": "Which library should be moved?",
        "move_none": "No registered library on this computer can be moved.",
        "move_to": "Choose the folder to move the library into. The library keeps its folder name.",
        "pick_folder": "Choose the folder in the next window.",
        "keep_folder": "Now: {path}. Choose another folder in the next window, or cancel there to keep it.",
        "done": "Finished.",
        "yes": "Yes", "no": "No",
        "no_zenity": "zenity was not found or there is no graphical session; asking in the terminal instead.",
    },
    "zh": {
        "title": "知识库设置",
        "menu": "要做什么？",
        "setup": "安装与建库：装技能、建知识库、告诉助手（以后再加一个库也选这项）",
        "backup": "备份已装的技能、知识库说明行和注册表",
        "rollback": "回滚到某次备份",
        "move": "把知识库移到别的文件夹",
        "uninstall": "卸载",
        "quit": "退出",
        "move_pick": "移动哪个知识库？",
        "move_none": "本机没有可以移动的已登记知识库。",
        "move_to": "选择要把知识库移到哪个文件夹里，库文件夹名不变。",
        "pick_folder": "请在下一个窗口里选择文件夹。",
        "keep_folder": "当前：{path}。在下一个窗口里另选文件夹，或在那里取消以保留当前文件夹。",
        "done": "已完成。",
        "yes": "是", "no": "否",
        "no_zenity": "没有找到 zenity 或不在图形桌面中，改为在终端里问答。",
    },
}


class Capture(io.TextIOBase):
    """Stands in for stdout: passes everything to the terminal and keeps it for the next dialog."""

    def __init__(self, real):
        super().__init__()
        self.real = real
        self.parts = []

    def write(self, s):
        self.real.write(s)
        self.parts.append(s)
        return len(s)

    def flush(self):
        self.real.flush()

    def take(self):
        text = "".join(self.parts).strip("\n")
        self.parts = []
        return text


class Dialogs:
    """The ask, yes and choose of install.Asker as zenity dialogs. Calling the object with a language
    returns it in that language, so it serves as the asker factory install.py and kb_manage.py take.
    Cancelling a dialog raises KeyboardInterrupt, which both treat as "cancelled"."""

    def __init__(self, capture, lang, zenity="zenity"):
        self.capture = capture
        self.zenity = zenity
        self(lang)

    def __call__(self, lang):
        self.lang = lang
        self.m = MSG[lang]
        return self

    def run(self, *args, stdin=None):
        p = subprocess.run([self.zenity, "--title=" + self.m["title"], *args], input=stdin,
                           capture_output=True, text=True)
        log.debug("zenity %s -> %s", args[0], p.returncode)
        return p.returncode, p.stdout.rstrip("\n")

    def show(self, text):
        if not text:
            return
        if text.count("\n") >= LONG_TEXT:
            self.run("--text-info", "--width=720", "--height=520", stdin=text)
        else:
            self.run("--info", "--no-markup", "--width=560", "--text=" + text)

    def text(self, prompt):
        """The question with whatever was printed since the last dialog above it."""
        pending = self.capture.take()
        if pending.count("\n") >= LONG_TEXT:
            self.show(pending)
            pending = ""
        return f"{pending}\n\n{prompt}" if pending else prompt

    def ask(self, prompt, default="", kind=None):
        if kind == "folder":
            return self.folder(prompt, default)
        rc, out = self.run("--entry", "--width=560", "--text=" + html.escape(self.text(prompt), quote=False),
                           "--entry-text=" + default)
        if rc != 0:
            raise KeyboardInterrupt
        return out.strip() or default

    def yes(self, prompt, default=True):
        args = ["--question", "--no-markup", "--width=560", "--text=" + self.text(prompt),
                "--ok-label=" + self.m["yes"], "--cancel-label=" + self.m["no"]]
        if not default:
            args.append("--default-cancel")
        return self.run(*args)[0] == 0

    def choose(self, prompt, options, default):
        rows = []
        for value, label in options:
            rows += ["TRUE" if value == default else "FALSE", value, label]
        rc, out = self.run("--list", "--radiolist", "--width=720", f"--height={220 + 36 * len(options)}",
                           "--text=" + html.escape(self.text(prompt), quote=False), "--column=", "--column=key",
                           "--column=" + self.m["title"], "--hide-column=2", "--print-column=2", *rows)
        if rc != 0:
            raise KeyboardInterrupt
        return out.split("|")[0] or default

    def folder(self, prompt, default):
        """A folder chooser, never a suggested folder. The question is shown first; the chooser opens in
        the home folder, or in the current answer when one is being changed (cancelling keeps it)."""
        note = self.m["keep_folder"].format(path=default) if default else self.m["pick_folder"]
        self.run("--info", "--no-markup", "--width=560", "--text=" + f"{self.text(prompt)}\n\n{note}")
        start = os.path.abspath(os.path.expanduser(default or "~"))
        while not os.path.isdir(start) and os.path.dirname(start) != start:
            start = os.path.dirname(start)
        rc, out = self.run("--file-selection", "--directory", "--filename=" + os.path.join(start, ""))
        if rc == 0 and out:
            return out.rstrip(os.sep) or os.sep
        if default:
            return default
        raise KeyboardInterrupt


def pick_ui(wanted, m):
    has_zenity = bool(shutil.which("zenity")) and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if wanted == "tty" or (wanted is None and not has_zenity):
        return "tty"
    if not shutil.which("zenity"):
        print(m["no_zenity"], file=sys.stderr)
        return "tty"
    return "zenity"


def move(q, m, asker, lang):
    libs = [(i, label, root) for i, label, root in kb_manage.registered_libs()
            if kb_manage.lib_check(root, install.MANAGE_DEFAULTS) is None]
    if not libs:
        print(m["move_none"])
        return
    lib_id = q.choose(m["move_pick"], [(i, f"{label}  {root}") for i, label, root in libs], libs[0][0])
    parent = q.ask(m["move_to"], kind="folder")
    kb_manage.main(["move", lib_id, "--to", parent, "--lang", lang], asker, install.MANAGE_DEFAULTS)


def run_action(action, q, m, asker, lang, a):
    if action == "setup":
        try:
            install.wizard(asker, lang, a.agent, a.preset, a.descriptions)
        except SystemExit:  # the wizard exits after printing why
            log.info("setup ended early")
    elif action == "move":
        move(q, m, asker, lang)
    else:
        kb_manage.main([action, "--lang", lang], asker, install.MANAGE_DEFAULTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ui", choices=["zenity", "tty"], default=os.environ.get("EVERGREEN_SETUP_UI") or None)
    ap.add_argument("--lang", choices=sorted(MSG))
    ap.add_argument("--agent", choices=sorted(install.TARGETS))
    ap.add_argument("--preset", choices=["life", "work"])
    ap.add_argument("--descriptions", metavar="FILE")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    if a.descriptions:
        try:
            install.load_descriptions(a.descriptions)
        except (OSError, ValueError) as e:
            ap.error(str(e))
    il = kb_manage.init_library()
    il.kbconf.utf8_stdio()
    lang = a.lang or il.detect_language()
    m = MSG[lang]
    capture = None
    if pick_ui(a.ui, m) == "zenity":
        capture = Capture(sys.stdout)
        sys.stdout = capture
        asker = Dialogs(capture, lang)
    else:
        asker = install.Asker
    q = asker(lang)
    actions = ["setup", "backup", "rollback", "move", "uninstall", "quit"]
    while True:
        try:
            action = q.choose(m["menu"], [(x, m[x]) for x in actions], "setup")
        except KeyboardInterrupt:
            break
        if action == "quit":
            break
        try:
            run_action(action, q, m, asker, lang, a)
        except KeyboardInterrupt:
            print(install.MSG[lang]["cancelled"])
        if capture:
            asker.show(capture.take() or m["done"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
