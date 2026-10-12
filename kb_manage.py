"""Back up, roll back, move and uninstall what install.py set up. Run it through install.py:

  python3 install.py backup [--note TEXT]   copy the installed skills, the instructions files, the registry
                                            and the install record into a new backup
  python3 install.py rollback [--id ID]     restore one backup; the present state is backed up first
  python3 install.py move ID --to FOLDER    move a registered local library into FOLDER (same folder name),
                                            copying and comparing every file before the registry changes
  python3 install.py uninstall              remove the skills, the knowledge-base line, the registry, the
                                            install record and the backups; library folders only when picked
Options: --lang en|zh (messages; default from the system language), --log-level.

Library folders are user data. Backup and rollback never copy or change them; move changes the registry
only after the copy matches the original file by file; uninstall keeps them unless each one is picked and
the confirmation word typed. Uses the Python standard library only.
"""
import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import sys

log = logging.getLogger("kb_manage")
ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ROOT, "skills", "kb-incremental", "scripts")
SKILLS = ["kb-note", "kb-query", "kb-incremental"]
COMMANDS = ("backup", "rollback", "move", "uninstall")
# Material folders next to a library, as the kb-incremental material chooser names them.
MATERIAL_SUFFIXES = ("-待整理", "-inbox")
# A spec file marks a folder as a library: the presets name it 00_Spec.md, Chinese libraries often 00_规范.md.
SPEC_RE = re.compile(r"^00_.*(spec|规范).*\.md$", re.I)
CONFIRM_WORDS = {"en": "delete", "zh": "删除"}

