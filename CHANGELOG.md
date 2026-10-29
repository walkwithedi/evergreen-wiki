# Changelog

All three skills share one version number. To release, update this file and the "Version:" line of every SKILL.md together and merge to main; the release workflow then publishes v<version>.

## 6.5.1

Skills
- The converter copy is doc2kb 2.2.0 (DOC2KB_VERSION; was 1.1.0): it also reads legacy .doc, .xls and .ppt files, and a large folder no longer slows down as it goes, since the converter's report is written once per batch instead of after every document.
- kb_batch.py make runs the converter as one batch (`batch_size` 0), so the writer sees the whole run and sources stay numbered and ordered across it, whatever the number of files; batch files are as before.

## 6.5.0

Client (tools/kb-client)
- Quick search starts again for every opening the input hint names: besides search, look up and 搜索, 查找, 知识库里, a message starting with tell me about, what is, 介绍, 讲讲, 讲解, 说说, 解释, 什么是, 查询, 查一下, 有没有 and the like is searched at once instead of being sent to the assistant. A test checks that every word the hint names starts a quick search.
- Permission cards have Deny, Always allow and Allow once. Always allow asks once, then OpenCode remembers the actions the card lists and Allow everything is switched on for that window; the separate Allow everything on this page button is gone. The header switch, the remembered count and Clear stay.

Skills
- kb-query is used only when the user asks to search the knowledge base or a message says to use kb-query (as Deep search does); other questions are answered without it, even when a library might record the answer. The English and Chinese descriptions say so.
- The instructions line names each library's folder ("<label> (<scope>) at <folder>"), says to use kb-query only when asked, and, with preferences.output plain, asks for plain-text replies. kb-query takes the libraries from that line and reads references/config.md only without it, references/environment.md only when Python cannot run or a folder cannot be reached, and references/backend-local.md only when searching without Python; the script, work-folder and ignored-file rules it needs are in SKILL.md. Upgrading through the client or install.py replaces the old line, found by its opening words; the rest of the file is kept.

## 6.4.1

Client (tools/kb-client)
- Opening the conversation no longer sends one request for a window that does not exist (answered 404) before loading the current window.

## 6.4.0

Client (tools/kb-client)
- Quick search starts only for a message beginning with search, search for, look up, 搜索, 搜索一下, 搜一下, 查找 or 知识库里; messages beginning with explain, tell me about, what is, 解释, 介绍, 有没有 and the like go to the assistant. The Search the knowledge base switch works as before.
- While the knowledge-base skills are not all installed or no library is there, the page opens with the knowledge base unfolded and Set up standing out, whatever the browser remembers, until it is folded on the page.
- The note to quit OpenCode in a terminal shows only while material is being ingested (the stages of an ingest in the conversation, or a running ingest of the client's own).
- The fallback that runs opencode run once per message is called one-shot mode (单次运行模式) on the page and in the README, apart from the simple version of --simple.
- Both kb-client.desktop entries find the client through readlink -f, so a link to them, on the desktop for example, works.

Workbench (tools/workbench)
- GET /api/state gives kb: the knowledge-base skills installed (of three) and the libraries registered whose folder is there; step 3 shows them and, until both are there, says to choose Set up first.

kb-ingest
- The description names "continue the ingest" and "write the missing cards" (继续入库, 补抽卡片), the modes Continue and Missing cards.

Installer and documents
- install.py suggests "ingest: <file or folder path>" instead of attaching documents, and says that this release reads libraries made by 4.0 or later (schema 3).
- README: a table of the three double-click entries, the two ways to ingest (Ingest under a library for many documents, searchable at once; "ingest: <path>" in the conversation for a few files), a note for 5.x, and 技能 for skill in Chinese. tools/opencode-setup: its entry no longer mentions restoring a backup, which is in the terminal menu. examples/: copy the sample before registering it; a Chinese README.

## 6.3.0

Client (tools/kb-client)
- Quick search: a message starting with search, look up, tell me about, what is or a Chinese word such as 搜索, 查找, 介绍, 讲解 or 什么是, or any message of a window whose Search the knowledge base switch is on, is not sent to the assistant. POST /api/quick splits it into keywords (punctuation, spaces and function words separate them; CJK runs longer than four characters give their pairs of characters), searches the index of every local library, and returns status-card items, cards and paragraphs ranked by the keywords they hold, 15 at most, at once. The client then calls the model of OpenCode's settings once (the window's model or the default; baseURL, apiKey, headers) and streams a summary from those passages only, each sentence numbered after them; numbers that are no passage are marked. Nothing found calls no model; a failed call keeps the passages and says why.
- Under each result, Deep search sends the message to the current window for kb-query, and Give to the assistant sends it unchanged. Results stay on the page, outside the conversation; the switch is kept per window in the browser.
- The API key is used in the client's server only, never sent to the page or logged.

## 6.2.0

kb-query
- answer.py select gets its cards and paragraphs from the index's search: those holding every keyword first, ranked by BM25 with a small weight for newer documents; when fewer than five hold every keyword, those holding only some follow, marked "only some keywords". At most 15 cards and paragraphs together (was 12 cards and 5 paragraphs); paragraphs of sources with cards can be listed too. Entity names and aliases of Table E, and topic names, match as before; the output format is unchanged, the JSON gains partial, and entities on cards.
- SKILL.md step 3 describes the new list; step 4 adds a rule: a card or paragraph holding only some keywords is quoted only when it answers the question itself.

Index (shared/scripts/kbindex.py)
- search() takes keywords as a list and relax (results holding only some keywords fill up a short list, marked partial); each keyword is matched on its own and the relevances add up. A keyword naming a topic brings its cards, one naming an entity the cards that name it.

Client (tools/kb-client)
- The search bar, its result list and the automatic summary are removed (GET /api/search, POST /api/search/summary): questions are asked in the conversation, where kb-query uses the same search. Source links in answers still open the paragraph and its neighbours (GET /api/context), now trying each local library.

## 6.1.0

Index (shared/scripts/kbindex.py)
- The full-text index splits Chinese, Japanese and Korean text into pairs of characters and other text into words, for paragraphs and, new, for cards (conclusion and quote). A keyword of two CJK characters now uses the index instead of LIKE; a keyword ending in a word matches at the start of a word; results are ranked with BM25. Keywords that leave a single CJK character, and SQLites without FTS5, use LIKE as before. An index made by an earlier version is made again on first use.
- search() and `kbindex.py query LIBRARY "QUERY"`: words and "quoted phrases" that must all match, entity names and aliases of Table E standing for each other, paragraphs and cards ranked together (BM25, a small weight for newer documents, a card before its own paragraph). context() gives a paragraph with its neighbours.
- answer.py select scores cards and paragraphs as before; it gets them from the new index.

Client (tools/kb-client)
- A search bar above the conversation searches a library's index (GET /api/search) and lists paragraphs and cards at once, the words marked; a click shows the paragraph with two before and after it (GET /api/context).
- The best ten results (up to 15,000 characters) go to the current conversation window with a request to answer from them by kb-query's rules and check the quotes (POST /api/search/summary). While that window works nothing is sent, and Summarise with AI sends them later.
- Source links in answers show as Name §N and open the same paragraph view.

## 6.0.1

Client (tools/kb-client)
- An unfinished ingest run of the client's own is shown in one line at the top of the conversation as soon as the page opens, with its progress and Stop, Continue, Discard and Details; a run stopped by a restart can be continued from there without opening the ingest panel. A finished run's line keeps its summary until Hide. The ingest panel reloads on every ingest event, also while it is closed.
- Copy answer under every answer of the assistant copies the answer as plain text: source links become (Name §N), Markdown marks are removed, table rows become tab-separated lines.
- The assistant's answers use the full width of the conversation; on a wide screen the conversation takes about a window's height also while the knowledge base is open.
- The unused progress line under the ingest stages is removed from the page.

## 6.0.0

