---
name: kb-query
description: Answers questions from the user's own knowledge base of Markdown files (Google Drive folder or local/Obsidian vault) by searching it first, never from memory. Use when a question may be recorded there - what was agreed or decided, current values and limits, owners, dates, status, open items, terms, how something changed; personal records such as IDs, health, insurance, money, contracts, due dates; or whether some material is already filed. When the user has a knowledge base set up (a kb-libraries.json registry, KB_LIBRARIES, or libraries named in project instructions), check it before searching code or answering from general knowledge, even if the user does not say "check my knowledge base". Not for general questions unrelated to the libraries. Read-only - intake, archive, health checks and setup belong to kb-incremental; saving notes belongs to kb-note.
---

# Knowledge base questions

Version: 1.5.0

Read-only: search, read and answer. Never create, change, move or delete anything in a library. Partitions, topics and terms are read from the library, never from this file.

Read references/config.md and references/environment.md once before starting.

## Step 1: which library

1. A question unrelated to every library's scope (general knowledge, writing, code): do not search; answer normally.
2. Load the registry and match the question against each scope. Search the libraries that fit.
3. Unclear, or more than one could hold the answer: search every library that might, without asking.
4. If unsure whether a question falls in a library, read that library's spec Table A to check; still unsure, treat as rule 3.
5. Intake, archive, health check or setup requests belong to kb-incremental.

For each library searched, read its backend file and _kb.json. Start the answer with: Library: <label(s)>.

## Step 2: which file first

| Question about | Read first |
| --- | --- |
| conclusions, positions, definitions, owners, boundaries, numbers, the current state of something | status card (always) |
| whether some material is filed | file index |
| open decisions (work) or due dates, renewals, follow-ups, payments, to-dos (life) | open items |
| how something changed, what it used to be | change log, with the status card for the current state |
| how a term is written, whether a name is standard, open issues | glossary, checked against the status card |
| which partition a subject belongs to | spec, Table A |
| details (meeting content, design specifics, reports, contract terms, statements) | status card to locate, then the source material |

## Step 3: search

Use the operations in the backend file, always inside the chosen library root.
- Summary files: find_by_name with the search key (references/config.md).
- Source material by name: find_by_name. File names look like <partition>_<topic>_<type>_<short title>.md, so a partition can be searched with its prefix ("05_"). Family material in a life library carries the family member in the short title.
- Source material by content: find_by_text.

Rules:
1. Never use a file ID or path from memory; use what the search returns.
2. Search with partial strings, not full titles.
3. Stay in the root folder level; never widen the search beyond the library. The entities folder is searched only for questions about one person, organisation, system or project as a whole.
4. Never use the ignored files listed in references/config.md.
5. Several copies of one summary file: use the most recently modified and add "several copies of this file exist; the newest was used".
6. Search cap: one search and one reworded retry per keyword; at most 8 searches for one library and 4 more for each extra library. Then stop and answer as "not found".
7. Several source files match: prefer the ones the status card or index mention, then newest first; read at most 5 per library.
8. Each library is searched with its own root only.

Quick-note fallback: only when the library itself has nothing relevant, search its notes folder (names.notes_dir) with find_by_text, not its filed subfolder. These count toward the cap.

History: only when the user asks for old versions, search the archive folder, and say the result is a superseded version.

## Step 4: answer

1. Priority: status card, then change log and lists, then source material. If source material disagrees with the status card, answer with the status card as current, point out the difference and where it is; do not decide who is right.
2. Every statement of fact names its basis file (full file name), with the library when several were searched: "basis: Life 00_Status-Card.md".
3. Use the standard terms from the status card and glossary; if the user used an older form, give the standard one and the old one in brackets once.
4. Numbers and dates exactly as written, with units and the time they refer to; no conversion or estimate. Where files disagree, list each with its source.
5. No inference. What the library does not record: "not recorded in the knowledge base". If general knowledge is really needed, put it in a separate paragraph headed "not from the knowledge base".
6. Items still open in the open-items list: state that and the deadline recorded.
7. Quick notes: mark "quick note, not yet filed" with the note's file name, and that it has not been checked; keep any "unconfirmed" mark.
8. Nothing found: say which libraries, files and keywords were searched, conclude "nothing found in the knowledge base", and suggest rewording or checking whether the material was filed.
9. With sensitivity enabled: never show class-A data in full (ID, card and account numbers, passwords, codes); mask with asterisks, at most the last keep_last characters. No health, money or investment advice and no interpretation of results, diagnoses, returns or coverage; report only what is recorded.
10. Answer only what was asked; mention the search process only when nothing was found or sources conflict.
11. Replies follow the library language and preferences.output.