MSG = {
    "en": {
        "backup_done": "Backup {id} written to {path}.",
        "backup_auto": "backup: the present state is saved as {id} ({path}); undo with: python3 install.py rollback --id {id}",
        "no_backups": "No backups yet.",
        "no_such_backup": "No backup {id}. Backups: {ids}",
        "pick_backup": "Which backup should be restored?",
        "restore_plan": "Restoring backup {id} ({time}{note}):",
        "will_restore": "  restore  {path}",
        "will_remove": "  remove   {path} (it did not exist then)",
        "restore_libs": "Library folders are not part of a backup and stay as they are.",
        "restore_ok": "Restore it?",
        "restored": "Restored backup {id}. The state before the restore is saved as {safety}.",
        "restart": "Restart your agent so it reads the change.",
        "cancelled": "Cancelled. Nothing was changed.",
        "not_registered": "Library {id!r} is not registered in {path}.",
        "no_registry": "No registry found at {path}.",
        "not_local": "not a local folder",
        "is_link": "a symbolic link",
        "missing": "the folder no longer exists",
        "protected": "the root, home folder or a folder holding it, this program, the skills or the instructions",
        "not_library": "no _kb.json and no 00_ spec file, so it does not look like a library",
        "cannot_move": "Cannot move {label} ({root}): {why}.",
        "batch_open": "Library {label} has an unfinished batch intake ({path}). Tell your agent \"continue intake\" or \"finish intake\" first, then move it.",
        "same_place": "The new place is where the library already is: {root}",
        "dest_inside": "The new place {parent} is inside {src}.",
        "parent_file": "{parent} is a file, not a folder.",
        "dest_taken": "{dest} already exists and is not empty; choose another folder.",
        "dest_registered": "{dest} is already registered as library {label}.",
        "move_plan": "Move library {label} (id {id})",
        "move_from": "  from  {src}",
        "move_to": "  to    {dest}",
        "move_size": "{n} files, {size}; free space at the new place: {free}",
        "no_space": "Not enough free space at the new place.",
        "move_how": "The folders are copied first and compared file by file (size and SHA-256). Only when every file matches does the registry point to the new place; otherwise the copy is removed and nothing else changes. Quit your agent before moving.",
        "move_ok": "Move it?",
        "copy_bad": "{dest} does not match the original: {paths}",
        "copy_failed": "Copy failed: {err}. The copy was removed; the registry and the original folders are unchanged.",
        "moved": "Copied and verified: {src} -> {dest}",
        "registry_moved": "Registry {path}: {label} now points to {dest}.",
        "remove_old": "Delete the original folders now? They are no longer used.",
        "type_word": "Type {word} to delete, anything else keeps them",
        "kept_old": "Kept the original folders. Delete them yourself when you no longer need them.",
        "old_changed": "{src} changed since the copy ({paths}); it was kept. Compare it with {dest} yourself.",
        "deleted": "deleted: {path}",
        "failed": "failed: {path}: {err}",
        "obsidian": "If you open the library in Obsidian, open the new folder there.",
        "nothing": "Nothing to uninstall: no skills, registry, knowledge-base line or install record found.",
        "un_items": "Uninstall removes:",
        "un_skill": "  skill          {path}",
        "un_registry": "  registry       {path} (every library registered in it: {n})",
        "un_state": "  install record and every backup  {path} (rollback is no longer possible)",
        "un_line": "  the knowledge-base line in {path} (the rest of the file stays)",
        "un_keep": "Your agent, its settings and other skills stay. A Claude Code plugin install is removed with /plugin.",
        "un_libs_q": "Also delete library folders? The default keeps them all.",
        "un_lib_q": "Delete {label} at {root} ({n} files){extra}?",
        "un_lib_extra": " together with {dirs}",
        "un_lib_skip": "  not offered: {label} at {root} ({why})",
        "un_lib_will": "  library folder  {path}",
        "un_ok": "Uninstall?",
        "line_removed": "removed the knowledge-base line from {path}",
        "file_removed": "deleted {path} (it held only the knowledge-base line)",
        "un_done": "Uninstalled. Restart your agent.",
        "un_failed": "Uninstalled with {n} failures; see the lines above.",
        "yes": "Y/n", "no": "y/N",
    },
    "zh": {
        "backup_done": "已备份为 {id}，位置 {path}。",
        "backup_auto": "备份：写入前的现状已保存为 {id}（{path}）；要撤销可运行 python3 install.py rollback --id {id}",
        "no_backups": "还没有备份。",
        "no_such_backup": "没有备份 {id}。现有备份：{ids}",
        "pick_backup": "恢复哪一次备份？",
        "restore_plan": "恢复备份 {id}（{time}{note}）：",
        "will_restore": "  恢复  {path}",
        "will_remove": "  删除  {path}（备份时还不存在）",
        "restore_libs": "知识库文件夹不在备份里，保持原样。",
        "restore_ok": "确认恢复？",
        "restored": "已恢复备份 {id}。恢复前的现状已保存为 {safety}。",
        "restart": "请重启助手，让它读到改动。",
        "cancelled": "已取消，没有改动任何内容。",
        "not_registered": "库 {id!r} 没有登记在 {path}。",
        "no_registry": "没有找到注册表 {path}。",
        "not_local": "不是本机文件夹",
        "is_link": "是符号链接",
        "missing": "文件夹已不存在",
        "protected": "是根目录、家目录或其上级，或包含本程序、技能或指令文件",
        "not_library": "没有 _kb.json，也没有 00_ 开头的规范文件，不像知识库",
        "cannot_move": "不能移动「{label}」（{root}）：{why}。",
        "batch_open": "知识库「{label}」有没做完的分批入库（{path}）。请先对助手说「继续入库」做完，或说「结束入库」，再来移动。",
        "same_place": "新位置就是知识库现在的位置：{root}",
        "dest_inside": "新位置 {parent} 在 {src} 里面。",
        "parent_file": "{parent} 是文件，不是文件夹。",
        "dest_taken": "{dest} 已存在且不是空文件夹，请换一个位置。",
        "dest_registered": "{dest} 已登记为知识库「{label}」。",
        "move_plan": "移动知识库「{label}」（id {id}）",
        "move_from": "  原位置  {src}",
        "move_to": "  新位置  {dest}",
        "move_size": "共 {n} 个文件，{size}；新位置所在磁盘剩余 {free}",
        "no_space": "新位置所在磁盘空间不够。",
        "move_how": "先复制，再逐个文件比对大小和 SHA-256；全部一致才把注册表里的位置改成新位置，不一致时清掉复制出的内容，其余都不动。移动前请先退出助手。",
        "move_ok": "确认移动？",
        "copy_bad": "{dest} 与原文件夹不一致：{paths}",
        "copy_failed": "复制失败：{err}。已清掉复制出的内容，注册表和原文件夹都没有改动。",
        "moved": "已复制并逐个文件核对一致：{src} -> {dest}",
        "registry_moved": "注册表 {path}：「{label}」的位置已改为 {dest}。",
        "remove_old": "现在删除原文件夹吗？它们已不再使用。",
        "type_word": "输入「{word}」确认删除，输入其他内容则保留",
        "kept_old": "已保留原文件夹，不再需要时请自行删除。",
        "old_changed": "{src} 在复制之后有改动（{paths}），已保留；请自行与 {dest} 核对。",
        "deleted": "已删除：{path}",
        "failed": "失败：{path}：{err}",
        "obsidian": "用 Obsidian 打开过这个库的，请在 Obsidian 里改为打开新位置。",
        "nothing": "没有可卸载的内容：没有找到技能、注册表、知识库说明行或安装记录。",
        "un_items": "卸载将删除：",
        "un_skill": "  技能          {path}",
        "un_registry": "  注册表        {path}（其中登记的全部 {n} 个库）",
        "un_state": "  安装记录与全部备份  {path}（之后不能再回滚）",
        "un_line": "  {path} 中的知识库说明行（文件其余内容不动）",
        "un_keep": "助手本身、它的设置和其他技能不受影响。Claude Code 插件方式安装的，用 /plugin 卸载。",
        "un_libs_q": "同时删除知识库文件夹吗？默认全部保留。",
        "un_lib_q": "删除「{label}」{root}（{n} 个文件）{extra}？",
        "un_lib_extra": "，连同 {dirs}",
        "un_lib_skip": "  不可删除：「{label}」{root}（{why}）",
        "un_lib_will": "  知识库文件夹  {path}",
        "un_ok": "确认卸载？",
        "line_removed": "已从 {path} 删去知识库说明行",
        "file_removed": "已删除 {path}（其中只有知识库说明行）",
        "un_done": "卸载完成。请重启助手。",
        "un_failed": "卸载完成，有 {n} 项失败，见上文。",
        "yes": "Y/n", "no": "y/N",
    },
}


