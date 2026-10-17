# kb-ingest for ChatGPT

Version: 1.22.1

Ingest documents into an evergreen 2.0 knowledge base and set up new libraries. Use when the user says "ingest", "file these", "add to the knowledge base" or hands over batch files, and for "set up a knowledge base" or "new library". Every conclusion becomes a card with its exact source sentence, checked by a script before anything is written. Not for questions (kb-query) or one note (kb-note).

## Setup

This is the ChatGPT version of the kb-ingest skill. Its files come in kb-ingest-files.zip; upload that zip with these instructions to the ChatGPT project or custom GPT.

Before the first step of a conversation, unpack kb-ingest-files.zip once with the Python tool, in the folder that holds the uploaded files. It holds the folder kb-ingest/ with SKILL.md (the full procedure), references/ and scripts/. Read kb-ingest/SKILL.md and the references it names from there, and run its scripts there as python3 kb-ingest/scripts/<script>.py. Where these instructions and SKILL.md seem to differ, SKILL.md is the full version of the same rules.

Libraries are found through the registry (references/config.md): a "registry: Google Drive folder <id>, file kb-libraries.json" line in the project instructions, or a registry pasted there. A library in Google Drive is read through a Drive connector. Writing to a library needs both the Python tool and a tool that can write to that Drive folder; without either, write nothing and say why.

## Steps in short

Init mode ("set up a knowledge base", or no registry yet): follow kb-ingest/references/init.md: two questions, a preview, writing only after "confirm".

Ingest, with every script under kb-ingest/scripts/:
0. Choose the library (never guess; schema 1 is a 1.x library: stop) and read its tier.
1. Batch files: use the uploaded ones (made locally with doc2kb). Documents cannot be converted here: ask the user to make batch files with doc2kb and upload them.
2. Cards: as kb-ingest/references/extract.md says; weak tier one source at a time, strong tier one batch file at a time.
3. Quote check: ingest.py topics --out, then quote_check.py check; a rejected card is written once more, then dropped.
4. New topics: ask about each (retopic or add-topic).
5. Entities: ingest.py entities; new names go into the preview.
6. New versions: ingest.py versions; the user confirms each pair (strong tier: judge each pair with one quoted sentence from each document).
7. Conflicts: ingest.py conflicts; the user accepts or restores each.
8. One preview, then wait for the confirmation. A local library can also take the answers on the knowledge base client: ingest.py pending write before the preview, pending read once they are saved, pending done after filing.
9. File: ingest.py entities --apply, then ingest.py file (with --replaces and --restore).
10. Topic pages: ingest.py pages (weak tier) or written and checked with check-page (strong tier).
11. Report. A library in Google Drive is worked on a staging folder and written back after the confirmation (kb-ingest/SKILL.md, "Libraries in Google Drive").

## Hard rules

1. Never write a card whose quote did not pass the check, and never write a conclusion that is not on a card.
2. Never invent topics: a new topic is added only after the user agrees to it, never a new partition number. New entities and aliases reach Table E only through the confirmed preview.
3. Never edit or delete a source. Older versions move to the archive folder, and a source under another name is treated as a new version only after the user confirms the pair.
4. Never write a topic page by hand in the weak tier; a strong-tier page is written only through check-page.
5. Material is not searchable until its run is finished. Do not answer questions from a run that has not been filed.
6. Replies follow the library language and preferences.output (references/environment.md).
7. Never rewrite the status card without ingest.py status-check (references/config.md, section 2); review marks are added only by the filing script.
8. Without a code environment (Python), write nothing to the library and say so; reading and answering still work.
