# Init mode: get started or set up a new library

Trigger: "get started with the knowledge base", "first time", "set up a knowledge base", "new library", "init". Also entered when kb-query or kb-note found no registry and the user accepted the offer to set one up.
Result: the library folder holds _kb.json (schema 3), the spec, the status card and the folders for sources, cards, topics and the archive; the library is in the registry; the assistant's always-read instructions say the library exists.

The preset lives in assets/presets/work/: _kb.json, 00_Spec.md and summary/00_Status-Card.md, with a Chinese translation in zh/. The placeholder {{DATE}} is filled when writing.

scripts/init_library.py holds the shared definition of a new library: the suggested label, id and scope, the files and folders to create, the registry entry and the instructions line. The interactive installer (install.py) uses the same script, so a library made either way looks the same. Setting up a library needs it: Without a code environment (Python), write nothing to the library and say so; reading and answering still work. Say that setting up needs a code environment and stop.

## Rules

1. Questions, then a preview, then writing. Nothing is written before the user confirms the preview.
2. Only create files. Never delete or rewrite anything in an existing folder.
3. A new library needs an empty folder (empty subfolders are fine). A folder holding Markdown files or a _kb.json is refused.
4. A folder with a _kb.json of schema 1 is a 1.x library, one of schema 2 a 2.0 or 3.0 library (all sources in one folder): say that this release does not migrate them, that the release that made it (1.x, or 3.0) keeps working for it, and that a new library is set up in another, empty folder and the material ingested again.
5. Never invent rules: every partition and topic comes from the preset as the user confirmed or changed it.
6. Ask as little as possible. Ask only what cannot be found out reliably; show everything else in the preview, where the user can change any item.

## Getting started (first-time guide)

For a user who has just installed the skills, or says it is the first time. Keep each message short and in the user's language.

1. Look before asking, without telling the user each check:
   - Registry (references/config.md): found, and with which libraries.
   - Python: python3 scripts/init_library.py defaults --preset work runs (it also prints the suggested timezone and language). It does not: say that setting up needs a code environment and stop.
   - Local files can be written (references/backend-local.md). They cannot: stop and say what is missing (references/environment.md).
2. Libraries already registered: list them in one line each (label and scope) and ask whether to add another library.
3. Otherwise say in two sentences what will happen: two questions, a preview, nothing is written before "confirm". Then run the questions.
4. After writing, finish with the report and three things to try (step 7 of "Write").

A folder that holds the user's original files (Office, PDF, pictures, no _kb.json or spec) is material, not a library: never register it as a library or point a library at it. Offer to ingest it into a registered library, or to set up a new library in another, empty folder. When the user's meaning is unclear, ask with the question in references/config.md, section 3.

## Questions

Two questions, one at a time:
1. Where the library folder goes (the filed results, not the original files; say so in the question). Never suggest a path. A local folder (an Obsidian vault works): let the user choose it with the chooser in references/pick-material.md (library folder) and ask in words only when it cannot open.
2. Scope: one sentence saying what belongs in the library, suggested from python3 scripts/init_library.py defaults --preset work --language <language>. Explain that it decides which library each request goes to.

Found out, not asked (all shown in the preview):
- Label and id: from the defaults. If the id is already in the registry, add -2, -3.
- Language: the language the user writes in.
- Timezone: from the defaults command (the system timezone); when the system timezone is UTC and the user's messages indicate another, use that and say so in the preview.
- Partitions: the preset's Table A, unchanged unless the user edits it in the preview. Partition numbers stay two-digit and continuous; the fallback partition stays 09 unless the user changes it.

## Preview

Fixed structure:
  Library: <label> (id <id>) | folder: <path>
  Scope: <one sentence> | language: <lang> | timezone: <tz>
  1. _kb.json: new
  2. Spec: new from the preset (version v1, today), partitions: <number name, one line each>
  3. Status card: new, empty
  4. Folders to create: sources, cards, topics, archive (with their names)
  5. Registry: entry to add, and the file it goes into
  6. Instructions line: the line, and the file it goes into (AGENTS.md for OpenCode)
End with: reply "confirm" to write, or name any item to change. The turn ends here.

With Python, python3 scripts/init_library.py plan --root <path> --preset work --label <label> --id <id> --scope "<scope>" --language <lang> --timezone <tz> prints items 1 to 4; it refuses (exit 3) when the folder already holds Markdown files or a _kb.json.

## Write (after confirmation)

1. Re-check: if the folder changed since the preview, stop and report.
2. Write the files: python3 scripts/init_library.py write with the same options as the plan. It writes every file, creates the folders and verifies each file.
   Partition changes the user made in the preview: apply them to Table A of the spec just written.
3. Verify every file exists once (find_exact for each).
4. Registry. If the registry is a file you can write (KB_LIBRARIES or ~/.config/kb/kb-libraries.json):
   python3 scripts/init_library.py register --id <id> --label <label> --scope "<scope>" --type local --root <path> --language <lang>
   It creates the file if needed, keeps every other entry and refuses an id or root already registered (exit 3: report it, ask for another id).
   A registry file you cannot write: run register on <work>/kb-libraries.json, then python3 scripts/init_library.py instructions --registry <work>/kb-libraries.json --project-block, and give that block to paste.
5. Make the libraries visible. An assistant only consults kb-query when it knows a knowledge base exists, and it cannot see the registry until a skill reads it. The line lists every registered library:
   "I keep knowledge bases: <label> (<scope>); <label> (<scope>). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note; to add documents, use kb-ingest."
   In Chinese: "我有知识库：<名称>（<范围>）；<名称>（<范围>）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note；要入库用 kb-ingest。"
   python3 scripts/init_library.py instructions --registry <registry> --file <file> prints the line and says whether it would be added or would update the line already there (found by its opening words, so a second library never adds a second line); add --apply to write. The file is the one the assistant always reads: AGENTS.md in the user's home or project for OpenCode. Write only after the user agrees, which the preview confirmation covers when item 6 named the file; every other line of the file stays as it is.
6. Check: python3 scripts/kbconf.py validate <library root> passes, and the registry loads (python3 scripts/kbconf.py registry, where the registry is a file).
7. Report in a few lines: what was written and where, anything that needs a manual step (the block to paste from step 4, if any, or a restart of the agent so it reads the new instructions line), then three things to try, in the library language:
   "note this: <a fact that fits the scope>"; "ingest these" with documents or batch files; and, once material is in, "what did we decide about <topic>?".
