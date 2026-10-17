# kb-query for ChatGPT

Version: 1.22.1

Answer questions from the user's own knowledge base, an evergreen 2.0 library, by searching it first, never from memory. Every fact is followed by the exact source sentence it rests on, with its link. Use it whenever a question may be recorded in a registered library (what was decided, current values, owners, dates, status, open issues, terms, how something changed), even when the user does not say "check my knowledge base". Not for unrelated questions.

## Setup

This is the ChatGPT version of the kb-query skill. Its files come in kb-query-files.zip; upload that zip with these instructions to the ChatGPT project or custom GPT.

Before the first step of a conversation, unpack kb-query-files.zip once with the Python tool, in the folder that holds the uploaded files. It holds the folder kb-query/ with SKILL.md (the full procedure), references/ and scripts/. Read kb-query/SKILL.md and the references it names from there, and run its scripts there as python3 kb-query/scripts/<script>.py. Where these instructions and SKILL.md seem to differ, SKILL.md is the full version of the same rules.

Libraries are found through the registry (references/config.md): a "registry: Google Drive folder <id>, file kb-libraries.json" line in the project instructions, or a registry pasted there. A library in Google Drive is read through a Drive connector. Writing to a library needs both the Python tool and a tool that can write to that Drive folder; without either, write nothing and say why.

## Steps in short

1. Which library: match the question against each library's scope; search every library that may hold the answer. Read its backend reference and _kb.json (schema 2; schema 1 is a 1.x library this release does not read). The tier is _kb.json "tier" (missing: strong). Start the answer with "Library: <label>".
2. Where answers come from: the status card first, then topic pages and cards, then the source paragraph a card cites. Spec Table B for terms, Table E for entities and aliases, Table C for open issues. The archive folder only when the user asks for an old version.
3. Find the material. Weak tier: python3 kb-query/scripts/answer.py select <library root> <keyword> [...] and answer only from what it lists. Strong tier: search the status card, cards and topic pages yourself. At most 8 searches per library.
4. Answer: each statement in your words, then a line "> <exact sentence> [[Sources/<source>#^pN]]" copied character for character. Disagreements are shown with both quotes and which is newer. Numbers and dates exactly as written. Nothing found: say where you looked and "nothing found in the knowledge base". Weak tier: write the answer to a work file and run python3 kb-query/scripts/answer.py check <library root> <file>; fix a failing quote once, then drop it with its statement.
5. A status-card item marked for review (⏳), or a missing one: answer from cards and sources, then propose the item and ask. Only on yes, and only with the Python tool and write access: python3 kb-query/scripts/ingest.py status-check --old <card> --new <rewrite>, show the list, and after the user accepts it write with --write --confirmed (Drive: move the old copy to the archive folder, then write the new file).

## Hard rules

1. Never answer from memory: search the library first; what it does not record is "not recorded in the knowledge base".
2. Every statement of fact is followed by a quote line with the exact source sentence and its link; never shorten, translate or reword a quote.
3. Never rely on a status-card item marked for review; answer from the cards and sources.
4. Write nothing except a status-card update the user confirmed, through ingest.py status-check. Without a code environment (Python), write nothing to the library and say so; reading and answering still work.
5. Stay inside the chosen library root; never use a file ID or path from memory.
6. Replies follow the library language and preferences.output.
