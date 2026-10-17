---
name: kb-ingest
description: Ingests documents into an evergreen 2.0 knowledge base (Google Drive or local/Obsidian). Use when the user says "ingest", "file these", "add to the knowledge base" or hands over batch files or documents for the library. Turns each batch into cards (a conclusion with its exact source sentence), checks every quote against the source with a script, files the sources, cards and topic pages, archives older versions, and asks the user about new topics. Weak tier (local models): scripts build the topic pages; strong tier (Claude, ChatGPT): the model writes them and a script checks every citation. Material is searchable only once its run is finished. Not for questions (kb-query) or saving one note (kb-note).
---

# Knowledge base ingest

Version: 1.22.1

This skill files material into a 2.0 library. Every conclusion it writes carries the source sentence it rests on, and a script checks that sentence before anything is written. The rules of a library (partitions, topics, folder names, tier) live in the library's own spec and _kb.json; read them each time, never from memory or from this file.

Before the first step, read references/config.md and references/environment.md once. Scripts are run as references/environment.md describes; paths such as scripts/ingest.py are relative to this skill's folder.

## Library layout

The summary files (status card, spec, indexes) sit in the library root. Beside them, named by the library's names in _kb.json:

- names.sources_dir (Sources): one Markdown file per source document, as converted, with paragraph anchors ^p1, ^p2, ...
- names.cards_dir (Cards): one cards file per source, with the same name.
- names.topics_dir (Topics): one page per topic.
- names.archive_dir (Archive): older versions of sources and cards, never deleted.

## Step 0: choose the library (always first)

1. Load the registry (references/config.md). A library named in the request or the project instructions is the one to use. No registry or no library: say so and stop; setting up a library is not part of this skill yet.
2. Otherwise match the material against each library's scope. Exactly one fits: propose it in one line and continue when the user agrees or the request already made it clear. None or several: ask which. Never default.
3. Read the backend file for that library (references/backend-gdrive.md or references/backend-local.md), then _kb.json and the spec from the library root.
4. The tier is _kb.json "tier": weak or strong. Missing: strong when you are a Claude or ChatGPT client, weak otherwise (OpenCode or a local model), and say which you assumed.
5. First line of the reply: Library: <label> (tier <tier>). From here on, read and write only inside that library.

A library in Google Drive needs a code environment to run the scripts. Without one, stop before step 2: say that writing to the library needs a code environment and that reading and questions still work.

## Step 1: batch files

- Batch files (made by doc2kb --kb-batch, names ending _b01.md, _b02.md, ...) are used as they are. All batch files of one run go through the steps together.
- Documents or folders, where commands can be run: make the batch files with python3 scripts/doc2kb_core.py --batch <folder> -o <work>/batches --kb-batch --library <library root> (for chosen files, --files <list file> instead of --batch). The library's tier sets the batch size. Never move or change the user's documents.
- Documents in a client without commands (a library in Google Drive used from claude.ai or ChatGPT): ask the user to make the batch files on their computer with doc2kb (or the knowledge base client) and upload them. Batch files are always made locally.

## Step 2: cards

Read references/extract.md and follow it.

- Weak tier: one source at a time (one section "# Snn ...", or one part of it). Write that source's cards, then go on to the next.
- Strong tier: one batch file at a time.

Write all cards of the run to <work>/cards.jsonl, one JSON object per line.

## Step 3: quote check

1. python3 scripts/ingest.py topics --library <library> --out <work>/topics.txt
2. python3 scripts/quote_check.py check <work>/cards.jsonl <batch files> --accepted <work>/accepted.jsonl --report <work>/report.json --topics <work>/topics.txt, adding --quote-min and --quote-max when _kb.json sets quote_min or quote_max.
3. Exit 3 means cards were rejected. Read each rejected card's reason in the report and write that card once more from the source, copying the sentence exactly (references/extract.md, "Fixing a rejected card"), into <work>/retry.jsonl. Check it the same way with --accepted <work>/accepted2.jsonl --report <work>/report2.json, then append the lines of accepted2.jsonl to accepted.jsonl. Cards rejected twice are dropped and listed in the ingest report. Never write a card that did not pass.

