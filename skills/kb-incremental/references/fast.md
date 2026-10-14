# Fast intake: file each item at once, consolidate later

Intake has two parts that need very different effort. Placing, naming, de-duplicating and writing an item is mechanical and quick; reading it closely, writing its key conclusions and comparing it with the status card takes the whole text and careful judgement. Fast intake does the first part for each item and delivers it at once, so every file is searchable seconds after the user hands it over. The second part waits for consolidation (references/consolidate.md), which handles many filed items in one round and asks the user once about the changes to the summary files.

## When

- _kb.json intake.mode is fast, or the key is missing; and the request does not ask for a full intake ("full intake", "完整入库"). Otherwise the five steps of SKILL.md run for every item as before.
- Every kind of material: uploads, pasted text, files on disk, quick notes (references/notes.md). Many files on disk still get a batch plan first (references/batches.md); inside a batch each file is filed and delivered as below.

## Before the first item

1. Step 0, Check 2 (spec, status card, file index; other summary files only when params require them for steps 1 to 4) and Check 3 and 4 as in SKILL.md. The status card is read only to recognise names and terms; it is not compared with the material now.
2. Make a work folder and a run file path in it: <work>/run.json (package.py starts it on first use).
3. Confirm once. Say in one line how many items will be filed, that each is written into the library as soon as it is ready and is searchable at once, and that key conclusions and status-card changes follow at consolidation, which shows every change for review first. Ask once, as a choice: Start (recommended) / Cancel. In Chinese: 「将逐个收录 <n> 个文件，每个处理完就写进知识库、立刻可查；关键结论和状态卡的改动留到整合时统一给你确认。开始吗？」 with 开始 / 取消. In batch mode the plan's Start is this confirmation. A single item still gets the question; "Start" is the confirmation for the direct-delivery preview of every item in this run, including same-name new versions, whose old copy moves to the archive folder as usual.

## Each item

Number the items 1, 2, 3 in the order they are filed. Where commands run:

1. Scan:
   python3 scripts/prep.py scan <original file> --library <library root> --work <work> --n <n> --max-heading-len <Table D>
   It copies the file index (and the spec) into the work folder the first time, checks for a duplicate upload, converts and cleans the item into <work>/body_<n>.md, reads the document date and lists Table B wordings in the body. It prints one card.
   - Exit 3 with "duplicate upload by content hash": record it for the run summary and go to the next item.
   - A source-name hit marked "hash differs" is a lead for a new version, as in step 4.
   - "read the original": the item could not be converted (a scan, a picture, a legacy format). Read it as Check 1 says and write <work>/body_<n>.md yourself, then go on.
   - Pictures: as references/convert.md says for the run as a whole.
   Pasted text: write it to <work>/paste_<n>.txt first and scan that; there is no original file, so leave out --source below.
2. Clean: masking (step 2.2) and the term fixes the card lists (step 2.3), one place at a time in the body file, as in SKILL.md. Read only what these need: the lines the card points to, and for masking a search of the body for the class-A patterns of params.
3. Place (step 1): from the card's outline and opening text, the file name, and the body's first section where these do not settle it. Topic expansion as in SKILL.md. In batch mode a new topic is used at once and recorded with batch_plan.py add --kind topic, as batches.md says, and the spec is rewritten at consolidation; outside batch mode the spec is rewritten at once and delivered with the item (rare, and the next items need it). In YAML mode map entities with meta.py entities as entity-yaml.md says; a new entity's page is written into <work>/out_<n>/<entities_dir>/ before step 5.
   Decide here whether the item is on the params close-reading list (by its type and the card; no reading for this).
4. Head: write <work>/head_<n>.md with the metadata only (front matter per entity-yaml.md, or the text header of params) and any section labels params put before the body. No key conclusions.
5. File:
   python3 scripts/prep.py file --n <n> --library <root> --work <work> --partition <nn> --topic "<topic>" --type "<type>" --title "<short title>" --orig "<source file name>" --source <original file> [--close-read] [--same-version] --backend <local|gdrive> --max-len <Table D>
   - Exit 3 with a file-name hit: judge step 4 with the evidence it asks for. Next version of that file: run again with --same-version (the change log entry waits for consolidation). Different material, or not enough evidence: rename to distinguish, run again with the new short title.
   - Exit 3 with "too long": shorten the short title and run again.
   It assembles the topic file into <work>/out_<n>/, adds the pending mark for a close-read item, updates the index copy and the consolidation queue copy in the work folder, and puts both and a short readme into <work>/out_<n>/.
6. Deliver <work>/out_<n>/ at once:
   - direct, local: python3 scripts/package.py preview <work>/out_<n> --library <root> --plan <work>/plan_<n>.json --run <work>/run.json --max-name-len <Table D>, then python3 scripts/package.py deliver --plan <work>/plan_<n>.json without waiting (the confirmation above covers it).
   - direct, Google Drive: remote-preview with the same --run, carry out the plan with the connector (an item marked "updated again in this run" is written over the named copy, not archived), then remote-log with the same plan; append its lines to the run log and readme when they exist already.
   - zip: no per-item delivery. Build every item, merge the out_<n> folders into one <work>/out (the last index and queue copies win), and pack it once at the end.
7. One progress line, nothing else for this item:
   <n>/<total> <file name>: filed, searchable now (consolidation pending)
   In Chinese: <n>/<总数> <文件名>：已入库，可查询（待整合）
   Duplicates: <n>/<total> <source file name>: already in the library (duplicate upload).

Without Python: do the same steps by hand: compare the source name with the index, clean by eye, write the head and the topic file, add the index row and the queue row (columns: file, source file, filed time, close-read yes or no; a close-read item gets the line <!-- kb:conclusions-pending --> at the end of its head, before the body), and deliver as the backend file says. Note "not script-checked" in the run summary.

## Interruptions

A run can stop between items. Every delivered item is in the library index with its content hash, so filing the same material again finds it as a duplicate upload and goes on with the rest. In batch mode, batch_plan.py next reports such files as "filed: <path> as <name>". An item stopped before its delivery left nothing in the library; prepare it again in a fresh work folder.

## After the last item

1. Run summary in a few lines: items filed, duplicates, renamed to distinguish (old name, new name, reason), new versions, topics and entities added (please review), anything to check by hand.
2. Then ask once, as a choice: Consolidate now (recommended) / Later. In Chinese: 「这次入库的 <n> 个文件还没整合：关键结论和状态卡都还没更新。现在整合吗？」 with 现在整合 / 稍后再说. Later: the queue keeps them, and the next conversation reminds (references/config.md, section 5).
