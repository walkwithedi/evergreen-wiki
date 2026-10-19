#!/usr/bin/env python3
"""Install the evergreen-wiki skills for OpenCode.

Interactive (recommended the first time):
  python3 install.py                          asks a few questions, installs the skills, can set up
                                              a local knowledge base, registers it and tells your
                                              agent it exists; previews everything before writing
Usage:
  python3 install.py --target opencode        ~/.config/opencode/skills
  python3 install.py --target agents          ~/.agents/skills (also read by OpenCode and other agents)
  python3 install.py --target claude-code     ~/.claude/skills (also read by OpenCode)
  python3 install.py --dest /some/skills/dir  any folder
Options: --locale zh (Chinese descriptions), --descriptions FILE (your own descriptions, in the shape of
locales/*/descriptions.json), --link (symlink instead of copy, for development), --force (replace an
existing install), --dry-run, --wizard (interactive even without a terminal); for the wizard, --agent
answers that question in advance. A new library is a work library whose topic pages are built by
the scripts.

Afterwards (details in kb_manage.py):
  python3 install.py backup                   back up the skills, the knowledge-base line and the registry
  python3 install.py rollback                 restore a backup
  python3 install.py move ID --to FOLDER      move a registered local library to another folder
  python3 install.py uninstall                remove what this installer set up; library folders stay
                                              unless you pick them
Replacing skills, a registry or an instructions file backs up the present state first.

OpenCode is the agent this release is tested with; other agents that read Agent Skills from these
folders may work but are not tested. Folder locations change between versions; check the agent's
documentation if a skill does not show up, and use --dest.
"""
import argparse
import json
import logging
import os
import re
import shutil
import sys

import kb_manage

log = logging.getLogger("install")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s"
ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS = ["kb-note", "kb-query", "kb-ingest"]
HOME = os.path.expanduser("~")
TARGETS = {
    # target: (path, verified against OpenCode's documentation); OpenCode reads all three
    "opencode": (os.path.join(HOME, ".config", "opencode", "skills"), True),
    "agents": (os.path.join(HOME, ".agents", "skills"), True),
    "claude-code": (os.path.join(HOME, ".claude", "skills"), True),
}


