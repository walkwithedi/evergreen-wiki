# Changelog

All three skills share one version number. To release, update this file, the "Version:" line of every SKILL.md and the plugin manifests together and merge to main; the release workflow then publishes v<version>.

## Unreleased

doc2kb reads archives and parses identical files once.
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
