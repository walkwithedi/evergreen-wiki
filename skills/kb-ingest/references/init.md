# Init mode: get started or set up a new library

Trigger: "get started with the knowledge base", "first time", "set up a knowledge base", "new library", "init". Also entered when kb-query or kb-note found no registry and the user accepted the offer to set one up.
Result: the library folder holds _kb.json (schema 2), the spec, the status card and the folders for sources, cards, topics and the archive; the library is in the registry; the assistant's always-read instructions say the library exists.

The preset lives in assets/presets/work/: _kb.json, 00_Spec.md and summary/00_Status-Card.md, with a Chinese translation in zh/. The placeholder {{DATE}} is filled when writing.

scripts/init_library.py holds the shared definition of a new library: the suggested label, id and scope, the files and folders to create, the registry entry and the instructions line. The interactive installer (install.py) uses the same script, so a library made either way looks the same. Use it whenever Python runs; without Python, do its job by hand as described at each step and say "not script-checked" in the report.

## Rules

1. Questions, then a preview, then writing. Nothing is written before the user confirms the preview.
2. Only create files. Never delete or rewrite anything in an existing folder.
3. A new library needs an empty folder (empty subfolders are fine). A folder holding Markdown files or a _kb.json is refused.
4. A folder with a _kb.json of schema 1 is a 1.x library: say that 2.0 does not migrate 1.x libraries, that the 1.x release keeps working for it, and that a 2.0 library is set up in another, empty folder and the material ingested again.
5. Never invent rules: every partition and topic comes from the preset as the user confirmed or changed it.
6. Ask as little as possible. Ask only what cannot be found out reliably; show everything else in the preview, where the user can change any item.

## Getting started (first-time guide)

For a user who has just installed the skills, or says it is the first time. Keep each message short and in the user's language.

1. Look before asking, without telling the user each check:
   - Registry (references/config.md): found, and with which libraries.
   - Python: python3 scripts/init_library.py defaults --preset work runs (it also prints the suggested timezone and language).
   - Backends: a Drive tool is available (references/backend-gdrive.md); local files can be written (references/backend-local.md).
2. Libraries already registered: list them in one line each (label and scope) and ask whether to add another library.
3. Otherwise say in two sentences what will happen: two questions, a preview, nothing is written before "confirm". Then run the questions.
4. After writing, finish with the report and three things to try (step 7 of "Write").

A folder that holds the user's original files (Office, PDF, pictures, no _kb.json or spec) is material, not a library: never register it as a library or point a library at it. Offer to ingest it into a registered library, or to set up a new library in another, empty folder. When the user's meaning is unclear, ask with the question in references/config.md, section 3.

## Questions

Two questions, one at a time:
1. Where the library folder goes (the filed results, not the original files; say so in the question). Never suggest a path. Local folder when local files can be written (an Obsidian vault works); where commands run, let the user choose the folder with the chooser in references/pick-material.md (library folder) and ask in words only when it cannot open. Google Drive when only a Drive tool is available (a folder link or ID; the folder must exist and be empty). Both available: ask which, suggesting local. Neither: stop and say what is missing (references/environment.md).
2. Scope: one sentence saying what belongs in the library, suggested from python3 scripts/init_library.py defaults --preset work --language <language>. Explain that it decides which library each request goes to.

Found out, not asked (all shown in the preview):
- Label and id: from the defaults. If the id is already in the registry, add -2, -3.
- Language: the language the user writes in.
- Timezone: from the defaults command (the system timezone); in claude.ai or wherever the system timezone is meaningless (often UTC on a server), the timezone the user's messages or profile indicate, else ask in the preview.
- Tier: strong when you are a Claude or ChatGPT client, weak when you run in OpenCode or on a local model. Say in the preview what it means in a few words (weak: scripts build the topic pages; strong: you write them and a script checks every citation), so the user can change it there.
- Partitions: the preset's Table A, unchanged unless the user edits it in the preview. Partition numbers stay two-digit and continuous; the fallback partition stays 09 unless the user changes it.

## Preview

Fixed structure:
  Library: <label> (id <id>) | backend: gdrive <id> / local <path>
  Scope: <one sentence> | language: <lang> | timezone: <tz> | tier: weak / strong
  1. _kb.json: new
  2. Spec: new from the preset (version v1, today), partitions: <number name, one line each>
  3. Status card: new, empty
  4. Folders to create: sources, cards, topics, archive (with their names)
  5. Registry: entry to add, and where (a file path, or kb-libraries.json in Google Drive: which folder, new or updated)
  6. Instructions line: the line, and the file it goes into; in claude.ai "one line to paste, once" or "already in the Project instructions, nothing to paste"
