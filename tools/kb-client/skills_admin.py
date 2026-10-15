#!/usr/bin/env python3
"""The skills OpenCode can use, for the client's Skills section: list them with what they do, and manage
them.

The three knowledge-base skills (kb_manage.SKILLS) are listed first, with their version; besides the
steps below they are upgraded by Set up with a newer release, which replaces their folders (a local
change then survives only in its backup). Every skill can be backed up before the assistant edits it,
restored from such a backup, imported from a folder or a zip file, or started from a template. Nothing
in a skill is ever run here.

Backups live in <state dir>/skill-backups/<skill>/<YYYYMMDD-HHMMSS>/, outside every skills folder.
Python 3 standard library only.
"""
import logging
import os
import re
import shutil
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import install  # noqa: E402
import kb_manage  # noqa: E402

log = logging.getLogger("skills_admin")

# The skills folders OpenCode reads, in the order it prefers them: its own, then its Claude Code and
# .agents compatibility. A skill name found in more than one is used from the first.
OPENCODE_ORDER = ("opencode", "claude-code", "agents")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
QUOTED_RE = re.compile(r'"([^"\n]{1,60})"|「([^」\n]{1,30})」')
MAX_IMPORT_BYTES = 20 * 1024 * 1024
MAX_IMPORT_FILES = 500

MSG = {
    "en": {
        "not_found": "No skill named {name} in the folders OpenCode reads.",
        "backed_up": "Backed up {name} to {path}",
        "no_backups": "{name} has no backup yet.",
        "pick_backup": "Restore {name} from which backup?",
        "restore_confirm": "Replace {folder} with the backup of {when}? The current version is backed up first.",
        "restored": "Restored {name} from the backup of {when}.",
        "source_kind": "Import a skill from",
        "from_folder": "A folder that holds SKILL.md",
        "from_zip": "A zip file",
        "pick_folder": "Choose the skill's folder.",
        "zip_path": "Full path of the zip file:",
        "preview": "Skill: {name}\nWhat it does: {desc}\nFiles: {n} ({size} KB)\nInstalled to: {dest}",
        "import_confirm": "Import this skill? Nothing in it is run.",
        "imported": "Imported {name} into {dest}. Start a new conversation to use it.",
        "new_name": "Name of the new skill (lowercase letters, digits and hyphens, such as weekly-report):",
        "new_purpose": "In one sentence, what should it do and when should it be used?",
        "new_confirm": "Create {path} with a SKILL.md to fill in?",
        "created": "Created {path}. The request to fill it in is in the box below the conversation.",
        "bad_name": "The name must be lowercase letters, digits and hyphens, at most 64 characters.",
        "taken": "A skill named {name} exists already ({folder}); nothing is overwritten.",
        "kb_name": "{name} is the name of a knowledge-base skill.",
        "no_skill_md": "There is no SKILL.md at the top of it (or in its only folder).",
        "bad_zip": "The zip cannot be read: {e}",
        "unsafe": "The zip holds a path outside its own folder: {p}",
        "too_big": "Too large: at most {files} files and {mb} MB.",
        "no_front": "SKILL.md does not start with name and description front matter.",
        "cancelled": "Cancelled; nothing changed.",
    },
    "zh": {
        "not_found": "OpenCode 能读到的技能文件夹里没有 {name}。",
        "backed_up": "已把 {name} 备份到 {path}",
        "no_backups": "{name} 还没有备份。",
        "pick_backup": "用哪一份备份恢复 {name}？",
        "restore_confirm": "用 {when} 的备份替换 {folder} 吗？会先备份现在的版本。",
        "restored": "已用 {when} 的备份恢复 {name}。",
        "source_kind": "从哪里导入技能",
        "from_folder": "含 SKILL.md 的文件夹",
        "from_zip": "zip 压缩包",
        "pick_folder": "选择技能所在的文件夹。",
        "zip_path": "zip 文件的完整路径：",
        "preview": "技能：{name}\n用途：{desc}\n文件：{n} 个（{size} KB）\n装到：{dest}",
        "import_confirm": "导入这个技能吗？导入时不运行其中任何内容。",
        "imported": "已把 {name} 导入 {dest}。新开一个对话即可使用。",
        "new_name": "新技能的名称（小写字母、数字和连字符，如 weekly-report）：",
        "new_purpose": "用一句话说明它做什么、什么时候用：",
        "new_confirm": "新建 {path}，并放一个待补全的 SKILL.md 吗？",
        "created": "已新建 {path}。补全它的请求已经填在对话框里。",
        "bad_name": "名称只能用小写字母、数字和连字符，最多 64 个字符。",
        "taken": "已有同名技能 {name}（{folder}），不会覆盖。",
        "kb_name": "{name} 是知识库技能的名称。",
        "no_skill_md": "最上层（或唯一的子文件夹里）没有 SKILL.md。",
        "bad_zip": "zip 文件读不了：{e}",
        "unsafe": "zip 里有指向自身文件夹以外的路径：{p}",
        "too_big": "太大了：最多 {files} 个文件、{mb} MB。",
        "no_front": "SKILL.md 开头没有 name 和 description。",
        "cancelled": "已取消，没有改动。",
    },
}


