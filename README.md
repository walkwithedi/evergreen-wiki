# evergreen-wiki

An LLM-maintained knowledge base that stays current, cites its sources and is easy for an assistant to search. Three agent skills keep a folder of Markdown files in order, in Google Drive or on disk (an Obsidian vault works as is):

| Skill | You say | It does |
| --- | --- | --- |
| kb-note | "note this" | saves a piece of the conversation as a source with checked cards, searchable at once |
| kb-ingest | "ingest these", "add to the knowledge base", "set up a knowledge base" | turns documents into cards, each a conclusion with the exact source sentence it rests on, checks every quote with a script, files sources and cards, archives older versions and rebuilds the topic pages; sets up new libraries |
| kb-query | any question the library may answer | searches the library first and follows every fact with the exact source sentence and its link, never from memory |

[中文说明](README.zh-CN.md)

## Why

An assistant that answers from a pile of documents returns whatever matches best, even an outdated plan, and a summary it writes can drift from what the documents say. evergreen-wiki keeps every answer tied to a sentence a script has found in a source:

- **Quote or no card.** Every conclusion in the library is a card: the conclusion, the exact sentence it rests on and a link to that paragraph of the source. A script looks each sentence up before anything is written; a reworded sentence is refused.
- **Answers quote.** Every fact in an answer is followed by its source sentence and link. In the weak tier a script selects the cards an answer may use and checks every quote in it before the reply.
- **Name equals version.** A new version of a document takes the old one's name; the old source and its cards move to the archive. A new version under another name is proposed by a script and confirmed by you. Nothing is ever deleted.
- **You decide what changes.** New topics, new entities, new versions, conclusions a new version drops or changes, and every rewrite of the status card are put to you first, in one preview (or as a form in the browser client).
- **Two tiers.** With a model of limited reasoning (the weak tier, such as a local model run through OpenCode) scripts do everything mechanical: they build the topic pages and pick what answers rest on. With a strong model (Claude, ChatGPT) the model writes the pages and answers, and scripts check every citation.
- **No code, no writes.** Writing to a library needs Python to run the checks. Without it the skills read and answer, and write nothing.

Documents are converted locally into batch files before they are ingested (Word, Excel, PowerPoint, PDF, mail): plain text with a source number per document and an anchor on every paragraph, cut to a size that fits the library's tier. Material becomes searchable once its run is filed.

The full reasoning is in [docs/methodology.md](docs/methodology.md) ([中文](docs/methodology.zh-CN.md)); the design and its implementation steps in [docs/design-2.0.md](docs/design-2.0.md).

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
| ChatGPT | the three `-chatgpt.zip` files: [In ChatGPT](#in-chatgpt) |
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

Documents are converted on your computer: make batch files with tools/doc2kb or the client's Build batch files and upload them in the conversation ("ingest these").

### In ChatGPT

1. Download the three `-chatgpt.zip` files from [Releases](../../releases) and unzip them.
2. Either make one custom GPT per skill (its instructions are `<skill>-prompt.md`, its knowledge `<skill>-files.zip`), or upload all six files to one project and add a project instruction such as: "For questions use kb-query-prompt.md, to save something kb-note-prompt.md, to add documents kb-ingest-prompt.md."
3. Turn on the Python tool. Reading and answering work with a Drive connector; writing to a library also needs a tool that can write to its Drive folder, and without one nothing is written.

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
  _pending/                decisions an ingest run waits for (local libraries; removed after filing)
```

Every name is configurable in `_kb.json`. A quick note is a source like any other ("Note <YYYYMMDD-HHMM> <title>"). Table E of the spec is the alias table of entities, and status-card items citing a source that got a new version carry a review mark (⏳) until they are checked.

## Coming from 1.x

The 1.x line is frozen: its last release, [v1.22.1](../../releases/tag/v1.22.1), stays available, and no further 1.x releases are made. 2.0 does not migrate 1.x libraries (schema 1); the skills say so and stop when they meet one. Keep using the 1.x release for such a library, or set up a 2.0 library in an empty folder and ingest the material again. The life library and its preset exist only in 1.x.

## Backends

| | Google Drive | Local folder |
| --- | --- | --- |
| Works in | claude.ai and Claude apps with the Drive connector; other agents with a Drive MCP server | any agent with file access (Claude Code, Codex, Gemini CLI, OpenCode, Claude desktop with file access) |
| Writing an ingest run | the scripts run on a staging folder, then the changed files are written to Drive after you confirm the preview; old copies move to the archive folder first | the scripts write straight into the folder after you confirm the preview |
| Needs | a code environment and a Drive tool that can write | Python 3.8+ |
| Obsidian | via Google Drive for desktop sync | open the folder as a vault |

Details: [docs/backends.md](docs/backends.md).

## Compatibility

| Environment | Status |
| --- | --- |
| Claude Code, local backend | the three skills run end to end on a copy of the sample library: an ingest run (strong tier, with a rejected and rewritten card, a new topic, a new entity, the pending file and a topic page check-page refused once), a quick note, questions in both tiers (with answer.py check), and a new version that marked a status-card item for review, which was then updated through status-check |
| claude.ai / Claude apps, Drive backend | supported through the staging folder; not yet tested end to end |
| ChatGPT | prompt versions built and checked by scripts; not yet tested end to end |
| Codex, Gemini CLI, OpenCode | not yet verified; reports welcome |

Scripts need Python 3.8+ and nothing outside the standard library. Without Python the skills read and answer, and write nothing.

## Tools

[tools/doc2kb](tools/doc2kb/) is the converter as a stand-alone tool: it turns whole folders of Office files, PDFs and mail into one Markdown knowledge base with an index, from a Linux desktop dialog or a cron job, incrementally. Each release attaches it as `doc2kb-v<version>.zip`.

[tools/kb-client](tools/kb-client/) runs the installer and its backup, rollback, move and uninstall commands in a page in the browser, served from your own computer, for people who do not use a terminal. It lists the registered libraries and the state of the skills, builds batch files from a folder of documents, shows the decisions an ingest run waits for as a form (Waiting for confirmation, with the status-card items to review), and holds a conversation with OpenCode (ingesting, quick notes, questions) with permission requests answered on the page. It comes with the evergreen-wiki zip.

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
