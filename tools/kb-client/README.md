# Knowledge base client: the installer in the browser

A page in the browser, served from your own computer, for people who do not use a terminal: install the skills, set up a library and tell the agent it exists, then back up, roll back, move a library or uninstall. The page lists the registered libraries, which agents have the skills and whether OpenCode is ready. The questions, previews and safety checks are those of `install.py` and `install.py backup|rollback|move|uninstall`; this tool only shows them on the page, so both behave the same.

This first version covers setting up and managing libraries. Talking to the agent from the page comes in a later version; until then, open the agent as usual.

[中文说明](README.zh-CN.md)

## Files

| File | What it is |
| --- | --- |
| `kb_client.py` | the local server: runs the installer's steps and passes their questions to the page |
| `web/` | the page (`index.html`, `app.js`, `style.css`); plain HTML, JavaScript and CSS, nothing loaded from the network |
| `kb-client.desktop` | double-click entry; opens a terminal window that runs `kb_client.py` and the page in the default browser |

## Requirements

- Linux desktop, Python 3.8 or newer (standard library only), the whole evergreen-wiki folder: the tool runs `install.py` and the skills two folders up.
- A browser with current JavaScript (`fetch`, `EventSource`), such as a recent Firefox or Chromium.

No network is needed. On a computer without one, copy evergreen-wiki-v<version>.zip from [Releases](https://github.com/walkwithedi/evergreen-wiki/releases), unzip it and start the tool from `tools/kb-client/`.

## Use

1. Double-click `kb-client.desktop` (Knowledge base). The first time, the desktop may ask whether to trust or run it; choose to trust and launch. If double-clicking opens the file as text, open a terminal in this folder and run `python3 kb_client.py`. The page opens in the default browser; the terminal window shows its address.
2. On the left, choose a step:
   - Set up: choose the agent, install the three skills, set up a library (kind, folder, scope; a preview comes before anything is written) and write the knowledge-base line into the agent's instructions file. A folder that already holds a library is registered as it is. Run it again to add another library.
   - Back up, Roll back, Uninstall: as `install.py backup`, `rollback` and `uninstall` (docs/manual-setup.md, section 6).
   - Move a library, or Move next to a library: pick the folder to move it into; then the move preview and confirmation of `install.py move`.
3. What a step prints appears above its question. Folder questions have a Browse button that opens a folder browser: start from the home folder or a mounted drive, open folders, and choose one. When the suggested folder does not exist yet, the browser opens at its nearest existing parent and keeps the rest of the path as the new folder's name, so choosing there answers with the suggested folder; clear the name to answer with the folder itself.
4. Cancel this step stops the step at its current question; what was finished stays. Quit stops the client. Closing the page also stops it after a while (`--idle`).

Typed folders that are not absolute are taken from the home folder.

Options: `--lang en|zh` (default: the system language), `--port N` (default: a free port), `--no-browser` (print the address only), `--idle SECONDS` (stop when no page has been open that long and no step is running; 0 never; default 120), `--log-level`. For Set up, `--agent <target>` and `--preset life|work` answer those questions in advance and `--descriptions <file>` replaces the skill descriptions, as with `install.py`; a wrapper script or a copy of the .desktop entry can fix them for a group of users.

## Safety

- The server listens on 127.0.0.1 only. The address it opens carries a random token; requests without it, or with another host name, are refused, so other pages in the browser cannot use the server.
- One step runs at a time. The folder browser only lists folders and file names; the client itself writes nothing outside what the installer's steps write after their confirmation.

## Checking on a desktop

The unit tests answer the questions over HTTP the way the page does. On a real desktop, check after a change:

1. Double-clicking the entry opens a terminal window and the page in the default browser.
2. Set up: the folder browser opens at the suggested place (or its nearest existing parent with the new folder's name filled in), lists mounted drives, and its answer appears in the question; the preview is readable before the confirmation.
3. Move: after the move the page lists the library at its new place, and the agent finds it there after a restart.
4. Uninstall: no library folder is deleted unless picked and the confirmation word typed.
5. Cancel this step stops the step without changing anything further; Quit stops the client and the terminal window closes.
