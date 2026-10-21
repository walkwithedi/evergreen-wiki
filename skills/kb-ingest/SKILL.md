---
name: kb-ingest
description: Ingests documents into an evergreen knowledge base (a local or Obsidian folder) and sets new libraries up. Use when the user says "ingest", "file these", "add to the knowledge base" or hands over batch files or documents for the library, for "set up a knowledge base", "new library" or "get started with the knowledge base", and for "health check" or "check the knowledge base". Turns each batch into cards (a conclusion with its exact source sentence), checks every quote against the source with a script, files the sources, cards and topic pages, archives older versions, and asks the user about new topics, new entities and possible new versions of documents. Scripts build the topic pages from the cards, so the model only extracts cards and words the replies. Material is searchable only once its run is finished. Init mode creates a library from the work preset, registers it and tells the assistant it exists. Not for questions (kb-query) or saving one note (kb-note).
---

# Knowledge base ingest

Version: 6.0.1

This skill files material into a library. Every conclusion it writes carries the source sentence it rests on, and a script checks that sentence before anything is written. The rules of a library (partitions, topics, folder names) live in the library's own spec and _kb.json; read them each time, never from memory or from this file.

## Modes

- Ingest: the steps below.
- Continue: "continue the ingest", "继续入库", or a run that stopped before it was finished. Choose the library as in step 0, run python3 scripts/ingest.py work list --library <library>, take the unfinished run the user means (ask when there are several), run python3 scripts/ingest.py progress --work <work> and go on from the step it names, with that folder as <work>. Never judge from memory how far a run got.
- Init and getting started: "set up a knowledge base", "new library", "first time", "get started with the knowledge base", or no registry yet while the user wants a library. Read references/init.md and follow it instead of the steps below; it does not run step 0.
- Missing cards: "write the missing cards", "补抽卡片". A library may hold sources filed without cards (step 9 without --cards, or the knowledge base client). Make the work folder as in step 0, then python3 scripts/ingest.py backfill --library <library> -o <work>/backfill --limit <n> writes batch files for the newest of them (or --source <path> for given ones); write their cards as in step 2, check them as in step 3, settle new topics and entities as in steps 4 and 5, then python3 scripts/ingest.py add-cards <batch files> --cards <work>/accepted.jsonl --library <library> --work <work> and the topic pages and the end of the run as in step 10. add-cards archives nothing and refuses a source that changed or has cards already.
- Health check: "check the knowledge base", "health check". Choose the library as in step 0, run python3 scripts/ingest.py check --library <library> and reply with its findings in the user's words, grouped as it groups them, with what fixes each kind: topic pages missing, out of date or no longer built are rebuilt with python3 scripts/ingest.py pages --library <library> --all after the user agrees (year pages no longer built are removed by it); cards whose quote is gone and cards files without their source come back right when the source is ingested again; status-card items go through the status-card rules (references/config.md, section 2); unfinished runs are continued (mode Continue) or, when the user gives them up, removed with python3 scripts/ingest.py work drop --library <library> --run <name>. The check writes nothing; change nothing without the user's agreement.

Before the first step, read references/config.md and references/environment.md once. Scripts are run as references/environment.md describes; paths such as scripts/ingest.py are relative to this skill's folder.

## Library layout

The summary files (status card, spec, indexes) sit in the library root. Beside them, named by the library's names in _kb.json:

- names.sources_dir (Sources): one Markdown file per source document, as converted, with paragraph anchors ^p1, ^p2, ..., in the folder the document came from below the material root (Sources/<folder>/<name>.md).
- A file name is one document wherever its folder is: a source whose name is already in the library, in any folder, is a new version of it.
- names.cards_dir (Cards): one cards file per source, with the same folder and name.
- names.topics_dir (Topics): one page per topic.
- names.archive_dir (Archive): older versions of sources and cards, in the same folders, never deleted.
- _index: the search index the scripts keep (scripts/kbindex.py); it is made from the files and can be deleted. Never edit it.
- .kb-work: one folder per run (references/environment.md), removed when the run is finished. It is not part of the library's content.

## Step 0: choose the library (always first)

1. Load the registry (references/config.md). A library named in the request or the project instructions is the one to use. No registry or no library: offer init mode once (references/init.md); never guess a library.
2. Otherwise match the material against each library's scope. Exactly one fits: propose it in one line and continue when the user agrees or the request already made it clear. None or several: ask which. Never default.
3. Read references/backend-local.md, then _kb.json and the spec from the library root. A _kb.json of schema 1 or 2 is a 1.x, 2.0 or 3.0 library: stop and say what references/init.md, rule 4, says. A "tier" in _kb.json is ignored; when it says strong, say once that topic pages are now always built by the script.
4. First line of the reply: Library: <label>. From here on, read and write only inside that library.
5. python3 scripts/ingest.py work new --library <library> prints the run's work folder; every <work> below is that path.

