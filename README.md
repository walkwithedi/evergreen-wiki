# evergreen-wiki

An LLM-maintained knowledge base that stays current, cites its sources and is easy for an assistant to search. Three agent skills keep a folder of Markdown files in order, in Google Drive or on disk (an Obsidian vault works as is):

| Skill | You say | It does |
| --- | --- | --- |
| kb-note | "note this" | saves a piece of the conversation as a quick note, to be filed later |
| kb-incremental | "file these", "file my quick notes", "archive old versions", "health check", "set up a knowledge base" | sorts material into partitions, de-duplicates it, keeps one current version per document, updates the status card when facts change, checks the library's health |
| kb-query | any question the library may answer | searches the library first and answers with the file it came from, never from memory |

[中文说明](README.zh-CN.md)

## Why

A knowledge base an assistant maintains goes stale or drifts unless the rules are strict. These skills follow a few strict ones:

- One file name per document. A new version replaces the old one under the same name; the old one moves to the archive folder. Nothing is ever deleted.
- One status card per library holds the current answer to every recurring question, each line linked to its source. The assistant rewrites it only when new material actually contradicts it, and a script checks that no line was lost in the rewrite.
- Every judgement (duplicate, new version, change of fact) needs a quote as evidence; without one the skill takes the conservative choice.
- Partitions and topics come from the library's own spec, which grows when material does not fit, and tells you each time.
- Entities (people, systems, organisations) get their own pages with backlinks, readable in Obsidian.

Uploads are converted to Markdown before intake (Word, Excel, PowerPoint, PDF, mail), so the assistant reads text instead of binary files: fewer tokens, faster runs. Files the converter cannot handle well (scans, documents that are mostly pictures) are read as originals, and when a batch holds many pictures you decide whether they are read. Each library turns this on or off in `_kb.json`; new libraries start with it on.

Intake is fast by default and comes in two parts. Fast intake places, names, de-duplicates and writes each file as soon as it is ready, with one progress line per file, so it can be searched at once; it does not read the whole text. Consolidation comes after, when you say "consolidate" or accept the offer at the end of an intake: it writes each file's key conclusions, compares the files with the status card, and shows every proposed change to the summary files as a numbered list for you to accept or leave out. Files waiting for it are listed in the library's consolidation queue, and the skills remind you while it is not empty. `_kb.json` `intake.mode` set to `full` (or "full intake" in a request) does everything for each file before it is written, as before.

A large folder is filed in batches. The assistant first counts the material (files per subfolder, types, sizes, what is already in the library) and shows a plan; after you start it, it files one subfolder or a few files at a time and prints a progress line after each batch, then rewrites the summary files once at the end and lists everything left for you to review. Progress is saved in the library, so you can stop between batches and say "continue intake" later, in a new conversation. The batch size is set in `_kb.json` (`intake`).

The full reasoning is in [docs/methodology.md](docs/methodology.md).

## How it fits together

Four pieces, all plain files on your computer or in Google Drive:

- The skills (kb-note, kb-query, kb-incremental): instructions and scripts your agent loads. They do the work.
- A library: a folder of Markdown files with its settings (`_kb.json`), spec, status card and file index. You can keep several, for example one for life and one for work.
- The registry (`kb-libraries.json`): the list of your libraries, with each one's id, label, scope and place. The skills read it to choose the library for a request.
- One line in the instructions your agent always reads (CLAUDE.md, AGENTS.md, GEMINI.md or Project instructions). It says the libraries exist, so the agent consults them before answering from memory.

```text
you --ask--> agent --reads--> instructions line ("I keep knowledge bases: ...")
               |
               +-- skill (kb-query, kb-note, kb-incremental)
                     +-- registry kb-libraries.json: which library, and where
                     +-- library folder: Markdown files, status card, file index
                           (+ Sources/: copies of the filed originals, in a local library that keeps them)
```

A local library can keep a copy of each filed original in its Sources folder, named after the topic file that holds its text and linked from it (`sources.keep` in `_kb.json`; new work libraries start with it on, life libraries off, because originals are not masked). The material you choose for an intake stays where it is.

