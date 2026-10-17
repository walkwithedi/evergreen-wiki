# Backends

The skills speak to a library through ten abstract operations (find by name, find exact, find by text, find folder, list, read, write new, ensure folder, move and rename, folder name). Each backend has a reference file that maps them to real tools; a skill reads only the one its library uses.

- Google Drive: [shared/references/backend-gdrive.md](../shared/references/backend-gdrive.md)
- Local folder: [shared/references/backend-local.md](../shared/references/backend-local.md)

## Google Drive

Uses the Google Drive connector (claude.ai and Claude apps) or any Drive MCP server with equivalent search, read, create and update tools. Searches are always limited to the library folder. The library list (kb-libraries.json) can live in Drive too, so claude.ai Project instructions only need one line pointing to it.

The scripts cannot write to Drive, so an ingest run or a quick note works on a staging folder laid out like the library: _kb.json, the spec, the status card, the cards folder and the run's same-named sources are read into it, the scripts run there, and after you confirm the preview the changed files are written back. Because Drive allows several files with one name, each old copy is first moved to the archive folder, so only one copy stays. Writing needs a code environment and a Drive tool that can write, with edit rights on the folder; without them the skills read and answer and write nothing.

No Drive tool in your agent? Sync the folder with Google Drive for desktop and register it as a local library.

## Local folder

Any agent that can read and write files and run Python 3.8+. The scripts (ingest.py) write straight into the folder after you confirm the preview: old versions move to the archive folder, new sources and cards are written and the touched topic pages rebuilt. Decisions an ingest run waits for are kept in _pending/ until the run is filed, so tools/kb-client can show them as a form. A folder cannot hold two files with the same name, so there is never a duplicate to clean up.

## Adding a backend

Write shared/references/backend-<type>.md with the same operation table and rules, add the type to kbconf.check_registry, run scripts/sync_shared.py, and open a pull request.
