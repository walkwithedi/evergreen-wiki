# Design: 4.0, libraries of ten thousand documents

Status: in progress. Each step below is its own pull request; 4.0.0 is released after the last one.

## 1. Scope

- 4.0 keeps the 3.0 setting (an offline Kylin workstation, OpenCode, local libraries, script-led steps) and makes one library carry about ten thousand documents: an import of what already exists, then a steady trickle of new material.
- A library of 2.0 or 3.0 (schema 2, one flat sources folder) is not read and not migrated; 3.0.x keeps working for it. 1.x libraries stay unmigrated as before.

## 2. Library layout (schema 3)

- A source keeps the folder it came from below the material root: Sources/<folder>/<name>.md, its cards file at Cards/<folder>/<name>.md, older versions under Archive/Sources/<folder> and Archive/Cards/<folder>. Folder parts are made safe for file names and links and cut to a length that fits (kbconf.rel_folder).
- A file name is one document wherever its folder is. A source whose name is in the library, in any folder, is a new version: the old one and its cards go to the archive and the new one goes to its own folder.
- Several sources of one run with the same name and different content form a group. By default the newest is current and the others go straight to the archive as its older versions; the owner can pick another current one or mark members as separate documents, which get their folder's last part in front of their name.
- A source with the same content (fingerprint of the text without notes, anchors and spacing) as one in the library, or as an earlier one of the run, is not filed again.
- A run can be filed without cards. Its sources can be searched and quoted at once; their cards are written later and only then reach topic pages and the status card.
- A topic with more than 60 cards keeps its newest year (and undated cards) on its page and each earlier year on a page "<topic> (YYYY)".

## 3. Index

- <library>/_index/kb.sqlite holds the sources (path, name, name key, fingerprint, date, whether it has cards), their paragraphs and every card. SQLite is part of the Python standard library.
- It is made from the files and kept current from them: each command compares file sizes and times with what the index holds and reads only what changed. The files stay the only record; the index can be deleted at any time and is made again. An index that this SQLite cannot read, or a damaged one, is made again; a folder that cannot be written gets an index in memory for that run.
- Paragraph search uses the trigram full-text index where the SQLite has it, else LIKE. Version candidates compare a new name only with library names sharing enough letter pairs.
- tests/test_scale.py builds a library of 10,000 sources with 100,000 cards and checks that an answer's material comes within five seconds, with and without the full-text index.

## 4. Steps

1. Library format and index (this document, kbconf, kbindex, ingest, answer, skills, the sample library, the scale test).
2. Health check: a read-only ingest.py check over the 4.0 layout and the index, a mode of kb-ingest ("health check") and a Health check button under each library in kb-client.
3. Client-run ingest in kb-client (tools/kb-client/ingest_run.py, auto.py; ingest.py file --sources, backfill and add-cards): choosing material with rules (folders, a time range) and a confirmed list, filing every document without cards first, writing cards for the chosen ones, writing the others' cards when the assistant is idle (pausable, giving way to the user), automatic ingest from a drop folder, decisions taken by group on the Waiting for confirmation page, and an adjustable number of parallel card runs (default one).
