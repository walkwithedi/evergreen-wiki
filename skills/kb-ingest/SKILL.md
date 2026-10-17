---
name: kb-ingest
description: Ingests documents into an evergreen 2.0 knowledge base (Google Drive or local/Obsidian) and sets new libraries up. Use when the user says "ingest", "file these", "add to the knowledge base" or hands over batch files or documents for the library, and for "set up a knowledge base", "new library" or "get started with the knowledge base". Turns each batch into cards (a conclusion with its exact source sentence), checks every quote against the source with a script, files the sources, cards and topic pages, archives older versions, and asks the user about new topics, new entities and possible new versions of documents. Weak tier (local models): scripts build the topic pages; strong tier (Claude, ChatGPT): the model writes them and a script checks every citation. Material is searchable only once its run is finished. Init mode creates a library from the work preset, registers it and tells the assistant it exists. Not for questions (kb-query) or saving one note (kb-note).
---

# Knowledge base ingest

Version: 1.22.1

This skill files material into a 2.0 library. Every conclusion it writes carries the source sentence it rests on, and a script checks that sentence before anything is written. The rules of a library (partitions, topics, folder names, tier) live in the library's own spec and _kb.json; read them each time, never from memory or from this file.

## Modes

- Ingest: the steps below.
- Init and getting started: "set up a knowledge base", "new library", "first time", "get started with the knowledge base", or no registry yet while the user wants a library. Read references/init.md and follow it instead of the steps below; it does not run step 0.

Before the first step, read references/config.md and references/environment.md once. Scripts are run as references/environment.md describes; paths such as scripts/ingest.py are relative to this skill's folder.

## Library layout

The summary files (status card, spec, indexes) sit in the library root. Beside them, named by the library's names in _kb.json:

- names.sources_dir (Sources): one Markdown file per source document, as converted, with paragraph anchors ^p1, ^p2, ...
- names.cards_dir (Cards): one cards file per source, with the same name.
- names.topics_dir (Topics): one page per topic.
- names.archive_dir (Archive): older versions of sources and cards, never deleted.

## Step 0: choose the library (always first)

1. Load the registry (references/config.md). A library named in the request or the project instructions is the one to use. No registry or no library: offer init mode once (references/init.md); never guess a library.
2. Otherwise match the material against each library's scope. Exactly one fits: propose it in one line and continue when the user agrees or the request already made it clear. None or several: ask which. Never default.
3. Read the backend file for that library (references/backend-gdrive.md or references/backend-local.md), then _kb.json and the spec from the library root. A _kb.json of schema 1 is a 1.x library: stop and say what references/init.md, rule 4, says.
4. The tier is _kb.json "tier": weak or strong. Missing: strong when you are a Claude or ChatGPT client, weak otherwise (OpenCode or a local model), and say which you assumed.
5. First line of the reply: Library: <label> (tier <tier>). From here on, read and write only inside that library.

Every library needs a code environment to run the scripts (hard rule 8). Without one, stop before step 2: say that writing to the library needs a code environment and that reading and questions still work.

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

## Step 5: entities

python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library> > <work>/entities.json

It compares the cards' entity names with the spec's Table E (the alias table). Names under merged are names or aliases of the table and are merged without asking. Each name under new goes into the preview with its suggested type and the closest names of the table; by default it is added as a new entity. When the user puts a name under an existing entity, or changes a type, write the decisions to <work>/entity-map.json: {"<name>": "<table name>"} records it as an alias, {"<name>": {"type": "<type>"}} sets the type (project, team, organisation, system or other).

## Step 6: new versions

python3 scripts/ingest.py versions <batch files> --library <library> > <work>/versions.json

- same_name: sources whose name is already in the library. They are new versions anyway: the old source and cards file go to the archive folder.
- candidates: library sources with a close name and shared paragraphs, which may be older versions of a source of the run under another name.
  - Weak tier: list each pair in the preview; the user picks the ones that are new versions.
  - Strong tier: read both sources of each pair and decide, giving one sentence of each, quoted exactly, that the decision rests on. Add a pair the script did not list only when a library source's name or content shows it is the older version, with the same two quotes. Every pair still waits for the user's confirmation in the preview.

Each confirmed pair is passed to step 9 as --replaces "<new>=<old>": the old source and its cards file go to the archive folder, and the new source keeps its own name.

## Step 7: conflicts

python3 scripts/ingest.py conflicts <batch files> --cards <work>/accepted.jsonl --library <library> > <work>/conflicts.json, with --replaces "<new>=<old>" for each pair proposed in step 6. In the preview, the conflicts of a pair the user does not confirm are dropped.

For each source the run replaces, it compares the old version's cards with the new version and the run's cards, and lists:
- changed: the old quote is gone and a new card's conclusion is close to the old one (both are listed);
- removed: the old quote is gone and no new card is close;
- not_carried: the old quote is still in the new version, but no card of this run quotes it.

Each goes into the preview with its id; by default the change is accepted. Write the entries the user restores, as the script printed them, to <work>/restore.json (a JSON list). A restored not_carried card becomes a current card of the new version again; any other restored card stays, citing the archived old version and marked as from an earlier version.

## Step 8: preview and confirm

Show one preview and wait for the user to confirm before anything is written:

