# Batch mode: many files in one intake

Filing a large folder in one pass is slow, and the user sees nothing for a long time. Batch mode counts the material first, shows a plan, then files it batch by batch with one progress line after each batch. Summary-file rewrites wait for one final step. Progress is saved after every batch, so a run can stop at any point and go on in a new conversation.

## When

- The material is files or folders on disk (a named path, or the material picker of references/pick-material.md) and commands can run. Uploads and pasted text are filed as usual.
- Run the plan below for every such intake. When it reports one batch, there is no batch mode: file the material as usual. With two or more batches, batch mode applies whether the user chose everything or only part of it.
- A run is already open: before planning, check for the progress file (find_exact names.batch_plan in the library root; for a Google Drive library, in the work folder). When it exists with pending batches, say in one line how far it got and ask whether to continue it or start over. "Continue intake" ("继续入库") always means: continue the open run.

Without Python there is no batch mode: say that a large folder will be slow and offer to file one subfolder at a time.

## 1. Plan

  python3 scripts/batch_plan.py plan <path> [<path> ...] --plan <progress file> --library-root <library root> --index <library root>/<index name>

The progress file is <library root>/<names.batch_plan> for a local library; for a Google Drive library use <work>/<names.batch_plan> (progress then lasts only for this conversation). The script reads intake.batch_files and intake.batch_mb from _kb.json; --batch-files and --batch-mb override them for this run. --first <group> (repeatable) puts groups first; --replace starts over when an open run exists (exit code 3 means one does).

It prints the files per group (count, size, types), what is left out and why (already in the library by content hash, identical copies within the material, archives and types intake cannot read, unreadable files) and the batches: one per first-level subfolder, a large one split in file name order, loose files of a chosen folder as one more. With more than one batch it writes the progress file.

Show the plan to the user in a short table or list: groups, files, batches, what is left out. Suggest an order only when there is a reason (for example policies before the meetings that apply them) and say the reason. Then ask once, as a choice:
- Start (recommended): every batch is filed and delivered in turn without further questions.
- Change the order: re-run plan with --first and --replace, show it again.
- File only some groups: re-run plan on those folders with --replace.
- Cancel.

"Start" is the user's confirmation for every batch delivery of this run. Tell the user they can stop between batches and continue later by saying "continue intake".

## 2. Each batch

  python3 scripts/batch_plan.py next --plan <progress file>

prints the batch number, its group and one "file: <path>" line per file ("missing: <path>" for a file moved since planning: record it with add --kind review and leave it out). File these paths through Check 1 to step 4 and delivery, as in SKILL.md, with these changes:

1. Read the file index from the library again for every batch: earlier batches have added to it.
2. Topics and entities: before step 1, take the topics and entities recorded in the progress file (status lists them) as part of Table A and Table E. A new topic is used at once and recorded, not written into the spec:
   python3 scripts/batch_plan.py add --plan <progress file> --batch <n> --kind topic --text "<partition>: <new topic> (reason; source file)"
   A new entity is recorded the same way with --kind entity; its entity page is delivered with the batch.
3. Step 5: judge the triggers as usual, but do not rewrite. Record each trigger and each open-items change with --kind trigger and --file <source file>: the class, the status-card item with its old wording, and the new wording with its source section.
4. Questions that would stop the run use the conservative rule and are recorded with --kind review and --file <source file>, never asked now: out of scope (no file, record the clause), rename to distinguish, a duplicate decided by name only, a picture decision over the image limit (leave placeholders), unreadable parts, a library or partition that does not fit well.
5. Delivery: direct delivery runs its preview as usual but does not wait; "Start" was the confirmation. Delivery of the batch holds only topic files, entity pages, the file index and the readme. With delivery = zip, make one zip per batch and list them all at the end.
6. Mark the batch and print one progress line:
   python3 scripts/batch_plan.py done --plan <progress file> --batch <n> --written <files> --duplicates <n> --review <n>
   Batch <n>/<total> <group>: <written> filed, <duplicates> duplicates, <review> to review. Next: <group>, or the final step.
7. Go straight on with the next batch. Keep the reply short: the progress line only, no per-file notes. When the conversation is getting long, stop after a finished batch and tell the user to open a new conversation and say "continue intake".

A failure inside a batch (a script error, a write that cannot be made): stop the run, report it, and leave the batch pending; nothing of a batch is marked done before its delivery.

## 3. Final step

When next reports no pending batch, or the user says "finish intake" ("收尾"):

1. status prints everything recorded. Rewrite the summary files once, as in SKILL.md steps 5 and topic expansion: the spec once for all recorded topics and entities (one version step), the status card, change log and open items for all recorded triggers, entity-page overviews where a trigger names a core entity. Re-check each recorded trigger against the current status card first; later batches may have changed it. Run the rewrite check for every file.
2. Deliver these rewrites with the normal preview and confirmation: they change existing conclusions, so this one step still waits for the user.
3. python3 scripts/batch_plan.py finish --plan <progress file>. When it says "archive the plan", move the progress file into the archive folder (move_rename to <archive_dir>/<stem><old_suffix><time stamp>.json). When it says "keep the plan", leave it: batches are still pending.
4. Report: batches filed and skipped, files filed, duplicates, the summary files rewritten, then "Please review" with every review item (batch, file, reason) and "Topics added this run (please review)".

Pending batches left at "finish intake" stay in the plan: say how many, and that "continue intake" files them later; the final step then runs again for what those batches record.
