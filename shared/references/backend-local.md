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
2. Searches cover the root folder only, not subfolders, so the archive folder is excluded; read the entities or notes folder only when a step says so.
3. Never delete a file. Older versions are moved to the archive folder.
4. Before any write or move that is not a brand-new file, show a preview and wait for the user to confirm. A batch intake run is confirmed once, for all its batches, when the user starts it (references/batches.md in kb-incremental); its progress file is updated without asking. A fast intake run (references/fast.md in kb-incremental) is confirmed once at its start, for the delivery of every item it files.
5. Keep line endings as LF and encoding as UTF-8.

## Delivery (delivery = direct)

A folder cannot hold two files with the same name, so versions never pile up and there is nothing for archive mode to clean. Intake output is written straight into the library in two rounds:

1. python3 scripts/package.py preview <output dir> --library <root> --plan <work>/deliver-plan.json --max-name-len <Table D>  
   Show the preview to the user: new files, and existing files whose old version will move to the archive folder. Stop and wait for confirmation.
2. After the user confirms: python3 scripts/package.py deliver --plan <work>/deliver-plan.json  
   The script re-checks every target, moves each old version to <archive_dir>/<stem><old_suffix><time stamp>.md (originals kept for an old version move there with it, under their own extension), copies the new file in, stores the readme as <archive_dir>/_delivery_<time>_README.txt and writes a run log next to it. Report its last lines.

Without Python, do the same by hand: for each file, if it exists move it to the archive folder under the suffixed name first, then write the new file; finally write a run log with the same lines the script would print.