- Sources to file, from the batch files' source tables; new versions (same name, and the pairs of step 6 with their scores or quotes).
- Conflicts of step 7: for each, the old conclusion with its quote and, for changed, the new one; the user accepts or restores each.
- Status-card items that will be marked for review: the items citing a source that gets a new version.
- Number of cards per source, and cards dropped.
- New entities: each name with its type and the closest names of Table E; the user may put a name under an existing entity or change its type.
- Topic pages that will be rebuilt (the accepted cards' topics, plus the topics of the cards files being archived).

A local library writes straight into the library after the confirmation. For a library in Google Drive, see "Libraries in Google Drive" below before writing.

Answering on the knowledge base client (local libraries): before showing the preview, write the decisions to be made to a pending file, which the client shows as a form on its Waiting for confirmation page:

  python3 scripts/ingest.py pending write --library <library> --entities <work>/entities.json --versions <work>/versions.json --conflicts <work>/conflicts.json

(add --report <work>/report.json when the new topics of step 4 were left for the preview). It prints the file's path; its name is the run's name. Say in the preview that the user can answer here or on the client's page. Answers given in the conversation are used as before. When the user, or the client in the conversation, says the decisions are saved, run python3 scripts/ingest.py pending read --library <library> --run <run> --work <work>: it prints the topics to add, the topics to put under others and the --replaces pairs, and writes <work>/entity-map.json and <work>/restore.json for step 9. After step 9: python3 scripts/ingest.py pending done --library <library> --run <run>.

## Step 9: file

1. When step 5 found new names or merged ones: python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library> --apply, adding --map <work>/entity-map.json when the user changed anything. It rewrites the cards with the table's names and adds the new entities and aliases to Table E, raising the spec's version once.
2. python3 scripts/ingest.py file <batch files> --cards <work>/accepted.jsonl --library <library>, adding --replaces "<new>=<old>" for each pair confirmed in step 6 and --restore <work>/restore.json when the user restored any conflict.

It writes the sources and cards files, archives older versions, marks the status-card items that cite an archived source for review, and prints a JSON record: sources written, files archived, topics touched, conflicts restored, status-card items marked. Exit 2 with "parts missing": a batch file of the run is not among those given; find it and run again, nothing was written. Exit 2 naming a --replaces source: that source is not in the library or not in the run; nothing was written.

## Step 10: topic pages

Take the topics from the record of step 9.

- Weak tier: python3 scripts/ingest.py pages --library <library> --topic "<topic>" (repeat --topic for each). The pages are built by the script from the cards; do not write or edit them.
- Strong tier: for each topic, read every cards file holding a card of that topic, then write the page as references/pages-strong.md says, to <work>/pages/<topic>.md. Then python3 scripts/ingest.py check-page --library <library> --topic "<topic>" --page <work>/pages/<topic>.md --write. Exit 3: the output lists unknown links (passages no card holds) and missing ones (cards the page does not cite); rewrite the page once to fix exactly those and check again. Still failing: build that page with ingest.py pages --topic "<topic>" instead and say so in the report.

## Step 11: ingest report

Reply with: sources filed (new and new versions), files archived, cards written per source, cards dropped with their reasons, topics added or merged, entities added or recorded as aliases, conflicts accepted and restored, status-card items marked for review, topic pages rebuilt and how (script or written and checked). Name the work folder only when a file there is useful to the user.

## Libraries in Google Drive

The scripts run on a staging folder in the work folder that is laid out like the library:

1. Before step 3: make <work>/stage. read _kb.json, the spec and the status card into it. list the cards folder and read every cards file into <work>/stage/<cards_dir>/. For each source of the run, find_exact its name in the sources folder and, when present, read it into <work>/stage/<sources_dir>/.
2. Run steps 3 to 10 with --library <work>/stage. add-topic and entities --apply change the staged spec. For step 6, list the sources folder and write the names to <work>/sources.txt, one per line, and add --known <work>/sources.txt: a candidate marked "read": true is a library source not yet staged; read it into <work>/stage/<sources_dir>/ and run versions again.
3. After the user confirms (step 8) and the scripts have run, deliver what changed, folder by folder:
   - For each file the record lists under archived: move_rename its Drive copy into the archive folder's subfolder of the same name (ensure_folder first), under the name the script gave it in <work>/stage/<archive_dir>/.
   - write_new each source and cards file the run wrote.
   - For each topic page rebuilt, the spec when add-topic or entities --apply changed it, and the status card when the record lists items marked for review: move_rename the Drive copy into the archive folder under <name><old_suffix><YYYYMMDDHHMMSS>.md, then write_new the new one.
   - find_exact each written name once more: exactly one copy must remain.
4. Report written and failed files. A permission error stops the delivery at once: the connected account needs edit rights on the folder.

## Hard rules

1. Never write a card whose quote did not pass the check, and never write a conclusion that is not on a card.
2. Never invent topics: a new topic is added only after the user agrees to it, never a new partition number. New entities and aliases reach Table E only through the confirmed preview.
3. Never edit or delete a source. Older versions move to the archive folder, and a source under another name is treated as a new version only after the user confirms the pair.
4. Never write a topic page by hand in the weak tier; a strong-tier page is written only through check-page.
5. Material is not searchable until its run is finished. Do not answer questions from a run that has not been filed.
6. Replies follow the library language and preferences.output (references/environment.md).
7. Never rewrite the status card without ingest.py status-check (references/config.md, section 2); review marks are added only by the filing script.
8. Without a code environment (Python), write nothing to the library and say so; reading and answering still work.
