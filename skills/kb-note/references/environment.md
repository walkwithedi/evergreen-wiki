# Working environment

These skills follow the Agent Skills format and run in any assistant that supports it. Check what you can do once, at the start, and pick the matching path.

## Work and output folders

- Work folder: a scratch folder for copies of summary files, change lists and plan files. Use your environment's temporary or scratch directory and create work/ and out/ inside it (in claude.ai this is usually /home/claude/; in a coding agent, a temporary directory outside the library).
- Never use the library root as the work folder.
- Handing a file to the user: use whatever your environment offers (a download link or file card, or the path on disk). For a local library with direct delivery there is nothing to hand over; the files land in the library.

## Capabilities and fallbacks

| Missing | What to do |
| --- | --- |
| Cannot run Python | Do each script's job by hand, following the "Without Python" note at that step, and mark the result "not script-checked" in the delivery note. |
| Cannot reach the library (no Drive tool, path not found) | Stop. Say which connector or path is missing. Never answer from memory. |
| Cannot write files | kb-note: show the finished note in the reply so the user can save it. kb-incremental: show every output file in full. |
| No registry | Say no library is set up and offer kb-incremental init mode. |

## Time

Take the current time in the library timezone (_kb.json timezone). Write dates as YYYY-MM-DD and times as HH:MM. Convert to UTC only where a backend query needs it.

## Replies

Reply in the library language (_kb.json language, else preferences.language, else the user's language). Follow preferences.output for formatting. Knowledge files keep their own formats: YAML front matter, Markdown tables in summary files and the Bases code block in entity pages are file formats, not reply formatting.
