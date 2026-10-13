# Manual setup

The [quick start](../README.md#quick-start) does all of this for you: `python3 install.py` in a terminal, or "get started with the knowledge base" in your assistant. This page is for doing each step by hand, adding libraries later, or understanding what the guided setup wrote.

[中文](manual-setup.zh-CN.md)

## 1. Install the skills

- Claude Code: `/plugin marketplace add walkwithedi/evergreen-wiki`, then `/plugin install evergreen-wiki@evergreen-wiki`.
- claude.ai or the Claude apps: download the kb-note, kb-query and kb-incremental zips from [Releases](../../../releases) and upload each in Settings > Capabilities > Skills (Chinese trigger phrases: the -zh zips).
- Other agents that read Agent Skills: `python3 install.py --target agents` (or `--target gemini`, `opencode`, `codex`, `claude-code`, or `--dest <folder>`); add `--locale zh` for Chinese trigger phrases, `--descriptions <file>` for your own descriptions (one line per skill, in the shape of `locales/zh/descriptions.json`), `--force` to replace an existing install, `--dry-run` to see what would happen. The guided setup (`python3 install.py`) takes `--agent <target>` and `--preset life|work` to skip those questions, and `--descriptions` as well. Given a folder that already holds a library (`_kb.json` or a `00_` spec file), it registers the folder as it is, without changing a file, after a preview; then tell your agent "init <label>" to complete the settings from the library's own spec.

## 2. Create a library

Ask your assistant: "set up a new knowledge base". It asks where (a Drive folder or a local folder), which preset (work or life) and what belongs in the library, works out language, timezone and the rest, shows a preview of everything it will create, and writes it after you confirm.

From a terminal the same files come from the script the skill uses:

```bash
python3 skills/kb-incremental/scripts/init_library.py plan  --root ~/kb/life --preset life
python3 skills/kb-incremental/scripts/init_library.py write --root ~/kb/life --preset life --scope "me and my family: IDs, health, insurance, money, home"
```

It refuses a folder that already holds Markdown files; for an existing library ask the assistant to "complete the settings" instead, which never overwrites files.

## 3. Register your libraries

A registry is a small JSON file listing each library and what belongs in it:

```json
{
  "schema": 1,
  "preferences": {"output": "markdown"},
  "libraries": [
    {"id": "life", "label": "Life", "scope": "me and my family: IDs, health, insurance, money, home",
     "backend": {"type": "local", "root": "~/Documents/life-kb"}},
    {"id": "work", "label": "Work", "scope": "work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports",
     "backend": {"type": "gdrive", "root": "<drive folder id>"}}
  ]
}
```

Put it in `~/.config/kb/kb-libraries.json` (on Windows `%APPDATA%\kb\kb-libraries.json`, or point `KB_LIBRARIES` at it). `init_library.py register --id ... --label ... --scope ... --type local|gdrive --root ...` adds an entry and refuses an id or folder that is already there.

On claude.ai, the guided setup keeps it in Drive (kb-libraries.json in the first library's folder) and gives you one line for the Project instructions: `registry: Google Drive folder <folder id>, file kb-libraries.json` inside a short sentence. You can also paste the whole JSON into the Project instructions, or build private zips that carry it: `python3 scripts/build_skill.py --config my-libraries.json` (never publish those).

The scope matters: it is how the assistant decides which library a note or question belongs to. Write one sentence per library, and keep scopes from overlapping.

## 4. Tell your assistant the libraries exist

Add one line to the instructions it always reads (CLAUDE.md, AGENTS.md, GEMINI.md, or claude.ai Project instructions):

```text
I keep knowledge bases: Life (me and my family: IDs, health, insurance, money, home); Work (work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note. At the start of a conversation, if a library holds an unfinished batch intake, ask whether to continue it.
```

Without it, questions that do not sound personal (for example "what is the payments API rate limit?") may be answered from code or general knowledge instead of your library. `init_library.py instructions --file <file> --apply` writes or updates this line from the registry, leaving the rest of the file alone.

| Agent | File the installer uses |
| --- | --- |
| Claude Code | ~/.claude/CLAUDE.md |
| Gemini CLI | ~/.gemini/GEMINI.md |
| Codex | ~/.codex/AGENTS.md (not yet confirmed) |
| OpenCode | ~/.config/opencode/AGENTS.md (not yet confirmed) |

## 5. Use it

"note this", "file these" with attachments, or just ask.

## 6. Back up, roll back, move, uninstall

Run these from the evergreen-wiki folder. Each one shows what it will do and asks before it changes anything; add `--lang zh` for Chinese messages.

- `python3 install.py backup [--note TEXT]` copies the installed skills, every instructions file that holds the knowledge-base line, the registry and the install record. The installer does the same on its own before it replaces skills, adds to a registry or writes the line.
- `python3 install.py rollback [--id ID]` restores one backup. The state before the restore is backed up first, so a rollback can be undone the same way.
- `python3 install.py move <library id> --to <folder>` moves a registered local library into that folder, keeping its folder name. Only the library moves: folders of original files stay where they are, since intake reads material from wherever the user picks it. The folder is copied, then compared file by file (size and SHA-256, empty folders and symbolic links included); only when everything matches does the registry point to the new place. Otherwise the copy is removed and nothing else changes. It refuses while a batch intake is unfinished, when the new place is inside the library, is not empty or is registered to another library, or when the disk is too small. Deleting the original folders is offered last, off by default and only after typing `delete`; they are compared once more first. Quit your agent before moving and restart it afterwards; in Obsidian, open the new folder.
- `python3 install.py uninstall` removes the three skills from every folder the installer used, the knowledge-base line (the rest of each file stays; a file left empty is deleted), the registry with every library in it, and the install record with all backups. Library folders stay unless you choose to delete them, are asked one at a time (default no) and type `delete`. Only folders with `_kb.json` or a `00_` spec file are offered; symbolic links, the root, your home folder and folders holding it, this program or an agent's settings never are. A plugin install is removed with `/plugin`.

The install record and backups live in `~/.config/evergreen-wiki/` (`%APPDATA%\evergreen-wiki` on Windows; `XDG_CONFIG_HOME` moves it). Library folders are never part of a backup: a rollback after a move restores only the registry entry, so roll back past a move only while the original folder still exists.
