# Archive mode: move older same-name copies to the archive folder

For Drive libraries (delivery = zip), where uploads leave several files with one name. In the main folder (and the entities folder) only the newest copy of each .md name stays; older copies move to the archive folder, renamed <stem><old_suffix><YYYYMMDDHHMMSS>.md, and a run log is written there.

A local library (delivery = direct) archives at delivery time and never has same-name copies; for it, archive mode only reports stray files (names with old_suffix, snapshot_prefix or a leading underscore in the root) and suggests moving them.

## Rules

1. Move and rename only. Never delete or trash anything.
2. Only groups of .md files with exactly the same name in the same folder: the library root, and the entities folder if it exists. Each folder is grouped separately. Files in the root whose names contain old_suffix, start with snapshot_prefix or start with an underscore are reported, not handled.
3. Two rounds: the preview ends the turn; act only after the user replies "confirm" or "go ahead".
4. Conflict groups (equal modified times, or newest by modified time differs from newest by created time) are left alone and listed for a human decision.
5. Touch nothing outside the preview.

## Round 1: preview

1. Choose the library (SKILL.md step 0). Find the archive folder (find_folder with names.archive_dir; if absent it will be created in round 2) and read the library folder's name (folder_name).
2. Take the current time in the library timezone, YYYY-MM-DD HH:MM:SS, as base-time.
3. Scope, one of:
   - A delivery was just made in this conversation: the file names in its readme's new and updated sections.
   - The user gave a time ("uploaded today"): files created after it.
   - Neither: files created in the last 48 hours.
   - Only when the user asks for "all": every .md in the root; warn first that a large library takes a while.
4. Candidates:
   - Names in scope: list with createdTime > '<UTC time>' and title contains '.md', paging until done. Skip when the scope is a readme's file list.
   - For each name, find every copy with find_exact, paging until no nextPageToken is returned; never stop because a page was short.
   - Do the same in the entities folder if it exists.
   - Keep only id, title, fileSize, createdTime, modifiedTime, parentId; write them as one JSON array to <work>/candidates.json.
5. Plan:
   python3 scripts/archive_plan.py --tz "<timezone>" --old-suffix "<old_suffix>" --snapshot-prefix "<snapshot_prefix>" --log-prefix "<run_log_prefix>" plan --files <work>/candidates.json --base-time "<base-time>" --folder-name "<folder name>" --scope "<scope>" --out <work>/plan.json
   Without Python: group by name yourself, keep the newest by modified time, leave every conflict alone, and number archive names one second apart from base-time.
6. Show the preview as printed and end with: reply "confirm" to archive. The turn ends here.

## Round 2: execute (after confirmation)

1. Re-check: search each planned name again and confirm the kept and archived IDs are still in the folder. Skip any changed group and record it as "changed after preview".
2. For each file to archive: move_rename to the archive folder with its new_title. Record "ok" or the error. On a permission error stop at once and report that the connected account needs edit rights on the folder.
3. Verify: after each group, find_exact should return one copy. Report any mismatch.
4. Write the results to <work>/results.json ({"<id>": "ok" or "<error>"}) and take the current time as end-time:
   python3 scripts/archive_plan.py --tz "<timezone>" --log-prefix "<run_log_prefix>" log --plan <work>/plan.json --results <work>/results.json --end-time "<end-time>" --out <work>/log.txt
5. write_new the log into the archive folder under the file name the script printed, as plain text.
6. Report: archived N, failed N, needs a decision N, with the names of failures and conflicts. Do not repeat the log.