The document converter is now its own project, [doc2kb](https://github.com/walkwithedi/doc2kb). This repository carries a copy of a doc2kb release and writes its batch files itself.

Removed and incompatible
- Batch files are made with `kb_batch.py make` instead of `doc2kb_core.py --kb-batch`. The options are the same (`--batch`, `--files`, `--only`, `--since`, `--fp-db`, `--library`, `--batch-chars`, `--tier`, `--lang`, ...) and so is the output: replace `python3 doc2kb_core.py ... --kb-batch` with `python3 kb_batch.py make ...` in scripts or prompts that call it. `doc2kb_core.py` no longer knows `--kb-batch`, `--tier`, `--batch-chars` or `--library`.
- tools/doc2kb is removed, and releases no longer attach `doc2kb-v<version>.zip`; the stand-alone converter is released by doc2kb.

Changed
- shared/scripts/doc2kb_core.py is a copy of doc2kb 1.1.0, recorded in DOC2KB_VERSION. scripts/sync_doc2kb.py copies a release in (`--from`) and checks the copy (`--check`); CI checks it against the release named in DOC2KB_VERSION.
- kb-ingest's step 1, the kb-client ingest run and the stage names on the page use `kb_batch.py make`.
- The batch file format is described in docs/batch-files.md. Converter tests live in doc2kb; tests/test_kb_batch.py covers making and splitting batch files.

## 5.0.0

5.0 makes an ingest run traceable from its own folder: each run works in <library>/.kb-work/, its cards are kept one file per source, a script says how far the run got, and a run counts as finished only once the filing script has written it into the library.

Removed and incompatible
- quote_check.py check is renamed verify; the name check is gone. Scripts or prompts that call quote_check.py check must call quote_check.py verify. ingest.py check (the health check) keeps its name.
- The work folder of kb-ingest and kb-note is no longer a temporary directory or a folder named in the request: it is always <library>/.kb-work/chat-<YYYYMMDD-HHMMSS>/. kb-query keeps a temporary directory outside the library.

Work folders (shared/scripts/ingest.py)
- ingest.py work new --library DIR makes a run folder and prints its path (--prefix chat or client); work list lists them, finished or not; work done --work DIR removes a run folder once progress says the run is finished; work drop --library DIR --run NAME removes an unfinished one the owner gave up. Only folders under .kb-work are removed.
- ingest.py progress --work DIR [--json]: the step a run reached and the next one, judged from the files in its folder (batch files, cards/Snn.jsonl per source, accepted.jsonl and report.json, entities.json, versions.json, conflicts.json, filed.json, pages.json).
- ingest.py file, add-cards and pages take --work DIR and append their records to filed.json and pages.json there. A run is finished when it was filed and every topic it touched has its page rebuilt.
- The health check lists run folders left unfinished for more than seven days.

Cards
- quote_check.py verify takes a folder of cards files (one per source, read in name order) as well as one file; a rejected card from a folder is reported with its file and line.
- Writing cards (references/extract.md): each source's cards go to <work>/cards/Snn.jsonl; a source with nothing worth a card gets an empty file.

Skills
- kb-ingest: a Continue mode ("continue the ingest") picks an unfinished run with work list and goes on from the step progress names. Step 0 makes the run folder; steps 9 and 10 pass --work; the run ends with progress and work done; the ingest report takes its numbers from the filing records. New hard rules: a run is finished only when progress says so, and until then the reply says which step it reached and that nothing is in the library yet; the run's files live only in its folder.
- kb-note: the note's work folder is a run folder under .kb-work; a note is reported as saved only once progress says the run is finished.

Client (tools/kb-client)
- A client-run ingest works in <library>/.kb-work/client-<id>/ instead of the client's state folder; Continue after a restart works as before. A finished run's folder is removed at once and its log kept as ingest-<id>.log in the client's log folder. A stopped or failed run can be discarded (Discard, POST /api/ingest/discard), which removes its folder. Runs saved by 4.0 in the state folder are still found.
- The ingest stages and steps follow the rename to quote_check.py verify.

## 4.0.0

4.0 keeps the 3.0 setting (an offline Kylin workstation, OpenCode, local libraries, script-led steps) and makes one library carry about ten thousand documents: sources keep the folders they came from, a library index makes filing, pages and answers independent of the library's size, and the knowledge base client ingests material itself, filing every document at once and writing cards first for the ones the rules pick and later for the rest. Libraries made by 2.0 or 3.0 are not read; 3.0.0 keeps working for them. The design is in docs/design-4.0.md.

Removed and incompatible
- Libraries are schema 3. A _kb.json of schema 2 (2.0.x and 3.0.x, one flat sources folder) is refused with a message naming 3.0.x, as schema 1 is; libraries are not migrated. install.py refuses such a folder in the same words.

Library layout
- A source keeps the folder it came from below the material root: Sources/<folder>/<name>.md, Cards/<folder>/<name>.md, older versions under Archive/Sources/<folder> and Archive/Cards/<folder>. kbconf.rel_folder() makes the folder from a batch file's original path: parts made safe for names and links, cut to 60 characters, a path over 180 characters shortened in the middle; an absolute path or one leading out of the root gives the top folder.
- A file name is one document wherever its folder is: a source whose name is in the library is a new version, archived from its old folder, and the new one goes to its own folder. A run's sources with one name and different content form a group: the newest is current and the others go straight to the archive, unless --groups (or the decisions file's "groups") picks another current one or marks members as separate documents, which get their folder's last part in front of their name.
- A source with the same content as one in the library or an earlier one of the run (kbindex.fingerprint: the text without notes, anchors and spacing) is not filed again and is listed under duplicates.
- ingest.py file without --cards files the sources only; the record lists them under without_cards, with older and duplicates.
- ingest.py pages: a topic with more than 60 cards keeps its newest year and undated cards on its page and each earlier year on "<topic> (YYYY)"; year pages no longer needed are removed.
- ingest.py versions also lists the run's groups and duplicates; same_name covers every folder; candidates carry old_path and are compared only with library names sharing enough letter pairs.

Index (shared/scripts/kbindex.py, copied into the three skills)
- <library>/_index/kb.sqlite holds sources, paragraphs and cards, made from the files and kept current by comparing sizes and times on every use; build, refresh, stats and search commands. Trigram full-text search where SQLite has it, else LIKE (KBINDEX_FULL_TEXT=0 forces LIKE). A damaged index, or one this SQLite cannot read, is made again; a folder that cannot be written gets an index in memory.
- ingest.py file, conflicts, versions and pages and answer.py select read through it. answer.py select also lists paragraphs of sources without cards yet, marked as such.
- tests/test_scale.py: 10,000 sources and 100,000 cards; an answer's material within five seconds (SCALE_SOURCES sets the size).

Health check
- ingest.py check (health_check, read only, exit 3 when it finds problems; --json): cards whose quote is no longer in its paragraph, links of the status card's items and of topic pages to files that do not exist, topic pages missing, out of date or no longer built (compared with what ingest.py pages builds, in memory), cards files without their source, status-card items marked for review or citing a source that is not current, runs waiting for decisions for more than seven days, and the number of sources without cards. ingest.py pages builds its pages through page_texts().
- kb-ingest has a health check mode ("health check", "check the knowledge base"; 体检). kb-client has a Health check button under each library (GET /api/check), listing the findings by kind.

Client-run ingest (tools/kb-client)
- ingest_run.py: Ingest under a library lists a material folder (POST /api/ingest/plan), marks the documents that get cards now by rules (folders, a time range) and runs the steps itself (POST /api/ingest/start): doc2kb conversion, versions (duplicates not filed again; groups of same-named documents and candidates wait for decisions), the other documents filed without cards (ingest.py file --sources), cards one source per message in the client's own windows (not counted against the eight, not saved; one to four at once; a rejected card sent back once), new topics and conflicts waiting for decisions, then entities, file and pages. A document that replaces one in the library, and every member of a group with an important member, gets its cards in the run; documents without text are not filed. State in <state dir>/ingest/<id>/run.json and run.log; Stop and Continue (/api/ingest/stop, /api/ingest/continue), also after a restart; finished runs removed after seven days. The write lock names the run's window.
- Backfill: writes the cards of documents filed without them while every conversation window has been idle for a minute, the rules' documents first, newest first, giving way to a conversation at once; Pause, Switch off, kept for the next start (POST /api/backfill). Cards with new topics wait for decisions; the others go through entities --apply, add-cards and pages.
- auto.py: automatic ingest from a library's drop folder (_Drop, _待入库) once the documents have not changed for two minutes and the assistant is free, unattended (Allow everything in its windows, questions answered with the recommended option) but decisions still wait; done documents move to _Filed/<date> (_已入库), ones without text to _Not filed (_未处理); the client keeps running while a library has it on (POST /api/auto).
- agent.py: windows have a kind (chat or ingest); ingest windows are the client's, do not count against MAX_WINDOWS and are not saved; answer_recommended() answers a question card with its recommended option.
- Waiting for confirmation: groups of same-named documents (current one, "another document"), duplicates listed, bulk buttons per group and a filter for long groups; decisions of the client's own runs are not said in a conversation.
- ingest.py: file and conflicts take --sources S01,S03; backfill writes batch files for library sources without cards (kb_batch.from_library keeps their anchors, so that split_back gives the library text again); add-cards writes their cards without archiving anything. kb-ingest has a missing-cards mode.
- tools/workbench: switching versions is also refused while the client's ingest runs or waits for decisions (GET /api/ingest).

Examples
- The sample materials sit in folders (Plans, Meetings, Status reports) and the sample library keeps them.

Workbench and client
- tools/workbench: switching between the simple and the full version is refused while a conversation of the client works or waits for an answer (an ingest run goes on in a conversation), besides a running management step; the wizard reads GET /api/chat/state for it.
- tools/kb-client: the write-lock line has a Show button that brings the step panel into view (or the holding window); under the stage bar, a line says that an ingest run takes long, with the command that opens OpenCode in the work folder and a Copy button.
- tools/opencode-setup: the key is shown as its first and last four characters with its length (「abcd…wxyz（共 N 位）」), so that the key in use can be told apart; ten characters or fewer show as asterisks.
- tools/kb-client: the Material card and its Build batch files step are removed; documents are ingested by asking in the conversation with a file or folder path, and kb-ingest converts them itself.

## 3.0.0

3.0 serves one setting: an offline Kylin workstation where OpenCode runs a privately deployed model. Libraries are local folders, and every step that can be decided mechanically is done by a script. Libraries made by 2.0 work unchanged. Google Drive libraries and the ChatGPT versions of the skills stay with 2.0.0, which is not developed further. The design is in docs/design-3.0.md.

