# Design: knowledge base 2.0

Status: agreed design, not yet implemented. This document is the reference for the 2.0 work; each implementation step below is its own pull request and may refine details here, updating this file in the same pull request.

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
   - Strong tier: the model rewrites each affected topic page from its cards.
4. Split and file (ingest.py file): the batch files are split back into one file per source, `Sources/<original file name>.md`, flat; two sources of one run with the same name get their parent folder's name in front. The original documents themselves are not kept in the library; each source file records its original path. Cards are stored under `Cards/`, one file per source with the source's name (quote_check.py write); each card is a section with its quote linked as `[[Sources/<source>#^pN]]`, its topic as `[[Topics/<page>|<topic>]]` and its entities as wiki links. Links name their folder because a source and its cards file share a name.
   - A source whose name is already in the library is a new version: the old source file and its cards file move to `Archive/Sources` and `Archive/Cards` as `<name>_old<YYYYMMDDHHMMSS>.md`; nothing is deleted. The topics of the archived cards are rebuilt with the new ones, so the old version's entries leave the pages.
   - A run with a part missing from its batch files writes nothing.
   - The run record lists the sources written, the files archived and the topics touched. For a library in Google Drive the script writes to a staging folder laid out like the library, which the skill uploads (step 3b).
5. Material is not searchable before its ingest run has finished. There is no fast lane that files material first and reconciles it later.
6. Library layout: the summary files (status card as the home page, spec, indexes) in the root; `Sources/`, `Cards/`, `Topics/` and `Archive/` beside them. Folder names come from the library's names (sources_dir, cards_dir, topics_dir, archive_dir) and can be changed per library.

### 3.3 Notes (kb-note)

A note recorded with kb-note becomes a source on the spot: cards are extracted and filed through the same pipeline (quote check, topic pages, status-card checks).

## 4. Decisions that need the owner

Scripts prepare each decision; the owner confirms. Nothing in this section is written without confirmation.

### 4.1 New versions of a document

- Weak tier: a script proposes candidate pairs (old source, new source); the owner picks the ones that are new versions.
- Strong tier: the model decides, quoting the passages of both documents its decision rests on.

### 4.2 Entities

- A script merges entity names using the alias table in the spec.
- A name not in the table is shown to the owner, who maps it to an existing entity or confirms it as new. The result is written back to the alias table.

### 4.3 Conflicts

- When new material contradicts a topic page or the status card, the page is rewritten directly.
- A script lists every conclusion that was removed or changed; the owner accepts or restores each one.

### 4.4 Status card

- The status card is the wiki's home page and overview.
- When a source is replaced by a new version, the status-card entries that cite it are marked for review.
- When a question touches an entry marked for review, or an entry that is missing, the answer is first built from the sources; the assistant then proposes an update to that entry, written only after the owner confirms.
- Entries of the status card can be used to answer directly, but the answer still quotes the source.

## 5. Question answering (kb-query)

- Every answer quotes the source sentences it rests on, with `[[source#anchor]]` links.
- Weak tier: a script selects the relevant cards and status-card entries by keyword, entity and topic; the model only organises the answer from what it is given and quotes the sentences.
- Strong tier: the model searches and reads the library itself, under the same quoting rule.

## 6. Runtime

### 6.1 Tiers

- The tier is a setting in _kb.json. Setup picks a default by agent: OpenCode and local models get the weak tier; Claude and ChatGPT clients get the strong tier. The owner can change it by hand.
- The weak tier is for models with limited reasoning and context: everything that can be decided mechanically is done by scripts, and the model is asked only for extraction and wording.

### 6.2 Libraries in Google Drive

- A Drive library is used from an AI client (Claude, ChatGPT) through the skills. Batch files are built locally with doc2kb and uploaded.
- The quote check and page assembly scripts run in the client's code environment. Without a code environment, the skills refuse to write to the library; reading and answering still work.

### 6.3 ChatGPT

ChatGPT uses the same skills; each skill also ships a prompt version (prompt.md) carrying the same rules, for clients that take instructions instead of skill folders.

## 7. Skills and tools

| Part | Role in 2.0 |
| --- | --- |
| kb-note | Records a note and files it through the ingest pipeline |
| kb-ingest | Ingests batch files; replaces kb-incremental |
| kb-query | Answers from the library with quoted sources |
| tools/doc2kb | Builds batch files locally |
| tools/kb-client | Gains two pages: "Build batch file" and "Waiting for confirmation" (the decisions of section 4) |

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

Card as the model writes it (one line per card):

```json
{"source": "S01", "anchor": "s01-p2", "quote": "Riverside Clinic will host the pilot.", "conclusion": "Riverside Clinic hosts the Project Atlas pilot.", "topic": "Pilot", "entities": ["Riverside Clinic", "Project Atlas"], "event_date": "2026-03-03"}
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

kbconf accepts and checks these keys (tier weak or strong, batch_chars at least 1000, quote_min at least 1, quote_max not below quote_min) while the schema stays 1; it becomes 2 when kb-incremental is removed (step 3c).

## 9. Implementation steps

Each step is a pull request; the 2.0 release comes after the last one.

0. This design document.
1. doc2kb: batch files with source numbers, anchors, tier-based batch size and chapter splitting.
2. Card format and the quote-check script, with tests.
3. kb-ingest, in three pull requests:
   - 3a. Scripts: library settings and topics in kbconf, ingest.py (file, pages), folder-qualified links in the cards files.
   - 3b. The kb-ingest skill: both tiers' procedures, calling the scripts; Drive libraries through a staging folder; ingest.py topics, add-topic, retopic and check-page. Not yet in the installer or the plugin manifests.
   - 3c. kb-incremental and the life preset removed; installer, kb-client, tests and documents updated; schema 2.
4. Owner decisions: version candidates, alias table, conflict lists, status-card review marks.
5. kb-query: weak-tier card selection and quoted answers; kb-note on the new pipeline.
6. prompt.md versions for ChatGPT; Drive libraries without a code environment refuse writes.
7. kb-client pages "Build batch file" and "Waiting for confirmation".
8. Documentation (README, methodology) and the 2.0 release.
