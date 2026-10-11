# Changelog

All three skills share one version number. Tag a release as v<version> after updating this file and the "Version:" line of every SKILL.md, the plugin manifests and this file together.

## Unreleased

Guided first-time setup.
- install.py without options starts an interactive installer: language, agent (detected), install, then three questions (kind of library, folder, scope), a preview, and it writes the library, registers it and adds or updates the instructions line after showing it. Existing options are unchanged.
- New scripts/init_library.py in kb-incremental: the one definition of a new library (suggested label, id, scope, timezone and language; files and folders; registry entry; instructions line; a block to paste into claude.ai Project instructions). Init mode and the installer both use it.
- Init mode has a getting-started guide ("get started with the knowledge base", 「开始使用知识库」): it looks at the environment first, asks three questions instead of five plus the partition table, and shows everything else in the preview.
- kb-query and kb-note offer setup once when no registry exists, instead of only saying nothing is set up.
- README quick start rewritten as two short paths (terminal, claude.ai); the manual steps moved to docs/manual-setup.md and docs/manual-setup.zh-CN.md.

## 1.0.0

First public version.
- kb-note, kb-query, kb-incremental rewritten in English from a private Chinese toolkit, with no library, folder ID or person built in.
- Registry (kb-libraries.json) and per-library _kb.json / _kb-params.md replace hard-coded libraries; any number of libraries.
- Two backends: Google Drive (zip delivery and archive mode) and local folder (direct delivery with automatic archiving).
- Every file and folder name configurable, so existing libraries in other languages keep their names.
- Work and life presets; fictional sample library.
- Scripts: kbconf.py (new), package.py (replaces package.sh, adds local delivery), clean, index_tool, card_check, archive_plan made language-neutral; Python 3.8+, standard library only.
- Chinese trigger-phrase builds (--locale zh); Claude Code plugin manifest; install.py for other agents.
- Health check no longer reports the inbox configuration file named in _kb.json inbox.config as a stray file (found in a read-only check against a real Drive library).
- From end-to-end testing in Claude Code: index_tool refuses to edit an index inside a library root; spaces become hyphens in file names; setup proposes an instructions line so the assistant knows the libraries exist; run logs use the neutral prefix _run-log_.
