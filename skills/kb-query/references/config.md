# Configuration: registry and library files

Nothing about a particular library is written in the skills. Everything comes from two places.

## 1. Registry: which libraries exist

Look for the registry in this order and use the first one found:

1. The current project instructions (claude.ai Project instructions, AGENTS.md, CLAUDE.md, GEMINI.md and the like), in one of two forms:
   - a line naming a registry in Google Drive: "registry: Google Drive folder <folder id>, file kb-libraries.json". find_exact kb-libraries.json in that folder (the folder ID comes from the instructions, not from memory) and read it; several copies: use the most recently modified and mention it. Not found: say so and offer init mode; do not search elsewhere.
   - a registry pasted as JSON (the older form; still read as is).
2. The file named by the environment variable KB_LIBRARIES.
3. ~/.config/kb/kb-libraries.json (on Windows %APPDATA%\kb\kb-libraries.json).
4. config/kb-libraries.json inside this skill folder (present only in a private build made with build_skill.py --config).

If none exists, nothing is set up yet. Never guess a folder ID or path. Offer setup once, in one line, then go on:
- kb-query: a question unrelated to any knowledge base is answered normally, without the offer. A question meant for the knowledge base: say it is not set up yet and offer: "No knowledge base is set up yet. Set one up now? Two questions, a preview, nothing written before you confirm."
- kb-note: show the finished note in the reply so nothing is lost, then make the same offer; once the library exists, offer to save the note there.
- kb-ingest (intake or setup asked for): the user already wants a library, so go straight to init mode (references/init.md in kb-ingest). Where local files can be written and commands run, do not ask for the library path in words: open the folder chooser first (references/pick-material.md in kb-ingest, library folder).
- If the user agrees, follow the getting-started part of kb-ingest's init mode (references/init.md in kb-ingest). If not, do not offer again in this conversation.

```json
{
  "schema": 1,
  "preferences": {"language": "en", "output": "markdown"},
  "libraries": [
    {"id": "work", "label": "Work", "scope": "team projects, decisions, specs, owners",
     "backend": {"type": "gdrive", "root": "<drive-folder-id>"}},
    {"id": "atlas", "label": "Project Atlas", "scope": "Project Atlas plans, minutes and reports",
     "backend": {"type": "local", "root": "~/kb/atlas"}}
  ]
}
```

A registry in Google Drive is the same JSON, kept by kb-ingest (init mode adds entries to it), so the project instructions never change when a library is added. It sits in the root of the first Drive library under the name kb-libraries.json; the knowledge-file searches skip it because it is not a Markdown file. Drive cannot rewrite a file in place, so an update moves the old copy to that library's archive folder and writes a new one; the folder ID in the instructions stays valid.

- id: short lowercase name used in replies and file names.
- scope: one sentence saying what belongs in the library. It is how you decide which library a request or question belongs to.
- backend.type: gdrive or local. Read references/backend-gdrive.md or references/backend-local.md accordingly, and only that one.
- preferences.output: markdown (default) or plain. With plain, replies use no Markdown markup at all (no headings, bold, bullets, code blocks or tables); number items as "1." or "(1)" instead. Knowledge files keep their own formats either way.
- preferences.language: language of replies when a library does not set its own.

## 2. Library files: how one library works

A 2.0 library holds, in its root, _kb.json (settings; its name starts with an underscore, so searches for knowledge files skip it), the spec and the status card, and beside them the folders for sources, cards, topics, the archive and quick notes.

| File or folder | Content |
| --- | --- |
| _kb.json | machine-readable settings, below |
| the spec (names.spec, default 00_Spec.md) | Table A partitions and topics, Table B term fixes, Table C open issues, Table E entities and their aliases, Table F value filters, folders and names, cards and evidence, scope |
| the status card (names.status_card) | what is true now, every item citing its source passage; the library's home page |
| names.sources_dir (Sources) | one Markdown file per source document, named after the original file, paragraphs anchored ^p1, ^p2, ... |
| names.cards_dir (Cards) | one cards file per source, with the same name: each card a conclusion with its exact source sentence |
| names.topics_dir (Topics) | one page per topic, every statement citing its card's source passage |
| names.archive_dir (Archive) | older versions of sources and cards, never deleted |
| names.notes_dir (Quick-Notes) | quick notes written by kb-note |

The spec is the source of every rule about partitions, topics, terms and entities. Read it from the library each time; never fill it in from memory or from these instructions.

### _kb.json

```json
{
  "schema": 2,
  "label": "Work",
  "preset": "work",
  "language": "en",
  "timezone": "Europe/London",
  "tier": "weak",
  "partitions": {"max": 9, "topic_start": 2, "fallback": "09"},
  "names": {}
}
```