class Refused(Exception):
    """A step that cannot go on; the message says why, in the page's language."""


def folders():
    """[(agent, skills folder)] OpenCode reads, in its order of preference."""
    return [(a, install.TARGETS[a][0]) for a in OPENCODE_ORDER if a in install.TARGETS]


def own_folder():
    """Where imported and new skills go: OpenCode's own skills folder."""
    return install.TARGETS["opencode"][0]


def backup_root():
    return os.path.join(kb_manage.state_dir(), "skill-backups")


def front_matter(text):
    """{name, description} from SKILL.md front matter; {} when it has none."""
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).split("\n"):
        k, sep, v = line.partition(":")
        if sep and k.strip() in ("name", "description"):
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def read_skill(path):
    try:
        with open(os.path.join(path, "SKILL.md"), encoding="utf-8", errors="replace") as f:
            text = f.read(200000)
    except OSError:
        return None
    fm = front_matter(text)
    m = re.search(r"^Version:\s*(\S+)", text, re.M)
    desc = fm.get("description", "")
    triggers = []
    for a, b in QUOTED_RE.findall(desc):
        q = (a or b).strip()
        if q and q not in triggers:
            triggers.append(q)
    return {"name": fm.get("name") or os.path.basename(path), "description": desc,
            "version": m.group(1) if m else "", "triggers": triggers[:6], "has_front": bool(fm)}


def backups(name):
    d = os.path.join(backup_root(), name)
    if not os.path.isdir(d):
        return []
    return sorted((b for b in os.listdir(d) if re.fullmatch(r"\d{8}-\d{6}", b)), reverse=True)


def list_skills():
    """Every skill in the folders OpenCode reads: [{name, description, version, triggers, folder, agent,
    kb, used, backups}] (kb: one of the knowledge-base skills), knowledge-base skills first, then by name."""
    out, seen = [], set()
    for agent, root in folders():
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            path = os.path.join(root, entry)
            if not os.path.isdir(path) or entry.startswith("."):
                continue
            info = read_skill(path)
            if info is None:
                continue
            info.update(folder=path, agent=agent, kb=entry in kb_manage.SKILLS,
                        used=entry not in seen, backups=len(backups(entry)), dir=entry)
            seen.add(entry)
            out.append(info)
    out.sort(key=lambda s: (not s["kb"], s["dir"], OPENCODE_ORDER.index(s["agent"])))
    return out


def find(name, lang):
    m = MSG[lang]
    for s in list_skills():
        if s["dir"] == name and s["used"]:
            return s
    raise Refused(m["not_found"].format(name=name))


def stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def backup(name, lang):
    """Copies the skill's folder in use into the backups; returns the backup folder."""
    s = find(name, lang)
    dest = os.path.join(backup_root(), name, stamp())
    while os.path.exists(dest):
        time.sleep(1)
        dest = os.path.join(backup_root(), name, stamp())
    shutil.copytree(s["folder"], dest, symlinks=True)
    log.info("backed up %s to %s", s["folder"], dest)
    return dest


def restore(name, when, lang):
    """Puts the backup of `when` in place of the skill's folder, after backing up the current one."""
    s = find(name, lang)
    src = os.path.join(backup_root(), name, when)
    if when not in backups(name):
        raise Refused(MSG[lang]["no_backups"].format(name=name))
    backup(name, lang)
    tmp = s["folder"] + ".restoring"
    shutil.copytree(src, tmp, symlinks=True)
    old = s["folder"] + ".replaced"
    os.rename(s["folder"], old)
    os.rename(tmp, s["folder"])
    shutil.rmtree(old)  # a copy of it is in the backups
    log.info("restored %s from %s", s["folder"], src)


