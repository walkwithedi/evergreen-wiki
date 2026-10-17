# Design: 3.0, offline and script-led

Status: implemented in 3.0.0. Each step below was its own pull request.

## 1. Scope

- 3.0 serves one setting: an offline Kylin workstation where OpenCode runs a privately deployed model. Libraries are local folders; every step that can be decided mechanically is done by a script.
- Everything outside that setting leaves the repository: the Google Drive backend, the ChatGPT versions of the skills, the strong tier, the Claude Code plugin manifests, and the code paths for Windows and macOS.
- 2.0.x stays available for Google Drive libraries and ChatGPT; no further 2.0.x releases are made. 1.x libraries are still not migrated.

## 2. Libraries

- The library format is unchanged: _kb.json stays schema 2, and a library made by 2.0 works in 3.0 without changes.
- tier is a 2.0 setting. 3.0 accepts it (weak or strong) and ignores it; topic pages are always built by ingest.py pages. When a library says strong, the skills say once that the pages are now built by the script.
- New libraries are written without tier. The batch size is batch_chars, default 20,000 characters.
- A registry entry of type gdrive is refused with a message naming 2.0.x; local is the only backend.

## 3. Skills

- kb-ingest: one procedure. Cards are written one source at a time; version candidates are listed for the user to pick; topic pages come from ingest.py pages. The staging-folder procedure for Drive and check-page are gone.
- kb-query: answer.py select gives the material and answer.py check checks every quote line before the reply. Without Python the assistant searches the library itself and writes nothing. kbfind.py is gone.
- kb-note: the note is filed and its topic pages rebuilt by the scripts.
- references: backend-local.md is the only backend file; pages-strong.md and backend-gdrive.md are gone. The registry is a file (KB_LIBRARIES or ~/.config/kb/kb-libraries.json) or a registry pasted into AGENTS.md.

## 4. Agent and platform

- OpenCode is the agent 3.0 is tested with. The installer offers the folders OpenCode reads: its own (~/.config/opencode/skills), ~/.agents/skills and ~/.claude/skills; other agents that read these folders may work but are not tested. The instructions line goes into OpenCode's AGENTS.md.
- Kylin only: the Windows registry and state locations, the Windows link handling and the macOS and Windows CI jobs are removed, and so are the platform checks in the tests. CI runs on Ubuntu, which stands in for Kylin, with Python 3.8, the version Kylin V10 ships. Handling of file names and archives made on other systems (GBK names, __MACOSX folders) stays, since material comes from anywhere.
- doc2kb no longer asks for a tier; --tier stays on the command line for older scripts and picks its limit (weak 20,000, strong 100,000 characters).

## 5. Steps

1. Trimming (this document, the removals of sections 2 to 4, tests).
2. The offline workbench: tools/opencode-setup (the OpenCode setup page and script) and tools/workbench (the three-step wizard that ends in kb-client). They use this repository's kb-client instead of a downloaded release. The hints on where a key is issued and how Node is switched are general and can be reworded in a local hints file (~/.config/opencode-setup/hints.conf) that is read, never run. Each release attaches workbench-bundle-<version>.zip, built by scripts/build_workbench.py from the repository zip: the workbench entry at the top and evergreen-wiki/ beside it. The ~/.bashrc block and the files under ~/.config/work-kb/ keep their names, so set-up workstations need nothing redone.
3. Documentation and the 3.0.0 release: README in both languages, methodology, backends and manual setup, the changelog.

Later, in their own designs: an evaluation set with a scoring script for the target models, Chinese-first skill text checked against that evaluation, and further load taken off the model (quotes filled in by script from an anchor and a sentence number, question keywords found by script).
