---
name: kb-note
description: Saves a small piece of information from the conversation into the user's knowledge base as a quick note, to be filed properly later by kb-incremental. Use when the user says "note this", "save this", "add this to my knowledge base", "jot this down" or similar, for example "note this: send the draft plan to Alex by Friday". Writes the user's words, key points and context to one new file in the library's quick-notes folder, replies with the file name and the key point, and when notes pile up suggests saying "file my quick notes". Only creates files, never changes existing ones. Use only when the user asks; never save on your own or ask whether to save. Requests aimed at the assistant's own memory ("remember that", "from now on") are not for this skill. Filing, archiving and health checks belong to kb-incremental; questions belong to kb-query.
---

# Quick notes: save a piece of the conversation

Version: 1.11.0

This skill does one thing: create one new file in a library's quick-notes folder. It never edits, moves or deletes any file, and never touches the library root, archive, entities or inbox.

Read references/config.md and references/environment.md once before starting.

## Step 1: what to save

1. If the request carries content, save that.
2. If it is only the command ("note this"), save the most recent information the user gave or confirmed. If it includes your own answer, save only what the user accepted.
3. If it could refer to several places, ask in one sentence which one. Do not guess.
4. Unrelated things in one request: one file each.
5. Tentative or unconfirmed statements are saved as they are, marked "unconfirmed" in the key points.

## Step 2: which library

Load the registry. Match the content against each library's scope.
1. The user named a library: use it.
2. Exactly one scope fits: use it.
3. None or several fit: ask "Which library: <labels>?" in one sentence. Never default.
Then read that library's backend file (references/backend-gdrive.md or references/backend-local.md) and its _kb.json (for language, timezone, sensitivity and names).

## Step 3: write the note

Plain text inside the file, no Markdown, in this fixed layout (labels in the library language):

Quick note
Time: YYYY-MM-DD HH:MM (<timezone>)
Library: <label>
Suggested partition and topic: <partition topic> / not judged
Source: assistant conversation
---
Words:
<the user's words, exactly; include needed context lines marked "<user_label>:" and "<assistant_label>:">

Key points:
1. <one point per line, only what the words say, nothing inferred or added>

Context:
<one to three sentences: what conversation or question this came up in, so it makes sense later>

Rules:
1. Suggested partition and topic: only if this conversation already read the library spec's Table A; otherwise "not judged". Do not fetch the spec just for this. It is only a hint.
2. With sensitivity enabled: mask ID numbers, card and account numbers, passwords and one-time codes with asterisks, keeping at most the last keep_last characters, in words and key points alike. Never add health, money or investment advice or interpretation.
3. Extra hard rules in the library's _kb-params.md also apply here.
4. Dates, numbers, names and organisations exactly as the user wrote them. A relative date ("next Wednesday") gets the computed date in brackets in the key points, marked "computed".

## Step 4: save it

1. Find the notes folder (names.notes_dir) in the library root with find_folder.
   - One: use it.
   - Several (Drive): use the oldest and mention the duplicates in the reply.
   - None: ensure_folder, and mention "notes folder created" in the reply.
2. File name: YYYYMMDD-HHMM_<short-topic>.md in the library timezone. The short topic is a few words summing up the content, no punctuation or slashes; in a family library include who it concerns. Several notes in the same minute: add -2, -3.
3. write_new in the notes folder with the content from step 3.
4. On failure retry once. If it still fails, give the reason and show the full note in the reply so the user can save it or ask again later.

## Step 5: confirm

Reply in one or two lines:
  Saved to <label> quick notes: <file name>
  Key point: <one sentence>

Then check the backlog: list the notes folder (one level, paging until done), count .md files and find the oldest. More than 20, or the oldest older than 14 days: add a line "N quick notes waiting (oldest YYYY-MM-DD); say 'file my quick notes' to file them." Otherwise say nothing about it.

Replies follow the library language and preferences.output.
