# evergreen-wiki

An offline, privately deployed knowledge base for intranet workstations (Kylin + OpenCode), kept by a local model such as DeepSeek or Qwen. Three agent skills keep a folder of Markdown files in order (an Obsidian vault works as is), and scripts do every step that can be decided mechanically, so a model of modest ability is enough. Every answer quotes a source sentence a script has checked; only the Python standard library is needed, and nothing goes online:

| Skill | You say | It does |
| --- | --- | --- |
| kb-note | "note this" | saves a piece of the conversation as a source with checked cards, searchable at once |
| kb-ingest | "ingest these", "add to the knowledge base", "set up a knowledge base" | turns documents into cards, each a conclusion with the exact source sentence it rests on, checks every quote with a script, files sources and cards, archives older versions and rebuilds the topic pages; sets up new libraries |
| kb-query | any question the library may answer | searches the library first and follows every fact with the exact source sentence and its link, never from memory |

[中文说明](README.zh-CN.md)

## Why

An assistant that answers from a pile of documents returns whatever matches best, even an outdated plan, and a summary it writes can drift from what the documents say. evergreen-wiki keeps every answer tied to a sentence a script has found in a source:

- **Offline.** Python 3.8 standard library, bash and pages opened from your own computer; no network, no packages to install.
- **Quote or no card.** Every conclusion in the library is a card: the conclusion, the exact sentence it rests on and a link to that paragraph of the source. A script looks each sentence up before anything is written; a reworded sentence is refused.
- **Answers quote.** A script selects the cards an answer may use, and every fact in the answer is followed by its source sentence and link, which a script checks before the reply.
- **Scripts do the mechanics.** Topic pages are built by a script from the cards; version candidates, entity merging and conflict lists are worked out by scripts. The model extracts cards and words the replies.
- **Name equals version.** A new version of a document takes the old one's name; the old source and its cards move to the archive. A new version under another name is proposed by a script and confirmed by you. Nothing is ever deleted.
- **You decide what changes.** New topics, new entities, new versions, conclusions a new version drops or changes, and every rewrite of the status card are put to you first, in one preview or as a form in the browser client.

Documents are converted locally into batch files before they are ingested (Word, Excel, PowerPoint, PDF, mail): plain text with a source number per document and an anchor on every paragraph, at most 20,000 characters per batch. Material becomes searchable once its run is filed.

The reasoning is in [docs/methodology.md](docs/methodology.md) ([中文](docs/methodology.zh-CN.md)); the design of this release, for libraries of about ten thousand documents, in [docs/design-4.0.md](docs/design-4.0.md) (it builds on [docs/design-3.0.md](docs/design-3.0.md)).

## How it fits together

- The skills (kb-note, kb-query, kb-ingest): instructions and scripts OpenCode loads. They do the work.
- A library: a folder of Markdown files with its settings (`_kb.json`), spec and status card, and folders for the sources, the cards and the topic pages. You can keep several, for example one per team or project.
- The registry (`~/.config/kb/kb-libraries.json`): the list of your libraries, with each one's id, label, scope and folder. The skills read it to choose the library for a request.
- One line in OpenCode's `AGENTS.md`. It says the libraries exist, so the assistant consults them before answering from memory.

```text
you --ask--> OpenCode --reads--> AGENTS.md line ("I keep knowledge bases: ...")
               |
               +-- skill (kb-query, kb-note, kb-ingest)
                     +-- registry kb-libraries.json: which library, and where
                     +-- library folder: spec, status card, Sources/, Cards/, Topics/
```

The material you choose for an ingest run stays where it is; the library keeps its converted text in Sources/.

## Downloads

Every release on the [Releases](../../releases) page carries three files:

| File | Use it for |
| --- | --- |
| `workbench-bundle-v<version>.zip` | the workstation: unpack it and double-click the entry at the top. It sets OpenCode up with your personal key and opens the knowledge base client |
| `evergreen-wiki-v<version>.zip` | the whole repository: skills, `install.py`, tools/workbench, tools/opencode-setup, tools/kb-client, tools/doc2kb, the sample library and the docs (the bundle holds the same, with the entry at the top) |
| `doc2kb-v<version>.zip` | the document converter alone |

## Quick start

### On the workstation (recommended)

1. Copy `workbench-bundle-v<version>.zip` to the workstation and unpack it.
2. Double-click `启动OpenCode工作台.desktop` at the top (trust it the first time). A page in the browser walks through three steps: check Node, opencode and the OpenCode configuration; paste your personal key, which is tested before it is written; open the workbench.
3. In the workbench, open Knowledge base and choose Set up (安装与建库; the workbench page is in Chinese): it installs the three skills into OpenCode, asks two questions (the library folder and what belongs in it), shows a preview and writes nothing until you confirm.
4. Ingest by asking in the conversation ("ingest these" with a file or folder path); answer the decisions under Waiting for confirmation; ask questions in the conversation.