class Refused(Exception):
    """A check stopped the command; the message is for the user. Exit code 2."""


def init_library():
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import init_library as il
    return il


# ---------- install record ----------

def state_dir():
    if os.name == "nt" and os.environ.get("APPDATA"):
        return os.path.join(os.environ["APPDATA"], "evergreen-wiki")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "evergreen-wiki")


def state_file():
    return os.path.join(state_dir(), "state.json")


def backup_dir():
    return os.path.join(state_dir(), "backup")


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as e:
        log.warning("cannot read %s: %s", path, e)
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def record(skills_dir=None, instructions=None):
    """Remember where install.py wrote, so backup and uninstall find it again."""
    st = read_json(state_file(), {})
    if not isinstance(st, dict):
        st = {}
    changed = False
    for key, value in (("skills_dirs", skills_dir), ("instruction_files", instructions)):
        if value:
            value = os.path.abspath(os.path.expanduser(value))
            lst = st.setdefault(key, [])
            if value not in lst:
                lst.append(value)
                changed = True
    if changed:
        write_json(state_file(), st)


def has_our_line(path):
    try:
        with open(path, encoding="utf-8") as f:
            return any(init_library().is_our_line(x) for x in f.read().split("\n"))
    except OSError:
        return False


def places(defaults, extra_dirs=()):
    """(skills folders, instructions files) to back up or uninstall: the recorded ones, the known agent
    folders that hold one of the skills, and the known instructions files that hold the line."""
    st = read_json(state_file(), {})
    st = st if isinstance(st, dict) else {}
    dirs = list(st.get("skills_dirs", [])) + [os.path.abspath(d) for d in extra_dirs]
    dirs += [d for d in defaults.get("skill_dirs", []) if any(os.path.lexists(os.path.join(d, s)) for s in SKILLS)]
    files = list(st.get("instruction_files", []))
    files += [f for f in defaults.get("instruction_files", []) if has_our_line(f)]
    return list(dict.fromkeys(dirs)), list(dict.fromkeys(files))


def registry_path():
    return init_library().registry_path()


# ---------- backup and rollback ----------