Every library needs a code environment to run the scripts (hard rule 8). Without one, stop before step 2: say that writing to the library needs a code environment and that reading and questions still work.

## Step 1: batch files

- Batch files (made by kb_batch.py make, names ending _b01.md, _b02.md, ...) are used as they are. All batch files of one run go through the steps together.
- Documents or folders: make the batch files with python3 scripts/kb_batch.py make --batch <folder> -o <work>/batches --library <library root>. Batch files the user handed over are copied to <work>/batches as they are, so that the run can be followed from its folder. The folders below <folder> become the sources' folders in the library. For chosen files inside one folder, add --only <list file> with their paths relative to it; files from several places go in with --files <list file> instead of --batch and land at the top of the sources folder. The library's batch_chars (default 20000 characters) sets the batch size. Never move or change the user's documents.

## Step 2: cards

Read references/extract.md and follow it. Work one source at a time (one section "# Snn ...", or one part of it): write that source's cards, then go on to the next.

Each source's cards go to their own file, <work>/cards/Snn.jsonl, one JSON object per line; a source with nothing worth a card gets an empty file. With many sources, run python3 scripts/ingest.py progress --work <work> now and then: it lists the sources that have no cards file yet. Step 3 starts only when it lists none.

## Step 3: quote check

1. python3 scripts/ingest.py topics --library <library> --out <work>/topics.txt
2. python3 scripts/quote_check.py verify <work>/cards <batch files> --accepted <work>/accepted.jsonl --report <work>/report.json --topics <work>/topics.txt, adding --quote-min and --quote-max when _kb.json sets quote_min or quote_max.
3. Exit 3 means cards were rejected. Read each rejected card's reason in the report (with its cards file and line) and write that card once more from the source, copying the sentence exactly (references/extract.md, "Fixing a rejected card"), into <work>/retry.jsonl. Check it the same way with --accepted <work>/accepted2.jsonl --report <work>/report2.json, then append the lines of accepted2.jsonl to accepted.jsonl. Cards rejected twice are dropped and listed in the ingest report. Never write a card that did not pass.

## Step 4: new topics

The new_topics of report.json, and of report2.json when step 3 checked rewritten cards, are topics the spec does not have. Ask the user about each one, as a choice: put it under one of the existing topics (name the closest ones), or add it as a new topic. Ask once per topic, never more than four at a time.

- Under an existing topic: python3 scripts/ingest.py retopic <work>/accepted.jsonl --from "<new topic>" --to "<existing topic>".
- Add: collect them and run python3 scripts/ingest.py add-topic --library <library> --topic "<topic>" (repeat --topic for each), which appends them to the fallback partition of Table A, raises the spec's version once and adds a revision line for each. With --partition NN when the user names a partition. Never add a partition number.

The user's answer to this question is their confirmation of the spec change.

## Step 5: entities

python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library> > <work>/entities.json

It compares the cards' entity names with the spec's Table E (the alias table). Names under merged are names or aliases of the table and are merged without asking. Each name under new goes into the preview with its suggested type and the closest names of the table; by default it is added as a new entity. When the user puts a name under an existing entity, or changes a type, write the decisions to <work>/entity-map.json: {"<name>": "<table name>"} records it as an alias, {"<name>": {"type": "<type>"}} sets the type (project, team, organisation, system or other).

## Step 6: new versions

python3 scripts/ingest.py versions <batch files> --library <library> > <work>/versions.json

