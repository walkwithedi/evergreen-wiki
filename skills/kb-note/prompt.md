# kb-note for ChatGPT

Version: 2.0.0

Save a small piece of information from the conversation into the user's knowledge base (an evergreen 2.0 library) at once, as a source with checked cards, so it can be found right away. Use when the user says "note this", "save this", "add this to my knowledge base" or similar. Not for the assistant's own memory ("remember that"). Ingesting documents and setting up libraries belong to kb-ingest; questions to kb-query.

## Setup

This is the ChatGPT version of the kb-note skill. Its files come in kb-note-files.zip; upload that zip with these instructions to the ChatGPT project or custom GPT.

Before the first step of a conversation, unpack kb-note-files.zip once with the Python tool, in the folder that holds the uploaded files. It holds the folder kb-note/ with SKILL.md (the full procedure), references/ and scripts/. Read kb-note/SKILL.md and the references it names from there, and run its scripts there as python3 kb-note/scripts/<script>.py. Where these instructions and SKILL.md seem to differ, SKILL.md is the full version of the same rules.

Libraries are found through the registry (references/config.md): a "registry: Google Drive folder <id>, file kb-libraries.json" line in the project instructions, or a registry pasted there. A library in Google Drive is read through a Drive connector. Writing to a library needs both the Python tool and a tool that can write to that Drive folder; without either, write nothing and say why.

## Steps in short

1. What to save: the content of the request, or the latest information the user gave or confirmed. Unclear: ask one short question. Unrelated things: one note each.
2. Which library: the one the user named, or the one scope that fits; otherwise ask which. Read its backend reference, _kb.json and spec.
3. The note as a source: write the user's words exactly to a text file, then python3 kb-note/scripts/ingest.py note --library <library> --title "<a few words>" --text <file> --context "<one sentence>" -o <work folder>. It prints the batch file of a one-source run.
4. Cards: write them from the words as kb-note/references/extract.md says; check them with kb-note/scripts/quote_check.py check (with --topics from ingest.py topics); run ingest.py entities. Ask first only when there is a new topic or a new entity.
5. File: ingest.py entities --apply when names were listed, ingest.py file, then the topic pages (weak tier: ingest.py pages; strong tier: write them as kb-note/references/pages-strong.md says and check them with ingest.py check-page --write). A library in Google Drive is worked on a staging folder and written back, as kb-note/references/backend-gdrive.md says.
6. Reply in two or three lines: the source saved, its cards, the topic pages rebuilt.

## Hard rules

1. Save only when the user asks; never save on your own or ask whether to save.
2. The user's words are saved exactly; cards quote only those words, and a card whose quote did not pass the check is not written.
3. Only add files and rebuild generated pages; never edit or delete an existing source or card.
4. A new topic or entity is written only after the user agrees.
5. Without a code environment (Python), write nothing to the library and say so; reading and answering still work. Show the note's words in the reply so nothing is lost.
6. Replies follow the library language and preferences.output.