def backup_paths(defaults, extra_dirs=()):
    dirs, files = places(defaults, extra_dirs)
    paths = [os.path.join(d, s) for d in dirs for s in SKILLS] + files + [registry_path(), state_file()]
    return list(dict.fromkeys(paths))


def copy_any(src, dest):
    if os.path.isdir(src) and not os.path.islink(src):
        shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
    else:
        shutil.copy2(src, dest, follow_symlinks=False)


def remove_any(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.name == "nt" and os.path.islink(path) and os.path.isdir(path):
        os.rmdir(path)  # a directory link on Windows is removed like a folder, its target stays
    elif os.path.lexists(path):
        os.remove(path)


def make_backup(paths, note):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bid, n = stamp, 2
    while os.path.exists(os.path.join(backup_dir(), bid)):
        bid, n = f"{stamp}-{n}", n + 1
    dest = os.path.join(backup_dir(), bid)
    os.makedirs(dest, mode=0o700)
    items = []
    for i, path in enumerate(paths, 1):
        existed = os.path.lexists(path)
        if existed:
            copy_any(path, os.path.join(dest, str(i)))
        items.append({"copy": str(i), "path": path, "existed": existed})
    write_json(os.path.join(dest, "manifest.json"),
               {"id": bid, "time": datetime.datetime.now().isoformat(timespec="seconds"), "note": note,
                "items": items})
    log.info("backup %s written to %s", bid, dest)
    return bid, dest


_auto = []


def backup_once(defaults, note, lang, extra_dirs=()):
    """Called by install.py before it replaces or changes something; one backup per run."""
    if _auto:
        return _auto[0]
    paths = backup_paths(defaults, extra_dirs)
    if not any(os.path.lexists(p) for p in paths):
        return None
    bid, dest = make_backup(paths, note)
    _auto.append(bid)
    print(MSG[lang]["backup_auto"].format(id=bid, path=dest))
    return bid


def list_backups():
    out = []
    if os.path.isdir(backup_dir()):
        for bid in sorted(os.listdir(backup_dir()), reverse=True):
            m = read_json(os.path.join(backup_dir(), bid, "manifest.json"), None)
            if isinstance(m, dict) and m.get("id") == bid:
                out.append(m)
    return out


def restore(m, defaults):
    src = os.path.join(backup_dir(), m["id"])
    paths = list(dict.fromkeys([it["path"] for it in m["items"]] + backup_paths(defaults)))
    safety, _ = make_backup(paths, "before restoring " + m["id"])
    for it in m["items"]:
        remove_any(it["path"])
        if it["existed"]:
            os.makedirs(os.path.dirname(it["path"]), exist_ok=True)
            copy_any(os.path.join(src, it["copy"]), it["path"])
    return safety


def cmd_backup(a, q, m, defaults):
    bid, dest = make_backup(backup_paths(defaults), a.note)
    print(m["backup_done"].format(id=bid, path=dest))
    return 0


def cmd_rollback(a, q, m, defaults):
    backups = list_backups()
    if not backups:
        print(m["no_backups"])
        return 0
    if a.id:
        found = [b for b in backups if b["id"] == a.id]
        if not found:
            raise Refused(m["no_such_backup"].format(id=a.id, ids=", ".join(b["id"] for b in backups)))
        b = found[0]
    else:
        opts = [(x["id"], f"{x['id']}  {x.get('note', '')}".rstrip()) for x in backups]
        bid = q.choose(m["pick_backup"], opts, backups[0]["id"])
        b = next(x for x in backups if x["id"] == bid)
    note = ", " + b["note"] if b.get("note") else ""
    print(m["restore_plan"].format(id=b["id"], time=b.get("time", ""), note=note))
    for it in b["items"]:
        if it["existed"]:
            print(m["will_restore"].format(path=it["path"]))
        elif os.path.lexists(it["path"]):
            print(m["will_remove"].format(path=it["path"]))
    print(m["restore_libs"])
    if not q.yes(m["restore_ok"]):
        print(m["cancelled"])
        return 0
    safety = restore(b, defaults)
    print(m["restored"].format(id=b["id"], safety=safety))
    print(m["restart"])
    return 0


# ---------- libraries ----------

def norm(path):
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))


