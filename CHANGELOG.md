# Changelog

All three skills share one version number. To release, update this file, the "Version:" line of every SKILL.md and the plugin manifests together and merge to main; the release workflow then publishes v<version>.

## Unreleased

- tools/kb-client: a batch intake continues across conversations. When the last batch script step was done and nothing waits, the page starts a new conversation with Continue intake after a three-second countdown (Cancel stops it); after Stop, an error, or an automatic round that filed no batch, a Continue intake button does it. The material of a run still open (the sources of its progress file) is allowed for reading in every conversation. Simple mode turns File material and Continue intake off.
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