Removed and incompatible
- The Google Drive backend: backend-gdrive.md, the staging-folder procedure, `init_library.py --drive-folder` and render, and docs/backends.md. A registry entry of type gdrive is refused with a message naming 2.0.x.
- The ChatGPT versions of the skills (every prompt.md, `build_skill.py --chatgpt`) and the Claude Code plugin manifests (.claude-plugin).
- The strong tier: pages-strong.md, `ingest.py check-page` and `init_library.py --tier`. A library's tier is read and ignored; topic pages are always built by `ingest.py pages`, and the batch size is batch_chars (default 20,000 characters).
- kb-query's kbfind.py and `--known`: answer.py select gives the material and answer.py check checks the quote lines.
- Windows and macOS: the Windows registry and state locations, the Windows link handling, the platform checks in the tests and the macOS and Windows CI jobs. Handling of file names and archives made on other systems stays.
- Releases no longer attach the skill zips; scripts/build_skill.py stays for private builds.

Agent and installer
- install.py offers OpenCode's skills folder (~/.config/opencode/skills) first, then ~/.agents/skills and ~/.claude/skills, and writes the instructions line into OpenCode's AGENTS.md (or ~/.claude/CLAUDE.md, which OpenCode reads when it has no AGENTS.md).
- doc2kb no longer asks for a tier in its dialog; `--tier` stays on the command line and picks its limit.

Offline workbench
- tools/opencode-setup: sets OpenCode up from one personal key, switches off its start-up downloads and checks a first start, as a page (ca_web.py) or a terminal menu (codeagent-setup.sh). The key is shown only as 「已设置（共 N 位）」. The hints on where a key is issued and how Node is switched are general and can be reworded in ~/.config/opencode-setup/hints.conf (keys AK_HINT and NODE_HINT, read as text and never run; CA_HINTS points elsewhere).
- tools/workbench: the three-step wizard (check Node, opencode and the configuration; key and self-check; open the workbench), which ends in this repository's kb-client with --simple --chat-first. The ~/.bashrc block and the files under ~/.config/work-kb/ keep their names, so a workstation set up before needs nothing redone.
- scripts/build_workbench.py builds workbench-bundle-<version>.zip from the repository zip: the workbench entry at the top (mode 755) and evergreen-wiki/ beside it; it stops when a tool is missing.

Releases and checks
- Each release attaches three files: workbench-bundle-v<version>.zip, evergreen-wiki-v<version>.zip and doc2kb-v<version>.zip. docs/release-downloads.md lists them.
- The release workflow, run by hand with refresh_notes on, rewrites the notes of the version's existing release from CHANGELOG.md and the download guide; its zips and tag stay as they are.
- CI runs the checks on Ubuntu with Python 3.8, standing in for Kylin. tests/test_workbench.py tests the workbench, the setup page and the bundle against a fake model endpoint.

Documentation
- README and README.zh-CN describe the workstation setting, the three downloads, the workbench quick start, "Coming from earlier releases" and the compatibility table. docs/manual-setup, the methodology, examples/README and the kb-client and doc2kb READMEs are updated for 3.0.

## 2.0.0

2.0 is a major version for work material: every answer quotes the source sentence it rests on. Documents are converted into batch files, the model takes cards from them (a conclusion with the exact sentence it rests on), a script checks every quote before a card is written, and topic pages and the status card are built from the cards. kb-ingest replaces kb-incremental; kb-query answers with a quote line after every fact; kb-note saves a note as a source with cards. Libraries are weak or strong tier; ChatGPT versions of the skills are attached to the release; nothing is written without a code environment. The 1.x line is frozen at 1.22.1, and 1.x libraries are not migrated.

Removed and incompatible
- kb-incremental is removed with its references and scripts (convert, clean, meta, assemble, card_check, index_tool, package, batch_plan, prep, consolidate, archive_plan), the life preset and examples/sample-life-kb. kb-ingest takes its place.
- Libraries are schema 2. A _kb.json of schema 1 is refused with a message saying it is a 1.x library (kbconf validate reports it, load_library raises, install.py and the skills stop on it); 1.x libraries keep working with the 1.x release. The 1.x keys (convert, intake, sources, delivery, inbox, sensitivity, metadata), the 1.x run files, _kb-params.md, the summary files beyond the status card and the quick-notes folder are gone.
- tools/kb-client: the client-run intake (intake.py), automatic intake (auto.py), the batch continuation and progress line, and the File material, Continue intake, File quick notes, Health check and Archive old versions buttons are removed, with /api/intake, /api/auto, /api/progress and /api/chat/task. Saved windows lose their kind and task; an intake window saved by an earlier version is dropped.

Library and settings (shared/scripts/kbconf.py)
- _kb.json accepts and checks tier (weak or strong), batch_chars (1000 or more), quote_min (1 or more) and quote_max (not below quote_min); names gain cards_dir (Cards) and topics_dir (Topics).
- topics() reads the topics of the spec's Table A (partitions from topic_start on, the semicolon list after the colon) and match_topic() compares them without regard to case and spacing; entities() reads the rows of Table E.
- A new library holds _kb.json (with tier), the spec, the status card and the folders Sources, Cards, Topics and Archive. The work preset's spec (Tables A, B, C, E, F; folders and names, cards and evidence, scope) and status card are written for 2.0, in English and Chinese.

doc2kb and batch files
- tools/doc2kb --kb-batch writes the documents into batch files `<source folder>_YYYYMMDD_b01.md`, ... (a second run on the same day adds the time). Each starts with a source table; sources are numbered S01, S02, ... over the run, oldest document first, each a section `# Snn <file name>`; paragraphs and list items end with an anchor `^snn-pN`, a table has one on the line below it. A batch holds at most `--batch-chars`, else the tier's limit (`--tier weak` 20,000, `strong` 100,000 characters), else `batch_chars` and `tier` from the `_kb.json` of `--library`, else weak. A longer document is cut at headings into parts that keep its number (`· 1/3`); a single paragraph or table over the limit is a batch of its own and is named in the output and the report. No pictures are exported. Date filter, duplicate removal and `--fp-db` work as in merged mode.
- tools/doc2kb/doc2kb.sh: the options dialog has "KB batch files", which asks for the tier. The doc2kb README lists quote_check.py.
- shared/scripts/kb_batch.py holds the batch file format; `split` joins each source's parts back into one file, restores heading levels and rewrites `^snn-pN` to `^pN` (a source with a part missing is not written); sources_table reads a batch file's source table.

Quote check (shared/scripts/quote_check.py)
- `check` takes cards (one JSON object per line: source, anchor, quote, conclusion, topic, entities, optional entity_types and event_date) and the run's batch files. A card passes when its quote has 6 to 300 characters (`--quote-min`, `--quote-max`) and occurs in its anchor's paragraph, list item or table, ignoring white space, full- and half-width punctuation and Markdown emphasis; a quote found in exactly one other paragraph of the source passes with its anchor corrected. With `--topics`, a known topic matches without regard to case and spacing and takes the list's spelling, and unknown topics pass and are listed as new. Repeated cards are dropped; each card gets the source's last-modified time as its date. Accepted cards go to a JSON lines file, rejected ones with their reason to the report; exit code 3 when any was rejected.
- `write` puts the accepted cards into one Markdown file per source (`--names` as for kb_batch.py split, `--lang en|zh`), with the quote linked as `[[Sources/<source>#^pN]]` and the topic as `[[Topics/<page>|<topic>]]`, entities as wiki links. A restored card may cite another source file than its cards file's and says it is from an earlier version. page_name() gives a topic's page file name; read_cards() reads a cards file back.

Filing a run (shared/scripts/ingest.py)
- `file` splits a run's batch files back into Sources/<original name>.md (two sources of the run with the same name get their parent folder's name in front), writes the accepted cards to Cards/, and moves a source already in the library, with its cards file, to Archive/Sources and Archive/Cards as <name>_old<YYYYMMDDHHMMSS>.md; a run with a part missing writes nothing. `--replaces NEW=OLD` archives OLD like a same-named version (a pair naming a source outside the run or the library writes nothing); `--restore` keeps the cards the owner restored. It marks status-card items citing an archived source for review, once, and prints the sources written, the files archived, the topics touched, the restored cards and the items marked. `--target` writes to a staging folder instead of the library.
- `pages` rebuilds Topics/<topic>.md from every cards file, newest first by event date or the source's date, for the topics named or all; a page says it is generated, and a topic left without cards keeps a page saying so. `check-page` checks a model-written topic page against the topic's current cards (exit 3 with unknown and missing links) and with --write puts a page that passes into the topics folder.
- `topics` prints the spec's topics; `add-topic` appends confirmed topics to a partition of Table A (partitions.fallback by default), raising the spec's version one minor step for the lot with one revision line per topic; `retopic` changes accepted cards' topic.
- `entities` merges the cards' entity names with Table E (names and aliases, without regard to case and spacing) and lists the other names with the suggested type, card count and closest table names; `--apply [--map]` rewrites the cards with the table's names and adds new rows and aliases to Table E with one version step and a revision line each.
- `versions` lists library sources that may be older versions of a run's sources under another name: close names once dates, version marks and punctuation are dropped (equal, or difflib ratio 0.8 or more) and at least half of the shorter source's paragraphs shared; same-named sources are listed apart; `--known` takes a Drive listing and marks names not yet staged.
- `conflicts` compares the cards of each source a run replaces with the new version and the run's cards and lists not_carried, changed and removed cards with ids.
- `status-check` compares a rewritten status card with the current one (removed, changed, lost links, added; exit 3); `--write` puts only a clean rewrite in place, and `--write --confirmed` a rewrite the owner accepted.
- `note` writes the batch file of a one-source run from a quick note.
- `pending write` puts a run's decisions to be made into <library>/_pending/<run>.json, `pending read` checks the owner's <run>.decisions.json and turns it into topics to add or merge, --replaces pairs, an entity map and a restore file, and `pending done` removes both; check_decisions() checks decisions for the client.
- ingest.py, quote_check.py, kb_batch.py and kbconf.py are copied into all three skills; references/extract.md and pages-strong.md live in shared/references and are copied into kb-ingest and kb-note.

