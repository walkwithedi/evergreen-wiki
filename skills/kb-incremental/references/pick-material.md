# Picking material (local libraries)

When the user asks for intake without naming a path, uploading files or pasting text (SKILL.md, Check 1) and the library is a local folder, run:

  python3 scripts/pick_materials.py --language <library language> --timeout 100

It asks whether to file a folder or files and opens the matching chooser on the user's desktop. Give the command a time limit above --timeout. Exit codes:
- 0: each output line is a chosen path. A folder means every file in it, subfolders included; files inside the library root are never material. Go on with Check 1 for these paths.
- 3: no dialog is possible here (no graphical session or no zenity). Ask the user for the path.
- 4: the user cancelled. Ask whether to go on, and for the path if so.
- 5: no answer in time. Ask the user for the path.

Never open the picker when the user named a path or uploaded files. Without Python, ask the user for the path.