End with: reply "confirm" to write, or name any item to change. The turn ends here.

With Python, python3 scripts/init_library.py plan --root <path> --preset work --label <label> --id <id> --scope "<scope>" --language <lang> --timezone <tz> --tier <tier> prints items 1 to 4; it refuses (exit 3) when the folder already holds Markdown files or a _kb.json. For Drive, run it with --root pointing at an empty work folder just to get the list.

## Write (after confirmation)

1. Re-check: if the folder changed since the preview, stop and report.
2. Write the files:
   - Local: python3 scripts/init_library.py write with the same options as the plan. It writes every file, creates the folders and verifies each file.
   - Drive: python3 scripts/init_library.py render --out <work>/init with the same options, then write_new each file it rendered into the library folder (the backend file says how to set file types) and ensure_folder for each folder it names.
   - Without Python: fill the preset files yourself (the spec with the confirmed Table A, version v1 and today's date; the status card with today's date), write _kb.json as the preset's with label, language, timezone and tier set, then ensure_folder for each folder.
   Partition changes the user made in the preview: apply them to Table A of the spec just written.
3. Verify every file exists once (find_exact for each).
4. Registry. If the registry is a file you can write (KB_LIBRARIES or ~/.config/kb/kb-libraries.json):
   python3 scripts/init_library.py register --id <id> --label <label> --scope "<scope>" --type local|gdrive --root <path or folder id> --language <lang>
   It creates the file if needed, keeps every other entry and refuses an id or root already registered (exit 3: report it, ask for another id). Without Python, add the entry by hand.
   Otherwise (claude.ai and other environments without a writable registry), keep the registry in Google Drive when a Drive tool is available:
   a. Find the current registry: a "registry: Google Drive folder <id>, file kb-libraries.json" line in the Project instructions (find_exact kb-libraries.json in that folder and read it), else a registry pasted as JSON in the instructions, else none. Put it, or nothing, in <work>/kb-libraries.json.
   b. python3 scripts/init_library.py register --registry <work>/kb-libraries.json --id ... --label ... --scope "..." --type gdrive --root <folder id> --language <lang>
   c. Write it to Drive. No Drive registry yet: write_new kb-libraries.json (application/json) in the root of the new library; that folder is now the registry folder. A Drive registry exists: move_rename its current copy into the archive folder of the library it sits in, as kb-libraries_old<YYYYMMDDHHMMSS>.json, then write_new the updated one in the same folder (Drive cannot rewrite a file in place). find_exact afterwards: exactly one kb-libraries.json in the registry folder.
   d. The instructions line: if the Project instructions already hold the "registry: Google Drive folder" line, nothing to paste; say so. Otherwise
      python3 scripts/init_library.py instructions --drive-folder <registry folder id> --language <lang>
      and give that one line to paste, with: open the Project, Project instructions, paste it (replacing any older knowledge base lines or pasted registry), save, and start a new conversation in the Project. This is the only time; later libraries go into the Drive registry without touching the instructions. Not working in a Project: say that only Project instructions persist, and suggest creating a Project for the knowledge base.
   No Drive tool (a local library in an agent that cannot write the registry file): run register on <work>/kb-libraries.json, then python3 scripts/init_library.py instructions --registry <work>/kb-libraries.json --project-block, and give that block to paste.
5. Make the libraries visible. An assistant only consults kb-query when it knows a knowledge base exists, and it cannot see the registry until a skill reads it. The line lists every registered library:
   "I keep knowledge bases: <label> (<scope>); <label> (<scope>). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note; to add documents, use kb-ingest."
   In Chinese: "我有知识库：<名称>（<范围>）；<名称>（<范围>）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note；要入库用 kb-ingest。"
   python3 scripts/init_library.py instructions --registry <registry> --file <file> prints the line and says whether it would be added or would update the line already there (found by its opening words, so a second library never adds a second line); add --apply to write. The file is the one the assistant always reads: CLAUDE.md, AGENTS.md or GEMINI.md in the user's home or project. Write only after the user agrees, which the preview confirmation covers when item 6 named the file; every other line of the file stays as it is. In claude.ai the line is the one from step 4d.
6. Check: python3 scripts/kbconf.py validate <library root or the rendered _kb.json> passes, and the registry loads (python3 scripts/kbconf.py registry, where the registry is a file).
7. Report in a few lines: what was written and where, anything that needs a manual step (the one-line paste in step 4d, if any, or a restart of the agent so it reads the new instructions line), then three things to try, in the library language:
   "note this: <a fact that fits the scope>"; "ingest these" with documents or batch files; and, once material is in, "what did we decide about <topic>?".
