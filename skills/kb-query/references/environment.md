# Working environment

These skills follow the Agent Skills format and run in any assistant that supports it. Check what you can do once, at the start, and pick the matching path.

## Work and output folders

- Work folder, kb-ingest and kb-note: each run has its own folder inside the library, <library>/.kb-work/chat-<YYYYMMDD-HHMMSS>/, made by python3 scripts/ingest.py work new --library <library>, which prints its path; <work> in the steps is that path. A folder whose name starts with a dot is not shown by Obsidian and not read by the index, and a run left unfinished can be continued from it later. Never pick another folder, not even one named in the request, and never put run files anywhere else in the library. When a run is finished (ingest.py progress says so), python3 scripts/ingest.py work done --work <work> removes its folder; python3 scripts/ingest.py work drop --library <library> --run <name> removes an unfinished one, only after the user agrees to give it up.
- Work folder, kb-query: a temporary directory outside the library, so that answering never writes into it.
- Handing a file to the user: give its path on disk. Files an ingest run writes land in the library; there is nothing to hand over.

## Running scripts

Paths such as scripts/ingest.py are relative to this skill's folder, not to the current directory. Run a script by its full path in the skill's folder, or as cd <skill folder> && python3 scripts/<name>.py ..., one command per call, with no pipes, redirections or chained commands; put text arguments in quotes.

## Capabilities and fallbacks

| Missing | What to do |
| --- | --- |
| Cannot run Python | Without a code environment (Python), write nothing to the library and say so; reading and answering still work. kb-query searches and answers without its scripts (no answer check). |
| Cannot reach the library (path not found) | Stop. Say which path is missing. Never answer from memory. |
| Cannot write files | kb-note: show the note's words in the reply so nothing is lost. kb-ingest: show every output file in full. kb-query: give a proposed status-card line for the user to add. |
| No registry | Offer setup once, as references/config.md describes; never guess a library location. |

## Time

Take the current time in the library timezone (_kb.json timezone). Write dates as YYYY-MM-DD and times as HH:MM.

## Replies

Reply in the library language (_kb.json language, else preferences.language, else the user's language). Follow preferences.output for formatting. Knowledge files keep their own formats: YAML front matter, Markdown tables in summary files and the Bases code block in entity pages are file formats, not reply formatting.
