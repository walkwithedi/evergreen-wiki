# Backends

The skills speak to a library through ten abstract operations (find by name, find exact, find by text, find folder, list, read, write new, ensure folder, move and rename, folder name). Each backend has a reference file that maps them to real tools; a skill reads only the one its library uses.

- Google Drive: [shared/references/backend-gdrive.md](../shared/references/backend-gdrive.md)
- Local folder: [shared/references/backend-local.md](../shared/references/backend-local.md)

## Google Drive

Uses the Google Drive connector (claude.ai and Claude apps) or any Drive MCP server with equivalent search, read, create and update tools. Searches are always limited to the library folder. Filed material is written straight into the folder after you confirm a preview; because Drive allows several files with one name, the old version of each file is first moved to the archive folder, so only one copy stays. The library list (kb-libraries.json) can live in Drive too, so claude.ai Project instructions only need one line pointing to it.

If you already run your own inbox automation (for example an Apps Script that unpacks uploaded zips), add an "inbox" object to _kb.json describing it; the skills then deliver a zip for you to upload there instead (or set "delivery": "zip" to always get a zip).

No Drive tool in your agent? Sync the folder with Google Drive for desktop and register it as a local library.

## Local folder

Any agent that can read and write files. Filed material is written directly in two rounds: a preview of new files and of the old versions that will be archived, then, after you confirm, package.py deliver moves old versions to the archive, copies the new files in and writes a run log. A folder cannot hold two files with the same name, so there is never anything left for archive mode to clean.

## Adding a backend

Write shared/references/backend-<type>.md with the same operation table and rules, add the type to kbconf.check_registry, run scripts/sync_shared.py, and open a pull request.
