# Knowledge base client: the knowledge base in the browser

A page in the browser, served from your own computer, for people who do not use a terminal: install the skills, set up a library and tell the agent it exists, back up, roll back, move a library or uninstall, and talk to OpenCode about the libraries: file material, take quick notes, run a health check, ask questions. The page lists the registered libraries, which agents have the skills and whether OpenCode is ready. The questions, previews and safety checks of the management steps are those of `install.py` and `install.py backup|rollback|move|uninstall`; the conversation uses the same skills, registry and OpenCode settings as OpenCode in a terminal, so both can be used side by side.

[中文说明](README.zh-CN.md)

## Files

| File | What it is |
| --- | --- |
| `kb_client.py` | the local server: runs the installer's steps and passes their questions to the page |
| `agent.py` | the conversation: starts `opencode serve` on 127.0.0.1, passes its events to the page and answers the permission requests the client may answer itself |
| `web/` | the page (`index.html`, `app.js`, `style.css`); plain HTML, JavaScript and CSS, nothing loaded from the network |
| `kb-client.desktop` | double-click entry; opens a terminal window that runs `kb_client.py` and the page in the default browser |

## Requirements

- Linux desktop, Python 3.8 or newer (standard library only), the whole evergreen-wiki folder: the tool runs `install.py` and the skills two folders up.
- A browser with current JavaScript (`fetch`, `EventSource`), such as a recent Firefox or Chromium.
- For the conversation: OpenCode with a model set up (checked with OpenCode 1.19). Without it the management steps work and the conversation says why it is off.

