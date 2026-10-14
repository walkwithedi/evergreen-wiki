# Quick-note filing: move notes from the waiting folder into the library

Trigger: "file my quick notes", "file the notes". kb-note saves each note as one small .md file in the library's notes folder (names.notes_dir). Each note has a header (time, library, suggested partition and topic) and a body (the user's words, key points, context).

This mode groups notes by partition and topic into material, files that material through the five steps and delivers it. After the user confirms the material reached the library, the filed notes move to <notes_dir>/<notes_done_dir>.

## Rules

1. Read only the .md files directly in the notes folder, never the filed subfolder.
2. Move notes only after the user confirms the intake landed, and only notes verified to be in the library (listed in this run's delivery note, or confirmed by text search in round 2). Never delete, rename or edit a note.
3. Notes that fit no topic get a new topic under "Topic expansion" and are filed. Notes that are out of scope, belong to another library, or exactly repeat library content stay where they are, with the reason in the delivery note.
4. The user's words are the basis and are never rewritten while grouping. Key points are only a guide; where they disagree with the words, the words win and the mismatch is logged as an issue.

## Round 1: group and deliver

1. Choose the library. If the user named one, use step 0. If not, look at the notes folder of every registered library: if only one has notes, use it; if several do, take the one with most notes and tell the user the others are waiting. One library and one delivery per run.
2. List the notes (list, paging until done). No folder or no notes: "<library>: no quick notes waiting", stop. More than 40: take the oldest 40 and say the rest wait for next time.
3. Avoid filing twice: for each note, find_by_text in the library root with the note's file name without .md. A hit on a file whose body contains "<note_marker> <note file name>" means "filed but not moved": skip that note and list it with the library file that contains it. If the search fails, process the note and mark it "not checked for duplicates". If every note is already filed, deliver nothing; list them and ask whether to move them.
4. Read the remaining notes and the summary files and spec (SKILL.md input checks).
5. Place each note by Table A (the suggested topic in its header is only a hint). One line each:
   Note: <file> -> <partition topic> / Expansion: partition XX gets topic "…" (reason) / Out of scope (spec clause)
   Notes of one kind share one new topic. A note in the wrong library: "wrong library", leave it, and tell the user to move it to the other library's notes folder.
6. Build material: notes with the same partition and topic become one item, oldest first. Each note starts with the line "<note_marker> <note file name>" (step 3 depends on it; never drop or change it), followed by its time, words, key points and context; separate notes with a line "-----". The source name of the item is "quick-notes_<YYYYMMDD-HHMM>_<partition><topic>" (start time of this run); there is no original file, so step 4 runs without --file.
7. File each item through the five steps, with these additions:
   - Step 1: type from Table A; if params allow a free type, use "quick notes"; otherwise the closest listed type, noted in the delivery note (expansion adds topics, never types). The document date is the latest note time in the item; an event date comes from the words, else "date not in material". Put the batch date in the short title ("quick notes to 2026-10-08") so it never matches an existing file.
   - Step 2: normal cleanup; with sensitivity enabled, check masking again even though kb-note masked on capture.
   - Step 3: always close-read (in fast mode: prep.py file --close-read, and consolidation writes the conclusions). Key conclusions only from words stated plainly and not marked "unconfirmed". Unconfirmed notes stay in the body but never become conclusions or trigger evidence.
   - Step 4: names never match by construction, so this is new material. A note that repeats the library exactly is marked "already recorded" but stays in the item.
   - Step 5: as usual. A note may be trigger evidence; quote its words and cite "source: quick note <file>".
8. Deliver as SKILL.md says. Add to the readme's change section: "Quick notes: N filed, M left"; list any added topics.
9. After the usual delivery note, add:
   - Notes filed: note file -> proposed file name.
   - Topics added (please review), if any.
   - Notes left in place, with reasons.
   - Filed but not moved (step 3 hits): note file -> library file; reply "notes are filed" to move them too.
   End with: once the files are in the library, reply "notes are filed" and I will move these notes to <notes_done_dir>.

## Round 2: move filed notes

When the user replies "notes are filed" (or similar):
1. ensure_folder <notes_dir>/<notes_done_dir>.
2. Which notes: if this conversation has the round 1 lists, use them. If not (a new conversation), list every note in the notes folder and run the step 3 search on each; move only notes whose marker line is found in a library file. Leave the rest.
3. move_rename each one into the filed folder; keep its name.
4. One line: moved N, failed M (with reasons).

If the user says the intake failed, move nothing; fix the cause and deliver again.
