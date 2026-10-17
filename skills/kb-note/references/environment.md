# Working environment

These skills follow the Agent Skills format and run in any assistant that supports it. Check what you can do once, at the start, and pick the matching path.

## Work and output folders

- Work folder: a scratch folder for copies of summary files, change lists and plan files. Use a temporary directory outside the library and create work/ and out/ inside it. When the request names a work folder ("Work folder: <path>", "工作文件夹：<路径>"), use that folder and create work/ and out/ inside it.
- Never use the library root as the work folder.
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
