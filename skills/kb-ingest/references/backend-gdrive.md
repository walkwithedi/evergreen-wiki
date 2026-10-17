# Backend: Google Drive

The library is a Drive folder; backend.root in the registry is its folder ID. The tool names below are those of the Google Drive connector in claude.ai and the Claude apps. Other environments may expose Drive through a different MCP server: use the equivalent tool, keep the same queries and rules. If no Drive tool is available, stop and tell the user to connect Google Drive (or to sync the folder to disk with Google Drive for desktop and register it as a local library).

## Operations

| Operation | How |
| --- | --- |
| find_by_name | search_files with parentId = '<folder id>' and title contains '<part of name>' |
| find_exact | search_files with parentId = '<folder id>' and title = '<name>' |
| find_by_text | search_files with parentId = '<folder id>' and fullText contains '<words>' |
| find_folder | search_files with parentId = '<parent id>' and title = '<name>' and mimeType = 'application/vnd.google-apps.folder' |
| list | search_files with parentId = '<folder id>' (add createdTime > '<UTC time>' to limit); keep paging while nextPageToken is returned, never stop because a page was short |
| read | read_file_content with the file ID from a search; if no text comes back, download_file_content |
| write_new | create_file with parentId, title, textContent; contentMimeType text/markdown for .md, application/json for .json, text/plain for .txt; disableConversionToGoogleType true |
| ensure_folder | find_folder; if absent, create_file with mimeType application/vnd.google-apps.folder |
| move_rename | update_file with fileId, the new parentId and, when renaming, the new title |
| replace_content | update_file with fileId and the new textContent; the file keeps its ID. Used only for a plan item marked "updated again in this run" (fast intake). If the connector cannot replace content, move the copy to the archive folder as for any old version instead, under a name built the same way |
| folder_name | get_file_metadata on the folder ID, use its title |

## Rules

1. Always restrict searches with parentId. Never search the whole Drive. parentId covers one folder level, so the archive folder is excluded automatically.
2. Use partial strings in title contains; escape single quotes in names with a backslash.
3. Never use a file ID from memory; take IDs from search results in this conversation.
4. If a file ID from an earlier step fails, search for the file again by name.
5. A permission error on write or move means the connected Google account cannot edit that folder: stop and say so.
6. Drive allows several files with one name in a folder. That is how versions pile up, and why archive mode exists.

## Delivery (delivery = direct, the default)

Drive allows several files with one name, so a new version is written only after the old one has moved to the archive folder. Same two rounds as a local library, with the connector doing the writes:

1. Round 1, preview. Copy _kb.json to <work>/_kb.json. For each output file (root files, and entity pages in the entities folder), find_exact its name in the folder it goes to, and collect every copy found as {"rel": "<name or entities_dir/name>", "id": "<file id>", "modified": "<modifiedTime>"} in <work>/existing.json (an empty list when nothing exists). Then
   python3 scripts/package.py remote-preview <work>/out --library <work>/_kb.json --existing <work>/existing.json --plan <work>/deliver-plan.json --max-name-len <Table D>
   Show the preview: new files, and existing files whose old copy will move to the archive folder. End with: reply "confirm" to write. The turn ends here.
2. Round 2, after the user confirms. ensure_folder the archive folder (and the entities folder if the plan has entity pages). For each item of the plan, in order:
   a. find_exact the name again. If the copies differ from the plan (a copy appeared, disappeared or changed modifiedTime), skip the item and record "changed after preview".
   b. move_rename each old copy listed under "archive" into the archive folder with its archive_as title.
   An item with "replace" (fast intake, updated again in this run): replace_content of that copy instead of b and c.
   c. write_new the new file (contentMimeType text/markdown, disableConversionToGoogleType true) in the root or the entities folder.
   d. find_exact once more: exactly one copy must remain. Record "ok" or the error in <work>/results.json as {"<rel>": "ok" | "<error>"}. On a permission error stop at once and report that the connected account needs edit rights on the folder.
3. python3 scripts/package.py remote-log --plan <work>/deliver-plan.json --results <work>/results.json prints the run log and two file names. write_new the log (text/plain) and the readme (text/plain, under the readme file name printed) into the archive folder.
4. Report written and failed counts from the log, and the names of any failures. Nothing is left for the user to upload, and archive mode is not needed afterwards.

Without Python: build the same preview by hand (archive names <stem><old_suffix><YYYYMMDDHHMMSS>.md, one second apart from now in the library timezone), carry out round 2 the same way, and write the run log with the same lines.

Fast intake (references/fast.md in kb-incremental) delivers each item as soon as it is filed: run round 1 with --run <work>/run.json and carry out round 2 without waiting, since the run was confirmed once at its start. The file index and the consolidation queue are archived once per run and replaced after that; remote-log says when to append to the run log and readme written earlier in the run instead of writing new ones.

Many files make many connector calls. Above about 30 files, say so in the preview and suggest splitting the material into two runs.

## Delivery (delivery = zip)

Used only when _kb.json sets delivery to zip, or has an "inbox" entry: the user runs an inbox script that unpacks uploaded zips (an Apps Script or similar, not part of this kit). Intake output is packed into one zip (scripts/package.py zip); follow the inbox hints for upload and keep the zip layout exactly as package.py builds it. Without an inbox script, the user uploads the files by hand and then runs archive mode, which moves the older same-name copies to the archive folder.

Quick notes (kb-note), the second round of note filing, init and archive mode always write to Drive directly, after a preview the user confirms (kb-note writes without a preview because it only ever creates one new file).
