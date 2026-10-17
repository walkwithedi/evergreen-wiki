# Backend: local folder

The library is a folder on disk; backend.root in the registry is its path (~ allowed). It may be an Obsidian vault or a folder synced by Google Drive for desktop, Dropbox or similar. Use the file tools of your environment (read, write, list, search, shell). If you cannot reach the path, stop and say which path is missing.

## Operations

| Operation | How |
| --- | --- |
| find_by_name | list the folder (one level, not recursive) and match names containing the string |
| find_exact | test whether <folder>/<name> exists |
| find_by_text | search file contents in the folder, one level only (grep -l -F or ripgrep with --max-depth 1); fall back to reading candidates if no search tool exists |
| find_folder | test whether <parent>/<name> is a directory |
| list | list the folder with modification times (ls -l, dir, or the file tool) |
| read | read the file as UTF-8 |
| write_new | write a new file; refuse if the name already exists |
| ensure_folder | create the folder if it does not exist |
| move_rename | move the file; refuse if the target exists |
| folder_name | the last part of the root path, or label in _kb.json |

## Rules

1. Stay inside the library root. Never touch files outside it.
2. Searches cover the root folder only, not subfolders, so the archive folder is excluded; read the sources, cards, topics or archive folder only when a step says so.
3. Never delete a file. Older versions are moved to the archive folder.
4. Before any write or move that is not a brand-new file, show a preview and wait for the user to confirm. An ingest run is confirmed once, for everything it writes, before the scripts that write run (kb-ingest, step 8).
5. Keep line endings as LF and encoding as UTF-8.

## Writing an ingest run

kb-ingest's scripts write straight into the library folder after the user confirms the preview: scripts/ingest.py file writes the sources and cards files and moves each older version, with its cards file, into the archive folder as <stem><old_suffix><YYYYMMDDHHMMSS>.md; scripts/ingest.py pages (or check-page --write) writes the topic pages. A folder cannot hold two files with the same name, so versions never pile up.

Without Python, do the same by hand: for each file, if it exists move it to the archive folder under the suffixed name first, then write the new file.
