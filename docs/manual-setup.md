# Manual setup

The [quick start](../README.md#quick-start) does all of this for you: `python3 install.py` in a terminal, or "get started with the knowledge base" in your assistant. This page is for doing each step by hand, adding libraries later, or understanding what the guided setup wrote.

[中文](manual-setup.zh-CN.md)

## 1. Install the skills

- Claude Code: `/plugin marketplace add walkwithedi/evergreen-wiki`, then `/plugin install evergreen-wiki@evergreen-wiki`.
- claude.ai or the Claude apps: download the kb-note, kb-query and kb-incremental zips from [Releases](../../../releases) and upload each in Settings > Capabilities > Skills (Chinese trigger phrases: the -zh zips).
- Other agents that read Agent Skills: `python3 install.py --target agents` (or `--target gemini`, `opencode`, `codex`, `claude-code`, or `--dest <folder>`); add `--locale zh` for Chinese trigger phrases, `--force` to replace an existing install, `--dry-run` to see what would happen.

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
    {"id": "work", "label": "Work", "scope": "team projects, decisions, owners, specs",
     "backend": {"type": "gdrive", "root": "<drive folder id>"}}
  ]
}
```

Put it in `~/.config/kb/kb-libraries.json` (on Windows `%APPDATA%\kb\kb-libraries.json`, or point `KB_LIBRARIES` at it). `init_library.py register --id ... --label ... --scope ... --type local|gdrive --root ...` adds an entry and refuses an id or folder that is already there.

On claude.ai, paste it into your Project instructions, or build private zips that carry it: `python3 scripts/build_skill.py --config my-libraries.json` (never publish those).

The scope matters: it is how the assistant decides which library a note or question belongs to. Write one sentence per library, and keep scopes from overlapping.

## 4. Tell your assistant the libraries exist

Add one line to the instructions it always reads (CLAUDE.md, AGENTS.md, GEMINI.md, or claude.ai Project instructions):

```text
I keep knowledge bases: Life (me and my family: IDs, health, insurance, money, home); Work (team projects, decisions, owners, specs). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note.
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