Details: [tools/workbench](tools/workbench/README.md), [tools/opencode-setup](tools/opencode-setup/README.md), [tools/kb-client](tools/kb-client/README.md).

### In a terminal

```bash
cd evergreen-wiki            # the unpacked repository
python3 install.py
```

The installer asks for your language, installs the three skills into OpenCode's skills folder, sets up a library, registers it and, after showing you the line, adds it to OpenCode's AGENTS.md. Restart OpenCode and say "note this: ...".

Later, from the same folder: `python3 install.py backup`, `rollback`, `move <library id> --to <folder>` and `uninstall`. Replacing skills, a registry or an instructions file is backed up first; library folders are never part of a backup, a move changes the registry only after every copied file matches, and uninstall keeps them unless you pick each one. See [docs/manual-setup.md](docs/manual-setup.md#6-back-up-roll-back-move-uninstall).

Try everything first on the fictional [sample library](examples/). Prefer to do each step by hand, or need the registry format? See [docs/manual-setup.md](docs/manual-setup.md).

## How a library looks

```text
work-kb/
  _kb.json                 settings: language, timezone, batch size, names
  00_Spec.md               partitions and topics, term fixes, folder names, scope
  00_Status-Card.md        current facts, each linked to its source passage
  Sources/<folder>/        one Markdown file per source document, in the folder it came from, paragraphs anchored ^p1, ^p2, ...
  Cards/<folder>/          one cards file per source: conclusion, exact quote, link, topic, date
  Topics/                  one page per topic, built from the cards, newest first; earlier years on pages of their own
  Archive/                 older versions of sources and cards, in the same folders
  _index/                  the search index the scripts keep; made from the files, can be deleted
  _pending/                decisions an ingest run waits for (removed after filing)
  .kb-work/                one work folder per ingest run (hidden; removed when the run is finished)
```

Every name is configurable in `_kb.json`. A quick note is a source like any other ("Note <YYYYMMDD-HHMM> <title>"). Table E of the spec is the alias table of entities, and status-card items citing a source that got a new version carry a review mark (⏳) until they are checked.

## Coming from earlier releases

- 4.0.x: 4.0 libraries are read and written by 5.0 as they are. quote_check.py check is now quote_check.py verify, so scripts or prompts of your own that call it need the new name. Each ingest run works in `.kb-work/` inside the library; the folder is removed when the run is finished.
- 3.0.x and 2.0.x: 4.0 libraries keep each source in the folder it came from (schema 3). A library made by 2.0 or 3.0 (schema 2, one flat sources folder) is not read and not migrated; keep using [v3.0.0](../../releases/tag/v3.0.0) for it, or set up a new library and ingest the material again.
- 2.0.x in 3.0.0: a local library made by 2.0 works in 3.0 as it is; its `tier` setting is read and ignored, and topic pages are always built by the script. Libraries in Google Drive and the ChatGPT versions of the skills stay with [v2.0.0](../../releases/tag/v2.0.0), which is not developed further.
- 1.x: libraries of schema 1 are not migrated; the skills say so and stop when they meet one. Keep using [v1.22.1](../../releases/tag/v1.22.1) for such a library, or set up a new library in an empty folder and ingest the material again.

## Compatibility

| Environment | Status |
| --- | --- |
| Kylin, OpenCode with a privately deployed model | the supported setting. Scripts, the installer, the workbench and kb-client are tested in CI with Python 3.8 (on Ubuntu, standing in for Kylin) against fake OpenCode and model endpoints; an end-to-end run on a workstation is the release check |
| Other agents that read Agent Skills from `~/.agents/skills` or `~/.claude/skills` | may work; not tested |

Scripts need Python 3.8+ and nothing outside the standard library. Without Python the skills read and answer, and write nothing.

## Tools

- [tools/workbench](tools/workbench/README.md): the three-step wizard on the workstation (check, key and self-check, open the workbench); the bundle's entry starts it.
- [tools/opencode-setup](tools/opencode-setup/README.md): sets OpenCode up from one personal key, switches off its start-up downloads and checks a first start, as a page or a terminal menu.
- [tools/kb-client](tools/kb-client/README.md): the knowledge base client in the browser, served from your own computer: a conversation with OpenCode in a chosen work folder, the libraries and skills, set up, back up, roll back, move, uninstall and Waiting for confirmation.
- [tools/doc2kb](tools/doc2kb/README.md): the converter as a stand-alone tool, from a desktop dialog or a cron job, incrementally. Each release also attaches it as `doc2kb-v<version>.zip`.

## Development

```bash
git config core.hooksPath .githooks       # once per clone: run every check before each commit
python3 scripts/run_checks.py             # all of the checks below at once
python3 -m unittest discover -s tests     # script tests
python3 scripts/check_repo.py             # skill consistency
python3 scripts/sync_shared.py            # copy shared/ into every skill and tool after editing it
python3 scripts/sensitive_scan.py         # personal data check
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Licence: [MIT](LICENSE).