def inside(path, parent):
    """path is parent or lies inside it, comparing real paths."""
    path, parent = os.path.realpath(path), os.path.realpath(parent)
    try:
        return os.path.commonpath([path, parent]) == parent
    except ValueError:  # different drives on Windows
        return False


def is_library(root):
    if os.path.isfile(os.path.join(root, init_library().kbconf.KB_JSON)):
        return True
    try:
        return any(SPEC_RE.match(f) for f in os.listdir(root))
    except OSError:
        return False


def registered_libs():
    """[(id, label, root)] from the registry; root is "" for a library that is not a local folder."""
    path = registry_path()
    reg = read_json(path, {})
    out = []
    for lib in reg.get("libraries", []) if isinstance(reg, dict) else []:
        backend = lib.get("backend") or {}
        root = backend.get("root", "") if backend.get("type", "local") == "local" else ""
        out.append((lib.get("id", ""), lib.get("label") or lib.get("id", ""), norm(root) if root else ""))
    return out


def protected(defaults):
    dirs, files = places(defaults)
    return [ROOT, state_dir()] + dirs + [os.path.dirname(f) for f in files]


def lib_check(root, defaults):
    """None when the folder may be moved or deleted, else the message key of the reason."""
    if not root or not os.path.isabs(root):
        return "not_local"
    if os.path.islink(root):
        return "is_link"
    if not os.path.isdir(root):
        return "missing"
    real = os.path.realpath(root)
    if real == os.path.dirname(real) or inside(os.path.expanduser("~"), real):
        return "protected"
    if any(inside(p, real) for p in protected(defaults) if p):
        return "protected"
    if not is_library(real):
        return "not_library"
    return None


def material_dirs(root):
    parent, name = os.path.split(root)
    out = []
    for suffix in MATERIAL_SUFFIXES:
        p = os.path.join(parent, name + suffix)
        if os.path.isdir(p) and not os.path.islink(p):
            out.append(p)
    return out


def count_files(root):
    return sum(len(files) for _, _, files in os.walk(root))


def tree_size(root):
    n = size = 0
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            n += 1
            if not os.path.islink(p):
                size += os.path.getsize(p)
    return n, size


def human(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0


def free_space(path):
    while not os.path.exists(path):
        path = os.path.dirname(path)
    return shutil.disk_usage(path).free


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(root):
    """relative path -> ("file", size, sha256) | ("link", target) | ("dir",); empty folders count."""
    out = {}
    for d, dirs, files in os.walk(root):
        for name in dirs + files:
            p = os.path.join(d, name)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if os.path.islink(p):
                out[rel] = ("link", os.readlink(p))
            elif os.path.isdir(p):
                out[rel] = ("dir",)
            else:
                out[rel] = ("file", os.path.getsize(p), sha256(p))
    return out


def diff_trees(a, b):
    """Relative paths that differ between two folders, at most 20."""
    ma, mb = manifest(a), manifest(b)
    return sorted(k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k))[:20]


def is_empty_dir(path):
    return os.path.isdir(path) and not os.path.islink(path) and not os.listdir(path)


def batch_plan(root):
    il = init_library()
    try:
        name = il.kbconf.load_library(root)["names"]["batch_plan"]
    except Exception as e:  # an incomplete library falls back to the default name
        log.info("cannot read the settings of %s: %s", root, e)
        name = il.kbconf.DEFAULT_NAMES["batch_plan"]
    return os.path.join(root, name)


