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
- kb-query: a question unrelated to any knowledge base is answered normally, without the offer. A question meant for the knowledge base: say it is not set up yet and offer: "No knowledge base is set up yet. Set one up now? Three questions, a preview, nothing written before you confirm."
- kb-note: show the finished note in the reply so nothing is lost, then make the same offer; once the library exists, offer to save the note there.
- kb-incremental (intake or setup asked for): the user already wants a library, so go straight to init mode (references/init.md in kb-incremental). Where local files can be written and commands run, do not ask for the library path in words: open the folder chooser first (references/pick-material.md in kb-incremental, library folder).
- If the user agrees, follow the getting-started part of kb-incremental init mode (references/init.md in kb-incremental). If not, do not offer again in this conversation.

```json
{
  "schema": 1,
  "preferences": {"language": "en", "output": "markdown"},
  "libraries": [
    {"id": "work", "label": "Work", "scope": "team projects, decisions, specs, owners",
     "backend": {"type": "gdrive", "root": "<drive-folder-id>"}},
    {"id": "life", "label": "Life", "scope": "me and my family: IDs, health, insurance, money, home",
     "backend": {"type": "local", "root": "~/kb/life"}}
  ]
}
```

A registry in Google Drive is the same JSON, kept by kb-incremental (init mode adds entries to it), so the project instructions never change when a library is added. It sits in the root of the first Drive library under the name kb-libraries.json; the knowledge-file searches skip it because it is not a Markdown file. Drive cannot rewrite a file in place, so an update moves the old copy to that library's archive folder and writes a new one; the folder ID in the instructions stays valid.

- id: short lowercase name used in replies and file names.
- scope: one sentence saying what belongs in the library. It is how you decide which library a request or question belongs to.
- backend.type: gdrive or local. Read references/backend-gdrive.md or references/backend-local.md accordingly, and only that one.
- preferences.output: markdown (default) or plain. With plain, replies use no Markdown markup at all (no headings, bold, bullets, code blocks or tables); number items as "1." or "(1)" instead. Knowledge files keep their own formats either way.
- preferences.language: language of replies when a library does not set its own.

## 2. Library files: how one library works

Three files sit in the library root. The two whose names start with an underscore are settings, so searches for knowledge files skip them; the spec is a summary file and is read like one.

| File | Content |
| --- | --- |
| _kb.json | machine-readable settings, below |
| _kb-params.md | process parameters: close-reading list, five trigger classes, readme sections, metadata header, issue categories, extra hard rules |
| the spec (names.spec, default 00_Spec.md) | Table A partitions and topics, Table B term fixes, Table C open issues, Table D thresholds, Table E entities, Table F value filters |

The spec is the source of every rule about partitions, topics, terms and thresholds. Read it from the library each time; never fill it in from memory or from these instructions.

### _kb.json

```json
{
  "schema": 1,
  "label": "Life",
  "preset": "life",
  "language": "en",
  "timezone": "Europe/London",
  "metadata": "yaml",
  "sensitivity": {"enabled": true, "keep_last": 4},
  "partitions": {"max": 10, "topic_start": 2, "fallback": "06"},
  "delivery": "",
  "convert": {"enabled": true, "image_limit": 10},
  "intake": {"batch_files": 10, "batch_mb": 20},
  "names": {}
}
```

- language: language of replies, readme files and new files for this library.
- timezone: IANA name or a fixed offset such as +08:00. Use it for every time stamp (note times, archive suffixes, log names). The scripts resolve IANA names only on Python 3.9+ with a timezone database (Windows usually has none); there, use the fixed offset.
- metadata: yaml (front matter and entity links, see entity-yaml.md) or text (plain header from _kb-params.md).
- sensitivity.enabled: when true, class-A data (ID numbers, card and account numbers, passwords, one-time codes) is masked to at most the last keep_last characters before anything is written or shown.
- partitions: highest partition number, first topic partition (00 and 01 hold summary files), and the fallback partition for new topics.
- delivery: direct or zip. Empty means direct: the assistant writes the files into the library after you confirm a preview, and archives the old versions at the same time. A Drive library with an inbox entry (its own unpack script) defaults to zip.
- convert: kb-incremental turns uploaded Office, PDF and mail files into Markdown with a script before reading them (fewer tokens, faster). enabled: true or false (false when the key is missing; new libraries from a preset start with true). image_limit: pictures in one batch that are read without asking (default 10); over it the user decides once for the batch. min_pdf_chars_per_page (default 200) and min_chars_per_image (default 100): below these a file is read as the original instead (a scan, or a document that is mostly pictures). outline_chars (default 6000; 0 turns it off): converted text longer than this also gets an outline (opening text, headings with line numbers), which is read first; the full text only where it is needed (references/convert.md in kb-incremental).
- intake: kb-incremental files many files in batches (references/batches.md in kb-incremental). A batch closes at batch_files files (default 10) or batch_mb megabytes (default 20); material that makes more than one batch is planned first and filed batch by batch. Lower them when one batch takes too long.
- sources: a local library with direct delivery can keep a copy of each filed original (section 3, Originals). keep: true or false (false when the key is missing; new work libraries start with true, life libraries with false, since originals bypass masking). max_mb (default 50; 0 means no limit): larger originals are not copied and the readme says so. Ignored for zip and Google Drive delivery.
- names: overrides for any default name below. Leave out the keys you do not change.

### Names