## Step 4: new topics

The report's new_topics are topics the spec does not have. Ask the user about each one, as a choice: put it under one of the existing topics (name the closest ones), or add it as a new topic. Ask once per topic, never more than four at a time.

- Under an existing topic: python3 scripts/ingest.py retopic <work>/accepted.jsonl --from "<new topic>" --to "<existing topic>".
- Add: collect them and run python3 scripts/ingest.py add-topic --library <library> --topic "<topic>" (repeat --topic for each), which appends them to the fallback partition of Table A, raises the spec's version once and adds a revision line for each. With --partition NN when the user names a partition. Never add a partition number.

The user's answer to this question is their confirmation of the spec change.

## Step 5: preview and confirm

Show one preview and wait for the user to confirm before anything is written:

- Sources to file, from the batch files' source tables. For each, find_exact its file name (the original name with .md) in the sources folder: present means a new version, and the old source and cards file go to the archive folder.
- Number of cards per source, and cards dropped.
- Topic pages that will be rebuilt (the accepted cards' topics, plus the topics of the cards files being archived).

A local library writes straight into the library after the confirmation. For a library in Google Drive, see "Libraries in Google Drive" below before writing.

## Step 6: file

python3 scripts/ingest.py file <batch files> --cards <work>/accepted.jsonl --library <library>

It writes the sources and cards files, archives older versions and prints a JSON record: sources written, files archived, topics touched. Exit 2 with "parts missing": a batch file of the run is not among those given; find it and run again, nothing was written.

## Step 7: topic pages

Take the topics from the record of step 6.

- Weak tier: python3 scripts/ingest.py pages --library <library> --topic "<topic>" (repeat --topic for each). The pages are built by the script from the cards; do not write or edit them.
- Strong tier: for each topic, read every cards file holding a card of that topic, then write the page as references/pages-strong.md says, to <work>/pages/<topic>.md. Then python3 scripts/ingest.py check-page --library <library> --topic "<topic>" --page <work>/pages/<topic>.md --write. Exit 3: the output lists unknown links (passages no card holds) and missing ones (cards the page does not cite); rewrite the page once to fix exactly those and check again. Still failing: build that page with ingest.py pages --topic "<topic>" instead and say so in the report.

## Step 8: ingest report

Reply with: sources filed (new and new versions), files archived, cards written per source, cards dropped with their reasons, topics added or merged, topic pages rebuilt and how (script or written and checked). Name the work folder only when a file there is useful to the user.

## Libraries in Google Drive

The scripts run on a staging folder in the work folder that is laid out like the library:

1. Before step 3: make <work>/stage. read _kb.json and the spec into it. list the cards folder and read every cards file into <work>/stage/<cards_dir>/. For each source of the run, find_exact its name in the sources folder and, when present, read it into <work>/stage/<sources_dir>/.
2. Run steps 3 to 7 with --library <work>/stage. add-topic changes the staged spec.
3. After the user confirms (step 5) and the scripts have run, deliver what changed, folder by folder:
   - For each file the record lists under archived: move_rename its Drive copy into the archive folder's subfolder of the same name (ensure_folder first), under the name the script gave it in <work>/stage/<archive_dir>/.
   - write_new each source and cards file the run wrote.
   - For each topic page rebuilt and the spec when add-topic changed it: move_rename the Drive copy into the archive folder under <name><old_suffix><YYYYMMDDHHMMSS>.md, then write_new the new one.
   - find_exact each written name once more: exactly one copy must remain.
4. Report written and failed files. A permission error stops the delivery at once: the connected account needs edit rights on the folder.

## Hard rules

1. Never write a card whose quote did not pass the check, and never write a conclusion that is not on a card.
2. Never invent topics: a new topic is added only after the user agrees to it, never a new partition number.
3. Never edit or delete a source. Older versions move to the archive folder.
4. Never write a topic page by hand in the weak tier; a strong-tier page is written only through check-page.
5. Material is not searchable until its run is finished. Do not answer questions from a run that has not been filed.
6. Replies follow the library language and preferences.output (references/environment.md).
