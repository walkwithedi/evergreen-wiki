# Init mode: get started, set up a new library or complete an existing one

Trigger: "get started with the knowledge base", "first time", "set up a knowledge base", "new library", "init", "complete the settings". Also entered when kb-query or kb-note found no registry and the user accepted the offer to set one up.
Result: the library root holds _kb.json, _kb-params.md, the spec and the empty summary files, the library is in the registry, and the assistant's always-read instructions say the library exists.

Presets live in assets/presets/<name>/: _kb.json, _kb-params.md, 00_Spec.md and summary/ (empty summary files). A preset may also have <language>/ with translated _kb-params.md, 00_Spec.md and summary/, used for a library in that language (work has zh/). Available: life and work. For a blank start, take the closer one and remove the topics the user does not want. Placeholders {{DATE}}, {{HEADING_LIMIT}} and {{FILENAME_LIMIT}} are filled when writing.

scripts/init_library.py holds the shared definition of a new library: the suggested label, id and scope per preset and language, the files and folders to create, the registry entry and the instructions line. The interactive installer (install.py) uses the same script, so a library made either way looks the same. Use it whenever Python runs; without Python, do its job by hand as described at each step and say "not script-checked" in the report.

## Rules

1. Questions, then a preview, then writing. Nothing is written before the user confirms the preview.
2. Only create files. The only move allowed is putting a replaced _kb.json into the archive folder. Never delete or rewrite knowledge files, summary files or the spec of an existing library.
3. A new library needs an empty folder (empty subfolders are fine). Any .md file in it: stop and switch to the existing-library branch.
4. Never invent rules. For a new library every partition, topic and type comes from the preset as the user confirmed or changed it. For an existing library every value is read from its spec.
5. Ask as little as possible. Ask only what cannot be found out reliably; show everything else in the preview, where the user can change any item.

## Getting started (first-time guide)

For a user who has just installed the skills, or says it is the first time. Keep each message short and in the user's language.

1. Look before asking, without telling the user each check:
   - Registry (references/config.md): found, and with which libraries.
   - Python: python3 scripts/init_library.py defaults runs (it also prints the suggested timezone and language).
   - Backends: a Drive tool is available (references/backend-gdrive.md); local files can be written (references/backend-local.md).
2. Libraries already registered: list them in one line each (label and scope) and ask whether to add another library or complete an existing one. A library that fails step 0 of SKILL.md (missing _kb.json or _kb-params.md) goes to the existing-library branch.
3. Otherwise say in two sentences what will happen: three questions, a preview, nothing is written before "confirm". Then run Round 1 for a new library.
4. After Round 2, finish with the report and three things to try (step 9 of Round 2).

## Branch

- The user names a registered library, or a folder that already holds a spec: existing library. Run SKILL.md step 0 (it may stop at the missing _kb.json; continue here).
- The user asks for a new library, names an empty folder, or comes from getting started with no library: new library.
- Unclear: ask once, new or existing.
- A folder that holds the user's original files (Office, PDF, pictures, no _kb.json or spec) is material, not a library: never register it as a library or point a library at it. Offer to file it into a registered library, or to set up a new library in another, empty folder. When the user's meaning is unclear, ask with the question in references/config.md, section 3.

## Round 1: questions (new library)

Three questions, one at a time, each with a suggested answer:
1. Where the library folder goes (the filed results, not the original files; say so in the question). Suggest the backend the environment supports: local folder when local files can be written (a path; an Obsidian vault works; suggest ~/kb/<preset>; where commands run, let the user choose the folder with the chooser in references/pick-material.md, library folder, and ask in words only when it cannot open; a folder chosen there before this question answers it), Google Drive when only a Drive tool is available (a folder link or ID; the folder must exist and be empty). Both available: ask which, suggesting local. Neither: stop and say what is missing (references/environment.md).
2. Preset: life (me and my family: IDs, health, insurance, money, home) or work (work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports). One line each; the partition table appears in the preview.
3. Scope: one sentence saying what belongs in the library, suggested from python3 scripts/init_library.py defaults --preset <preset> --language <language>. Explain that it decides which library each request goes to.

