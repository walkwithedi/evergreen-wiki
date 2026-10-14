# Batch mode: many files in one intake

Filing a large folder in one pass is slow, and the user sees nothing for a long time. Batch mode counts the material first, shows a plan, then files it batch by batch with one progress line after each batch. Summary-file rewrites wait for one final step. Progress is saved after every batch, so a run can stop at any point and go on in a new conversation.

## When

- The material is files or folders on disk (a named path, or the material picker of references/pick-material.md) and commands can run. Uploads and pasted text are filed as usual.
- Run the plan below for every such intake. When it reports one batch, there is no batch mode: file the material as usual. With two or more batches, batch mode applies whether the user chose everything or only part of it.
- Material can come from several folders and files anywhere; give plan every path in one call. Each intake chooses its own material; nothing is remembered from the last one.
- A run is already open: before planning, check for the progress file (find_exact names.batch_plan in the library root; for a Google Drive library, in the work folder). "Continue intake" ("继续入库") always means: continue the open run. When the user brings new material while the run has pending batches, say in one line how far it got and ask once, as a choice:
  - Add to this intake (recommended): plan <paths> --append; the new batches follow the pending ones, files already in the run are left out as duplicates, and one final step covers everything.
  - New material first: plan <paths> --append --front; the new batches go before the pending ones, the rest of the run follows.
  - Drop the rest of the old run: batch_plan.py skip --plan <file> --rest, then the final step for what was filed (section 3), then plan the new material. Filed files stay; original files are never touched.
  Without new material, the reminder of references/config.md, section 4 applies.

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

"Start" is the user's confirmation for every batch delivery of this run. Tell the user they can stop at any time, even inside a batch (closing the window, an interruption), and continue later by saying "continue intake"; the next conversation also reminds them.

## 2. Each batch

  python3 scripts/batch_plan.py next --plan <progress file> --index <library root>/<index name>

marks the batch started and prints the batch number, its group and one "file: <path>" line per file. Other lines:
- "missing: <path>": a file moved since planning. Record it with add --kind review and leave it out.
- "filed: <path> as <name>": its content is in the library by now (an interrupted run filed it). Leave it out.
- "resumed (interrupted)" in the header: the batch was started before and not finished. A topic or entity file of this batch that is already in the library under the name you would give it, with no index row for its source, was written before the interruption: do not overwrite or rename it; record it with add --kind review ("written before an interruption, please check") and go on.
- Exit code 4, "missing folder: <folder>" lines: every file of the batch is gone, usually a removable or network drive that is not connected. Stop, nothing is marked; ask the user to connect it and say "continue intake", or to skip that batch (skip --batch <n>).
File the "file:" paths through Check 1 to step 4 and delivery, as in SKILL.md, with these changes:

1. Copy the file index from the library into the work folder again for every batch: earlier batches have added to it. index_tool reads it; there is no need to read it yourself.
1a. Within one conversation, what you read for the first batch stays current until the final step, because this mode defers every summary rewrite: the spec, the status card, the other summary files, the params, _kb.json and the references. Do not read them again for later batches; take the topics and entities added since from the progress file (rule 2). In a new conversation ("continue intake"), read them once, as for a first batch.
2. Topics and entities: before step 1, take the topics and entities recorded in the progress file (status lists them) as part of Table A and Table E. A new topic is used at once and recorded, not written into the spec:
   python3 scripts/batch_plan.py add --plan <progress file> --batch <n> --kind topic --text "<partition>: <new topic> (reason; source file)"
   A new entity is recorded the same way with --kind entity; its entity page is delivered with the batch.
3. Step 5: judge the triggers as usual, but do not rewrite. Record each trigger and each open-items change with --kind trigger and --file <source file>: the class, the status-card item with its old wording, and the new wording with its source section.
4. Questions that would stop the run use the conservative rule and are recorded with --kind review and --file <source file>, never asked now: out of scope (no file, record the clause), rename to distinguish, a duplicate decided by name only, a picture decision over the image limit (leave placeholders), unreadable parts, a library or partition that does not fit well.
5. Delivery: direct delivery runs its preview as usual but does not wait; "Start" was the confirmation. Delivery of the batch holds only topic files, entity pages, the file index and the readme. With delivery = zip, make one zip per batch and list them all at the end.
6. Mark the batch and print one progress line:
   python3 scripts/batch_plan.py done --plan <progress file> --batch <n> --written <files> --duplicates <n> --review <n>
   Batch <n>/<total> <group>: <written> filed, <duplicates> duplicates, <review> to review. Next: <group>, or the final step.
7. Go straight on with the next batch. Keep the reply short: the progress line only, no per-file notes. When the conversation is getting long, stop after a finished batch and tell the user to open a new conversation and say "continue intake". Stop only right after that batch's done and its progress line, starting nothing else, so that a client can tell this stop from a failure and continue the run in a new conversation.

A failure inside a batch (a script error, a write that cannot be made): stop the run, report it, and leave the batch pending; nothing of a batch is marked done before its delivery.

### Fast mode (intake.mode fast, the default)

Inside each batch, file every "file:" path as references/fast.md says, items numbered across the whole run, with --run <work>/run.json kept for the whole conversation: each file is delivered on its own and gets its own progress line, so it is searchable at once. Rules 3 and 5 above change: step 5 is not judged now (consolidation does it), and delivery happens per file, not per batch. Rule 2 still records new topics and entities with batch_plan.py add. After the last file of a batch, mark the batch done as rule 6 says, with its progress line after the per-file lines.

## 3. Final step

When next reports no pending batch, or the user says "finish intake" ("收尾"):

In fast mode the final step is consolidation (references/consolidate.md): say how many files the run filed, then ask once, as a choice: Consolidate now (recommended) / Later. Now: consolidation writes the recorded topics and entities into the spec in its first round and then runs batch_plan.py finish (step 3 below). Later: run finish now with the spec rewrite only (step 1 for topics and entities, no trigger rewrite), and the queue keeps the files for consolidation. Steps 1 and 2 below apply to full mode.

1. status prints everything recorded. Rewrite the summary files once, as in SKILL.md steps 5 and topic expansion: the spec once for all recorded topics and entities (one version step), the status card, change log and open items for all recorded triggers, entity-page overviews where a trigger names a core entity. Re-check each recorded trigger against the current status card first; later batches may have changed it. Run the rewrite check for every file.
2. Deliver these rewrites with the normal preview and confirmation: they change existing conclusions, so this one step still waits for the user.
3. python3 scripts/batch_plan.py finish --plan <progress file>. When it says "archive the plan", move the progress file into the archive folder (move_rename to <archive_dir>/<stem><old_suffix><time stamp>.json). When it says "keep the plan", leave it: batches are still pending.
4. Report: batches filed and skipped, files filed, duplicates, the summary files rewritten, then "Please review" with every review item (batch, file, reason) and "Topics added this run (please review)".

Pending batches left at "finish intake" stay in the plan: say how many, and that "continue intake" files them later; the final step then runs again for what those batches record.
