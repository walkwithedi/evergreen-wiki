# Changelog

All three skills share one version number. Tag a release as v<version> after updating this file and the "Version:" line of every SKILL.md, the plugin manifests and this file together.

## 1.0.0

First public version.
- kb-note, kb-query, kb-incremental rewritten in English from a private Chinese toolkit, with no library, folder ID or person built in.
- Registry (kb-libraries.json) and per-library _kb.json / _kb-params.md replace hard-coded libraries; any number of libraries.
- Two backends: Google Drive (zip delivery and archive mode) and local folder (direct delivery with automatic archiving).
- Every file and folder name configurable, so existing libraries in other languages keep their names.
- Work and life presets; fictional sample library.
- Scripts: kbconf.py (new), package.py (replaces package.sh, adds local delivery), clean, index_tool, card_check, archive_plan made language-neutral; Python 3.8+, standard library only.
- Chinese trigger-phrase builds (--locale zh); Claude Code plugin manifest; install.py for other agents.
- From end-to-end testing in Claude Code: index_tool refuses to edit an index inside a library root; spaces become hyphens in file names; setup proposes an instructions line so the assistant knows the libraries exist; run logs use the neutral prefix _run-log_.
