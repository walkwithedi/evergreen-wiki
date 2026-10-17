# Design: knowledge base 2.0

Status: implemented in 2.0. This document was the reference for the 2.0 work; each implementation step below was its own pull request and refined details here in the same pull request.

## 1. Scope

- 2.0 changes evergreen-wiki itself and serves work material only. The life library type and its preset are removed.
- The core function is reliable question answering: every answer carries the source sentences it rests on.
- 2.0 is a major version. The 1.x line is frozen: its published releases stay available, no further 1.x releases are made, and 1.x libraries are not migrated.

## 2. Terms

| Term | Meaning |
| --- | --- |
| Batch file | One Markdown file that holds a batch of source documents, built locally by doc2kb |
| Source | One document inside a batch file, numbered S01, S02, … within the batch |
| Anchor | A stable identifier on a paragraph of a source, used by cards and links |
| Card | One claim taken from a source: conclusion, anchor, quote, topic, entities |
| Tier | How much of the work the model does: weak or strong, set per library |
| Topic page | A wiki page for one topic, built from cards |
| Status card | The library's home page and overview of what is true now |

## 3. Intake

Both backends (local folder and Google Drive) use the same pipeline.

### 3.1 Batch file (doc2kb)

- doc2kb turns a set of files into one batch file. Batch files are always built locally, never by the assistant.
- Each source is a section of its own, numbered S01, S02, … over the run, oldest document first, with its original file name. Paragraphs and list items end with an anchor (`^s01-p2`); a table has one anchor on the line below it. Headings carry none.
- The batch size limit comes from the tier (characters per batch: weak 20,000, strong 100,000), given on the command line or read from _kb.json. doc2kb starts a new batch when the next source would exceed it, and cuts a single source longer than the limit at headings into consecutive parts that keep its number. A single paragraph or table longer than the limit is not cut; it becomes a batch of its own.
- Pictures are not exported; their placeholders stay in the text.
- tools/doc2kb/SPEC.md (section 5.6) holds the exact format; kb_batch.py writes it and splits it back.

### 3.2 Ingest (kb-ingest)

kb-ingest takes the batch files of one run (made with doc2kb where commands run, uploaded by the user otherwise) and processes them according to the tier. skills/kb-ingest/SKILL.md holds the procedure; the steps below are what it does.

- Card extraction reads one source at a time in the weak tier and one batch file at a time in the strong tier (references/extract.md).
- Cards the quote check rejects are written once more from the source with the reason given; a card rejected twice is dropped and reported.
- New topics are put to the user one by one: under an existing topic (ingest.py retopic) or added to Table A (ingest.py add-topic: the fallback partition unless the user names one, one version step for the lot, a revision line per topic). The answer is the confirmation of the spec change.
- One preview (sources, new versions, cards per source, topic pages to rebuild) is confirmed before anything is written.
- Strong-tier pages (references/pages-strong.md) are checked by ingest.py check-page: every cited passage must be a current card of the topic and every such card must be cited. A page failing twice is built by the script instead.
- A library in Google Drive is worked on a staging folder: _kb.json, the spec, the whole cards folder and the run's same-named sources are read into it, the scripts run there, and after the confirmation the changed files are written back, old copies first moved to the archive folder.

1. Card extraction, both tiers: the model extracts cards for each source, one JSON object per line. A card holds the source number, the anchor, the quoted sentence, a conclusion, a topic, the entities it mentions and, when the quote states one, an event date. The card's date is not the model's to give: the script takes it from the source's last-modified time.
2. Quote check, both tiers (quote_check.py check): a script checks every card against the batch files of its run.
   - The quote has 6 to 300 characters and occurs in the paragraph, list item or table of its anchor. The comparison ignores white space, full- and half-width punctuation and Markdown emphasis; any other difference fails, so a reworded quote never passes.
   - A quote found in exactly one other paragraph of the same source passes with its anchor corrected; one found in several paragraphs, across paragraphs or nowhere fails.
   - A topic not among the library's topics passes and is listed for the owner to confirm (section 4.2 works the same way for entities). The library's topics are those of the spec's Table A: each partition from topic_start on lists them after the colon, separated by semicolons; they compare without regard to case and spacing, and a known topic takes the spec's spelling. A repeated card (same source, quote and conclusion) is dropped.
   - Cards that fail are not written; the report lists each with its reason, together with the corrected anchors and new topics.
