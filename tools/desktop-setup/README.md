# Desktop setup: the installer in dialogs

A menu and dialogs for the evergreen-wiki installer on a Linux desktop, for people who do not use a terminal: install the skills, set up a library and tell the agent it exists, then back up, roll back, move a library or uninstall. The questions, previews and safety checks are those of `install.py` and `install.py backup|rollback|move|uninstall`; this tool only shows them as dialogs, so both behave the same.

[中文说明](README.zh-CN.md)

## Files

| File | What it is |
| --- | --- |
| `desktop_setup.py` | the menu and the dialogs (zenity); without zenity or a graphical session it asks in the terminal |
| `evergreen-wiki-setup.desktop` | double-click entry; opens a terminal window that runs `desktop_setup.py` |

## Requirements

- Linux desktop, Python 3.8 or newer (standard library only), the whole evergreen-wiki folder: the tool runs `install.py` and the skills two folders up.
- `zenity` for the dialogs. Without it, or outside a graphical session, the same questions are asked in the terminal.

No network is needed. On a computer without one, copy evergreen-wiki-v<version>.zip from [Releases](https://github.com/walkwithedi/evergreen-wiki/releases), unzip it and start the tool from `tools/desktop-setup/`.

## Use

1. Double-click `evergreen-wiki-setup.desktop` (Knowledge base setup). The first time, the desktop may ask whether to trust or run it; choose to trust and launch. If double-clicking opens the file as text, open a terminal in this folder and run `python3 desktop_setup.py`.
2. Pick an item from the menu:
   - Set up: choose the agent, install the three skills, set up a library (kind, folder, scope; a preview comes before anything is written) and write the knowledge-base line into the agent's instructions file. A folder that already holds a library is registered as it is. Run it again to add another library.
   - Back up, Roll back, Uninstall: as `install.py backup`, `rollback` and `uninstall` (docs/manual-setup.md, section 6).
   - Move a library: pick a registered library and, in the folder chooser, the folder to move it into; then the move preview and confirmation of `install.py move`.
3. The menu comes back after each item; Quit or closing the menu ends the tool.

Folder questions offer the suggested folder or a folder chooser; cancelling the chooser goes back to that choice. Text printed by a step is shown in the next dialog, a long preview in a scrolling window first. Closing a list, text or folder dialog cancels the current item and closing a yes/no question answers no; what was finished stays.

Options: `--ui zenity|tty` (or `EVERGREEN_SETUP_UI`) forces dialogs or terminal questions, `--lang en|zh` the language (default: the system language), `--log-level`. For Set up, `--agent <target>` and `--preset life|work` answer those questions in advance and `--descriptions <file>` replaces the skill descriptions, as with `install.py`; a wrapper script or a copy of the .desktop entry can fix them for a group of users.

## Checking on a desktop

The unit tests answer the dialogs with a stand-in for zenity. On a real desktop, check after a change:

1. Double-clicking the entry opens a terminal window and the menu dialog; without zenity the menu is asked in that terminal.
2. Set up: the library folder question offers the suggested folder and a chooser; cancelling the chooser returns to the choice. The preview is readable before the confirmation, and the closing dialog lists what to try.
3. Move: the folder chooser opens, the preview shows both places, and the library is found at the new place by the agent after a restart.
4. Uninstall: no library folder is deleted unless picked and the confirmation word typed.
5. Closing a list or text dialog stops the current item without changing anything further.
