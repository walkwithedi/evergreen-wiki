00_Spec
Version: v1
Last updated: {{DATE}}
Note: read by the kb-incremental skill. Tables A to F are read as structured data; when editing, keep table names and column names unchanged. Topic files carry YAML front matter and link entities, so the library can be opened directly in Obsidian.

1. Table A: partitions and topics

Each partition lists its topics as one running description. New topics are appended to the end of the description.

00 Spec and status card: fixed files only (the spec and the status card).
01 Indexes and logs: fixed files only (file index, open decisions, change log, glossary).
02 Strategy and goals: goals and OKRs; roadmaps; strategy memos; budgets and funding.
03 Projects: project plans; status reports; milestones and release plans; retrospectives.
04 Architecture and design: solution designs; design reviews; architecture decision records; capacity and sizing.
05 Meetings and decisions: minutes; decision logs; review feedback and how it was handled.
06 Operations: runbooks and procedures; incident reviews; on-call and duty rosters; change records.
07 Ownership and organisation: team responsibilities; ownership and handover of systems and data; roles (never personal data).
08 Data and metrics: metric definitions; recurring reports; dashboard snapshots.
09 Reference and frameworks: standards and policies; external references; templates; fallback for new topics.

Type list: free; use the material's actual form (minutes, design, plan, list, table, report, reference, decision record).

2. Table B: term fixes

Original | Fixed | Note
No entries yet. When a system, team or term is written inconsistently and the owner confirms the standard form, add it here.

3. Table C: open issues

No. | Issue | Files | Date logged
No entries yet.

4. Table D: thresholds

Parameter | Value
Heading demotion limit (characters) | {{HEADING_LIMIT}}
File name length limit (characters) | {{FILENAME_LIMIT}}
Large file threshold (bytes) | 1000000

5. Table E: entities

Name | Type | Aliases | Core | Note
No entries yet.

Types: system, project, team, organisation, other.
Only names in Table E may be written as links. A new entity met during intake may be registered in the same run and listed in the readme for review; until registered it stays plain text.
Separate aliases with semicolons. Mark the few entities that deserve a maintained overview as core = yes.

6. Table F: value filters

Empty-value forms | Noise values | Maintenance
none; n/a; not applicable; - | placeholders, SQL keywords, ticket codes, generic words such as "system" or "platform" | add new noise wording found during intake; this counts as a spec change

7. Naming

Topic files: <partition>_<topic>_<type>_<short title>.md. No date in the name: the same name means the same document in successive versions, and older versions are archived.
Embed what tells similar material apart in the short title:
(1) Recurring material (weekly reports, monthly metrics): the period, as in 08_Recurring reports_report_2026-W41.md.
(2) One template filled by several parties: the party, as in 03_Status reports_report_2026-09-Payments.md.
(3) Similar topics with different content: a distinguishing word.
Summary files have fixed names; see _kb.json names.
Entity pages live in the entities folder, named after the entity.
Older versions move to the archive folder with the old suffix and a time stamp; temporary snapshots start with the snapshot prefix; run logs start with an underscore.

8. Metadata

Topic files start with YAML front matter between two --- lines, fields in this order:
document_date: YYYY-MM-DDTHH:MM (unquoted)
partition: "05"
topic: "Minutes"
type: "minutes"
systems: ["[[Payments Gateway]]"] (Table E names as quoted links; after Table F filtering)
systems_note: "…" (only when wording was filtered or empty)
keywords: ["…"] (Table E names as links, others plain)
status: "current"
size: "large" (only at the Table D large file threshold)
source_file: "…"
source_path: "…"
source_characters: number
source_images: number
After the front matter: key conclusions, then the cleaned body. No links in the body.
Duplicate and trigger judgements go into the readme only, never into knowledge files.

9. Entity pages

Each Table E entity has a page in the entities folder with type: "entity", entity_type, core and aliases in its front matter, and an Obsidian Bases query listing every file that links to it (archive and entities folders excluded).
Core entities also have an Overview section maintained by kb-incremental: every sentence cites a source link; current state cites the status card only; it is updated only when filed material links to the entity and triggers.

10. Scope

Filed: material that records a conclusion, decision, owner, number, plan or state relevant to the owner's work. Weakly related material (general reports, raw detail tables, other teams' material) is filed only if it holds something the status card or an open decision depends on. Not filed: advertising, newsletters, duplicates.

11. Evidence

Conclusions rest on documents, not on hearsay. Unconfirmed statements are marked "to verify", logged as open issues and kept out of the status card.
Every entry in the status card, change log and open decisions cites its source as a link, such as basis: [[05_Minutes_minutes_2026-09-Release-review]].