| Key | Default | Meaning |
| --- | --- | --- |
| spec | 00_Spec.md | the library spec |
| status_card | 00_Status-Card.md | current valid conclusions (work) or current status (life) |
| index | 01_File-Index.md | file index |
| open_items | 01_Open-Items.md | open decisions (work) or due dates and to-dos (life) |
| changelog | 01_Change-Log.md | how conclusions changed over time |
| glossary | 01_Glossary-Issues.md | term fixes, masking log, open issues |
| archive_dir | Archive | where older versions go |
| entities_dir | Entities | entity pages |
| sources_dir | Sources | copies of filed originals (only when sources.keep is on) |
| notes_dir | Quick-Notes | quick notes waiting to be filed |
| notes_done_dir | Filed | quick notes already filed (inside notes_dir) |
| old_suffix | _old | archived copies: <stem>_old<YYYYMMDDHHMMSS>.md |
| snapshot_prefix | snapshot_ | temporary snapshots, never used as sources |
| readme | README.txt | the readme that comes with each delivery |
| run_log_prefix | _run-log_ | run log file name prefix (archive mode and direct delivery) |
| batch_plan | _intake-batches.json | progress file of a batch intake run, in the library root until the run is finished |
| note_marker | Quick note: | first line of each quick note inside a filed batch |
| assistant_label, user_label | Assistant, User | speaker labels in quick notes |

Each summary file also has a search key, the file name without its number prefix and extension (00_Status-Card.md → Status-Card). A library may set spec_key, status_card_key and so on in names. Search with the key, not the full name, and always use the name actually found in the library when you write the file back; if the library name differs from the configured one, say so in the delivery note.

In kb-incremental, scripts/kbconf.py prints the resolved configuration: python3 scripts/kbconf.py show <library root or _kb.json>. Elsewhere, merge the defaults above with the names in _kb.json yourself.

### Ignored files

Every search and every read of knowledge files skips: the archive folder; the sources folder (names.sources_dir, copies of originals: opened only through a topic file's original link, see kb-query); names that start with an underscore (run logs, _kb.json, _kb-params.md, an inbox configuration file, the batch progress file); names that start with snapshot_prefix; names that contain old_suffix followed by a time stamp.

## 3. Library folder and material: words to use with the user

Users do not know the inner workings, so the library folder and the material must never be confused, and the reply names them the same way every time:

- Library folder: where the filed Markdown files, the spec, the status card and the file index live. There is one per library and it matters: the assistant writes here, and the registry records only this folder (backend.root). In Chinese: 知识库文件夹（整理好的结果，助手维护）.
- Material: the user's own original files (Word, PDF, spreadsheets, mail, pictures), from any number of folders or single files anywhere (a work folder, a network or removable drive, the desktop). The assistant only reads it and never changes it. It is chosen anew for every intake: never registered, remembered or suggested. In Chinese: 资料来源（你的原始文件，可以来自多个文件夹，只读不改）.
- Originals: in a local library that keeps them (sources.keep), a copy of each filed original stored in the library's sources folder under its topic file's name and linked from it. The material itself stays where it was. In Chinese: 原件（库里保存的原始文件副本）.

Rules:
1. To the user, say only "library folder" and "material" (知识库文件夹, 资料来源), with the short explanation in brackets the first time each appears in a conversation. Never say registry, root, backend, _kb.json or 注册表 to the user, except in the init preview and when the user uses the word first.
2. No folder is ever chosen for the user. Where a desktop chooser can open (references/pick-material.md in kb-incremental), let the user pick there; otherwise ask for the path in one sentence without suggesting one. Folders already chosen can be changed in the init preview.
3. Material outside the library folder is normal. Never offer to change a registered library's folder because the material is somewhere else. Folders the user names that hold original files are material: read them from there. Change a library's folder only when the user explicitly asks to move the library or points it at a folder that already holds that library (_kb.json or a 00_ spec file); a move of a local library goes through install.py move.
4. When it is unclear which the user means, ask once with this question, each option saying what follows:
   "Is <folder> where your original files are, or where the filed knowledge base should be?
   1. Original files (material): I read them from there and file the results into <library label>; nothing in that folder changes.
   2. Knowledge base (library folder): <library label> will be kept there from now on; only choose this when the folder holds no original files."
   In Chinese:
   「<文件夹> 是放你原始文件的地方，还是放整理结果的知识库？
   1. 原始文件（资料来源）：我从这里读取，整理结果放进<库名>，这个文件夹里的东西不会被改动。
   2. 知识库（知识库文件夹）：今后<库名>的整理结果放在这里；只有这个文件夹里没有原始文件时才选。」

## 4. Unfinished intake: remind once per conversation

A batch intake (references/batches.md in kb-incremental) can stop between batches or be interrupted inside one; its progress file (names.batch_plan) stays in the library root of a local library until the run is finished. Every skill checks for it, so the user is reminded next time:

1. After the library is chosen (and, when the instructions line asks for it, at the start of a conversation for each registered local library), find_exact names.batch_plan in the library root. Not there: nothing to say. A Google Drive library keeps its plan only for one conversation: skip this.
2. Where commands run, python3 scripts/batch_plan.py status --plan <file> in kb-incremental (kb-query and kb-note: read the JSON; batches with status "pending" are left, final_step "pending" means the summary step is due). Nothing left and the final step done: say nothing.
3. Otherwise say in one line how far it got (batches done of all, files left, last update; "interrupted in batch <n>" when a pending batch has a start time), then ask once, as a choice:
   - Continue intake (recommended): kb-incremental, batch mode, continue the open run.
   - Later: no further reminder in this conversation.
   - End this intake: python3 scripts/batch_plan.py skip --plan <file> --rest, then the final step for what was filed. Filed files stay; the original files are not touched.
   In Chinese: 「上次的分批入库还没做完：已完成 <n>/<总数> 批，还剩 <m> 个文件（<时间> 更新）。要继续吗？」 with 继续入库 / 稍后再说 / 结束这次入库.
4. Ask at most once per conversation. kb-query and kb-note only remind: after their own answer or note, "Continue intake" hands over to kb-incremental; they never file material themselves.