No network is needed. On a computer without one, copy evergreen-wiki-v<version>.zip from [Releases](https://github.com/walkwithedi/evergreen-wiki/releases), unzip it and start the tool from `tools/kb-client/`.

## Use

1. Double-click `kb-client.desktop` (Knowledge base). The first time, the desktop may ask whether to trust or run it; choose to trust and launch. If double-clicking opens the file as text, open a terminal in this folder and run `python3 kb_client.py`. The page opens in the default browser; the terminal window shows its address.
2. On the left, choose a step:
   - Set up: choose the agent, install the three skills, set up a library (kind, folder, scope; a preview comes before anything is written) and write the knowledge-base line into the agent's instructions file. A folder that already holds a library is registered as it is. Run it again to add another library.
   - Back up, Roll back, Uninstall: as `install.py backup`, `rollback` and `uninstall` (docs/manual-setup.md, section 6).
   - Move a library, or Move next to a library: pick the folder to move it into; then the move preview and confirmation of `install.py move`.
3. What a step prints appears above its question. Folder questions have a Browse button that opens a folder browser: start from the home folder or a mounted drive, open folders, and choose one. No folder is suggested: the browser opens in the home folder. When the folder already in the answer does not exist yet (changing the folder at the preview, for example), the browser opens at its nearest existing parent and keeps the rest of the path as the new folder's name, so choosing there answers with that folder; clear the name to answer with the folder itself.
4. Cancel this step stops the step at its current question; what was finished stays. Quit stops the client and the OpenCode it started. Closing the page also stops both after a while (`--idle`), unless the assistant is still working.

### Conversation

OpenCode is looked for, in this order: `--opencode <path>` (or `KB_CLIENT_OPENCODE`), the program search path, the common install folders (`~/.opencode/bin`, `~/.local/bin`, `~/bin`, `/usr/local/bin`, `~/.npm-global/bin`), and the interactive shell (`bash -ic`), which also finds an `opencode` that `~/.bashrc` defines as a function or alias; such an `opencode` is then always run through `bash -ic`, so what the function does first still happens. Hovering over the OpenCode label at the top shows what was found and how.

When the page opens, the client starts OpenCode in the background (`opencode serve`, listening on 127.0.0.1, in the home folder) and shows what OpenCode prints while it starts; starting can take a while, and the client waits up to `--start-timeout` seconds. Then:

- Type a question or request in the box at the bottom; Enter sends, Shift+Enter starts a new line. A message sent while the assistant works is shown as queued and handled after the current work. Stop ends the assistant's current work.
- The buttons above the conversation send the skills' own phrases: File material (choose the library, then tick any number of files and folders in the folder browser; the paths go with the request, so the skill does not open its own chooser), Quick note, File quick notes, Health check, Archive old versions, Continue intake. With more than one library the page asks which one.
- When the assistant asks a question with choices, it appears as a card with the choices; a confirmation it asks for in words is answered in the box.
- New conversation starts a clean one. The page keeps one current conversation; reopening the page or the client picks it up again. Earlier conversations stay in OpenCode and can be opened there.
- What the assistant does is shown as it happens: its steps one line each (reading a file, running a script), its reasoning and the working notes before a step folded into one grey line each (click to read), its answer as normal text. Work it hands to a subagent (OpenCode's own helpers, such as explore) appears indented under "Subagent", with the subagent's own steps, permission requests and questions.
- Open in a terminal opens the same conversation in OpenCode's own interface (`opencode --session=<id>`) in a new terminal window (the first found of x-terminal-emulator, mate-terminal, gnome-terminal, konsole, xterm), with the user's own OpenCode settings. While you continue there, the conversation on the page pauses; reload the page when you are back.

Permissions. Every action of the OpenCode the client starts is set to ask first (`OPENCODE_CONFIG_CONTENT`, for that process only; the user's OpenCode settings are not changed). The client answers "allow once" itself for: reading and changing files inside a registered local library; reading the material chosen for this conversation, the installed skills and the agent's own settings; sending a subagent that only looks things up (explore); running a script of an installed skill (`python3 <skill>/scripts/<name>.py ...`, optionally after one `cd <folder> &&`, with no other shell syntax). The same rules apply to a subagent's requests. Each such answer is noted in the conversation. Everything else appears as a card saying what the assistant wants to read, change or run, with Allow this once and Deny; there is no "always allow". Paths are compared as real paths, so a link out of a library is not allowed.

Simple mode. When OpenCode's server does not start in time or lacks the requests the client uses, the conversation runs `opencode run <message>` once per message instead and says so on the page; in this mode the assistant cannot ask for permission or ask questions on the page.

Typed folders that are not absolute are taken from the home folder.

Options: `--lang en|zh` (default: the system language), `--port N` (default: a free port), `--no-browser` (print the address only), `--idle SECONDS` (stop when no page has been open that long and no step is running; 0 never; default 120), `--start-timeout SECONDS` (wait that long for OpenCode to start; default 90), `--opencode PATH` (the OpenCode program to use), `--log-level`. For Set up, the kind of library suggested is work; `--agent <target>` and `--preset life|work` answer those questions in advance and `--descriptions <file>` replaces the skill descriptions, as with `install.py`; a wrapper script or a copy of the .desktop entry can fix them for a group of users.

## Safety

- The server listens on 127.0.0.1 only. The address it opens carries a random token; requests without it, or with another host name, are refused, so other pages in the browser cannot use the server.
- The page talks only to this server; the server talks to OpenCode. OpenCode's own server has no password: any program on this computer that finds its port can use it, as with OpenCode started in a terminal. It listens on 127.0.0.1 only, on a port chosen at start, and stops with the client.
- The client stores only the current conversation's id, in `~/.config/evergreen-wiki/kb-client.json`.
- One step runs at a time. The folder browser only lists folders and file names, and only inside the home folder and mounted drives (a folder elsewhere can still be typed into the answer); the page's own three files are the only files the server sends; the client itself writes nothing outside what the installer's steps write after their confirmation.

## Checking on a desktop

The unit tests answer the questions over HTTP the way the page does. On a real desktop, check after a change:

1. Double-clicking the entry opens a terminal window and the page in the default browser.
2. Set up: the folder browser opens in the home folder (when changing the folder at the preview, at the current answer or its nearest existing parent with the new folder's name filled in), lists mounted drives, and its answer appears in the question; the preview is readable before the confirmation.
3. Move: after the move the page lists the library at its new place, and the agent finds it there after a restart.
4. Uninstall: no library folder is deleted unless picked and the confirmation word typed.
5. Cancel this step stops the step without changing anything further; Quit stops the client and the terminal window closes.
6. Conversation: OpenCode starts and the page says it is ready (note how long it takes); a question about a library is answered from it.
7. File material: tick two folders; the request lists them, no other chooser opens, and the intake runs to its report without the terminal. Reading the material and writing the library ask nothing; an action outside them shows a card.
8. Reopening the page shows the same conversation; New conversation starts a clean one.
9. After Quit, no `opencode serve` process is left (`ps -ef | grep "opencode serve"`).
10. Double-clicking finds OpenCode also when it is set up only for terminals (in `~/.bashrc`); the label at the top says how it was found.
11. A subagent's steps appear indented while it works; explore is sent without a card.
12. Reasoning and working notes are folded; a message sent while the assistant works waits as queued.
13. Open in a terminal opens the same conversation in a terminal window.
14. Set up suggests a work library; after reopening the client, the skills and libraries are still listed.
