# Picking material or a library folder (local libraries)

scripts/pick_materials.py opens choosers on the user's desktop, so the user clicks instead of typing a path. It has two modes. Give the command a time limit above --timeout.

## Material

When the user asks for intake without naming a path, uploading files or pasting text (SKILL.md, Check 1) and the library is a local folder, run:

  python3 scripts/pick_materials.py --language <library language> --timeout 100

It asks whether to file folders or files and opens the matching chooser in the home folder; several folders or files can be selected at once. Nothing is preselected and nothing is remembered: material can come from anywhere and is chosen anew for every intake. To add material from another place in the same request, run it again and file all the paths together.
- 0: each output line is a chosen path. A folder means every file in it, subfolders included; files inside the library root are never material. Go on with Check 1 for these paths.
- 3: no dialog is possible here (no graphical session or no zenity). Ask the user for the path.
- 4: the user cancelled. Ask whether to go on, and for the path if so.
- 5: no answer in time. Ask the user for the path.

Never open the picker when the user named paths or uploaded files. Without Python, ask the user for the paths, without suggesting one.

## Library folder

When a local library folder is needed and the user has not named one: no registry or no library in it while the user asks for intake or setup (references/config.md), or question 1 of init mode for a local library (references/init.md). Run:

  python3 scripts/pick_materials.py --library --language <user language> --timeout 100

It opens one folder chooser in the home folder, with no folder preselected. Exit code 0 prints the chosen folder; 3, 4 and 5 mean the same as above: ask the user for the path in one sentence, without suggesting one (for 4, first ask whether to go on). To change the folder in the init preview, run it again with --start <the folder chosen so far>. Then look at the folder before going on:
- It holds _kb.json or a spec (a file starting with 00_ whose name contains Spec or 规范): an existing library. Init mode, existing-library branch.
- It is empty, or holds neither .md files nor original files: a new library there. Init mode, new-library branch, with this folder as the answer to question 1.
- It holds other Markdown files: say so and ask whether to choose another folder or treat it as an existing library.
- It holds original files (Office, PDF, pictures) but no _kb.json or spec: it is material, not a library folder. Say so in the words of references/config.md, section 3, and ask for an empty folder for the library; the original files can be filed from where they are later.
Choosing a folder writes nothing; the init preview and the user's "confirm" still come before any file is written.
