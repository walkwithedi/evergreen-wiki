# evergreen-wiki

An LLM-maintained knowledge base that stays current, cites its sources and is easy for an assistant to search. Three agent skills keep a folder of Markdown files in order, in Google Drive or on disk (an Obsidian vault works as is):

| Skill | You say | It does |
| --- | --- | --- |
| kb-note | "note this" | saves a piece of the conversation as a source with checked cards, searchable at once |
| kb-ingest | "ingest these", "add to the knowledge base", "set up a knowledge base" | turns documents into cards, each a conclusion with the exact source sentence it rests on, checks every quote with a script, files sources and cards, archives older versions and rebuilds the topic pages; sets up new libraries |
| kb-query | any question the library may answer | searches the library first and follows every fact with the exact source sentence and its link, never from memory |

[中文说明](README.zh-CN.md)

## Why

A knowledge base an assistant maintains goes stale or drifts unless the rules are strict. These skills follow a few strict ones:

- One file name per document. A new version replaces the old one under the same name; the old one moves to the archive folder. Nothing is ever deleted.
- Every conclusion in the library is a card that carries the exact sentence it rests on, linked to the paragraph in the source. A script looks each quote up in the source before anything is written; a card whose quote is not found is not written.
- Topic pages are built from the cards, newest first. With a model of limited reasoning (a weak tier, such as a local model run through OpenCode) a script builds them; with a strong model the model writes them and a script checks every citation.
- Partitions and topics come from the library's own spec. A topic the spec does not have is added only after you agree.

Documents are converted locally into batch files before they are ingested (Word, Excel, PowerPoint, PDF, mail): plain text with a source number per document and an anchor on every paragraph, cut to a size that fits the library's tier. The assistant reads these instead of binary files, and quotes and links point at the anchors. Material becomes searchable once its run is filed.

The full reasoning is in [docs/methodology.md](docs/methodology.md).

## How it fits together

Four pieces, all plain files on your computer or in Google Drive:

- The skills (kb-note, kb-query, kb-ingest): instructions and scripts your agent loads. They do the work.
- A library: a folder of Markdown files with its settings (`_kb.json`), spec and status card, and folders for the sources, the cards and the topic pages. You can keep several, for example one per team or project.
- The registry (`kb-libraries.json`): the list of your libraries, with each one's id, label, scope and place. The skills read it to choose the library for a request.
- One line in the instructions your agent always reads (CLAUDE.md, AGENTS.md, GEMINI.md or Project instructions). It says the libraries exist, so the agent consults them before answering from memory.

```text
you --ask--> agent --reads--> instructions line ("I keep knowledge bases: ...")
               |
               +-- skill (kb-query, kb-note, kb-ingest)
                     +-- registry kb-libraries.json: which library, and where
                     +-- library folder: spec, status card, Sources/, Cards/, Topics/
```

The material you choose for an ingest run stays where it is; the library keeps its converted text in Sources/.

The installer (`install.py`) puts these in place and later backs them up, rolls back, moves a library or uninstalls. [tools/kb-client](tools/kb-client/) shows the same steps as a page in the browser. [tools/doc2kb](tools/doc2kb/) converts whole folders of documents to Markdown on its own.

### Which download

Every release on the [Releases](../../releases) page carries these files:

| File | What it is | Use it for |
| --- | --- | --- |
| `kb-note-<version>.zip`, `kb-query-<version>.zip`, `kb-ingest-<version>.zip` | one skill each, English trigger phrases | uploading the skills to claude.ai or the Claude apps |
| the same names ending in `-zh.zip` | the same skills with Chinese trigger phrases | the same, in Chinese |
| the same names ending in `-chatgpt.zip` | each skill's prompt (`<skill>-prompt.md`, at most 8000 characters) and its files (`<skill>-files.zip`) | ChatGPT: put the prompt into a custom GPT's instructions and upload the files zip as knowledge; or upload all three skills' files to one project, with a project instruction saying which prompt file to follow for questions, notes and ingesting. Writing to a library needs the Python tool and write access to its Drive folder |
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

Pick the path that matches where you use your assistant. Every path asks two questions (where the library lives, what belongs in it), shows a preview, and writes nothing until you confirm.

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

1. Download the kb-note, kb-query and kb-ingest zips from [Releases](../../releases) (the -zh zips for Chinese trigger phrases) and upload each in Settings > Capabilities > Skills.
2. Connect Google Drive, create an empty folder for the library, and open a Project for your knowledge base.
3. In the Project, say "get started with the knowledge base". The assistant asks two questions, shows a preview, writes the library into the folder and gives you one line to paste into the Project instructions. Paste it, save, and start a new conversation in the Project. That line points to the library list kept in Drive, so adding more libraries later needs no further pasting, and filed material is written straight into Drive after you confirm a preview.

Try everything first on the fictional [sample library](examples/). Prefer to do each step by hand, or need the registry format? See [docs/manual-setup.md](docs/manual-setup.md).

## How a library looks

```text
work-kb/
  _kb.json                 settings: language, timezone, tier, names
  00_Spec.md               partitions and topics, term fixes, folder names, scope
  00_Status-Card.md        current facts, each linked to its source passage
  Sources/                 one Markdown file per source document, paragraphs anchored ^p1, ^p2, ...
  Cards/                   one cards file per source: conclusion, exact quote, link, topic, date
  Topics/                  one page per topic, built from the cards, newest first
  Archive/                 older versions of sources and cards
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
| Claude Code, local backend | the 2.0 skills are covered by the script tests and the sample library; end-to-end runs are still to do |
| claude.ai / Claude apps, Drive backend | supported; English build not yet re-tested |
| Codex, Gemini CLI, OpenCode | not yet verified; reports welcome |

Scripts need Python 3.8+ and nothing outside the standard library. Without Python the skills do the same work by hand and say so (and read uploads without converting them).

## Tools

[tools/doc2kb](tools/doc2kb/) is the converter as a stand-alone tool: it turns whole folders of Office files, PDFs and mail into one Markdown knowledge base with an index, from a Linux desktop dialog or a cron job, incrementally. Each release attaches it as `doc2kb-<version>.zip`.

[tools/kb-client](tools/kb-client/) runs the installer and its backup, rollback, move and uninstall commands in a page in the browser, served from your own computer, for people who do not use a terminal, lists the registered libraries and the state of the skills, and holds a conversation with OpenCode (ingesting, quick notes, questions) with permission requests answered on the page; it comes with the evergreen-wiki zip.

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