kb-ingest
- Ingests a run's batch files into a 2.0 library: the library and its tier are chosen; batch files are used as given or made with doc2kb where commands run; cards are written one source at a time (weak tier) or one batch at a time (strong tier, references/extract.md) and checked with quote_check.py, rejected ones rewritten once; new topics of both quote-check reports are put to the user and merged (retopic) or added to the spec (add-topic); new entities (step 5) and new versions (step 6: weak tier, the owner picks the script's candidates; strong tier, the model judges each pair quoting both documents) are listed, and conflicts (step 7) with the status-card items to be marked; one preview is confirmed; ingest.py file files the run; topic pages are built by ingest.py pages (weak tier) or written by the model and checked by check-page (strong tier, references/pages-strong.md, which asks for one statement per card and covers restored cards; a page failing twice is built by the script).
- For a local library the decisions are written to the pending file before the preview. A library in Google Drive is worked on a staging folder (with the status card) and written back after the confirmation; the Drive procedure passes the sources listing to versions. A hard rule keeps status-card rewrites behind status-check.
- Init mode (references/init.md, scripts/init_library.py and pick_materials.py) sets up a library from the work preset: two questions (folder, scope) and the tier found out (strong for Claude and ChatGPT clients, weak for OpenCode and local models), shown in the preview. init_library.py takes --tier and drops --sensitivity, --convert and --sources. The skill's description takes the setup phrases; step 0 offers init mode when there is no registry.

kb-query
- Rewritten for 2.0: answers come from the status card, topic pages, cards and sources (spec tables for terms, entities and open issues); every fact is followed by a quote line with the exact source sentence and its link.
- Weak tier: scripts/answer.py select lists the cards and status-card items the keywords point to (Table E aliases expand an entity, a topic name brings its cards; best 12; among equals the newer event date, then the newer source, first; source paragraphs as a fallback, marked not on a card), and answer.py check verifies each quote line against its linked paragraph before the reply.
- A status-card item marked for review, or a missing one, is answered from the cards and sources and then proposed; it is written only after the user confirms, through ingest.py status-check --write --confirmed. The 1.x reading table, quick-note fallback, originals and sensitivity rules are gone.

kb-note
- A note becomes a source on the spot ("Note <YYYYMMDD-HHMM> <title>", written by ingest.py note); its cards are checked and filed and the topic pages rebuilt; the user is asked only about new topics or entities. Writing needs Python; without it the note is shown in the reply.

All skills
- No write without a code environment, for every skill and backend: each skill's hard rules say so in the same words; init does not write a library by hand, and references/backend-local.md and environment.md have no by-hand ways of writing. kb-query and kb-note have a Hard rules section.
- ChatGPT versions: each skill has prompt.md (at most 8000 characters, the same version, every hard rule of SKILL.md word for word; scripts/check_repo.py checks all three). scripts/build_skill.py --chatgpt builds <skill>-<version>-chatgpt.zip (<skill>-prompt.md and <skill>-files.zip, the skill folder as it is, which the prompt has ChatGPT unpack in its Python tool); the release workflow attaches them.
- shared/references: config.md describes the 2.0 library files and _kb.json, the review mark, the rewrite check and _pending among the ignored files; backend-local.md and backend-gdrive.md describe writing an ingest run (local: straight into the library after the confirmation; Drive: from the staging folder); environment.md names ingest.py.

tools/kb-client
- Build batch files (a step under Material) runs doc2kb on a material folder into a new or empty folder outside every library (default ~/kb-batches/<material>_<date>), with the chosen library's tier, and offers Copy path and Ingest these.
- Waiting for confirmation shows the pending ingest runs of local libraries as forms (new topics, new entities, version pairs, conflicts; GET and POST /api/pending), writes the checked decisions next to the pending file and says in the conversation that they are saved; it also lists status-card items marked for review, each with Ask.
- Quick note stays, and material is ingested by asking in the conversation. The write lock is held by management steps only; while one runs, requests to change a library or run kb-ingest's or kb-note's scripts show a card. The stage bar follows the 2.0 scripts (Convert, Check quotes, File, Topic pages).

Installer, examples and documentation
- install.py installs kb-note, kb-query and kb-ingest, with no preset question and no --preset; a new library's tier follows the agent (weak for OpenCode, strong for the others) and is item 7 of the preview. kb_manage.py: move no longer checks for an unfinished batch intake; backups and skill lists name kb-ingest. Plugin manifests, build_skill.py, sync_shared.py, check_repo.py (the work preset and the sample library must validate) and locales/zh name kb-ingest.
- examples/sample-work-kb: a fictional work library (tier weak) built from three mails in examples/sample-materials with the cards in examples/sample-work-cards.jsonl; tests/test_examples.py checks that the scripts make exactly this library. examples/new-material holds a mail to try an ingest run with.
- README and README.zh-CN rewritten (why the design is this way, ChatGPT, the library layout, a "Coming from 1.x" section, backends, compatibility with the end-to-end result, tools); docs/methodology.md rewritten and docs/methodology.zh-CN.md added; docs/backends.md and docs/manual-setup describe 2.0; docs/design-2.0.md holds the design and is marked implemented.

## 1.22.1

Upgrading the knowledge-base skills from the browser client is a step of its own and asks no setup questions, and a repository check is fixed. The skills are unchanged.
- tools/kb-client Upgrade runs the new step skill_upgrade (install.upgrade) instead of Set up. It replaces each knowledge-base skill in the folder where OpenCode reads it (a missing one goes to OpenCode's own folder) without asking which agent, whether to install or whether to replace, after a backup. With a usable library (a registered local library whose folder exists, or one that is not a local folder) the libraries stay as they are and the knowledge-base line is refreshed in the instructions file OpenCode reads, after one question when it changes; without one the library questions of Set up follow. The step holds the write lock and restarts OpenCode when it ends. Set up and install.py are unchanged.
- tools/kb-client Skills: Upgrade is greyed out while an intake run, a task window or a step holds the write lock; its tooltip names what it waits for and, for intake, that automatic intake can be switched off first. A refused step unfolds the knowledge base and shows the server's reason instead of a generic message.
- install.py: a skill is copied next to the installed one first (.NAME.new) and swapped in afterwards, so a failed copy leaves the installed skill as it was.
- tests/test_sensitive_scan.py: the temporary repositories leave out the git variables that point at another repository (GIT_INDEX_FILE, GIT_DIR and the like). `git commit -a` passes its own index to the pre-commit hook, and the tests wrote into it, so the commit failed with "invalid object".

## 1.22.0

The browser client keeps several conversation windows, and the tasks that write the libraries run one at a time. The skills are unchanged.
- tools/kb-client windows: a row of tabs above the conversation, one OpenCode conversation each (agent.Window), at most eight plus the intake's own window. POST /api/chat/open (a new window, or with --chat-first an earlier conversation, in the window that has it or a new one), /api/chat/close (a working window only with stop), /api/chat/focus; send, new, stop, allow_all and terminal take win, GET /api/chat/state?win= shows one window, and the conversation events carry win. A "windows" event lists the windows (kind chat, task or intake, title from OpenCode, status, cards waiting, Allow everything) and the write lock. The windows and the current one are kept in kb-client.json (windows, current; with --chat-first windows_by_dir per work folder, which takes over the earlier sessions entry) and come back after a restart; a background tab marks work, waiting cards and new replies. /api/chat/switch is replaced by open. Simple mode keeps one window.
- tools/kb-client write lock: an intake run (manual or automatic), a task window while the assistant works there or a card waits, and Set up, Roll back, Move and Uninstall exclude one another (409 locked); Back up, the graph and the conversations in other windows do not. Health check, Archive old versions, File quick notes and the skill's batch continuation go through POST /api/chat/task (task, library, text, win), each in a task window; a later message in a task window takes the lock again. While one window holds the lock, requests from the others that edit files in a library, run kb-incremental's or kb-note's scripts or run a command naming those folders show a card, whatever Allow everything says (agent.touches); reading and read-only commands are answered as before.
- tools/kb-client intake: a run talks in the intake window instead of the current conversation, so the other windows stay usable and the run no longer switches back at the end (intake.Run takes win instead of back_to). A run from the page takes Allow everything from the window it was started in; an automatic run switches it on in the intake window only and starts once no write task holds the lock, without waiting for the other windows.
- Allow everything is per window.
- tools/kb-client: on a wide screen the left column folds into a narrow strip (« at its top right; the strip, labelled Skills or Knowledge base, unfolds it), so the conversation takes its width; the page stays at most 1440px wide. The browser remembers it, apart for --chat-first, and it starts unfolded; unfolding the knowledge base unfolds the column too. Narrow screens are unchanged.

## 1.21.0

The browser client files a library's material by itself, unattended, and offers an upgrade of the knowledge-base skills only when it has a newer version. The skills are unchanged.
- tools/kb-client automatic intake (new auto.py, local libraries): a switch under each library (POST /api/auto) makes a drop folder at the library's top (_Inbox, or _待入库 in Chinese) with a Not-filed subfolder. The client looks every minute, takes a file once it has not changed for two minutes, and starts an intake run (the files, then the consolidation queue) when OpenCode is idle with no card waiting and nothing else runs, starting OpenCode when needed. Allow everything is on for the run's length only; switching it off stops the run. Each finished file leaves the drop folder: removed when its original was copied into the library's sources folder or it was already in the library, moved to Filed/ when written without such a copy, moved to Not-filed/ when it needs a person or failed. A stopped run pauses the library until a new file comes; with nothing new, a non-empty consolidation queue gets a consolidation-only run until one ends without emptying it. The library card shows the drop folder, waiting files, the last run and the files in Not-filed; switches and last runs are kept in <state dir>/auto-intake.json. The client does not stop for being idle while a library has automatic intake on. intake.Run takes hooks (item_done, ended), reports auto in its snapshot and kept (the original's copy is in the library) for written items.
- tools/kb-client Skills: the knowledge-base skills no longer offer Change and Restore; Upgrade is greyed out while the installed version is the same as or newer than the one this client comes with (/api/skills reports it as release).
- tools/kb-client graph: folders whose names start with an underscore are left out, as the skills leave them out of searches.

