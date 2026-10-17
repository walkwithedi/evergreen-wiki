00_Spec
Version: v1
Last updated: 2026-02-01
Note: read by the knowledge-base skills (kb-ingest, kb-query, kb-note). Tables A, B, C, E and F are read as structured data; when editing, keep table names and column names unchanged. Links are Obsidian wiki links, so the library can be opened directly in Obsidian.

1. Table A: partitions and topics

Each partition lists its topics as one running description, separated by semicolons. New topics are appended to the end of the description; kb-ingest adds one only after the owner agrees, never a new partition number.

00 Spec and status card: fixed files only (the spec and the status card).
01 Indexes and logs: fixed files only.
02 Goals and plans: annual and phase goals; work plans; budgets and funding.
03 Projects and tasks: project plans; progress and weekly reports; milestones; task records; retrospectives.
04 Proposals and deliverables: proposals and designs; research and analysis; deliverables; review comments.
05 Meetings and decisions: minutes; decision logs; feedback and how it was handled.
06 Policies and procedures: rules and policies; procedures and how-to guides; frequently asked questions.
07 Organisation and roles: department and role responsibilities; division of work and handovers; contact points by role (never personal data).
08 Data and reports: metric definitions; recurring reports; statistics.
09 Reference and templates: external standards and policies; reference material; templates; fallback for new topics.

2. Table B: term fixes

Original | Fixed | Note
No entries yet. When a name, department or term is written inconsistently and the owner confirms the standard form, add it here.

3. Table C: open issues

No. | Issue | Files | Date logged
No entries yet.

4. Table E: entities

Name | Type | Aliases | Core | Note
No entries yet.

Types: project, department or team, organisation, system or product, other.
Separate aliases with semicolons. The table is the alias list: names on cards are merged by it, and a name not in it is put to the owner before it is added.

5. Table F: value filters

Empty-value forms | Noise values | Maintenance
none; n/a; not applicable; - | placeholders, SQL keywords, ticket codes, generic words such as "system", "platform" or "department" | add new noise wording found during intake; this counts as a spec change

6. Folders and names

Sources: one Markdown file per source document, named after the original file (report.docx becomes report.md). The same name means the same document in successive versions: a new version takes the name and the old one moves to the archive folder.
Cards: one cards file per source, with the source's name. Topics: one page per topic. Archive: older versions of sources and cards, never deleted.
Folder and summary file names are set in _kb.json names.

7. Cards and evidence

Every conclusion in the library is a card: the conclusion, the exact sentence of the source it rests on, its anchor, a topic and the entities it names. A script checks each sentence against the source before the card is written; a reworded sentence is refused.
Topic pages and the status card cite cards by their source links, such as [[Sources/kickoff minutes#^p2]]. Nothing is stated without such a link.

8. Scope

Filed: material that records a conclusion, decision, owner, number, plan or state relevant to the owner's work. Weakly related material (general reports, raw detail tables, other teams' material) is filed only if it holds something the status card depends on. Not filed: advertising, newsletters, duplicates.