def remove_any(path):
    if os.path.islink(path) or os.path.isfile(path):
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def install_one(name, dest_root, a, desc):
    """The new copy is made complete next to the old folder first (.NAME.new), then swapped in, so a
    failed copy leaves the installed skill as it was."""
    src = os.path.join(ROOT, "skills", name)
    dest = os.path.join(dest_root, name)
    exists = os.path.lexists(dest)
    if exists and not a.force:
        print(f"skip: {dest} exists (use --force to replace)")
        return False
    action = "link" if a.link else "copy"
    print(f"{action}: skills/{name} -> {dest}")
    if a.dry_run:
        return True
    os.makedirs(dest_root, exist_ok=True)
    new, old = os.path.join(dest_root, f".{name}.new"), os.path.join(dest_root, f".{name}.old")
    remove_any(new)
    remove_any(old)
    try:
        if a.link:
            os.symlink(src, new, target_is_directory=True)
        else:
            shutil.copytree(src, new, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            if desc:
                p = os.path.join(new, "SKILL.md")
                with open(p, encoding="utf-8") as f:
                    text = f.read()
                text = re.sub(r"^description: .*$", lambda m: "description: " + desc[name], text, count=1, flags=re.M)
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
        if exists:
            os.rename(dest, old)
        try:
            os.rename(new, dest)
        except BaseException:
            if exists:
                os.rename(old, dest)
            raise
    except BaseException:
        remove_any(new)
        raise
    remove_any(old)
    return True


# Interactive setup. The questions and defaults are the ones init mode uses
# (skills/kb-ingest/references/init.md); the files come from the same script.

# The skills folders OpenCode reads: its own first, then ~/.agents/skills and ~/.claude/skills, which
# other agents read too.
AGENT_ORDER = ["opencode", "agents", "claude-code"]
AGENT_NAMES = {"opencode": "OpenCode", "agents": "~/.agents/skills (OpenCode and other agents)",
               "claude-code": "~/.claude/skills (OpenCode and Claude Code)"}
AGENT_HOMES = {"opencode": os.path.join(HOME, ".config", "opencode"), "agents": os.path.join(HOME, ".agents"),
               "claude-code": os.path.join(HOME, ".claude")}
# The file the agent always reads, where one line tells it the libraries exist:
# (path, verified against the agent's own documentation). OpenCode reads its own AGENTS.md, and
# CLAUDE.md when it has none.
INSTRUCTION_FILES = {
    "opencode": (os.path.join(HOME, ".config", "opencode", "AGENTS.md"), False),
    "claude-code": (os.path.join(HOME, ".claude", "CLAUDE.md"), True),
}
# Where backup and uninstall look besides the folders this installer recorded.
MANAGE_DEFAULTS = {"skill_dirs": [p for p, _ in TARGETS.values()],
                   "instruction_files": [p for p, _ in INSTRUCTION_FILES.values()]}

MSG = {
    "en": {
        "agent": "Which agent should get the skills?",
        "found": "found on this computer",
        "other": "another folder",
        "folder": "Skills folder",
        "install": "Install kb-note, kb-query and kb-ingest into {dest}?",
        "replace": "{names} already installed there. Replace with this version?",
        "unverified": "note: this folder is not confirmed by the agent's documentation; if the skills do not show up, run again and choose another folder.",
        "registered": "Libraries already registered in {path}:",
        "setup": "Set up a local knowledge base for work material now? Two questions, a preview, nothing is written before you confirm.",
        "q_root": "Question 1 of 2. Folder for the library: where the filed results go, not your original files (new or empty; an Obsidian vault works)",
        "need_root": "Please choose or type the library folder; there is no default.",
        "q_scope": "Question 2 of 2. One sentence: what belongs in this library? The assistant uses it to pick the library for each request.",
        "q_id": "Short id (lowercase letters, digits, hyphens)",
        "id_taken": "The id {id!r} is already registered; using {new!r}. Change it in the preview if you like.",
        "preview": "Preview",
        "items": ["Folder", "Label", "Id", "Scope", "Language", "Timezone"],
        "files": "Files to create",
        "folders": "Folders to create",
        "registry": "Registry entry, added to {path}",
        "confirm": "Press Enter or y to write, a number to change that item, n to cancel",
        "cancelled": "Cancelled. Nothing was written.",
        "written": "Library written to {root} and registered in {path}.",
        "line": "Your agent only consults the knowledge base when it knows one exists. Line for {path} ({what}):",
        "line_added": "added", "line_updated": "updated", "line_unchanged": "already there",
        "line_ok": "Write it?",
        "line_paste": "Add this line to the instructions your agent always reads (AGENTS.md):",
        "skipped_line": "Not written. Add the line above yourself when you are ready.",
        "done": "Done. Restart your agent, then try:",
        "tries": ['"note this: the review meeting moves to Friday"', '"ingest these" with documents attached',
                  '"what did we decide about the pilot?"'],
        "later": "No library set up. To set one up later, run this again or tell your agent: \"get started with the knowledge base\".",
        "bad": "Not valid: {err}",
        "existing": "{root} already holds a library. It can be registered as it is; nothing in the folder changes.",
        "existing_items": ["Folder", "Label", "Id", "Scope"],
        "old_library": "{root} holds a 1.x library. This release does not migrate 1.x libraries: keep using the 1.x release for it, or choose an empty folder for a new library and ingest the material again.",
        "flat_library": "{root} holds a 2.0 or 3.0 library (all sources in one folder). This release reads 4.0 libraries only and does not migrate them: keep using the 3.0 release for it, or choose an empty folder for a new library and ingest the material again.",
        "registered_only": "Library {root} registered in {path} as it is.",
        "upgraded": "Skills upgraded: {skills}.",
        "was": "{name} {new} (was {old})", "new_skill": "{name} {new} (new)",
        "kept": "Libraries unchanged. Restart your agent to use the new skills.",
        "yes": "Y/n", "no": "y/N",
    },
    "zh": {
        "agent": "把技能装到哪个助手？",
        "found": "本机已检测到",
        "other": "其他文件夹",
        "folder": "技能文件夹",
        "install": "把 kb-note、kb-query、kb-ingest 装到 {dest}？",
        "replace": "{names} 已经装在那里。替换为当前版本？",
        "unverified": "提示：该文件夹未经此助手官方文档确认；若技能没有出现，请重新运行并选择其他文件夹。",
        "registered": "{path} 中已登记的知识库：",
        "setup": "现在建一个放工作资料的本地知识库吗？共两个问题，写入前会先给预览，确认后才写。",
        "q_root": "问题 1/2：知识库文件夹放在哪里（放整理好的结果，不是放原始文件的地方；新文件夹或空文件夹；Obsidian 库也可以）",
        "need_root": "请选择或输入知识库文件夹，没有默认位置。",
        "q_scope": "问题 2/2：用一句话说明这个库收什么内容。助手靠这句话判断每次请求该用哪个库。",
        "q_id": "简短 id（小写字母、数字、连字符）",
        "id_taken": "id {id!r} 已被登记，改用 {new!r}；可以在预览里修改。",
        "preview": "预览",
        "items": ["文件夹", "名称", "id", "范围", "语言", "时区"],
        "files": "将创建的文件",
        "folders": "将创建的文件夹",
        "registry": "注册表条目，写入 {path}",
        "confirm": "回车或 y 写入；输入编号修改该项；n 取消",
        "cancelled": "已取消，没有写入任何内容。",
        "written": "知识库已写入 {root}，并登记到 {path}。",
        "line": "助手只有知道你有知识库时才会去查。要写入 {path} 的一行（{what}）：",
        "line_added": "新增", "line_updated": "更新已有的一行", "line_unchanged": "已存在，无需改动",
        "line_ok": "写入吗？",
        "line_paste": "请把这一行加到助手每次都会读的指令文件里（AGENTS.md）：",
        "skipped_line": "未写入。准备好后请自行添加上面这一行。",
        "done": "完成。重启助手后可以试试：",
        "tries": ["「记一下：评审会改到周五」", "附上文档说「入库」", "「试点的事最后怎么定的？」"],
        "later": "暂未建库。以后要建库，重新运行本向导，或对助手说「开始使用知识库」。",
        "bad": "无效：{err}",
        "existing": "{root} 里已经有知识库，可以按原样登记，不改动文件夹里的任何文件。",
        "existing_items": ["文件夹", "名称", "id", "范围"],
        "old_library": "{root} 里是 1.x 的知识库。本版本不迁移 1.x 的库：这个库可以继续用已发布的 1.x 版本，或另选一个空文件夹新建知识库，再把材料重新入库。",
        "flat_library": "{root} 里是 2.0 或 3.0 的知识库（来源都在一个文件夹里）。本版本只读 4.0 的库，不迁移旧库：这个库可以继续用 3.0 版本，或另选一个空文件夹新建知识库，再把材料重新入库。",
        "registered_only": "已把 {root} 按原样登记到 {path}。",
        "upgraded": "技能已升级：{skills}。",
        "was": "{name} {new}（原 {old}）", "new_skill": "{name} {new}（新装）",
        "kept": "知识库不变。重启助手后用上新技能。",
        "yes": "Y/n", "no": "y/N",
    },
}


class Asker:
    """Reads answers from stdin; works with a terminal and with piped input (tests).
    tools/kb-client answers the same three methods from a page in the browser."""

    def __init__(self, lang="en"):
        self.m = MSG[lang]

    def ask(self, prompt, default="", kind=None):
        """kind="folder" marks a folder path; a dialog asker shows a folder chooser for it."""
        shown = f"{prompt} [{default}]: " if default else f"{prompt}: "
        try:
            ans = input(shown)
        except EOFError:
            print()
            raise KeyboardInterrupt
        return ans.strip() or default

    def yes(self, prompt, default=True):
        ans = self.ask(f"{prompt} ({self.m['yes'] if default else self.m['no']})").lower()
        if not ans:
            return default
        return ans[0] in ("y", "是", "好")

    def choose(self, prompt, options, default):
        """options: [(value, text)]; answer with the number or the value."""
        print(prompt)
        for i, (_, text) in enumerate(options, 1):
            print(f"  {i}. {text}")
        values = [v for v, _ in options]
        while True:
            ans = self.ask(">", str(values.index(default) + 1))
            if ans.isdigit() and 1 <= int(ans) <= len(options):
                return values[int(ans) - 1]
            if ans in values:
                return ans


def choose_dest(q, m, agent=None, agent_default=None):
    if agent:
        if not TARGETS[agent][1]:
            print(m["unverified"])
        return agent, TARGETS[agent][0]
    found = [t for t in AGENT_ORDER if os.path.isdir(AGENT_HOMES[t])]
    default = agent_default if agent_default in AGENT_ORDER else "opencode"
    opts = [(t, f"{AGENT_NAMES[t]}  ({TARGETS[t][0]}){'  - ' + m['found'] if t in found else ''}")
            for t in AGENT_ORDER]
    opts.append(("other", m["other"]))
    target = q.choose(m["agent"], opts, default)
    if target == "other":
        return None, os.path.abspath(os.path.expanduser(q.ask(m["folder"], kind="folder")))
    if not TARGETS[target][1]:
        print(m["unverified"])
    return target, TARGETS[target][0]


def load_descriptions(path):
    """A descriptions file: {"kb-note": "...", ...}, one line each, the shape of locales/*/descriptions.json."""
    with open(os.path.expanduser(path), encoding="utf-8") as f:
        desc = json.load(f)
    bad = [n for n in SKILLS if not (isinstance(desc, dict) and isinstance(desc.get(n), str) and desc[n].strip()
                                     and "\n" not in desc[n] and len(desc[n]) <= 1024)]
    if bad:
        raise ValueError(f"{path}: needs one line of at most 1024 characters for {', '.join(bad)}")
    return desc


def skill_descriptions(lang, descriptions=None):
    """The descriptions the wizard writes into SKILL.md: the file given, else the language's own (none
    for English, whose descriptions are in the skills)."""
    if descriptions:
        return load_descriptions(descriptions)
    if lang != "en":
        with open(os.path.join(ROOT, "locales", lang, "descriptions.json"), encoding="utf-8") as f:
            return json.load(f)
    return None


def install_skills(q, m, target, dest_root, lang, descriptions=None):
    if not q.yes(m["install"].format(dest=dest_root)):
        return
    present = [n for n in SKILLS if os.path.lexists(os.path.join(dest_root, n))]
    force = bool(present) and q.yes(m["replace"].format(names=", ".join(present)))
    if force:
        kb_manage.backup_once(MANAGE_DEFAULTS, "before installing skills", lang, [dest_root])
    opts = argparse.Namespace(force=force, dry_run=False, link=False)
    desc = skill_descriptions(lang, descriptions)
    done = sum(install_one(n, dest_root, opts, desc) for n in SKILLS)
    kb_manage.record(skills_dir=dest_root)
    print(f"installed {done} of {len(SKILLS)} skills in {dest_root}")


def confirm(q, m, items, can_write=True):
    """The answer to a preview: "" or y to write, n to cancel, or the number of the item to change. An
    asker with its own confirm (tools/kb-client) offers these as choices; a terminal types them."""
    if hasattr(q, "confirm"):
        return q.confirm(m["confirm"], items, can_write)
    return q.ask(m["confirm"]).strip().lower()


def free_id(base, taken):
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def ask_root(q, m, il, default):
    """Returns (folder, True when it already holds a library)."""
    while True:
        answer = q.ask(m["q_root"], default, kind="folder").strip()
        if not answer:
            print(m["need_root"])
            continue
        root = os.path.abspath(os.path.expanduser(answer))
        if kb_manage.is_protected(root, MANAGE_DEFAULTS):
            lang = next(k for k, v in MSG.items() if v is m)
            print(m["bad"].format(err=f"{root}: {kb_manage.MSG[lang]['protected']}"))
            continue
        if os.path.isdir(root) and kb_manage.is_library(root):
            schema = library_schema(il, root)
            if schema in (1, 2):
                key = "old_library" if schema == 1 else "flat_library"
                print(m["bad"].format(err=m[key].format(root=root)))
                continue
            return root, True
        try:
            il.check_root(root)
            return root, False
        except il.Refused as e:
            print(m["bad"].format(err=e))


def library_schema(il, root):
    try:
        return il.kbconf.load_json(os.path.join(root, il.kbconf.KB_JSON)).get("schema")
    except (OSError, ValueError, AttributeError, il.kbconf.ConfigError):
        return None


def register_existing(q, m, il, lang, reg_path, root, s):
    """Registers a folder that already holds a library, as it is. Returns the registry, None when
    cancelled, or "again" to choose another folder."""
    try:
        label = il.kbconf.load_json(os.path.join(root, il.kbconf.KB_JSON)).get("label")
    except (OSError, ValueError, il.kbconf.ConfigError):
        label = None
    s["label"] = label if isinstance(label, str) and label.strip() else os.path.basename(root)
    print(m["existing"].format(root=root))
    while True:
        values = [root, s["label"], s["id"], s["scope"]]
        try:
            entry = il.registry_entry(s["id"], s["label"], s["scope"], "local", root)
            il.add_to_registry(reg_path, entry, lang, dry_run=True)
            print(f"\n{m['preview']}")
            for i, (k, v) in enumerate(zip(m["existing_items"], values), 1):
                print(f"  {i}. {k}: {v}")
            print(m["registry"].format(path=reg_path))
            print("  " + json.dumps(entry, ensure_ascii=False))
            ok = True
        except (il.Refused, il.kbconf.ConfigError) as e:
            print(m["bad"].format(err=e))
            ok = False
        ans = confirm(q, m, m["existing_items"], ok)
        if ok and ans in ("", "y", "yes", "是"):
            break
        if ans.startswith("n"):
            print(m["cancelled"])
            return None
        if ans == "1":
            return "again"
        if ans.isdigit() and 2 <= int(ans) <= 4:
            key = ["label", "id", "scope"][int(ans) - 2]
            s[key] = q.ask(m["existing_items"][int(ans) - 1], s[key])
    kb_manage.backup_once(MANAGE_DEFAULTS, "before registering a library", lang)
    reg = il.add_to_registry(reg_path, entry, lang)
    print(m["registered_only"].format(root=root, path=reg_path))
    return reg


def library_settings(il, s):
    """Validate through the same code the skill uses; returns the completed settings."""
    ns = argparse.Namespace(preset=s["preset"], label=s["label"], id=s["id"], scope=s["scope"],
                            language=s["language"], timezone=s["timezone"], date=None)
    return il.settings(ns)


def show_preview(m, il, s, root, reg_path, entry):
    files, folders = il.build_files(s)
    values = [root, s["label"], s["id"], s["scope"], s["language"], s["timezone"]]
    print(f"\n{m['preview']}")
    for i, (k, v) in enumerate(zip(m["items"], values), 1):
        print(f"  {i}. {k}: {v}")
    print(f"{m['files']}: " + ", ".join(p for p, _ in files))
    print(f"{m['folders']}: " + ", ".join(folders))
    print(m["registry"].format(path=reg_path))
    print("  " + json.dumps(entry, ensure_ascii=False))


def edit_item(q, m, il, s, root, n):
    item = m["items"][n - 1]
    if n == 1:
        while True:
            new, existing = ask_root(q, m, il, root)
            if not existing:
                return new
            print(m["bad"].format(err=m["existing"].format(root=new)))
    key = ["", "label", "id", "scope", "language", "timezone"][n - 1]
    s[key] = q.ask(item, s[key])
    return root


def setup_library(q, m, il, lang):
    reg_path = il.registry_path()
    reg = il.load_registry_or_new(reg_path, lang)
    taken = [lib.get("id") for lib in reg.get("libraries", [])]
    if taken:
        print(m["registered"].format(path=reg_path))
        for lib in reg["libraries"]:
            print(f"  {lib.get('id')}: {lib.get('label')} - {lib.get('scope')}")
    if not q.yes(m["setup"]):
        return None
    s = il.defaults("work", lang)
    new_id = free_id(s["id"], taken)
    if new_id != s["id"]:
        print(m["id_taken"].format(id=s["id"], new=new_id))
        s["id"] = new_id
    root = ""  # no default: the user chooses the library folder
    while True:
        root, existing = ask_root(q, m, il, root)
        if not existing:
            break
        done = register_existing(q, m, il, lang, reg_path, root, dict(s))
        if done != "again":
            return done
    s["scope"] = q.ask(m["q_scope"], s["scope"])
    while True:
        try:
            s = library_settings(il, s)
            entry = il.registry_entry(s["id"], s["label"], s["scope"], "local", root)
            il.add_to_registry(reg_path, entry, lang, dry_run=True)
            show_preview(m, il, s, root, reg_path, entry)
        except (il.Refused, il.kbconf.ConfigError) as e:
            print(m["bad"].format(err=e))
            ans = confirm(q, m, m["items"], False)
            if ans.startswith("n"):
                print(m["cancelled"])
                return None
            if ans.isdigit() and 1 <= int(ans) <= len(m["items"]):
                root = edit_item(q, m, il, s, root, int(ans))
            continue
        ans = confirm(q, m, m["items"])
        if ans in ("", "y", "yes", "是"):
            break
        if ans.startswith("n"):
            print(m["cancelled"])
            return None
        if ans.isdigit() and 1 <= int(ans) <= len(m["items"]):
            root = edit_item(q, m, il, s, root, int(ans))
    kb_manage.backup_once(MANAGE_DEFAULTS, "before setting up a library", lang)
    il.create_library(root, s)
    reg = il.add_to_registry(reg_path, entry, lang)
    print(m["written"].format(root=root, path=reg_path))
    return reg


def add_instructions_line(q, m, il, target, reg, lang):
    path, verified = INSTRUCTION_FILES.get(target, (None, False))
    write_line(q, m, il, path, verified, reg, lang)


def write_line(q, m, il, path, verified, reg, lang):
    """Shows the knowledge-base line for the instructions file at path and writes it after a question;
    asks nothing when the file already has it. Without a path the line is shown to be pasted."""
    line = il.instructions_line(reg, lang)
    if not path:
        print(m["line_paste"])
        print("  " + line)
        return
    what = il.update_instructions_file(path, line, dry_run=True)
    print(m["line"].format(path=path, what=m["line_" + what]))
    print("  " + line)
    if not verified:
        print(m["unverified"])
    if what == "unchanged":
        return
    if q.yes(m["line_ok"]):
        kb_manage.backup_once(MANAGE_DEFAULTS, "before writing the knowledge-base line", lang)
        il.update_instructions_file(path, line)
        kb_manage.record(instructions=path)
    else:
        print(m["skipped_line"])


def skill_version(folder):
    """The Version: line of a skill folder's SKILL.md, or ""."""
    try:
        with open(os.path.join(folder, "SKILL.md"), encoding="utf-8", errors="replace") as f:
            m = re.search(r"^Version:\s*(\S+)", f.read(200000), re.M)
    except OSError:
        return ""
    return m.group(1) if m else ""


def usable_library(reg):
    """True when the registry names a library that can be used: a local one whose folder is there, or
    one that is not a local folder (it cannot be checked from here)."""
    for lib in reg.get("libraries", []):
        backend = lib.get("backend") or {}
        if backend.get("type", "local") != "local":
            return True
        root = backend.get("root")
        if root and os.path.isdir(os.path.expanduser(root)):
            return True
    return False


def upgrade(asker=Asker, lang="en", places=None, default_root=None, instructions=None, descriptions=None):
    """Replaces the knowledge-base skills with this release, asking nothing about where or whether.
    places maps a skill to the skills folder its copy in effect is in; a skill without one goes to
    default_root. The present state is backed up first. With a usable library the libraries stay as they
    are and only the knowledge-base line in instructions (a file path, or None to show it) is refreshed,
    after a question when it changes; without one the library questions of the wizard follow."""
    sys.path.insert(0, os.path.join(ROOT, "skills", "kb-ingest", "scripts"))
    import init_library as il
    q = asker(lang)
    m = MSG[lang]
    del kb_manage._auto[:]  # one backup per upgrade, also when a client runs several
    places = places or {}
    roots = {n: places.get(n) or default_root or TARGETS["agents"][0] for n in SKILLS}
    olds = {n: skill_version(os.path.join(roots[n], n)) for n in SKILLS}
    dirs = list(dict.fromkeys(roots[n] for n in SKILLS))
    desc = skill_descriptions(lang, descriptions)  # a bad descriptions file stops before anything is written
    kb_manage.backup_once(MANAGE_DEFAULTS, "before upgrading skills", lang, dirs)
    opts = argparse.Namespace(force=True, dry_run=False, link=False)
    for n in SKILLS:
        install_one(n, roots[n], opts, desc)
    for d in dirs:
        kb_manage.record(skills_dir=d)
    done = [m["was" if olds[n] else "new_skill"].format(name=n, new=skill_version(os.path.join(roots[n], n)),
                                                       old=olds[n]) for n in SKILLS]
    print(m["upgraded"].format(skills=", ".join(done) if lang == "en" else "、".join(done)))
    verified = next((v for p, v in INSTRUCTION_FILES.values() if p == instructions), True)
    reg = il.load_registry_or_new(il.registry_path(), lang)
    if usable_library(reg):
        write_line(q, m, il, instructions, verified, reg, lang)
        print(m["kept"])
        return
    reg = setup_library(q, m, il, lang)
    if reg is None:
        print(m["later"])
        return
    write_line(q, m, il, instructions, verified, reg, lang)
    print("\n" + m["done"])
    for t in m["tries"]:
        print("  " + t)


def wizard(asker=Asker, lang=None, agent=None, descriptions=None, agent_default=None):
    """asker(lang) returns the object that asks the questions. lang and agent (a --target name) answer
    those questions in advance; descriptions is a file that replaces the skill descriptions; agent_default
    is the agent (a --target name) chosen beforehand when that question is asked."""
    sys.path.insert(0, os.path.join(ROOT, "skills", "kb-ingest", "scripts"))
    import init_library as il
    il.kbconf.utf8_stdio()
    try:
        lang = lang or asker("en").choose("Language / 语言", [("zh", "中文"), ("en", "English")],
                                          il.detect_language())
    except KeyboardInterrupt:
        sys.exit(1)
    q = asker(lang)
    m = MSG[lang]
    try:
        target, dest_root = choose_dest(q, m, agent, agent_default)
        install_skills(q, m, target, dest_root, lang, descriptions)
        reg = setup_library(q, m, il, lang)
        if reg is None:
            print(m["later"])
            return
        add_instructions_line(q, m, il, target, reg, lang)
        print("\n" + m["done"])
        for t in m["tries"]:
            print("  " + t)
    except KeyboardInterrupt:
        print("\n" + m["cancelled"])
        sys.exit(1)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in kb_manage.COMMANDS:
        sys.exit(kb_manage.main(sys.argv[1:], Asker, MANAGE_DEFAULTS))
    ap = argparse.ArgumentParser(description="Install evergreen-wiki skills",
                                 epilog="Also: install.py {backup,rollback,move,uninstall} -h")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--target", choices=sorted(TARGETS))
    g.add_argument("--dest")
    g.add_argument("--wizard", action="store_true", help="interactive setup (the default in a terminal)")
    ap.add_argument("--locale")
    ap.add_argument("--descriptions", metavar="FILE",
                    help="skill descriptions to use instead of the built-in ones (shape of locales/*/descriptions.json)")
    ap.add_argument("--agent", choices=sorted(TARGETS), help="wizard: the agent, instead of asking")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    a = ap.parse_args()
    logging.basicConfig(level=a.log_level, format=LOG_FORMAT, stream=sys.stderr)
    if a.descriptions:
        if a.locale or a.link:
            ap.error("--descriptions rewrites SKILL.md and cannot be combined with --locale or --link")
        try:
            load_descriptions(a.descriptions)
        except (OSError, ValueError) as e:
            ap.error(str(e))
    if a.wizard or not (a.target or a.dest):
        # Both ends must be a terminal.
        if not a.wizard and not (sys.stdin.isatty() and sys.stdout.isatty()):
            ap.error("give --target or --dest, or run without options in a terminal for interactive setup")
        if a.locale or a.link or a.force or a.dry_run:
            ap.error("--locale, --link, --force and --dry-run go with --target or --dest; the wizard asks instead")
        return wizard(agent=a.agent, descriptions=a.descriptions)
    if a.agent:
        ap.error("--agent answers a wizard question; use --target or --dest without the wizard")
    if a.link and a.locale:
        ap.error("--locale rewrites SKILL.md and cannot be combined with --link")
    if a.dest:
        dest_root = os.path.abspath(os.path.expanduser(a.dest))
    else:
        dest_root, verified = TARGETS[a.target]
        if not verified:
            print(f"note: the {a.target} skills folder ({dest_root}) is not confirmed by its official "
                  "documentation; if the skills do not show up, try --target opencode or --dest.")
    desc = load_descriptions(a.descriptions) if a.descriptions else None
    if a.locale:
        with open(os.path.join(ROOT, "locales", a.locale, "descriptions.json"), encoding="utf-8") as f:
            desc = json.load(f)
    if a.force and not a.dry_run and any(os.path.lexists(os.path.join(dest_root, n)) for n in SKILLS):
        kb_manage.backup_once(MANAGE_DEFAULTS, "before installing skills",
                              "zh" if (a.locale or "").startswith("zh") else "en", [dest_root])
    done = sum(install_one(n, dest_root, a, desc) for n in SKILLS)
    if not a.dry_run:
        kb_manage.record(skills_dir=dest_root)
    print(f"{'would install' if a.dry_run else 'installed'} {done} of {len(SKILLS)} skills in {dest_root}")
    if done:
        print("next: restart your agent and say \"get started with the knowledge base\", "
              "or run python3 install.py without options for guided setup.")


if __name__ == "__main__":
    main()