def move_jobs(lib_id, to, m, defaults):
    """Check the move; returns (label, [(source, destination)]) with the library first."""
    libs = {i: (label, root) for i, label, root in registered_libs()}
    if lib_id not in libs:
        raise Refused(m["not_registered"].format(id=lib_id, path=registry_path()))
    label, root = libs[lib_id]
    why = lib_check(root, defaults)
    if why:
        raise Refused(m["cannot_move"].format(label=label, root=root or "-", why=m[why]))
    plan = batch_plan(root)
    if os.path.exists(plan):
        raise Refused(m["batch_open"].format(label=label, path=plan))
    parent = norm(to)
    if os.path.lexists(parent) and not os.path.isdir(parent):
        raise Refused(m["parent_file"].format(parent=parent))
    jobs = [(root, os.path.join(parent, os.path.basename(root)))]
    jobs += [(p, os.path.join(parent, os.path.basename(p))) for p in material_dirs(root)]
    if os.path.realpath(jobs[0][1]) == os.path.realpath(root):
        raise Refused(m["same_place"].format(root=root))
    for src, dest in jobs:
        if inside(parent, src):
            raise Refused(m["dest_inside"].format(parent=parent, src=src))
        if os.path.lexists(dest) and not is_empty_dir(dest):
            raise Refused(m["dest_taken"].format(dest=dest))
    for i, (other_label, other_root) in libs.items():
        if i != lib_id and other_root and os.path.realpath(other_root) == os.path.realpath(jobs[0][1]):
            raise Refused(m["dest_registered"].format(dest=jobs[0][1], label=other_label))
    return label, jobs


