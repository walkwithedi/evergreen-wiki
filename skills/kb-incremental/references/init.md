# Init mode: set up a new library or complete an existing one

Trigger: "set up a knowledge base", "new library", "init", "complete the settings".
Result: the library root holds _kb.json, _kb-params.md, the spec and the empty summary files, and the library is in the registry.

Presets live in assets/presets/<name>/: _kb.json, _kb-params.md, 00_Spec.md and summary/ (empty summary files). Available: life and work. For a blank start, take the closer one and remove the topics the user does not want. Placeholders {{DATE}}, {{HEADING_LIMIT}} and {{FILENAME_LIMIT}} are filled when writing.

## Rules

1. Questions, then a preview, then writing. Nothing is written before the user confirms the preview.
2. Only create files. The only move allowed is putting a replaced _kb.json into the archive folder. Never delete or rewrite knowledge files, summary files or the spec of an existing library.
3. A new library needs an empty folder (empty subfolders are fine). Any .md file in it: stop and switch to the existing-library branch.
4. Never invent rules. For a new library every partition, topic and type comes from the preset as the user confirmed or changed it. For an existing library every value is read from its spec.

## Branch

- The user names a registered library, or a folder that already holds a spec: existing library. Run SKILL.md step 0 (it may stop at the missing _kb.json; continue here).
- The user asks for a new library, or names an empty folder: new library.
- Unclear: ask once, new or existing.

## Round 1: questions (new library)

Ask one question at a time, each with a suggested answer:
1. Backend and location: a Google Drive folder (folder ID or link) or a local folder path (an Obsidian vault works).
2. Preset: work or life. Show its partition table briefly.
3. Label, short id and one-sentence scope (used to route requests between libraries).
4. Language and timezone. Language decides the Table D length limits: python3 scripts/kbconf.py limits --language <lang>.
5. Life preset only: keep sensitivity classes and masking on (suggested) or off.
Then show the full partition table and let the user keep, rename or drop each partition and topic, and set the fallback partition. Partition numbers stay two-digit and continuous.

## Round 1: checks (existing library)

1. Find and read the spec. Not found: stop, nothing can be derived.
2. List the root's subfolders and look for _kb.json and _kb-params.md (find_exact).
3. Derive _kb.json from the spec: partitions.max = highest partition in Table A; topic_start = first partition after the summary partitions; metadata = yaml if the spec has Table E and front matter, else text; names = the summary file names actually in the library and the archive, entities and notes folder names the spec uses (only where they differ from defaults); language from the spec's language; timezone asked once.
4. If _kb.json exists, compare field by field. If _kb-params.md is missing, offer the closest preset's params as a draft, every clause marked "from preset, please confirm".
5. Check that partitions.fallback is a partition in Table A; suggest the broadest one if not.

## Preview (both branches)

Fixed structure:
  Library: <label> | branch: new / existing | backend: gdrive <id> / local <path>
  1. _kb.json: new / unchanged / replace (field: current -> new)
  2. _kb-params.md: new from preset <name> / unchanged / draft for review
  3. Spec: new from preset (version v1, today) / unchanged
  4. Summary files: list of files to create with their names
  5. Folders: archive, entities, notes: present / to create
  6. Registry: entry to add (see below)
End with: reply "confirm" to write. The turn ends here.

## Round 2: write (after confirmation)

1. Re-check: if the folder or the existing files changed since the preview, stop and report.
2. Replacing _kb.json: move the old one into the archive folder as _kb_old<YYYYMMDDHHMMSS>.json first.
3. Write the files with write_new (the backend file says how to set file types). New library: fill the spec template with the confirmed Table A, type list and Table D limits, version v1 and today's date; summary files get their title, "Last updated: <today>" and empty headers; the file index header is
   Entries: 0
   Last updated: YYYY-MM-DD
   | File name | Source file name | Source hash |
   | --- | --- | --- |
   so scripts/index_tool.py can maintain it.
4. ensure_folder for the archive, entities (YAML mode) and notes folders.
5. Verify every file exists once.
6. Registry: if the registry is a file you can write (KB_LIBRARIES or ~/.config/kb/kb-libraries.json), show the entry and add it after the user agrees, creating the file if needed. Otherwise give the entry (or the whole registry) as a block for the user to paste into project instructions, or to bake into a private skill build (build_skill.py --config).
7. Make the libraries visible. An assistant only consults kb-query when it knows a knowledge base exists, and it cannot see the registry until a skill reads it. Propose one line for the instructions the assistant always reads (CLAUDE.md, AGENTS.md or GEMINI.md in the user's home or project, or the claude.ai Project instructions), listing every registered library:
   "I keep knowledge bases: <label> (<scope>); <label> (<scope>). For questions about these, use kb-query before searching code or answering from memory; to save something, use kb-note."
   Add it after the user agrees (to an existing file, append; never replace other content), or give it to paste.
8. Report what was written and anything that needs a manual decision.