The installer (`install.py`) puts these in place and later backs them up, rolls back, moves a library or uninstalls. [tools/kb-client](tools/kb-client/) shows the same steps as a page in the browser. [tools/doc2kb](tools/doc2kb/) converts whole folders of documents to Markdown on its own.

### Which download

Every release on the [Releases](../../releases) page carries these files:

| File | What it is | Use it for |
| --- | --- | --- |
| `kb-note-<version>.zip`, `kb-query-<version>.zip`, `kb-incremental-<version>.zip` | one skill each, English trigger phrases | uploading the skills to claude.ai or the Claude apps |
| the same names ending in `-zh.zip` | the same skills with Chinese trigger phrases | the same, in Chinese |
| `evergreen-wiki-v<version>.zip` | the whole repository: skills, `install.py` with its backup, rollback, move and uninstall commands, tools/kb-client, tools/doc2kb, the sample library and the docs | installing for a terminal agent without git, on a computer without network, or from the page in the browser on a Linux desktop |
| `doc2kb-v<version>.zip` | the document converter alone | converting folders of documents to Markdown without the skills |

### Which path

| Your situation | What to do |
| --- | --- |
| claude.ai or the Claude apps, library in Google Drive | upload the three skill zips: [In claude.ai or the Claude apps](#in-claudeai-or-the-claude-apps-google-drive) |
| Claude Code | the plugin or the installer: [In a terminal](#in-a-terminal-claude-code-codex-gemini-cli-opencode) |
| Codex, Gemini CLI, OpenCode or another agent that reads Agent Skills | the installer: [In a terminal](#in-a-terminal-claude-code-codex-gemini-cli-opencode) |
| A computer without network | copy `evergreen-wiki-v<version>.zip` over, then the installer or the desktop tool |
| A Linux desktop, no terminal | `evergreen-wiki-v<version>.zip`, then the dialogs: [On a Linux desktop](#on-a-linux-desktop-without-a-terminal) |
| Only converting documents to Markdown | `doc2kb-v<version>.zip`: [tools/doc2kb](tools/doc2kb/) |
| Trying it first | the fictional [sample library](examples/) |

## Quick start

Pick the path that matches where you use your assistant. Every path asks three questions (which kind of library, where it lives, what belongs in it), shows a preview, and writes nothing until you confirm.

### In a terminal (Claude Code, Codex, Gemini CLI, OpenCode)

```bash
git clone https://github.com/walkwithedi/evergreen-wiki && cd evergreen-wiki
python3 install.py
```

The installer asks for your language and agent, installs the three skills, sets up a local library (an Obsidian vault works), registers it and, after showing you the line, tells your agent the library exists. Restart your agent and say "note this: ...".

Claude Code users who prefer the plugin: `/plugin marketplace add walkwithedi/evergreen-wiki`, then `/plugin install evergreen-wiki@evergreen-wiki`, restart, and say "get started with the knowledge base".

No network on the computer? Download evergreen-wiki-v<version>.zip from [Releases](../../releases) elsewhere, copy it over, unzip it and run `python3 install.py` in the folder; it needs Python 3.8 or later and nothing else.

Later, from the same folder: `python3 install.py backup`, `rollback`, `move <library id> --to <folder>` and `uninstall`. Replacing skills, a registry or an instructions file is backed up first; library folders are never part of a backup, a move changes the registry only after every copied file matches, and uninstall keeps them unless you pick each one. See [docs/manual-setup.md](docs/manual-setup.md#6-back-up-roll-back-move-uninstall).

### On a Linux desktop, without a terminal

1. Download `evergreen-wiki-v<version>.zip` from [Releases](../../releases) and unzip it.
2. In the top folder, double-click `kb-client.desktop` (Knowledge base); the first time, choose to trust and launch it. The page opens in the default browser.
3. Choose Set up: pick your agent, install the skills, set up a library and let the agent know about it. The same page backs up, rolls back, moves a library and uninstalls, lists the registered libraries and, with OpenCode set up, lets you talk to OpenCode there.

It needs Python 3.8 or later and a browser. Details in [tools/kb-client](tools/kb-client/).

### In claude.ai or the Claude apps (Google Drive)

1. Download the kb-note, kb-query and kb-incremental zips from [Releases](../../releases) (the -zh zips for Chinese trigger phrases) and upload each in Settings > Capabilities > Skills.
2. Connect Google Drive, create an empty folder for the library, and open a Project for your knowledge base.
3. In the Project, say "get started with the knowledge base". The assistant asks three questions, shows a preview, writes the library into the folder and gives you one line to paste into the Project instructions. Paste it, save, and start a new conversation in the Project. That line points to the library list kept in Drive, so adding more libraries later needs no further pasting, and filed material is written straight into Drive after you confirm a preview.

Try everything first on the fictional [sample library](examples/). Prefer to do each step by hand, or need the registry format? See [docs/manual-setup.md](docs/manual-setup.md).

## How a library looks

```text
life-kb/
  _kb.json                 settings: language, timezone, names, sensitivity, conversion
  _kb-params.md            process parameters: what to close-read, what counts as a change
  00_Spec.md               partitions and topics, term fixes, thresholds, entities
  00_Status-Card.md        current facts, each linked to its source
  01_File-Index.md         every filed document with its source file and hash
  01_Open-Items.md         due dates and to-dos (life) or open decisions (work)
  01_Change-Log.md         how facts changed over time
  01_Glossary-Issues.md    term fixes, masking log, open issues
  02_Checkups_report_2026-annual.md
  ...
  Entities/                one page per person, organisation or system
  Archive/                 older versions and run logs
  Quick-Notes/             notes waiting to be filed
```

Every name is configurable in `_kb.json`, so an existing library in another language keeps its own file names.

## Backends

| | Google Drive | Local folder |
| --- | --- | --- |
| Works in | claude.ai and Claude apps with the Drive connector; other agents with a Drive MCP server | any agent with file access (Claude Code, Codex, Gemini CLI, OpenCode, Claude desktop with file access) |
| Delivery of filed material | written directly after you confirm a preview; old versions archived on the spot | the same |
| Obsidian | via Google Drive for desktop sync | open the folder as a vault |

Details: [docs/backends.md](docs/backends.md).

## Compatibility

| Environment | Status |
| --- | --- |
| Claude Code, local backend | end-to-end tested on the sample library and a new work library: query, note, intake, quick-note filing, health check, init, two-library routing |
| claude.ai / Claude apps, Drive backend | supported; English build not yet re-tested |
| Codex, Gemini CLI, OpenCode | not yet verified; reports welcome |

Scripts need Python 3.8+ and nothing outside the standard library. Without Python the skills do the same work by hand and say so (and read uploads without converting them).

## Tools

[tools/doc2kb](tools/doc2kb/) is the converter as a stand-alone tool: it turns whole folders of Office files, PDFs and mail into one Markdown knowledge base with an index, from a Linux desktop dialog or a cron job, incrementally. Each release attaches it as `doc2kb-<version>.zip`.

[tools/kb-client](tools/kb-client/) runs the installer and its backup, rollback, move and uninstall commands in a page in the browser, served from your own computer, for people who do not use a terminal, lists the registered libraries and the state of the skills, and holds a conversation with OpenCode (file material, quick notes, health checks, questions) with permission requests answered on the page; it comes with the evergreen-wiki zip.

## Development

```bash
git config core.hooksPath .githooks       # once per clone: run every check before each commit
python3 scripts/run_checks.py             # all of the checks below at once
python3 -m unittest discover -s tests     # script tests
python3 scripts/check_repo.py             # skill and manifest consistency
python3 scripts/sync_shared.py            # copy shared/ into every skill and tool after editing it
python3 scripts/sensitive_scan.py         # personal data check
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Licence: [MIT](LICENSE).