## 1.20.2

The browser client files material without masking it and, with Allow everything on, goes on from the files to the end of consolidation without anybody answering.
- tools/kb-client intake: the assistant is asked for term fixes only, and told to do no masking or redaction: the body stays as it is. A library's own sensitivity setting is unchanged.
- tools/kb-client intake: after the files, the run consolidates the library's queue, one round of references/consolidate.md per new conversation, until the queue is empty (or it did not get shorter in two rounds in a row, or as many rounds as the queue had files plus two are used). With Allow everything on, the round is unattended (Accept all) and question cards during the run are answered with their recommended option (agent.answer_recommended); otherwise the round asks as usual, and a card waiting for a person does not count against the turn's time limit. The run's snapshot has a consolidation section; Stop and Continue cover it. The panel shows the round and says that the run takes long, with how to use OpenCode from a terminal meanwhile; Open in a terminal is refused (409) during a run.
- kb-incremental consolidation step 5: an unattended request takes Accept all without asking and notes it in the readme.

## 1.20.1

The browser client no longer locks the knowledge-base skills, keeps an intake going when it stops in the middle, and writes logs.
- tools/kb-client: the knowledge-base skills are no longer locked. Requests on their folders follow the usual rules (a read-only command or one of their scripts is answered by the client, a change shows a card, Allow everything allows it), and the Skills section offers Change and Restore for them too, beside Upgrade, which now says that it replaces the folder. The lock refused read-only commands such as ls on a skill folder and script runs it could not recognise, which stopped intakes. agent.locked_target, skills_admin.locked_folders and the "locked" event are removed; /api/skills reports kb instead of locked.
- tools/kb-client intake: each run works in <state dir>/intake/<run>/ instead of the client's temporary folder, which is emptied when the client stops, and saves its state there (intake-run.json) after every change; a client started again shows an interrupted run as stopped, and Continue intake files the rest. The client does not stop for being idle while a run is going, stops cleanly on SIGTERM, and goes back to the conversation that was open before the run when it ends (and at start, after an interrupted run). The assistant is told to stop when the body file is missing instead of scanning the original again. Finished runs' folders are removed after seven days.
- tools/kb-client logs: <state dir>/logs/kb-client-YYYYMMDD.log (kept seven days, owner only) with OpenCode's start, restarts and stops, every permission request and its answer, steps and why the client stopped; each intake run writes intake.log with the scripts, exit codes and output tails, the assistant's turns, the decisions and the names written (never a file's text). Manage and the intake panel show where they are.

## 1.20.0

The browser client files material itself, so that a file counts as filed only once it is in the library, and says plainly whether the knowledge-base skills are installed.
- tools/kb-client File material (new intake.py, local libraries): the client runs kb-incremental's scripts for each chosen file (prep.py scan, prep.py file, package.py preview --run and deliver) and asks the assistant, in a new conversation per file, only for masking, term fixes, the head file and a decision file (partition, topic, type, short title, close-read), which it checks and asks again for up to three times. A file name already in the index goes back to the assistant (next version or another title). Duplicates by content hash are skipped; files no text can be read from are listed for the user. POST /api/intake (library and paths, or resume), POST /api/intake/stop, GET /api/intake; progress as "intake" events in the conversation stream; the conversation is refused (409) while a run is going. Google Drive libraries are filed by the assistant as before.
- kbconf.tzinfo (all skills): on Python 3.8, which has no zoneinfo, a library's IANA time zone that is this computer's own (TZ, /etc/localtime, /etc/timezone) uses the current local offset, and the UTC names are UTC. Setup writes the system zone, so on 3.8 every prep.py file and package.py run of such a library stopped with "needs Python 3.9+" and nothing could be filed. Other names still ask for a fixed offset.
- tools/kb-client intake: a script refusal that no answer can fix (refused: from prep.py file) fails the file at once with the reason; a file that fails after three answers names the last reason.
- tools/kb-client task buttons: File material and Quick note with a line each; Continue intake only while files are left, File quick notes only while notes wait (libraries report their count as notes), Health check and Archive old versions under More. The buttons stay visible with the knowledge base folded.
- tools/kb-client knowledge-base skills: one rule for the status chip and Getting started, the three skills in the folders OpenCode reads (/api/state kb_skills: found with folder and version, missing, folders checked). The chip is always shown and opens the details, with Install them when one is missing. The skill lists reload after Set up, Uninstall and Roll back, which left them out of date until the page was reloaded.

## 1.19.0

The browser client folds the knowledge base the same way with or without --chat-first, keeps a skill list beside the conversation and formats the assistant's answers.
- tools/kb-client: the Knowledge base button sits beside the title as a filled button and is shown in every mode. Folded, the page fills the window: a read-only skill list (one line per skill in use, opened for the description and trigger phrases, knowledge-base skills first, scrolling in its column, a filter past eight skills) and the conversation. Unfolded, the libraries, Manage, the Skills section and the step panel come back; with --simple the read-only list stays in place of the Skills section. The page starts unfolded, folded with --chat-first; the browser remembers each apart.
- tools/kb-client: the assistant's answers are shown as Markdown (headings, lists, quotes, tables, rules, inline code, bold, italic, web links), built as DOM nodes so that nothing in an answer runs. Fenced code has a Copy button and colours for Python, shell, JavaScript, JSON, YAML, SQL and diff. The user's messages stay plain text.
- tools/kb-client: larger text in the conversation (16px, code 14px), a page up to 1440px wide and a four-line input box.

## 1.18.0

The browser client can open as a front end for OpenCode, with the knowledge base folded away.
- tools/kb-client --chat-first: the page opens on the conversation; the libraries, Manage, Skills, the task buttons, the stage bar, the ideas and the knowledge-base items of Getting started fold under a Knowledge base button (remembered by the browser). Above the conversation: the work folder (chosen with the folder browser, the last five remembered; never the root, the home folder, a folder holding it or a system folder; agent.check_workdir), a model list (GET /config/providers, sent with the message as model; for the current conversation) and Earlier conversations (GET /session, the work folder's main conversations, newest first; POST /api/chat/sessions and /api/chat/switch). Choosing a folder starts OpenCode there and picks up that folder's last conversation (POST /api/chat/workdir). Reads and edits inside the work folder are answered by the client (places["edit"] in agent.decide); commands other than read-only ones and anything outside it still ask, and locked skill folders stay refused. An edit step carries its diff (metadata.diff, shown up to 400 lines under Show the change). kb-client.json keeps the work folder, the recent ones and each folder's last conversation.
- tools/kb-client --simple: the welcome text no longer names Roll back, Move and Uninstall.
- tools/kb-client: Allow everything (conversation header, and Allow everything on this page on each card; POST /api/chat/allow_all). After one confirmation the client answers every request itself, including the cards already waiting, until it is switched off or the client quits; kept in memory only, so it outlasts reloading the page and New conversation but not a restart. Changes to the knowledge-base skills are still refused.

## 1.17.0

The browser client runs skill scripts written over several lines, and has a simpler version for groups of users.
- tools/kb-client --simple: Roll back, Move, Uninstall, the Skills section and Clear for remembered answers are hidden, and the client refuses those steps and requests with 403 (kb_client.SIMPLE_REFUSED); Set up, Back up, the graph and the conversation stay. /api/state reports simple.
- tools/kb-client: a skill script command written over several lines with backslashes, or ending in 2>&1 or 2>/dev/null, counts as the skill's own script (agent.plain_command): it is answered by the client like the one-line form and is no longer refused as a change to a locked skill folder. Any other shell syntax still goes to the user, and to the lock check.

## 1.16.0

Intake is fast by default: each file is written into the library as soon as it is placed, and reconciling it with the summary files waits for consolidation, reviewed change by change. The browser client shows the ideas behind the knowledge base, has a new look, and lists and manages skills, with the knowledge-base skills locked.
- kb-incremental fast intake (new references/fast.md): with _kb.json intake.mode fast (new setting; also when it is missing) each item goes through conversion, cleanup, term fixes and masking, placement, the duplicate and version check, assembly and delivery on its own, with one progress line per file, and is searchable at once. Step 3 (key conclusions) and step 5 (triggers) wait for consolidation. One confirmation at the start covers every delivery of the run. intake.mode full, or "full intake" in a request, keeps the previous per-item process.
- kb-incremental consolidation (new mode, "consolidate"; new references/consolidate.md): works through the consolidation queue in rounds of intake.consolidate_files (default 10). Close-read files get their key conclusions written into the head of the filed topic file; every file is checked against the status card with quotes as before; the proposed changes to the status card, change log and open items are listed by number and the user accepts all, leaves some out or cancels the round. Rewrites pass card_check before delivery; a filled topic file's previous copy moves to the archive folder.
- New consolidation queue (names.consolidation_queue, default _Consolidation-Queue.md): a Markdown table in the library root (file, source file, filed time, close-read), kept in Google Drive libraries too. Never searched or used as a source. kb-query, kb-note and kb-incremental remind once per conversation while it holds files (config.md, section 5); kb-query says when a basis file is not consolidated yet. The health check reports its length and age.
- New scripts/prep.py: scan runs the duplicate check, conversion, cleanup, date and term search for one item and prints one card; file builds the name, stops on a file-name hit until the version is decided, assembles the topic file (with the pending mark for close-read items), updates the index and queue copies and prepares the item's delivery folder.
- New scripts/consolidate.py: list the queue by filed time, fill a pending topic file with a new head while keeping its body byte for byte (refuses a missing mark, a dropped original line or a changed body), done removes rows from a work-folder copy of the queue.
- package.py preview, remote-preview and deliver take --run: within one fast-intake run the file index and the queue are archived once and replaced after that, and the readme and run log are one file per run. The queue file is the one underscore name delivery accepts.
- Batch mode in fast intake delivers each file inside a batch on its own; the final step offers consolidation.
- tools/kb-client: the stage bar places prep.py and consolidate.py.
- tools/kb-client ideas: the welcome area shows the ideas behind the knowledge base as cards that turn every eight seconds (Previous, Next, More, Pause; held while pointed at or focused; still under reduced motion); a one-line version sits under the stage bar during an intake.
- tools/kb-client look: a blue-grey colour scheme for light and dark themes with system fonts only (sans for text, monospace for paths, logs and tool steps), larger line height, message bubbles by role, tool steps as compact grey lines, cards and questions with an accent bar, a tick on finished stages; on narrow screens the side column follows the work area.
- tools/kb-client Skills section (new skills_admin.py, GET /api/skills, steps skill_backup, skill_restore, skill_import, skill_new): lists every skill OpenCode reads with version, description and trigger phrases, marking a shadowed copy; Try it fills the box. The knowledge-base skills are locked: Upgrade runs Set up, and the assistant's requests to change their folders are refused without a card (agent.locked_target). Other skills: Change backs the folder up to ~/.config/evergreen-wiki/skill-backups and prepares an edit request with guidance; Restore puts a backup back; Import copies a skill from a folder or a checked zip (no paths outside it, no links, at most 500 files and 20 MB, no overwriting, nothing run); New skill writes a SKILL.md from a template and prepares the request to complete it.
- tools/kb-client: fewer permission cards. Read-only commands (ls, cat, head, tail, wc, stat, file, du, grep, rg, find without -exec, -delete and the like, pwd, echo, test) joined by ; && || or |, with at most 2>/dev/null and only the variables HOME, USER, KB_LIBRARIES and PWD, are answered by the client when every path lies in the readable places (agent.read_only_command). Full paths of existing files and folders written in a message count as the conversation's material (read only). Always allow answers are kept in kb-client.json and answered by the client after OpenCode or the client starts again; a remembered command pattern covers only a plain command, never one joined to another. Manage shows how many are remembered, with Clear (POST /api/chat/forget), which forgets them and restarts OpenCode.
- tools/kb-client: a shorter page. A step that finished well folds to its title and result line; Getting started folds once when Set up completes what it was missing. When a turn ends, each answer folds its steps into one line with counts by kind and failures, also for subagents and for a conversation picked up again; the conversation's height follows the window.

## 1.15.0

The browser client continues a batch intake across conversations and guides first use; queries read only the passages that answer; scripts take over the mechanical parts of placing an item.
- tools/kb-client: a batch intake continues across conversations. When the last batch script step was done and nothing waits, the page starts a new conversation with Continue intake after a three-second countdown (Cancel stops it); after Stop, an error, or an automatic round that filed no batch, a Continue intake button does it. The material of a run still open (the sources of its progress file) is allowed for reading in every conversation. Simple mode turns File material and Continue intake off.
- tools/kb-client: a Getting started card at the top of the page lists OpenCode found, OpenCode started, the skills where OpenCode reads them, a library, the knowledge-base line in OpenCode's instructions, and pdftotext (optional), each with what to do; with the first five done it offers three example requests that fill the box without sending. It can be hidden (remembered in the browser). The task buttons are off until a library exists. A missing model in OpenCode's settings no longer keeps the conversation off: OpenCode is started and the model shows as a warning. Check again (POST /api/chat/recheck) looks for OpenCode again as at start and starts it, or starts it anew after it stopped or fell back to simple mode (agent.Agent.retry), without restarting the client. GET /api/state adds opencode_skills, instructions and pdftotext.
- install.py: the library and registration previews take their answer through confirm(); kb-client asks it as choices (Write, Change an item first and then which, Cancel), the terminal as before.
- kb-query reads only what answers in a local library: new scripts/kbfind.py (read-only; kbconf.py is now copied into kb-query too). find prints the blocks of the root-level files that hold the keywords (a list item, a table row with its header row, a paragraph, the front matter) with their headings and line numbers, skipping the same files the skills never use as a source; toc lists a file's sections with line ranges and sizes. The status card and other summary files are read by their matching blocks and sections, whole only under 8000 characters, without a match, or when the question is about the whole file; source material is read by its matching passages, whole only when the question needs the whole document. Google Drive libraries and environments without Python are unchanged.
- kb-incremental: new scripts/meta.py (read-only) for the mechanical parts of placing an item: name builds the topic file name and checks it against the Table D limit; date reads the document date from the document's own metadata (else the file system time, marked unreliable) in the library's time zone; entities looks wording up among the Table E names and aliases, drops Table F empty-value forms and quoted noise values, and lists near names as possible aliases, leaving the rest to the assistant; terms lists the body lines holding a Table B original wording; yaml writes front matter from a JSON object. Without Python, or when the spec's tables cannot be read, the steps are done by hand as before. kb-client's stage bar places meta.py's steps.
- kb-incremental batch intake (batches.md): a stop for a long conversation comes right after a batch's done and progress line.

## 1.14.0

Easier start and a visible intake in the browser client, fewer tokens in a large intake, and originals kept in local libraries.
- Originals in the library (local libraries with direct delivery): new _kb.json setting sources {keep, max_mb} and names.sources_dir (default Sources). With keep on, assemble.py --source copies each filed original into the sources folder under its topic file's name with its own extension and adds original: "[[Sources/<file>]]" to YAML front matter; originals larger than max_mb (default 50) or missing are not copied and listed in the readme. package.py preview and deliver carry the sources folder and archive the originals of a topic file's old version with it (also under another extension, or when the new version has no original); zip and the Drive preview refuse the folder. New work libraries start with keep on, life libraries off (originals bypass masking); init_library.py and install.py ask with --sources on|off. The sources folder is never searched or used as a source; kb-query opens a linked original only for what the text lacks. Hard rule 15 and the user wording add originals; the material stays where it is. Existing libraries are unchanged (keep is off when the key is missing). kb-client's graph shows kept originals as their own kind.
- kb-incremental conversion: converted text longer than convert.outline_chars (new setting, default 6000; 0 turns it off) also gets an outline (size, opening text, headings with line numbers), read first. The full text, or the sections concerned, is read for close-reading material, where a status-card search hits or a trigger may apply, where the outline does not settle placement or version, and for pictures. Files handled from their outline are searched for every Table E name and alias and for the subjects of the status-card items; term fixes are found by search in the body file. The topic file still holds the whole text. The delivery note counts files handled from their outline. Library files keep their format: no migration; claude.ai users get this by uploading the new skill packages.
- kb-incremental: the head file of a topic file holds everything before the body, including section labels set by params.
- kb-incremental: topic files are assembled by script (scripts/assemble.py: the head with metadata and key conclusions, one blank line, then the cleaned body file as it is), so the body is never typed out again; clean.py writes the body file, and masking and term fixes are made in it in place. Refuses an existing output file, an empty body and unclosed front matter.
- kb-incremental batch intake: within one conversation, the spec, summary files, params, _kb.json and references read for the first batch are not read again for later batches (every summary rewrite waits for the final step); the file index is copied to the work folder again for every batch and read by index_tool.
- tools/kb-client: Set up chooses OpenCode beforehand (install.py wizard and choose_dest: agent_default, which only changes the default answer); when Set up has finished, the client restarts the OpenCode it started (after the current work when the assistant is busy), so the conversation uses the new skills and instructions line without restarting the client. The page says so while OpenCode restarts.
- tools/kb-client: a skill script whose quoted arguments hold shell characters, such as batch_plan.py add --text "Projects: Atlas (new topic; a.docx)", is allowed without a card; outside quotes the rule is unchanged, and a double-quoted argument with $, a backquote or a backslash still goes to the user.
- All three skills (shared environment.md): scripts are run by their full path in the skill's folder or as cd <skill folder> && python3 scripts/<name>.py, one command per call, with text arguments in quotes.
- tools/kb-client: Graph under each local library draws the links between its Markdown files on the page (GET /api/graph: entities, summary files, documents and links without a page; the skills' ignored files and the spec's example links left out; at most 2000 files), drawn with plain JavaScript and SVG, nothing loaded from elsewhere. Files changed since the client started have a ring and can be shown alone with their neighbours; a click lists a file's links both ways. The graph says that Obsidian, opened on the library folder, shows a fuller graph and backlinks, with the folder and a Copy path button. The line at the end of a batch intake opens it.
- tools/kb-client: intake shows a stage bar (take stock, convert, duplicates and names, clean up, compare conclusions, file, wrap up) taken from the skill script being run (tool steps carry a fixed script name, agent.stage_script), each stage with one line on why and more on a click; a progress line from the run's progress file (GET /api/progress: counts and group names, no paths); a result line per finished batch and one at the end of the run; the client's own answers counted on one foldable line.
- tools/kb-client: a work folder of the client's own (in the system temporary folder, removed when the client stops) is named in the task buttons' requests and allowed for writing like a library; plain mkdir [-p] and cp [-p|-r|-R] within the allowed places (sources readable, target writable, no wildcards or ~) are answered by the client too.
- All three skills (shared environment.md): a work folder named in the request ("Work folder: <path>", "工作文件夹：<路径>") is used as the work folder.
- tools/desktop-setup removed: tools/kb-client does the same steps in a page in the browser, double-clicked from kb-client.desktop at the top of the folder. READMEs and the download guide point there.
- tools/kb-client: the local server no longer looks up the host name of 127.0.0.1 when it starts, which could hold the page back for a DNS timeout on some systems.

## 1.13.0

Knowledge base client in the browser: the management steps and a conversation with OpenCode on one page.
- kb-client.desktop at the top of the folder: the same double-click entry as tools/kb-client/kb-client.desktop, so the client starts from the top folder of the unzipped release.
- tools/kb-client: permission cards add Always allow when OpenCode names what it would stop asking for (the request's always patterns, listed on the card); the client passes the reply "always" to OpenCode, which remembers it as in a terminal. POST /api/chat/permission takes reply once, always or reject (allow true or false still works).
- tools/kb-client: a conversation with OpenCode on the page. The client starts `opencode serve` on 127.0.0.1 in the home folder when the page opens (waiting up to --start-timeout, default 90 seconds, and showing what OpenCode prints meanwhile), keeps one current conversation (picked up again when the page or the client is reopened; New conversation starts another; the id is kept in ~/.config/evergreen-wiki/kb-client.json) and passes its replies, tool steps, questions and permission requests to the page; Stop aborts the current work, and Quit or the idle stop ends OpenCode too. Buttons send the skills' phrases: File material (choose the library, then tick files and folders in the folder browser, which now selects several), Quick note, File quick notes, Health check, Archive old versions, Continue intake. Every action of that OpenCode is set to ask (OPENCODE_CONFIG_CONTENT, that process only); the client answers "allow once" itself for reading and writing inside a registered local library, reading the material chosen in the conversation, the skills and the agent settings, and running a skill's own script with no other shell syntax, and notes each such answer; everything else is a card with Allow this once and Deny. Without OpenCode's server interface the conversation runs `opencode run` once per message (simple mode, no permissions or questions on the page). Checked against OpenCode 1.19. Subagents' sessions are followed too: their steps appear indented on the page, and their permission requests and questions are answered like the main conversation's (sending the explore subagent is allowed without asking). Reasoning and the working notes before a step are folded into one line each; a message sent while the assistant works waits as queued. Open in a terminal opens the same conversation in OpenCode's own interface in a new terminal window. OpenCode is looked for with --opencode (or KB_CLIENT_OPENCODE), on PATH, in common install folders and through the interactive shell, which finds an opencode that ~/.bashrc defines as a function or alias; such a one is run through bash -ic. Set up in the client suggests a work library (install.py wizard: preset_default).
- tools/kb-client: the installer and install.py backup, rollback, move and uninstall as a page in the browser, served by a local Python server (standard library only) and started by double-clicking kb-client.desktop on a Linux desktop. The page lists the registered libraries, the agents that have the skills and whether OpenCode has a model set. Each step runs the installer's own ask, yes and choose calls, so the questions, previews and checks are the same; what a step prints is streamed to the page above its question. Folder questions open a folder browser that only lists folders, inside the home folder and the mounted drives (other folders can be typed); a folder in the answer that does not exist yet opens at its nearest existing parent with the new folder's name kept. The server listens on 127.0.0.1 only, refuses requests without the token in the address it opens or with another host name, runs one step at a time and stops when no page has been open for a while. English and Chinese. Talking to the agent from the page comes later.
- install.py wizard: a library folder that is the root, the home folder or a folder holding it, or that holds this program, the install record, the skills or the instructions files is refused with the reason and asked again, both for a new library and for registering an existing one (the same rule move and uninstall already follow, now kb_manage.is_protected).

## 1.12.0

Library folder and material folder kept apart.
- All three skills (shared config.md, section 3): the folder holding the filed knowledge base and the folder holding the user's original files are named to the user as "library folder" and "material folder" (知识库文件夹, 资料文件夹), each with a short explanation; registry, root and backend are not said to the user outside the init preview. Material outside the library folder is normal and is read where it is; a library's folder changes only on an explicit request to move it. A fixed two-option question for when it is unclear which folder the user means.
- kb-incremental: hard rule 15 on the two folders; init mode and the folder chooser treat a folder of original files as material, never as a library, and ask for an empty folder for a new library.
- No folder is chosen for the user. install.py, tools/desktop-setup and init mode no longer suggest ~/kb/<id>: the desktop asks with a chooser that opens in the home folder (in the current answer when changing it in the preview), the terminal asks until a path is typed, and the skills ask without suggesting a path where no chooser can open.
- Material from anywhere, chosen anew each time: pick_materials.py selects several folders or files at once and always opens in the home folder (--library-root and the <library>-待整理 / -inbox start folder are gone). install.py move and uninstall act on the library folder only; folders of original files next to it are neither moved nor deleted.
- Batch intake: plan --append adds new material to an open run (after the pending batches, or before them with --front), leaving out files already in the run; skip --rest ends a run; next --index marks a batch started, says when a batch was interrupted, leaves out files filed before the interruption, and exits 4 without marking anything when every file of the batch is missing (a disconnected drive). batches.md: a three-way choice when new material meets an open run, and how to resume an interrupted batch.
- Reminder of an unfinished intake (config.md, section 4): all three skills check the library for an open run and ask once per conversation whether to continue, do it later or end it; the instructions line also asks for this at the start of a conversation.
- README (English and Chinese): a section on how the pieces fit together (skills, library folders, registry, instructions line), what each release download is for and which path to take in which situation; a quick-start path for a Linux desktop without a terminal.
- Every release's notes end with the same download guide (docs/release-downloads.md, version filled in).

## 1.11.0

Existing libraries and preset answers in the installer.
- install.py wizard: a folder that already holds a library (_kb.json or a 00_ spec file) is registered as it is after a preview (folder, label from its _kb.json, id, scope), without changing a file; the user then says "init <label>" to complete its settings. Answering 1 at the preview chooses another folder. A folder with only loose Markdown is still refused.
- install.py: --descriptions FILE installs the skills with descriptions from a file in the shape of locales/*/descriptions.json (checked: one line of at most 1024 characters per skill); --agent and --preset life|work answer those wizard questions in advance. tools/desktop-setup takes the same three options for Set up.

## 1.10.0

The installer in dialogs.
- tools/desktop-setup: a menu with zenity dialogs for the installer and install.py backup, rollback, move and uninstall, started by double-clicking evergreen-wiki-setup.desktop on a Linux desktop. It puts dialogs behind the installer's own ask, yes and choose calls, so the questions, previews and checks are the same; text a step prints appears in the next dialog. Folder questions offer the suggested folder or a folder chooser. Without zenity or a graphical session it asks in the terminal. English and Chinese.
- install.py: the question asker can be replaced (wizard(asker, lang)); folder questions are marked so a dialog asker can show a folder chooser.

## 1.9.0

Backup, rollback, moving a library and uninstall in the installer.
- install.py backup, rollback, move and uninstall (kb_manage.py): backup copies the installed skills, the instructions files holding the knowledge-base line, the registry and the install record; rollback restores one and backs up the present state first; move copies a registered local library and its material folder, compares every file (size and SHA-256) and only then points the registry to the new place, refusing while a batch intake is unfinished; uninstall removes the skills, the line, the registry, the install record and the backups, and deletes a library folder only when it is picked and the confirmation word typed. Messages in English and Chinese. Details in docs/manual-setup.md, section 6.
- The installer records where it wrote (~/.config/evergreen-wiki/state.json) and backs up the present state before it replaces skills, adds to a registry or writes the knowledge-base line.
- README: offline installation from the release zip.
- kb-incremental: the description lists "finish intake" (「结束入库」) with the other intake phrases, so the request starts the skill on its own.

## 1.8.0

Filing a large folder in batches.
- kb-incremental: intake of files or folders on disk first runs the new scripts/batch_plan.py, which lists the material per first-level subfolder (count, size, types), leaves out files already in the library by content hash, identical copies, archives and types intake cannot read, and cuts the rest into batches: one per subfolder, a large one split in file name order, loose files as one more. A batch closes at intake.batch_files files or intake.batch_mb megabytes (new _kb.json key, defaults 10 and 20). One batch: intake runs as before.
- With more than one batch the user sees the plan and starts the run once; the batches are then filed and delivered in turn without further questions, with one progress line each. Step 5 and the spec rewrite for new topics and entities wait for one final step, which rewrites the summary files once (with the usual preview) and lists every item to review. Questions that would stop a batch take the conservative rule and go on the review list. Process in references/batches.md.
- Progress is kept in the library root (names.batch_plan, default _intake-batches.json; underscore names are never sources) and moved to the archive folder when the run is finished. "Continue intake" picks up an open run in a new conversation; "finish intake" runs the final step early.
- The local backend's preview rule counts the start of a batch run as the confirmation for its batch deliveries.

## 1.7.0

Choosing the library folder on the desktop.
- kb-incremental: when a local library folder is needed and the user has not named one (no registry or no library in it while the user asks for intake or setup, or question 1 of init mode), scripts/pick_materials.py --library opens a folder chooser instead of asking for the path in words. A folder with _kb.json or a spec goes to the existing-library branch, an empty one to the new-library branch; the init preview and "confirm" still come before anything is written. Without a dialog, on cancel or timeout the assistant asks for the path as before. Process in references/pick-material.md; references/config.md, references/init.md and step 0 point to it.
- The material chooser takes --library-root and opens in the material folder next to the library (<library>-待整理 or <library>-inbox) when one exists, else in the home folder.

## 1.6.0

doc2kb reads archives and parses identical files once; clearer skill descriptions.
- Skill descriptions (English and Chinese) say in plain words what each skill does for the user, with example requests: kb-incremental lists what intake, archive, health check, init and quick-note filing each do; kb-query says each fact names its source file and what happens when nothing is found; kb-note says it only creates new files and reminds the user to file notes that pile up. Every trigger phrase is kept.
- Documents inside .zip and .tar (.tar.gz, .tar.bz2, .tar.xz) archives, and archives inside them up to 3 levels, are converted as if the archive were a folder; their paths read pack.zip/a/report.docx in the scan, index and report and work with --only and incremental tasks. An archive can be named directly. Members are unpacked into a private temporary folder that is removed when the run ends; member paths cannot leave it, and size limits (512 MB per member, 2 GB per archive) stop runaway archives. Encrypted members, damaged archives and .7z/.rar are listed as failed with the reason. GBK zip names are decoded.
- Files with identical bytes (archive members included) are parsed once, before the text comparison: the copy whose output exists is kept first, then one outside any archive, then the first path. They are listed with the text duplicates in the report and the kept copy's note; -D turns both off.

## 1.5.0

Picking material on the desktop, and a general default scope for work libraries.
- kb-incremental: when the user asks for intake without naming a path, uploading files or pasting text, and the library is a local folder, the new scripts/pick_materials.py asks whether to file a folder or files and opens the matching desktop chooser (zenity; files can be selected several at once). Without a graphical session or zenity, on cancel or after --timeout seconds it exits with a code that tells the assistant to ask for the path instead. Process in references/pick-material.md. A named path or an upload never opens the picker.
- The suggested scope of a new work library is "work goals and plans, projects and tasks, meetings and decisions, policies and procedures, reports" (Chinese: 工作目标与计划、项目与事务、会议与决策、制度流程、报表等工作资料), in line with the 1.4.0 partitions. The installer and the manual-setup examples use the same wording. Existing libraries keep their scope.

## 1.4.0

A general-purpose work preset, in English and Chinese.
- Work preset partitions suit any kind of office work: 02 Goals and plans, 03 Projects and tasks, 04 Proposals and deliverables, 05 Meetings and decisions, 06 Policies and procedures, 07 Organisation and roles, 08 Data and reports, 09 Reference and templates (fallback).
- Entity types are project, department or team, organisation, system or product, other; the front-matter entity field is entities (entities_note) instead of systems. The close-reading list, the five trigger classes and the issue categories use general wording. The spec says that entities accumulate as material is filed.
- A preset may carry translated text files in <preset>/<language>/; init_library.py and install.py use them for a library in that language and fall back to the English files. The work preset has a Chinese translation (zh/): spec, params and summary files, with YAML keys and file names unchanged.
- Existing libraries keep their own spec; only new libraries get the new preset.

## 1.3.0

Uploads are converted to Markdown before intake.
- kb-incremental: when _kb.json has convert.enabled, Check 1 first runs the new scripts/convert.py on the uploaded files and reads the converted text instead of the Word, Excel, PowerPoint, PDF or mail file, which saves tokens and time. A file the converter cannot handle well (conversion failed, a PDF with little text per page, a document that is mostly pictures) is read as the original; pictures, plain text and legacy formats are read as before. The step-4 hash still uses the original upload. Process in references/convert.md.
- Pictures inside converted files become placeholder lines. Up to convert.image_limit pictures per batch (default 10) are read and written into the text; above it the user decides once for the batch, and unread pictures are counted as issues.
- New _kb.json key convert (enabled, image_limit, min_pdf_chars_per_page, min_chars_per_image), validated by kbconf. Both presets turn it on, so new libraries start with it; libraries without the key keep reading originals. Init mode and install.py show it in the preview, and init_library.py takes --convert on|off.
- New tools/doc2kb: the converter as a stand-alone tool (desktop dialogs, incremental cron mode, duplicate clean-up). Output labels and messages in English or Chinese (--lang, DOC2KB_LANG or the locale). Releases attach doc2kb-<version>.zip.
- The converter lives in shared/scripts/doc2kb_core.py; sync_shared.py now copies shared files into tools as well as skills.
- Converter behaviour: English picture references ("shown below", "see figure") count as describing a picture; batch runs print machine-readable STAT lines, which doc2kb.sh reads instead of matching messages; doc2kb.sh exits 3 on a first run without a time range; mail dates count as reliable in the date-filter list.

## 1.2.0

Fewer manual steps with Google Drive.
- Drive libraries are delivered directly: after a preview and "confirm", the assistant moves each old version to the archive folder and writes the new files with the Drive connector. No zip to download, unpack and upload, and no separate "archive" step. New package.py subcommands remote-preview and remote-log plan the moves and write the run log. Libraries with an inbox entry (their own unpack script), or delivery set to zip, keep the zip.
- The registry can live in Drive (kb-libraries.json in the first library's folder), kept up to date by init mode. claude.ai Project instructions need one line pointing to it, pasted once; later libraries need no pasting. A registry pasted as JSON still works.
- Health checks no longer report kb-libraries.json as a stray file.

## 1.1.0

Guided first-time setup.
- install.py without options starts an interactive installer: language, agent (detected), install, then three questions (kind of library, folder, scope), a preview, and it writes the library, registers it and adds or updates the instructions line after showing it. Existing options are unchanged.
- New scripts/init_library.py in kb-incremental: the one definition of a new library (suggested label, id, scope, timezone and language; files and folders; registry entry; instructions line; a block to paste into claude.ai Project instructions). Init mode and the installer both use it.
- Init mode has a getting-started guide ("get started with the knowledge base", 「开始使用知识库」): it looks at the environment first, asks three questions instead of five plus the partition table, and shows everything else in the preview.
- kb-query and kb-note offer setup once when no registry exists, instead of only saying nothing is set up.
- README quick start rewritten as two short paths (terminal, claude.ai); the manual steps moved to docs/manual-setup.md and docs/manual-setup.zh-CN.md.

## 1.0.0

First public version.
- kb-note, kb-query, kb-incremental in English, with no library, folder ID or person built in.
- Registry (kb-libraries.json) and per-library _kb.json / _kb-params.md replace hard-coded libraries; any number of libraries.
- Two backends: Google Drive (zip delivery and archive mode) and local folder (direct delivery with automatic archiving).
- Every file and folder name configurable, so existing libraries in other languages keep their names.
- Work and life presets; fictional sample library.
- Scripts: kbconf.py (new), package.py (replaces package.sh, adds local delivery), clean, index_tool, card_check, archive_plan made language-neutral; Python 3.8+, standard library only.
- Chinese trigger-phrase builds (--locale zh); Claude Code plugin manifest; install.py for other agents.
- Health check no longer reports the inbox configuration file named in _kb.json inbox.config as a stray file.
- index_tool refuses to edit an index inside a library root; spaces become hyphens in file names; setup proposes an instructions line so the assistant knows the libraries exist; run logs use the neutral prefix _run-log_.