- schema: 2. A _kb.json with schema 1 belongs to a 1.x library: 2.0 does not read or migrate it; say so and stop (the 1.x release keeps working for it, or a 2.0 library is set up and the material ingested again).
- language: language of replies and new files for this library.
- timezone: IANA name or a fixed offset such as +08:00. Use it for every time stamp (note times, archive suffixes). The scripts resolve IANA names only on Python 3.9+ with a timezone database (Windows usually has none); there, use the fixed offset.
- tier: weak or strong. Weak: scripts build the topic pages and select what answers rest on, for models with limited reasoning (OpenCode, local models). Strong: the assistant writes the topic pages and a script checks every citation (Claude, ChatGPT). Missing: decided by the assistant in use, and said.
- batch_chars (optional): characters per batch file instead of the tier's (weak 20000, strong 100000).
- quote_min, quote_max (optional): the length a card's quote must keep to (default 6 to 300 characters).
- partitions: highest partition number, first topic partition (00 and 01 hold summary files), and the fallback partition for new topics.
- names: overrides for any default name below. Leave out the keys you do not change.

### Names

| Key | Default | Meaning |
| --- | --- | --- |
| spec | 00_Spec.md | the library spec |
| status_card | 00_Status-Card.md | what is true now, the library's home page |
| sources_dir | Sources | source documents |
| cards_dir | Cards | cards files |
| topics_dir | Topics | topic pages |
| archive_dir | Archive | where older versions go |
| entities_dir | Entities | entity pages |
| notes_dir | Quick-Notes | quick notes waiting to be ingested |
| notes_done_dir | Filed | quick notes already ingested (inside notes_dir) |
| old_suffix | _old | archived copies: <stem>_old<YYYYMMDDHHMMSS>.md |
| snapshot_prefix | snapshot_ | temporary snapshots, never used as sources |
| note_marker | Quick note: | first line of each quick note |
| assistant_label, user_label | Assistant, User | speaker labels in quick notes |

Each summary file also has a search key, the file name without its number prefix and extension (00_Status-Card.md → Status-Card). A library may set spec_key, status_card_key and so on in names. Search with the key, not the full name, and always use the name actually found in the library when you write the file back.

Where scripts run, scripts/kbconf.py prints the resolved configuration: python3 scripts/kbconf.py show <library root or _kb.json>. Elsewhere, merge the defaults above with the names in _kb.json yourself.

### Ignored files

Every search and every read of knowledge files skips: the archive folder; names that start with an underscore (_kb.json and other settings); names that start with snapshot_prefix; names that contain old_suffix followed by a time stamp.

## 3. Library folder and material: words to use with the user

Users do not know the inner workings, so the library folder and the material must never be confused, and the reply names them the same way every time:

- Library folder: where the sources, cards, topic pages, the spec and the status card live. There is one per library and it matters: the assistant writes here, and the registry records only this folder (backend.root). In Chinese: 知识库文件夹（整理好的结果，助手维护）.
- Material: the user's own original files (Word, PDF, spreadsheets, mail, pictures), from any number of folders or single files anywhere (a work folder, a network or removable drive, the desktop). The assistant only reads it and never changes it. It is chosen anew for every intake: never registered, remembered or suggested. In Chinese: 资料来源（你的原始文件，可以来自多个文件夹，只读不改）.

Rules:
1. To the user, say only "library folder" and "material" (知识库文件夹, 资料来源), with the short explanation in brackets the first time each appears in a conversation. Never say registry, root, backend, _kb.json or 注册表 to the user, except in the init preview and when the user uses the word first.
2. No folder is ever chosen for the user. Where a desktop chooser can open (references/pick-material.md in kb-ingest), let the user pick there; otherwise ask for the path in one sentence without suggesting one. Folders already chosen can be changed in the init preview.
3. Material outside the library folder is normal. Never offer to change a registered library's folder because the material is somewhere else. Folders the user names that hold original files are material: read them from there. Change a library's folder only when the user explicitly asks to move the library or points it at a folder that already holds that library (_kb.json or a 00_ spec file); a move of a local library goes through install.py move.
4. When it is unclear which the user means, ask once with this question, each option saying what follows:
   "Is <folder> where your original files are, or where the filed knowledge base should be?
   1. Original files (material): I read them from there and file the results into <library label>; nothing in that folder changes.
   2. Knowledge base (library folder): <library label> will be kept there from now on; only choose this when the folder holds no original files."
   In Chinese:
   「<文件夹> 是放你原始文件的地方，还是放整理结果的知识库？
   1. 原始文件（资料来源）：我从这里读取，整理结果放进<库名>，这个文件夹里的东西不会被改动。
   2. 知识库（知识库文件夹）：今后<库名>的整理结果放在这里；只有这个文件夹里没有原始文件时才选。」
