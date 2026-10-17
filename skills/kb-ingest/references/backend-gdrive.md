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
| folder_name | get_file_metadata on the folder ID, use its title |

## Rules

1. Always restrict searches with parentId. Never search the whole Drive. parentId covers one folder level, so the archive folder is excluded automatically.
2. Use partial strings in title contains; escape single quotes in names with a backslash.
3. Never use a file ID from memory; take IDs from search results in this conversation.
4. If a file ID from an earlier step fails, search for the file again by name.
5. A permission error on write or move means the connected Google account cannot edit that folder: stop and say so.
6. Drive allows several files with one name in a folder, so a new version is written only after the old copy has moved to the archive folder; find_exact afterwards must find exactly one copy.

## Writing an ingest run

The scripts cannot write to Drive, so kb-ingest and kb-note run them on a staging folder laid out like the library and then writes the changed files back after the user confirms the preview (kb-ingest, "Libraries in Google Drive"): each old copy is moved into the archive folder with move_rename, under <stem><old_suffix><YYYYMMDDHHMMSS>.md, before write_new writes the new file (contentMimeType text/markdown, disableConversionToGoogleType true); find_exact afterwards finds exactly one copy of each name. A permission error stops the writing at once: the connected account needs edit rights on the folder.

Many files make many connector calls. Above about 30 files, say so in the preview and suggest splitting the material into two runs.

kb-note stages the same way as kb-ingest (_kb.json, the spec, the status card and the cards folder), runs its scripts there and writes the new source and cards file and the rebuilt topic pages back. Init writes to Drive directly, after a preview the user confirms; kb-query replaces only the status card, after the user confirmed the change.
