---
name: kb-note
description: Saves a small piece of information from the conversation into the user's knowledge base (an evergreen library) at once, as a source with cards, so it can be found right away. Use when the user says "note this", "save this", "add this to my knowledge base", "jot this down" or similar, for example "note this: send the draft plan to Alex by Friday". Keeps the user's words as a new source, takes cards from them (each a conclusion with the exact sentence it rests on, checked by a script), files them and rebuilds the topic pages they touch; asks first only when the note brings a new topic or entity. Use only when the user asks; never save on your own or ask whether to save. Requests aimed at the assistant's own memory ("remember that", "from now on") are not for this skill. Ingesting documents and setting up libraries belong to kb-ingest; questions belong to kb-query.
---

# Quick notes: save a piece of the conversation

Version: 6.4.0

A note becomes a source of the library on the spot: the user's words are the source text, cards are taken from them and checked like any other, and the topic pages they touch are rebuilt. It only adds files and rebuilds generated pages; it never edits or deletes an existing source or card.

Read references/config.md and references/environment.md once before starting. Scripts are run as references/environment.md says; paths such as scripts/ingest.py are relative to this skill's folder.

## Step 1: what to save

1. If the request carries content, save that.
2. If it is only the command ("note this"), save the most recent information the user gave or confirmed. If it includes your own answer, save only what the user accepted.
3. If it could refer to several things, ask in one sentence which one. Do not guess.
4. Unrelated things in one request: one note each.
5. Tentative or unconfirmed statements are saved as they are; their cards say "unconfirmed" in the conclusion.

## Step 2: which library

Load the registry. Match the content against each library's scope.
1. The user named a library: use it.
2. Exactly one scope fits: use it.
3. None or several fit: ask "Which library: <labels>?" in one sentence. Never default.
Then read references/backend-local.md, the library's _kb.json (language, timezone, names; schema 1 is a 1.x library this release does not write: say so) and its spec. python3 scripts/ingest.py work new --library <library> prints the note's work folder; every <work> below is that path.

Writing needs Python (hard rule 5). Without it, do not write: show the note's words in the reply and say that saving needs a code environment.

## Step 3: the note as a source

1. Write the user's words, exactly, to <work>/note.txt: one paragraph per thought, no Markdown. Lines of the conversation needed to understand them are marked "<user_label>: " and "<assistant_label>: " (_kb.json names). Dates, numbers and names as the user wrote them; a relative date ("next Wednesday") stays as written.
2. python3 scripts/ingest.py note --library <library> --title "<a few words>" --text <work>/note.txt --context "<one sentence: what conversation this came up in>" -o <work>/note

It prints the batch file of a one-source run: the source "Note <YYYYMMDD-HHMM> <title>" ("随手记 ..." in Chinese), the words anchored by paragraph, and where it came from, when and the context as note lines, which cannot be quoted.

## Step 4: cards and checks

1. Write the cards from the words, as references/extract.md says, to <work>/cards/S01.jsonl. A relative date gets the computed date in the conclusion, marked "computed"; never put it in the quote.
2. python3 scripts/ingest.py topics --library <library> --out <work>/topics.txt, then python3 scripts/quote_check.py verify <work>/cards <batch file> --accepted <work>/accepted.jsonl --report <work>/report.json --topics <work>/topics.txt. A rejected card is written once more from the words; one rejected twice is dropped and named in the reply.
3. python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library>.
4. Only when the report lists new topics or the entity report lists new names, ask before writing, in one question: each new topic under an existing topic or as a new one (ingest.py retopic, add-topic), each new name as a new entity or as an alias of an existing one (--map). Otherwise go on without asking.

## Step 5: file

1. When the entity report listed any name: python3 scripts/ingest.py entities <work>/accepted.jsonl --library <library> --apply (with --map when the user chose aliases or types).
2. python3 scripts/ingest.py file <batch file> --cards <work>/accepted.jsonl --library <library> --work <work>
3. Topic pages, for the topics in the record: python3 scripts/ingest.py pages --library <library> --topic "<topic>" (repeat --topic) --work <work>.
4. python3 scripts/ingest.py progress --work <work>. When it says finished: yes, python3 scripts/ingest.py work done --work <work>; otherwise do the step it names first.

On a write failure, retry once; if it still fails, give the reason and show the note's words in the reply.

## Step 6: reply

Only after step 5 finished (hard rule 7). In two or three lines, in the library language and preferences.output:
  Saved to <label>: <source name>
  Cards: <the conclusions, one line each>
  Topic pages rebuilt: <topics>

## Hard rules

1. Save only when the user asks; never save on your own or ask whether to save.
2. The user's words are saved exactly; cards quote only those words, and a card whose quote did not pass the check is not written.
3. Only add files and rebuild generated pages; never edit or delete an existing source or card.
4. A new topic or entity is written only after the user agrees.
5. Without a code environment (Python), write nothing to the library and say so; reading and answering still work. Show the note's words in the reply so nothing is lost.
6. Replies follow the library language and preferences.output.
7. Never say a note was saved before ingest.py progress says finished: yes; until then say what is left. The note's files live only in its work folder under .kb-work.
