# workbench: OpenCode workbench wizard

[中文](README.zh-CN.md)

A ready-to-use offline workbench: [opencode-setup](../opencode-setup/README.md) (enter a personal API key, switch off opencode's start-up downloads, check a first start) and the [knowledge base client](../kb-client/README.md) behind one double-click. A page in the browser walks through three steps and then opens the client in its conversation-first form: talk to the assistant in a chosen work folder, switch models, go back to earlier conversations and see each change's diff, with the knowledge base folded away until needed. The wizard's pages are in Chinese.

## Files

| File | Role |
| --- | --- |
| `启动OpenCode工作台.desktop` | Double-click entry: opens a terminal running `wk_web.py` and the wizard in the default browser. The workbench bundle has the same entry at its top level; it can be sent to the desktop (see Use). |
| `wk_web.py` | Local server: steps 1 and 2 reuse `../opencode-setup/ca_web.py` and run `codeagent-setup.sh check` and `setup`; step 3 starts `../kb-client/kb_client.py` and hands its address to the page. Python 3 standard library only. |
| `web/` | The wizard page (`index.html`, `app.js`, `style.css`); nothing is loaded from the network. |

## Requirements

- As for opencode-setup: Kylin or Ubuntu, bash 4.4+, python3 3.8+, Node 22+, opencode installed, an existing OpenCode configuration.
- A browser with `fetch` and `EventSource` (a recent Firefox or Chromium).
- Optional: `pdftotext` (poppler-utils); without it PDFs are read whole, more slowly.
- No network access and no packages to install.

## Bundle

Download `workbench-bundle-<version>.zip` from Releases and unpack it on the workstation. Its top level holds the entry and an `evergreen-wiki/` folder (the same content as `evergreen-wiki-<version>.zip`):

```
启动OpenCode工作台.desktop   the entry (double-click it)
evergreen-wiki/              the skills, tools/workbench, tools/opencode-setup, tools/kb-client and the rest
```

Keep the layout inside `evergreen-wiki/` as it is. From a clone of the repository, double-click the entry in `tools/workbench/`. Other places can be given with `python3 wk_web.py --codeagent <folder> --wiki <repository folder>`.

## Use

1. Double-click `启动OpenCode工作台.desktop` at the top of the unpacked folder (trust it the first time), or run `python3 wk_web.py` in `tools/workbench`. The entry can be linked or copied to the desktop: it looks for the wizard in its own folder, in `evergreen-wiki/tools/workbench/` next to it and in the place the wizard records at each start (`~/.config/work-kb/location`).
2. Work through the three steps; a step's button is available once the one before is done:
   1. Check: Node version, opencode and the OpenCode configuration.
   2. Key and self-check: paste the key and set up, as opencode-setup does (test first, back up, switch off downloads, check a first start). The step is done once the marked block is in `~/.bashrc`. "Already configured, skip" records that OpenCode was set up another way. The hints on where to get a key and how to switch Node can be reworded locally (opencode-setup, Local hints).
   3. Open the workbench: choose the simple version (default; install and set up, back up, skills read-only) or the full one (also roll back, move, uninstall and manage skills), then open it. The client starts with `--chat-first`: a work folder chosen above the conversation (opencode runs there; commands and anything outside the folder still ask), models per conversation, up to eight conversation tabs, earlier conversations, diffs of each change, the skills list on the left, and the knowledge base under the button next to the title. The knowledge base is a local work library whose topic pages are built by scripts; ingest by asking in the conversation or through Build batch files, answer the decisions under Waiting for confirmation, and use Quick note to save a sentence. Libraries made by 1.x are not read.
3. Once steps 1 and 2 are done, a later start opens the workbench after a three-second countdown ("stay on this page" stops it).
4. The client runs on its own: it keeps working after the wizard stops, and stops by itself some time after its page is closed.

The wizard keeps its two choices in `~/.config/work-kb/state.json` and logs to `~/.config/work-kb/logs/wk-web-<date>.log` (owner only, kept 7 days).

## Versions

Released with evergreen-wiki under the repository's version; changes are in CHANGELOG.md.

- 3.0.0: moved into evergreen-wiki as `tools/workbench/`; it uses this repository's `tools/kb-client` and `tools/opencode-setup` instead of downloading a release, and each release attaches `workbench-bundle-<version>.zip`. The choices, location and logs under `~/.config/work-kb/` keep their paths.