Found out, not asked (all shown in the preview):
- Label and id: from the defaults for the preset. If the id is already in the registry, add -2, -3.
- Language: the language the user writes in. It sets the Table D limits (python3 scripts/kbconf.py limits --language <lang>).
- Timezone: from the defaults command (the system timezone); in claude.ai or wherever the system timezone is meaningless (often UTC on a server), the timezone the user's messages or profile indicate, else ask in the preview.
- Sensitivity and masking: the preset's setting (on for life, off for work).
- Conversion: on, as both presets set it. Uploads are turned into Markdown by a script before intake, which saves tokens and time (references/convert.md). Say in the preview what it does in a few words, so the user can turn it off there.
- Partitions: the preset's Table A, unchanged unless the user edits it in the preview. Partition numbers stay two-digit and continuous; the fallback partition stays the preset's unless the user changes it.

## Round 1: checks (existing library)

1. Find and read the spec. Not found: stop, nothing can be derived.
2. List the root's subfolders and look for _kb.json and _kb-params.md (find_exact).
3. Derive _kb.json from the spec: partitions.max = highest partition in Table A; topic_start = first partition after the summary partitions; metadata = yaml if the spec has Table E and front matter, else text; names = the summary file names actually in the library and the archive, entities and notes folder names the spec uses (only where they differ from defaults); language from the spec's language; timezone asked once. Conversion is not in the spec: keep the value of an existing _kb.json, else suggest {"enabled": true} in the preview.
4. If _kb.json exists, compare field by field. If _kb-params.md is missing, offer the closest preset's params as a draft, every clause marked "from preset, please confirm".
5. Check that partitions.fallback is a partition in Table A; suggest the broadest one if not.

## Preview (both branches)

Fixed structure:
  Library: <label> (id <id>) | branch: new / existing | backend: gdrive <id> / local <path>
  Scope: <one sentence> | language: <lang> | timezone: <tz> | sensitivity: on / off
  Convert uploads to Markdown first: on / off (fewer tokens and faster intake; pictures in a batch over the limit are read only if you agree)
  1. _kb.json: new / unchanged / replace (field: current -> new)
  2. _kb-params.md: new from preset <name> / unchanged / draft for review
  3. Spec: new from preset (version v1, today), partitions: <number name, one line each> / unchanged
  4. Summary files: list of files to create with their names
  5. Folders: archive, entities, notes: present / to create
  6. Registry: entry to add, and where (a file path, or kb-libraries.json in Google Drive: which folder, new or updated)
  7. Instructions line: the line, and the file it goes into; in claude.ai "one line to paste, once" or "already in the Project instructions, nothing to paste"
End with: reply "confirm" to write, or name any item to change. The turn ends here.

For a new library with Python, python3 scripts/init_library.py plan --root <path> --preset <preset> --label <label> --id <id> --scope "<scope>" --language <lang> --timezone <tz> --sensitivity on|off --convert on|off prints items 1 to 5; it refuses (exit 3) when the folder already holds Markdown files. For Drive, run it with --root pointing at an empty work folder just to get the list.

## Round 2: write (after confirmation)

1. Re-check: if the folder or the existing files changed since the preview, stop and report.
2. Replacing _kb.json: move the old one into the archive folder as _kb_old<YYYYMMDDHHMMSS>.json first.
3. Write the files of a new library:
   - Local: python3 scripts/init_library.py write with the same options as the plan. It writes every file, creates the archive, notes and (YAML mode) entities folders, and verifies each file.
   - Drive: python3 scripts/init_library.py render --out <work>/init with the same options, then write_new each file it rendered into the library folder (the backend file says how to set file types) and ensure_folder for the folders it names.
   - Without Python: fill the preset files yourself: the spec template with the confirmed Table A, type list and Table D limits, version v1 and today's date; summary files with their title, "Last updated: <today>" and empty headers; the file index header is
     Entries: 0
     Last updated: YYYY-MM-DD
     | File name | Source file name | Source hash |
     | --- | --- | --- |
     so scripts/index_tool.py can maintain it. Then ensure_folder for the archive, entities (YAML mode) and notes folders.
   Partition changes the user made in the preview: apply them to Table A of the spec just written (it is new, so rule 2 does not apply yet).
