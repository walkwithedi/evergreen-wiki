# Configuration: registry and library files

Nothing about a particular library is written in the skills. Everything comes from two places.

## 1. Registry: which libraries exist

Look for the registry in this order and use the first one found:

1. A registry pasted into the current project instructions (claude.ai Project instructions, AGENTS.md, CLAUDE.md, GEMINI.md and the like).
2. The file named by the environment variable KB_LIBRARIES.
3. ~/.config/kb/kb-libraries.json (on Windows %APPDATA%\kb\kb-libraries.json).
4. config/kb-libraries.json inside this skill folder (present only in a private build made with build_skill.py --config).

If none exists, nothing is set up yet. Never guess a folder ID or path. Offer setup once, in one line, then go on:
- kb-query: a question unrelated to any knowledge base is answered normally, without the offer. A question meant for the knowledge base: say it is not set up yet and offer: "No knowledge base is set up yet. Set one up now? Three questions, a preview, nothing written before you confirm."
- kb-note: show the finished note in the reply so nothing is lost, then make the same offer; once the library exists, offer to save the note there.
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
  "names": {}
}
```

- language: language of replies, readme files and new files for this library.
- timezone: IANA name or a fixed offset such as +08:00. Use it for every time stamp (note times, archive suffixes, log names). The scripts resolve IANA names only on Python 3.9+ with a timezone database (Windows usually has none); there, use the fixed offset.
- metadata: yaml (front matter and entity links, see entity-yaml.md) or text (plain header from _kb-params.md).
- sensitivity.enabled: when true, class-A data (ID numbers, card and account numbers, passwords, one-time codes) is masked to at most the last keep_last characters before anything is written or shown.
- partitions: highest partition number, first topic partition (00 and 01 hold summary files), and the fallback partition for new topics.
- delivery: zip or direct. Empty means zip for gdrive and direct for local.
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
| notes_dir | Quick-Notes | quick notes waiting to be filed |
| notes_done_dir | Filed | quick notes already filed (inside notes_dir) |
| old_suffix | _old | archived copies: <stem>_old<YYYYMMDDHHMMSS>.md |
| snapshot_prefix | snapshot_ | temporary snapshots, never used as sources |
| readme | README.txt | the readme that comes with each delivery |
| run_log_prefix | _run-log_ | run log file name prefix (archive mode and direct delivery) |
| note_marker | Quick note: | first line of each quick note inside a filed batch |
| assistant_label, user_label | Assistant, User | speaker labels in quick notes |

Each summary file also has a search key, the file name without its number prefix and extension (00_Status-Card.md → Status-Card). A library may set spec_key, status_card_key and so on in names. Search with the key, not the full name, and always use the name actually found in the library when you write the file back; if the library name differs from the configured one, say so in the delivery note.

In kb-incremental, scripts/kbconf.py prints the resolved configuration: python3 scripts/kbconf.py show <library root or _kb.json>. Elsewhere, merge the defaults above with the names in _kb.json yourself.

### Ignored files

Every search and every read of knowledge files skips: the archive folder; names that start with an underscore (run logs, _kb.json, _kb-params.md, an inbox configuration file); names that start with snapshot_prefix; names that contain old_suffix followed by a time stamp.