def taken(name, lang):
    m = MSG[lang]
    if not NAME_RE.fullmatch(name or ""):
        raise Refused(m["bad_name"])
    if name in kb_manage.SKILLS:
        raise Refused(m["kb_name"].format(name=name))
    for s in list_skills():
        if s["dir"] == name:
            raise Refused(m["taken"].format(name=name, folder=s["folder"]))
    if os.path.exists(os.path.join(own_folder(), name)):
        raise Refused(m["taken"].format(name=name, folder=os.path.join(own_folder(), name)))


def check_folder(path, lang):
    """(skill folder inside path, info, files, bytes) for a folder that holds a skill."""
    m = MSG[lang]
    path = os.path.abspath(os.path.expanduser(path))
    top = path
    if not os.path.isfile(os.path.join(top, "SKILL.md")):
        subs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")] \
            if os.path.isdir(path) else []
        if len(subs) == 1 and os.path.isfile(os.path.join(path, subs[0], "SKILL.md")):
            top = os.path.join(path, subs[0])
        else:
            raise Refused(m["no_skill_md"])
    n = size = 0
    for d, _, files in os.walk(top):
        for f in files:
            p = os.path.join(d, f)
            if os.path.islink(p):
                continue
            n += 1
            size += os.path.getsize(p)
    if n > MAX_IMPORT_FILES or size > MAX_IMPORT_BYTES:
        raise Refused(m["too_big"].format(files=MAX_IMPORT_FILES, mb=MAX_IMPORT_BYTES // (1024 * 1024)))
    info = read_skill(top)
    if not info or not info["has_front"]:
        raise Refused(m["no_front"])
    return top, info, n, size


def unpack_zip(path, into, lang):
    """Unpacks a zip into the folder `into` after checking every name; returns into."""
    m = MSG[lang]
    try:
        with zipfile.ZipFile(os.path.expanduser(path)) as z:
            infos = z.infolist()
            if len(infos) > MAX_IMPORT_FILES or sum(i.file_size for i in infos) > MAX_IMPORT_BYTES:
                raise Refused(m["too_big"].format(files=MAX_IMPORT_FILES, mb=MAX_IMPORT_BYTES // (1024 * 1024)))
            for i in infos:
                name = i.filename.replace("\\", "/")
                parts = [p for p in name.split("/") if p]
                if name.startswith("/") or re.match(r"[A-Za-z]:", name) or ".." in parts:
                    raise Refused(m["unsafe"].format(p=i.filename))
                if (i.external_attr >> 16) & 0o170000 == 0o120000:  # a symbolic link
                    raise Refused(m["unsafe"].format(p=i.filename))
            for i in infos:
                target = os.path.join(into, *[p for p in i.filename.replace("\\", "/").split("/") if p])
                if i.is_dir():
                    os.makedirs(target, exist_ok=True)
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(i) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    except (zipfile.BadZipFile, OSError) as e:
        raise Refused(m["bad_zip"].format(e=e))
    return into


def install_copy(top, name):
    dest = os.path.join(own_folder(), name)
    os.makedirs(own_folder(), exist_ok=True)
    shutil.copytree(top, dest, symlinks=False, ignore=shutil.ignore_patterns("__pycache__", ".git"))
    return dest


TEMPLATE = {
    "en": """---
name: {name}
description: {purpose} Use when the user asks for this, for example "{name}".
---

# {title}

What this skill does: {purpose}

## Steps

1. (to be filled in)

## Output

(to be filled in)
""",
    "zh": """---
name: {name}
description: {purpose}使用者提出这类要求时使用，例如说「{name}」。
---

# {title}

用途：{purpose}

## 步骤

1. （待补全）

## 输出

（待补全）
""",
}


def create(name, purpose, lang):
    taken(name, lang)
    dest = os.path.join(own_folder(), name)
    os.makedirs(dest)
    purpose = " ".join(purpose.split()).replace("---", "-")
    if purpose and purpose[-1] not in ".。!！?？":
        purpose += "。" if lang == "zh" else "."
    with open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATE[lang].format(name=name, purpose=purpose, title=name.replace("-", " ").capitalize()))
    return dest