def copy_tree(src, dest):
    if is_empty_dir(dest):
        os.rmdir(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(src, dest, symlinks=True)


def update_registry_root(lib_id, dest):
    il = init_library()
    path = registry_path()
    reg = il.kbconf.load_json(path)
    for lib in reg.get("libraries", []):
        if lib.get("id") == lib_id:
            lib.setdefault("backend", {})["root"] = il.registry_entry(lib_id, "", "", "local", dest)["backend"]["root"]
            break
    problems = il.kbconf.check_registry(reg)
    if problems:
        raise il.kbconf.ConfigError("; ".join(problems))
    write_json(path, reg)
    return path


def remove_old(jobs, q, m, lang):
    if not q.yes(m["remove_old"], False):
        print(m["kept_old"])
        return 0
    word = CONFIRM_WORDS[lang]
    if q.ask(m["type_word"].format(word=word)) != word:
        print(m["kept_old"])
        return 0
    failed = 0
    for src, dest in jobs:
        bad = diff_trees(src, dest)
        if bad:
            print(m["old_changed"].format(src=src, dest=dest, paths=", ".join(bad)))
            failed += 1
            continue
        try:
            shutil.rmtree(src)
            print(m["deleted"].format(path=src))
        except OSError as e:
            failed += 1
            print(m["failed"].format(path=src, err=e))
    return 1 if failed else 0


def cmd_move(a, q, m, defaults):
    label, jobs = move_jobs(a.id, a.to, m, defaults)
    n = size = 0
    for src, _ in jobs:
        n2, s2 = tree_size(src)
        n, size = n + n2, size + s2
    free = free_space(jobs[0][1])
    print(m["move_plan"].format(label=label, id=a.id))
    for src, dest in jobs:
        print(m["move_from"].format(src=src))
        print(m["move_to"].format(dest=dest))
    print(m["move_size"].format(n=n, size=human(size), free=human(free)))
    if size * 1.05 + 10 * 1024 * 1024 > free:
        raise Refused(m["no_space"])
    print(m["move_how"])
    if not q.yes(m["move_ok"]):
        print(m["cancelled"])
        return 0
    made = []
    try:
        for src, dest in jobs:
            log.info("copy %s -> %s", src, dest)
            copy_tree(src, dest)
            made.append(dest)
        for src, dest in jobs:
            bad = diff_trees(src, dest)
            if bad:
                raise OSError(m["copy_bad"].format(dest=dest, paths=", ".join(bad)))
        reg = update_registry_root(a.id, jobs[0][1])
    except (OSError, shutil.Error, ValueError, init_library().kbconf.ConfigError) as e:
        for dest in made:
            shutil.rmtree(dest, ignore_errors=True)
        print(m["copy_failed"].format(err=e))
        return 1
    for src, dest in jobs:
        print(m["moved"].format(src=src, dest=dest))
    print(m["registry_moved"].format(path=reg, label=label, dest=jobs[0][1]))
    rc = remove_old(jobs, q, m, a.lang)
    print(m["restart"])
    print(m["obsidian"])
    return rc


# ---------- uninstall ----------

def remove_line(path):
    il = init_library()
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rest = "\n".join(x for x in text.split("\n") if not il.is_our_line(x))
    if not rest.strip():
        os.remove(path)
        return "file_removed"
    rest = re.sub(r"\n{3,}", "\n\n", rest).rstrip("\n") + "\n"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(rest)
    os.replace(tmp, path)
    return "line_removed"


def cmd_uninstall(a, q, m, defaults):
    dirs, files = places(defaults)
    skills = [os.path.join(d, s) for d in dirs for s in SKILLS if os.path.lexists(os.path.join(d, s))]
    lines = [f for f in files if has_our_line(f)]
    reg = registry_path()
    libs = registered_libs()
    state = state_dir()
    if not (skills or lines or os.path.lexists(reg) or os.path.lexists(state)):
        print(m["nothing"])
        return 0
    deletable, skipped = [], []
    for lib_id, label, root in libs:
        why = lib_check(root, defaults)
        (skipped if why else deletable).append((label, root, m[why] if why else ""))
    picked = []
    if deletable and q.yes(m["un_libs_q"], False):
        for label, root, _ in deletable:
            extra = material_dirs(root)
            text = m["un_lib_extra"].format(dirs=", ".join(extra)) if extra else ""
            if q.yes(m["un_lib_q"].format(label=label, root=root, n=count_files(root), extra=text), False):
                picked += [root] + extra
    print(m["un_items"])
    for p in skills:
        print(m["un_skill"].format(path=p))
    for f in lines:
        print(m["un_line"].format(path=f))
    if os.path.lexists(reg):
        print(m["un_registry"].format(path=reg, n=len(libs)))
    if os.path.lexists(state):
        print(m["un_state"].format(path=state))
    for p in picked:
        print(m["un_lib_will"].format(path=p))
    for label, root, why in skipped:
        print(m["un_lib_skip"].format(label=label, root=root or "-", why=why))
    print(m["un_keep"])
    if picked:
        word = CONFIRM_WORDS[a.lang]
        if q.ask(m["type_word"].format(word=word)) != word:
            print(m["cancelled"])
            return 0
    elif not q.yes(m["un_ok"], False):
        print(m["cancelled"])
        return 0
    failed = 0

    def drop(path):
        nonlocal failed
        try:
            remove_any(path)
            print(m["deleted"].format(path=path))
        except OSError as e:
            failed += 1
            print(m["failed"].format(path=path, err=e))

    # Library folders first: once the registry is gone nothing says where they are.
    for p in picked:
        drop(p)
    for f in lines:
        try:
            print(m[remove_line(f)].format(path=f))
        except OSError as e:
            failed += 1
            print(m["failed"].format(path=f, err=e))
    for p in skills + [reg, state]:
        if os.path.lexists(p):
            drop(p)
    try:
        os.rmdir(os.path.dirname(reg))  # only when the registry was the last thing in its folder
    except OSError:
        pass
    print(m["un_failed"].format(n=failed) if failed else m["un_done"])
    return 1 if failed else 0


# ---------- entry point ----------

def main(argv, asker, defaults):
    """argv starts with the command; asker(lang) reads answers; defaults lists the known agent folders:
    {"skill_dirs": [...], "instruction_files": [...]}."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--lang", choices=sorted(MSG))
    common.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "WARNING").upper(),
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    ap = argparse.ArgumentParser(prog="install.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup", parents=[common], help="back up the installed files").add_argument("--note", default="")
    sub.add_parser("rollback", parents=[common], help="restore a backup").add_argument("--id")
    p = sub.add_parser("move", parents=[common], help="move a registered local library")
    p.add_argument("id", help="the library id in the registry")
    p.add_argument("--to", required=True, help="folder to move the library into; the folder name stays")
    sub.add_parser("uninstall", parents=[common], help="remove what install.py set up")
    a = ap.parse_args(argv)
    logging.basicConfig(level=a.log_level, stream=sys.stderr,
                        format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s")
    il = init_library()
    il.kbconf.utf8_stdio()
    a.lang = a.lang or il.detect_language()
    m = MSG[a.lang]
    cmd = {"backup": cmd_backup, "rollback": cmd_rollback, "move": cmd_move, "uninstall": cmd_uninstall}[a.cmd]
    try:
        return cmd(a, asker(a.lang), m, defaults)
    except Refused as e:
        print(e)
        return 2
    except KeyboardInterrupt:
        print("\n" + m["cancelled"])
        return 1
