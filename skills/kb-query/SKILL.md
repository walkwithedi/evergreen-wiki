---
name: kb-query
description: Answers questions from the user's own knowledge base (an evergreen library in a local or Obsidian folder) by searching it first, never from memory; every fact is followed by the exact source sentence it rests on, with a link to it, and when nothing is found it says where it looked. Use when a question may be recorded there - what was agreed or decided, current values and limits, owners, dates, status, open issues, terms, how something changed, or whether some material is already in the library. Examples: "When is the launch date?", "Who owns Project Atlas?". When the user has a knowledge base set up (a kb-libraries.json registry, KB_LIBRARIES, or libraries named in project instructions), check it before searching code or answering from general knowledge, even if the user does not say "check my knowledge base". Not for unrelated general questions. Writes nothing except a status-card update the user confirmed; ingesting and setup belong to kb-ingest, saving notes to kb-note.
---

# Knowledge base questions

Version: 5.0.0

Search, read and answer. The only file this skill ever changes is the status card, and only after the user confirmed the change (step 5). Partitions, topics, terms and entities are read from the library, never from this file.

Read references/config.md and references/environment.md once before starting. Scripts are run as references/environment.md says; paths such as scripts/answer.py are relative to this skill's folder.

## Step 1: which library

1. A question unrelated to every library's scope (general knowledge, writing, code): do not search; answer normally.
2. Load the registry and match the question against each scope. Search the libraries that fit.
3. Unclear, or more than one could hold the answer: search every library that might, without asking.
4. If unsure whether a question falls in a library, read that library's spec Table A to check; still unsure, treat as rule 3.
5. Ingesting and setup requests belong to kb-ingest; "note this" belongs to kb-note.

For each library searched, read references/backend-local.md and _kb.json. A _kb.json of schema 1 is a 1.x library: say that this release does not read it and that the 1.x release does. Start the answer with: Library: <label(s)>.

## Step 2: where answers come from

| Question about | Read |
| --- | --- |
| the current state of something: conclusions, owners, numbers, dates, status | the status card, then the cards and topic pages behind it |
| one topic in general, how it developed | the topic page (names.topics_dir), newest first |
| details, the exact wording, a whole document | the cards, then the source file (names.sources_dir) at the card's anchor |
| how a term is written, whether a name is standard | spec Table B (term fixes) and Table E (entities and their aliases) |
| open issues | spec Table C |
| which partition or topic a subject belongs to | spec Table A |
| whether some material is in the library | the sources folder, by name |

Never use the ignored files listed in references/config.md. The archive folder holds superseded versions: search it only when the user asks for an old version, and say the result is superseded.

## Step 3: find the material

Pick the question's keywords: names, terms (the standard form from Table B and the user's form), numbers, dates.

  python3 scripts/answer.py select <library root> <keyword> [<keyword> ...]

It lists the status-card items and the cards the keywords point to (a keyword that names an entity of Table E counts for all its aliases; a keyword that names a topic brings that topic's cards), best first, each with its quote and source link; items marked for review say so; it also lists the source paragraphs holding a keyword, marked as not on a card: those of sources without cards yet ("source without cards yet": filed, their cards still to be written) and, when no card matches, those of any source. Answer only from what it lists. When it finds nothing, try once more with other forms of the keywords, then answer as not found.

Without Python: search yourself, inside the library root only. Status card first (read it whole when it is under 8000 characters), then the cards and topic pages with find_by_text; read a source file only at the paragraph a card cites, or whole when the question needs the whole document.

Rules:
1. Never use a file ID or path from memory; use what the search returns.
2. Search cap: at most 8 searches or select runs for one library and 4 more for each extra library. Then answer as not found.

## Step 4: answer

Every statement of fact is followed by a quote line with the exact sentence it rests on and its link:

  The pilot was extended to 2026-04-27.
  > The steering group approved extending the pilot by two weeks, to 2026-04-27. [[Sources/Meetings/Atlas steering minutes 2026-03-13#^p2]]

1. Quote character for character from a card's quote or the source paragraph, with the link the card or select gives. Never shorten, translate or reword a quote; the statement above it says it in your words, in the library language.
2. Priority: the status card, then cards and topic pages, then source paragraphs. When they disagree, give each with its quote and say which is newer; do not decide who is right.
3. A status-card item marked for review (⏳) is not relied on: answer from the cards and sources instead, and go on to step 5.
4. A card from an earlier version (restored by the owner) says so; say so in the answer too.
5. A source paragraph that is not on a card is quoted the same way, with "(not on a card)" after the link.
6. Numbers and dates exactly as written, with units and the time they refer to; no conversion or estimate. No inference: what the library does not record is "not recorded in the knowledge base". If general knowledge is really needed, put it in a separate paragraph headed "not from the knowledge base", without quotes.
7. Use the standard terms (Table B, Table E); if the user used another form, give the standard one with theirs in brackets once.
8. Nothing found: say which libraries and keywords were searched and conclude "nothing found in the knowledge base".
9. Answer only what was asked; mention the search only when nothing was found or sources conflict. Replies follow the library language and preferences.output.

Write the answer to <work>/answer.md first and run python3 scripts/answer.py check <library root> <work>/answer.md. Exit 3 lists the quotes not found in their linked paragraph: copy each again from the card or paragraph, exactly, and check once more; a quote that still fails is removed together with its statement. Then reply with the answer.

## Step 5: status-card update (only with the user's confirmation)

When the answer rests on cards or sources because the status card has no item for a recurring question, or its item is marked for review:

1. After the answer, propose the item: one numbered line in the status card's own style, citing the passages the answer quoted ([[Sources/<source>#^pN]]), and for a marked item the text that replaces it (without the mark). Ask whether to write it; never write without a yes.
2. On yes: copy the status card to <work>/status-card.md and make the change there. Run python3 scripts/ingest.py status-check --old <status card> --new <work>/status-card.md. It lists removed and changed items and source links no longer cited: show that list to the user. When they accept it, run the same command with --write --confirmed --library <library root>. Change nothing else on the card.
3. Without Python, do not change the status card (hard rule 4); give the proposed line for the user to add by hand or through kb-ingest.

## Hard rules

1. Never answer from memory: search the library first; what it does not record is "not recorded in the knowledge base".
2. Every statement of fact is followed by a quote line with the exact source sentence and its link; never shorten, translate or reword a quote.
3. Never rely on a status-card item marked for review; answer from the cards and sources.
4. Write nothing except a status-card update the user confirmed, through ingest.py status-check. Without a code environment (Python), write nothing to the library and say so; reading and answering still work.
5. Stay inside the chosen library root; never use a file ID or path from memory.
6. Replies follow the library language and preferences.output.