3. Topic pages:
   - Weak tier: a script (ingest.py pages) rebuilds each touched topic page, `Topics/<topic>.md`, from every cards file: the topic's cards newest first (event date, else the source's date), each with its date, conclusion, quote linked `[[Sources/<source>#^pN]]` and a link to its cards file. The page says it is generated; edits to it are overwritten. A topic left without cards keeps a page saying so. The model writes no page text.
   - Strong tier: the model rewrites each affected topic page from its cards. check-page compares source links, so two cards from the same paragraph count as cited when the link appears once; references/pages-strong.md asks for one statement per card.
4. Split and file (ingest.py file): the batch files are split back into one file per source, `Sources/<original file name>.md`, flat; two sources of one run with the same name get their parent folder's name in front. The original documents themselves are not kept in the library; each source file records its original path. Cards are stored under `Cards/`, one file per source with the source's name (quote_check.py write); each card is a section with its quote linked as `[[Sources/<source>#^pN]]`, its topic as `[[Topics/<page>|<topic>]]` and its entities as wiki links. Links name their folder because a source and its cards file share a name.
   - A source whose name is already in the library is a new version: the old source file and its cards file move to `Archive/Sources` and `Archive/Cards` as `<name>_old<YYYYMMDDHHMMSS>.md`; nothing is deleted. The topics of the archived cards are rebuilt with the new ones, so the old version's entries leave the pages.
   - A run with a part missing from its batch files writes nothing.
   - The run record lists the sources written, the files archived and the topics touched. For a library in Google Drive the script writes to a staging folder laid out like the library, which the skill uploads (step 3b).
5. Material is not searchable before its ingest run has finished. There is no fast lane that files material first and reconciles it later.
6. Library layout: the summary files (status card as the home page, spec, indexes) in the root; `Sources/`, `Cards/`, `Topics/` and `Archive/` beside them. Folder names come from the library's names (sources_dir, cards_dir, topics_dir, archive_dir) and can be changed per library.

### 3.3 Notes (kb-note)

A note recorded with kb-note becomes a source on the spot: cards are extracted and filed through the same pipeline (quote check, topic pages, status-card checks).

- ingest.py note writes the user's words as the batch file of a one-source run, "Note <YYYYMMDD-HHMM> <title>" ("随手记 ..." in Chinese): the words are the source text, anchored by paragraph; where it came from, when and the context are note lines, which cards cannot quote.
- The run then goes through quote_check, entities, file and the topic pages. The user is asked first only when the note brings a new topic or a new entity; otherwise it is written at once, since it only adds files and rebuilds generated pages.
- There is no quick-notes folder: new libraries do not get one, and questions do not search one.

## 4. Decisions that need the owner

Scripts prepare each decision; the owner confirms. Nothing in this section is written without confirmation.

### 4.1 New versions of a document

- A source whose name is already in the library is a new version without asking (section 3.2, step 4).
- For a source under a name not yet in the library, a script (ingest.py versions) proposes candidate pairs (new source, library source): the names are equal or close (difflib ratio 0.8 or more) once dates, version marks (v2, rev, final, draft, copy, (1), 副本, 终稿, 定稿, 修订版) and punctuation are dropped, and at least half of the shorter source's paragraphs of 20 characters or more are in the other. A series that differs only by date in its names (weekly reports) is not proposed, because its contents differ.
- Weak tier: the owner picks the pairs that are new versions in the preview.
- Strong tier: the model judges each pair, quoting one sentence of each document its decision rests on, and may add a pair the script missed under the same rule; the owner confirms in the preview.
- A confirmed pair is filed with ingest.py file --replaces NEW=OLD: the old source and its cards move to the archive as for a same-named version, and the new source keeps its own name.
- A library in Google Drive passes the names of its sources folder (--known); a close name not yet in the staging folder is read in and the script runs again.