- same_name: sources whose name is already in the library, in any folder. They are new versions anyway: the old source and cards file go to the archive folder, and the new version goes to its own folder.
- duplicates: sources with the same content as a source of the library, or as an earlier source of the run, wherever and however named. They are not filed again; list them with the library path they match.
- groups: several sources of the run with one name and different content. By default the newest (last modified) is the current version and the others are filed straight into the archive as its older versions. List each group with its members; the user may pick another current one, or mark members as separate documents (they get their folder's name in front of theirs). Write the decisions to <work>/groups.json as {"<name>": {"current": "<path>", "separate": ["<path>"]}} and pass --groups <work>/groups.json to the conflicts command and to step 9.
- candidates: library sources with a close name and shared paragraphs, which may be older versions of a source of the run under another name. List each pair in the preview; the user picks the ones that are new versions.

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

- Sources to file, from the batch files' source tables, with their folders; new versions (same name, and the pairs of step 6 with their scores); duplicates not filed again; groups of same-named sources with the current member of each.
- Conflicts of step 7: for each, the old conclusion with its quote and, for changed, the new one; the user accepts or restores each.
- Status-card items that will be marked for review: the items citing a source that gets a new version.
- Number of cards per source, and cards dropped.
- New entities: each name with its type and the closest names of Table E; the user may put a name under an existing entity or change its type.
- Topic pages that will be rebuilt (the accepted cards' topics, plus the topics of the cards files being archived).

The scripts write straight into the library after the confirmation.

Answering on the knowledge base client: before showing the preview, write the decisions to be made to a pending file, which the client shows as a form on its Waiting for confirmation page:

  python3 scripts/ingest.py pending write --library <library> --entities <work>/entities.json --versions <work>/versions.json --conflicts <work>/conflicts.json

(add --report <work>/report.json when the new topics of step 4 were left for the preview). It prints the file's path; its name is the run's name. Say in the preview that the user can answer here or on the client's page. Answers given in the conversation are used as before. When the user, or the client in the conversation, says the decisions are saved, run python3 scripts/ingest.py pending read --library <library> --run <run> --work <work>: it prints the topics to add, the topics to put under others and the --replaces pairs, and writes <work>/entity-map.json and <work>/restore.json for step 9. After step 9: python3 scripts/ingest.py pending done --library <library> --run <run>.

## Step 9: file

1. When step 5 found new names or merged ones: python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library> --apply, adding --map <work>/entity-map.json when the user changed anything. It rewrites the cards with the table's names and adds the new entities and aliases to Table E, raising the spec's version once.
2. python3 scripts/ingest.py file <batch files> --cards <work>/accepted.jsonl --library <library> --work <work>, adding --replaces "<new>=<old>" for each pair confirmed in step 6, --restore <work>/restore.json when the user restored any conflict and --groups <work>/groups.json when the user decided on any group.

When the user asks to file material first and write its cards later (a large amount, for example), run step 9 without --cards after the preview: the sources are filed and can be searched and quoted at once; their cards come later, and until then they are not on topic pages or the status card.

It writes the sources and cards files, archives older versions, marks the status-card items that cite an archived source for review, and prints a JSON record: sources written, files archived, topics touched, conflicts restored, status-card items marked. Exit 2 with "parts missing": a batch file of the run is not among those given; find it and run again, nothing was written. Exit 2 naming a --replaces source: that source is not in the library or not in the run; nothing was written.

## Step 10: topic pages

Take the topics from the record of step 9.

python3 scripts/ingest.py pages --library <library> --topic "<topic>" (repeat --topic for each) --work <work>. The pages are built by the script from the cards; do not write or edit them.

Then python3 scripts/ingest.py progress --work <work>. Only when it says finished: yes, read the records in <work>/filed.json for step 11 and run python3 scripts/ingest.py work done --work <work>. Otherwise do the step it names first.

## Step 11: ingest report

Every number in the report comes from the records of step 9 (filed.json) and of the scripts of this run, never from counting by hand. Reply with: sources filed (new and new versions, with their folders), duplicates not filed, older versions of a group filed to the archive, files archived, cards written per source, cards dropped with their reasons, topics added or merged, entities added or recorded as aliases, conflicts accepted and restored, status-card items marked for review, topic pages rebuilt. Name the work folder only when a file there is useful to the user.

## Hard rules

1. Never write a card whose quote did not pass the check, and never write a conclusion that is not on a card.
2. Never invent topics: a new topic is added only after the user agrees to it, never a new partition number. New entities and aliases reach Table E only through the confirmed preview.
3. Never edit or delete a source. Older versions move to the archive folder, and a source under another name is treated as a new version only after the user confirms the pair.
4. Never write a topic page by hand: topic pages are built only by ingest.py pages.
5. Material is not searchable until its run is finished. Do not answer questions from a run that has not been filed.
6. Replies follow the library language and preferences.output (references/environment.md).
7. Never rewrite the status card without ingest.py status-check (references/config.md, section 2); review marks are added only by the filing script.
8. Without a code environment (Python), write nothing to the library and say so; reading and answering still work.
9. A run is finished only when ingest.py progress --work <work> says finished: yes, which needs the record of ingest.py file (or add-cards) and the topic pages it touched. Until then never say that the material was ingested, filed or is done, and never give a number of cards in the library: say which step the run reached (cards written, checked, waiting for confirmation, ...), that nothing is in the library yet, and the next step progress names. Run progress before every reply that ends a run or says how far it got.
10. The run's files live only in its work folder under .kb-work; the cards of a source live only in their own file, <work>/cards/Snn.jsonl.