4. Existing library: write only the files the preview marked new or replace, with write_new.
5. Verify every file exists once (find_exact for each).
6. Registry. If the registry is a file you can write (KB_LIBRARIES or ~/.config/kb/kb-libraries.json):
   python3 scripts/init_library.py register --id <id> --label <label> --scope "<scope>" --type local|gdrive --root <path or folder id> --language <lang>
   It creates the file if needed, keeps every other entry and refuses an id or root already registered (exit 3: report it, ask for another id). Without Python, add the entry by hand.
   Otherwise (claude.ai and other environments without a writable registry), keep the registry in Google Drive when a Drive tool is available:
   a. Find the current registry: a "registry: Google Drive folder <id>, file kb-libraries.json" line in the Project instructions (find_exact kb-libraries.json in that folder and read it), else a registry pasted as JSON in the instructions, else none. Put it, or nothing, in <work>/kb-libraries.json.
   b. python3 scripts/init_library.py register --registry <work>/kb-libraries.json --id ... --label ... --scope "..." --type gdrive --root <folder id> --language <lang>
   c. Write it to Drive. No Drive registry yet: write_new kb-libraries.json (application/json) in the root of the new library; that folder is now the registry folder. A Drive registry exists: move_rename its current copy into the archive folder of the library it sits in, as kb-libraries_old<YYYYMMDDHHMMSS>.json, then write_new the updated one in the same folder (Drive cannot rewrite a file in place). find_exact afterwards: exactly one kb-libraries.json in the registry folder.
   d. The instructions line: if the Project instructions already hold the "registry: Google Drive folder" line, nothing to paste; say so. Otherwise
      python3 scripts/init_library.py instructions --drive-folder <registry folder id> --language <lang>
      and give that one line to paste, with: open the Project, Project instructions, paste it (replacing any older knowledge base lines or pasted registry), save, and start a new conversation in the Project. This is the only time; later libraries go into the Drive registry without touching the instructions. Not working in a Project: say that only Project instructions persist, and suggest creating a Project for the knowledge base.
   No Drive tool (a local library in an agent that cannot write the registry file): the older form. Run register on <work>/kb-libraries.json, then python3 scripts/init_library.py instructions --registry <work>/kb-libraries.json --project-block, and give that block to paste.
   Without Python, do the same by hand: edit the JSON yourself; the Drive line is "I keep knowledge bases; their list and scopes are in Google Drive (registry: Google Drive folder <id>, file kb-libraries.json). ..." as init_library.py prints it, with the "registry: ..." part kept in English.
7. Make the libraries visible. An assistant only consults kb-query when it knows a knowledge base exists, and it cannot see the registry until a skill reads it. The line lists every registered library:
   "I keep knowledge bases: <label> (<scope>); <label> (<scope>). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note."
   In Chinese: "我有知识库：<名称>（<范围>）；<名称>（<范围>）。相关问题先用 kb-query 查知识库，再查代码或凭记忆回答；要记录用 kb-note。"
   python3 scripts/init_library.py instructions --registry <registry> --file <file> prints the line and says whether it would be added or would update the line already there (found by its opening words, so a second library never adds a second line); add --apply to write. The file is the one the assistant always reads: CLAUDE.md, AGENTS.md or GEMINI.md in the user's home or project. Write only after the user agrees, which the preview confirmation covers when item 7 named the file; every other line of the file stays as it is. In claude.ai the line is the one from step 6d.
8. Check: python3 scripts/kbconf.py validate <library root or the rendered _kb.json> passes, and the registry loads (python3 scripts/kbconf.py registry, where the registry is a file).
9. Report in a few lines: what was written and where, anything that needs a manual step (the one-line paste in step 6d, if any, or a restart of the agent so it reads the new instructions line), then three things to try, in the library language:
   "note this: <a fact that fits the scope>"; a question the library will answer once material is filed ("what is due this month?" for life, "what did we decide about <topic>?" for work); "file these" with a document attached.
