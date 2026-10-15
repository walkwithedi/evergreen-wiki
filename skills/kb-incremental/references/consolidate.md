# Consolidation: conclusions and summary files for items filed by fast intake

Fast intake (references/fast.md) files each item without its key conclusions and without comparing it with the status card. Consolidation does that work for the files in the consolidation queue (names.consolidation_queue), a round at a time: it reads each file closely where needed, writes its key conclusions into it, judges the triggers, and rewrites the summary files once per round after the user has reviewed every change. Nothing reaches the status card without that review.

Trigger: "consolidate", "整合", "整合入库", the choice after a fast intake or a batch run, or the reminder of references/config.md, section 5.

## Before the first round

1. Step 0, then read the spec, status card, file index, and the change log and open items (their reading conditions in params assume a trigger; consolidation always may rewrite them). Read the glossary when a term issue comes up.
2. Copy the queue into a work folder and list the round:
   python3 scripts/consolidate.py list <work>/<queue name> --limit <intake.consolidate_files>
   Empty queue: say so and stop.
3. Say in one line how many files wait and how many rounds that makes; go straight on with the first round.

## Each round

For each file of the round, in queue order:

1. Close-read files (queue column yes): the topic file carries the pending mark. Read it section by section (kb-query's kbfind.py toc lists them, or read the headings) and write the key conclusions as step 3 of SKILL.md says, each naming its section heading. Then write the new head to <work>/head_<file stem>.md: the old head exactly as it is (front matter or text header, section labels) without the mark line, followed by the key conclusions in the place params give them. Then:
   python3 scripts/consolidate.py fill <library root>/<file> <work>/head_<file stem>.md <work>/out/<file>
   (A Google Drive library: save the topic file into the work folder first and fill from that copy.)
   It refuses a file without the mark, a head that drops the original line, and anything that would change the body. A refusal: fix the head and run it again; never edit the body.
2. All files: step 5 of SKILL.md. Ask its three questions for each trigger class, quoting the new material and the status card; no quote, no trigger. Write the twenty lines into this round's notes, not into the reply. Record each trigger as a change: the class, the status-card item with its old wording, the new wording, and the file with its section. Items that settle or open an open item are recorded the same way. A file filed as the same-name new version of an older one also gets its change log entry here.
3. Topics and entities a batch run recorded and has not written into the spec yet (batch_plan.py status, when a progress file is open) are written into the spec in this round: one rewrite, one version step, a revision note for each, as topic expansion says. The batch run's final step is then done (batches.md, section 3).

Then the summary files:

4. Re-check every recorded change against the current status card (an earlier change in this round may have touched the same item). Write the change list for the user, numbered, one line each:
   <n>. <status card | change log | open items>: <old wording> -> <new wording> (<file>, <section>)
   Deletions: <n>. Delete: <old wording> (reason).
   No change: "No summary rewrite this round".
5. Ask once, as a choice: Accept all (recommended) / Leave some out first / Cancel the round. In Chinese: 全部采用 / 先剔除其中几条 / 取消本轮. When the request says the run is unattended (the user allowed everything beforehand and nobody answers), do not ask: take Accept all, and write "unattended, all accepted" into the readme's change section. "Leave some out": ask which numbers, as a second choice when there are four or fewer, otherwise in one line; changes left out are not applied and their files stay in the queue with a note in the readme ("changes not accepted: <numbers>"). Cancel: nothing is written; the queue is unchanged.
6. Rewrite the accepted changes into the status card, change log and open items (and entity overviews where a trigger names a core entity), as SKILL.md step 5 says, and run the rewrite check for every rewritten file. Never deliver a file that fails it.
7. Remove the consolidated files from the queue copy:
   python3 scripts/consolidate.py done <work>/<queue name> --name <file> [--name <file> ...]
   Files whose changes were left out stay.
8. Put the queue copy, the rewritten summary files and the spec into <work>/out/ next to the filled topic files, write the readme (params sections; the change section lists the accepted changes by number), and deliver as the backend file says: the preview shows that each filled topic file's pre-consolidation copy moves to the archive folder. The user already reviewed the changes, so deliver after the preview without asking again.
9. One progress line:
   Round <r>/<rounds>: <n> files consolidated, <c> summary changes, <q> files still in the queue.
   In Chinese: 第 <r>/<轮数> 轮：整合 <n> 个文件，状态卡等改动 <c> 条，队列还剩 <q> 个。
   Go on with the next round. When the conversation is getting long, stop after a delivered round and tell the user to say "consolidate" in a new conversation; the queue keeps the rest.

Without Python: do the same by hand. For a close-read file write the topic file again as the new head, one blank line and the body copied unchanged from after the mark; compare old and new summary files item by item; edit the queue table. Mark the readme "not script-checked".

## Rules that do not change

Every judgement needs a quote. Never infer, never trim or edit body text, never delete: old versions of topic files and summary files move to the archive folder. Process data never triggers. A file that the status card cannot be matched with goes into open items as SKILL.md says.