### 4.2 Entities

- The spec's Table E is the alias table: Name | Type | Aliases | Core | Note.
- A script (ingest.py entities) merges the cards' entity names that match a name or alias of the table, without regard to case and spacing.
- Other names are listed in the preview, each with the type the model suggested on the card (entity_types: project, team, organisation, system or other) and the closest names of the table. By default each is added as a new entity; the owner may record it as an alias of an existing entity or change its type.
- After the confirmation, ingest.py entities --apply rewrites the cards with the table's names and adds the new rows and aliases to Table E, with one version step and a revision line each.

### 4.3 Conflicts

- When new material contradicts a topic page or the status card, the page is rewritten directly.
- A script lists every conclusion that was removed or changed; the owner accepts or restores each one.
- Topic pages: when a source is replaced (same name or a confirmed pair), ingest.py conflicts compares the old version's cards with the new version and the run's cards before the preview. An old card whose quote is still in the new version and quoted by a new card is unchanged. The others are listed: not_carried (the quote is still there but no new card quotes it), changed (the quote is gone and a new card's conclusion is close, difflib ratio 0.6 or more) and removed. By default each change is accepted; ingest.py file --restore keeps the ones the owner restores: a not_carried card becomes a current card of the new version again; any other card stays in the new version's cards file, citing the archived old source and marked as from an earlier version, and topic pages show it so.
- Status card: a rewrite is checked by ingest.py status-check against the current card: items pair by their text, else by a source link they share; removed and changed items and source links no longer cited are listed for the owner, and only a rewrite without them is written.

### 4.4 Status card

- The status card is the wiki's home page and overview.
- When a source is replaced by a new version, the status-card entries that cite it are marked for review: ingest.py file appends "⏳ review: <source> has a new version (<date>)" to each, once, and lists them in the run record.
- When a question touches an entry marked for review, or an entry that is missing, the answer is first built from the sources; the assistant then proposes an update to that entry, written only after the owner confirms.
- Entries of the status card can be used to answer directly, but the answer still quotes the source.

## 5. Question answering (kb-query)

- Every answer quotes the source sentences it rests on, with `[[source#anchor]]` links.
- Weak tier: a script selects the relevant cards and status-card entries by keyword, entity and topic; the model only organises the answer from what it is given and quotes the sentences.
- Strong tier: the model searches and reads the library itself, under the same quoting rule.
- Answer format: each statement is followed by a quote line, `> <exact sentence> [[Sources/<source>#^pN]]`.
- Selection (answer.py select): a keyword naming an entity of Table E stands for all its names; a card scores one point per keyword in its conclusion or quote, two per entity a keyword names and two when a keyword names its topic; the best 12 are listed, newest first among equals (event date, else the source's date), with status-card items that hold a keyword and their review marks. When no card matches, up to five source paragraphs holding a keyword are listed as not on a card.
- Check (answer.py check): every quote line must hold a sentence of its linked paragraph, compared as the quote check does. The weak tier checks every answer before replying; a quote that fails is copied again once, then dropped with its statement.
- Status card: an item marked for review, or a missing one, is answered from the cards and sources; kb-query then proposes the item and writes it only after the user confirms, through ingest.py status-check --write --confirmed (the owner has seen what is removed or changed). It is the only file kb-query writes.

## 6. Runtime

### 6.1 Tiers

- The tier is a setting in _kb.json. Setup picks a default by agent: OpenCode and local models get the weak tier; Claude and ChatGPT clients get the strong tier. The owner can change it by hand.
- The weak tier is for models with limited reasoning and context: everything that can be decided mechanically is done by scripts, and the model is asked only for extraction and wording.

### 6.2 Libraries in Google Drive

- A Drive library is used from an AI client (Claude, ChatGPT) through the skills. Batch files are built locally with doc2kb and uploaded.
- The quote check and page assembly scripts run in the client's code environment. Without a code environment, the skills refuse to write to the library; reading and answering still work.
- This holds for every write and every backend: ingesting, notes, status-card updates and setting up a library. Each skill's hard rules say "Without a code environment (Python), write nothing to the library and say so; reading and answering still work.", and the by-hand ways of writing are gone.

### 6.3 ChatGPT

ChatGPT uses the same skills; each skill also ships a prompt version (prompt.md) carrying the same rules, for clients that take instructions instead of skill folders.

- prompt.md is at most 8000 characters, so it fits a custom GPT's instructions. It sums up the steps and holds every hard rule of SKILL.md word for word (scripts/check_repo.py checks the length, the version and the rules).
- Each release attaches <skill>-<version>-chatgpt.zip: <skill>-prompt.md and <skill>-files.zip, the skill folder as it is. The prompt has ChatGPT unpack the files zip once in its Python tool, so SKILL.md, the references, the scripts and the presets keep their paths.
- Writing to a library needs the Python tool and write access to the library's Drive folder; without either, nothing is written.

## 7. Skills and tools

| Part | Role in 2.0 |
| --- | --- |
| kb-note | Records a note and files it through the ingest pipeline |
| kb-ingest | Ingests batch files; replaces kb-incremental |
| kb-query | Answers from the library with quoted sources |
| tools/doc2kb | Builds batch files locally |
| tools/kb-client | Gains two pages: "Build batch file" and "Waiting for confirmation" (the decisions of section 4) |

- Build batch files is a step of the client: the material folder, the library whose tier sets the batch size, and a new or empty output folder outside every library (default ~/kb-batches/<material>_<date>, kept after the client closes); doc2kb writes the batch files there, and the page offers Copy path and Ingest these.
- Waiting for confirmation reads `_pending/<run>.json` in local libraries, which kb-ingest writes before its preview (ingest.py pending write: new topics, new entities, version candidates, conflicts), and shows each run as a form. The answers are checked (ingest.py check_decisions) and written as `<run>.decisions.json`; the client says in the conversation that they are saved, and kb-ingest reads them (ingest.py pending read) and removes both files after filing (pending done). Answers given in the conversation work as before. The page also lists status-card items marked for review, each with a button that asks kb-query about it.

- All links in the library are Obsidian wiki links (`[[page]]`, `[[source#anchor]]`).
- Shells that bundle the skills only update the version they bundle.

## 8. Data formats (sketches)

These sketches fix the shape; exact field names are settled in the step that implements them.

Batch file:

```markdown
# S01 Project Atlas kickoff minutes.docx
> Original path: Atlas/kickoff minutes.docx

The kickoff took place on 3 March. ^s01-p1

Riverside Clinic will host the pilot. ^s01-p2

# S02 Project Atlas schedule.xlsx · 1/2
> Original path: Atlas/schedule.xlsx

| Phase | Start |
| --- | --- |
| Pilot | April |

^s02-p1
```

Card as the model writes it (one line per card; entity_types only for entities not in Table E):

```json
{"source": "S01", "anchor": "s01-p2", "quote": "Riverside Clinic will host the pilot.", "conclusion": "Riverside Clinic hosts the Project Atlas pilot.", "topic": "Pilot", "entities": ["Riverside Clinic", "Project Atlas"], "entity_types": {"Riverside Clinic": "organisation"}, "event_date": "2026-03-03"}
```

Version candidates (ingest.py versions):

```json
{"same_name": ["Project Atlas schedule.md"],
 "candidates": [{"new": "Project Atlas plan final.md", "old": "Project Atlas plan.md", "name_score": 1.0, "overlap": 0.75, "read": false}]}
```

Conflict (ingest.py conflicts; the entries to restore go to file --restore as a JSON list):

```json
{"id": "c1", "kind": "changed", "source": "Project Atlas plan.md", "old_source": "Project Atlas plan.md",
 "old": {"conclusion": "The pilot starts in April.", "quote": "The pilot starts in April.", "anchor": "p1", "topic": "Pilot"},
 "new": {"conclusion": "The pilot starts in May.", "quote": "The pilot starts in May.", "anchor": "s01-p1", "topic": "Pilot"}}
```

Restored card in a cards file:

```markdown
## The pilot starts in April.

> The pilot starts in April. [[Archive/Sources/Project Atlas plan_old20260401090000#^p1]]

- Topic: [[Topics/Pilot|Pilot]]
- Date: 2026-03-01 09:00 · from an earlier version
```

Entity report (ingest.py entities) and the owner's decisions (--map):

```json
{"merged": {"Atlas": "Project Atlas"},
 "new": [{"name": "Riverside", "type": "organisation", "cards": 2, "closest": ["Riverside Clinic"]}]}
{"Riverside": "Riverside Clinic", "Scheduling Service": {"type": "system"}}
```

Cards file (Cards/Project Atlas kickoff minutes.md):

```markdown
# Cards: [[Sources/Project Atlas kickoff minutes]]

Source: [[Sources/Project Atlas kickoff minutes]] · Document last modified: 2026-03-04 05:06

## Riverside Clinic hosts the Project Atlas pilot.

> Riverside Clinic will host the pilot. [[Sources/Project Atlas kickoff minutes#^p2]]

- Topic: [[Topics/Pilot|Pilot]]
- Entities: [[Riverside Clinic]], [[Project Atlas]]
- Date: 2026-03-04 05:06 (event: 2026-03-03)
```

Topic page (Topics/Pilot.md), weak tier:

```markdown
# Pilot

> This page is generated from the cards by a script; edits here are overwritten.

- 2026-03-03 · Riverside Clinic hosts the Project Atlas pilot.
  > Riverside Clinic will host the pilot. [[Sources/Project Atlas kickoff minutes#^p2]] · [[Cards/Project Atlas kickoff minutes|card]]
```

_kb.json additions:

```json
{
  "schema": 2,
  "tier": "weak",
  "batch_chars": 20000,
  "quote_min": 6,
  "quote_max": 300,
  "names": {"sources_dir": "Sources", "cards_dir": "Cards", "topics_dir": "Topics"}
}
```

kbconf accepts and checks these keys (tier weak or strong, batch_chars at least 1000, quote_min at least 1, quote_max not below quote_min). The schema is 2; a _kb.json of schema 1 is a 1.x library and is refused, since 2.0 does not migrate 1.x libraries.

## 9. Implementation steps

Each step is a pull request; the 2.0 release comes after the last one.

0. This design document.
1. doc2kb: batch files with source numbers, anchors, tier-based batch size and chapter splitting.
2. Card format and the quote-check script, with tests.
3. kb-ingest, in three pull requests:
   - 3a. Scripts: library settings and topics in kbconf, ingest.py (file, pages), folder-qualified links in the cards files.
   - 3b. The kb-ingest skill: both tiers' procedures, calling the scripts; Drive libraries through a staging folder; ingest.py topics, add-topic, retopic and check-page. Not yet in the installer or the plugin manifests.
   - 3c. kb-incremental and the life preset removed; installer, kb-client, tests and documents updated; schema 2.
4. Owner decisions, in two pull requests:
   - 4a. Version candidates and the alias table: ingest.py versions, file --replaces and entities; the kb-ingest steps and preview that use them.
   - 4b. Conflict lists with restore, status-card review marks and the status-card rewrite check (ingest.py conflicts, file --restore, status-check); the kb-ingest step and preview that use them.
5. kb-query: weak-tier card selection, quoted answers checked by a script and confirmed status-card updates; kb-note on the new pipeline, without a quick-notes folder.
6. prompt.md versions for ChatGPT, with -chatgpt.zip release assets and check_repo checks; no write without a code environment, for every skill and backend.
7. kb-client pages "Build batch file" and "Waiting for confirmation", with ingest.py pending (write, read, done) between kb-ingest and the page.
8. Documentation (README, methodology) and the 2.0 release.
