# Manual setup

The [quick start](../README.md#quick-start) does all of this for you: the workbench on the workstation, `python3 install.py` in a terminal, or "get started with the knowledge base" in OpenCode. This page is for doing each step by hand, adding libraries later, or understanding what the guided setup wrote.

[中文](manual-setup.zh-CN.md)

## 1. Install the skills

`python3 install.py --target opencode` copies the three skills into `~/.config/opencode/skills` (or `--target agents` for `~/.agents/skills`, `--target claude-code` for `~/.claude/skills`, both of which OpenCode also reads, or `--dest <folder>`). Add `--locale zh` for Chinese trigger phrases, `--descriptions <file>` for your own descriptions (one line per skill, in the shape of `locales/zh/descriptions.json`), `--force` to replace an existing install, `--dry-run` to see what would happen.

The guided setup (`python3 install.py`) takes `--agent <target>` to skip that question, and `--descriptions` as well. Given a folder that already holds a library (`_kb.json` of schema 3), it registers the folder as it is, without changing a file, after a preview. A 1.x library (schema 1) or a 2.0 or 3.0 library (schema 2, one flat sources folder) is refused: keep using the release that made it, or set up a new library in an empty folder and ingest the material again.

## 2. Create a library

Ask OpenCode: "set up a new knowledge base". It asks for the library folder and what belongs in the library, works out language, timezone and the rest, shows a preview of everything it will create, and writes it after you confirm.

From a terminal the same files come from the script the skill uses:

```bash
python3 skills/kb-ingest/scripts/init_library.py plan  --root ~/kb/atlas --preset work
python3 skills/kb-ingest/scripts/init_library.py write --root ~/kb/atlas --preset work --scope "Project Atlas plans, minutes and reports"
```

It refuses a folder that already holds Markdown files or a `_kb.json`.

## 3. Register your libraries

A registry is a small JSON file listing each library and what belongs in it:

```json
{
  "schema": 1,
  "preferences": {"output": "markdown"},
  "libraries": [
    {"id": "atlas", "label": "Project Atlas", "scope": "Project Atlas plans, minutes and reports",
     "backend": {"type": "local", "root": "~/kb/atlas"}},
    {"id": "work", "label": "Work", "scope": "work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports",
     "backend": {"type": "local", "root": "~/kb/work"}}
  ]
}
```

Put it in `~/.config/kb/kb-libraries.json`, or point `KB_LIBRARIES` at it. `init_library.py register --id ... --label ... --scope ... --root ...` adds an entry and refuses an id or folder that is already there. An entry of type gdrive is refused: Google Drive libraries are read by the 2.0.x release.

The scope matters: it is how the assistant decides which library a note or question belongs to. Write one sentence per library, and keep scopes from overlapping.

## 4. Tell OpenCode the libraries exist

Add one line to `~/.config/opencode/AGENTS.md` (or the AGENTS.md of a project):

```text
I keep knowledge bases: Project Atlas (Project Atlas plans, minutes and reports); Work (work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note; to add documents, use kb-ingest.
```

Without it, questions that do not sound personal (for example "what is the payments API rate limit?") may be answered from code or general knowledge instead of your library. `init_library.py instructions --registry <registry> --file <file> --apply` writes or updates this line from the registry, leaving the rest of the file alone. OpenCode reads `~/.claude/CLAUDE.md` when it has no AGENTS.md; the knowledge base client writes the line where OpenCode will read it.

## 5. Use it

"note this", "ingest these" with a file or folder path, or just ask.

## 6. Back up, roll back, move, uninstall

Run these from the evergreen-wiki folder. Each one shows what it will do and asks before it changes anything; add `--lang zh` for Chinese messages.

- `python3 install.py backup [--note TEXT]` copies the installed skills, every instructions file that holds the knowledge-base line, the registry and the install record. The installer does the same on its own before it replaces skills, adds to a registry or writes the line.
- `python3 install.py rollback [--id ID]` restores one backup. The state before the restore is backed up first, so a rollback can be undone the same way.
- `python3 install.py move <library id> --to <folder>` moves a registered local library into that folder, keeping its folder name. Only the library moves: folders of original files stay where they are, since ingesting reads material from wherever the user picks it. The folder is copied, then compared file by file (size and SHA-256, empty folders and symbolic links included); only when everything matches does the registry point to the new place. Otherwise the copy is removed and nothing else changes. It refuses when the new place is inside the library, is not empty or is registered to another library, or when the disk is too small. Deleting the original folders is offered last, off by default and only after typing `delete`; they are compared once more first. Quit OpenCode before moving and restart it afterwards; in Obsidian, open the new folder.
- `python3 install.py uninstall` removes the three skills from every folder the installer used, the knowledge-base line (the rest of each file stays; a file left empty is deleted), the registry with every library in it, and the install record with all backups. Library folders stay unless you choose to delete them, are asked one at a time (default no) and type `delete`. Only folders with `_kb.json` or a `00_` spec file are offered; symbolic links, the root, your home folder and folders holding it, this program or an agent's settings never are.

The install record and backups live in `~/.config/evergreen-wiki/` (`XDG_CONFIG_HOME` moves it). Library folders are never part of a backup: a rollback after a move restores only the registry entry, so roll back past a move only while the original folder still exists.
