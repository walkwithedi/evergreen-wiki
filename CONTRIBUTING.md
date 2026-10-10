# Contributing

Thanks for helping. A few rules keep the skills reliable:

1. Edit shared files only under shared/, then run python3 scripts/sync_shared.py. CI fails when a copy is stale.
2. Keep environment-specific tool names and paths in the backend and environment references; SKILL.md and other references use the abstract operations. scripts/check_repo.py enforces this.
3. Scripts use only the Python standard library, run on Python 3.8+, log to stderr in the format used by the other scripts and accept --log-level.
4. Never hard-code a library file or folder name in a script; take it from kbconf names.
5. Changing a rule in a SKILL.md changes behaviour for every user. Explain the failure it prevents in the pull request, and add a test where a script is involved.
6. No personal data, ever: run python3 scripts/sensitive_scan.py. Examples use obviously fictional names (Riverside Clinic, Project Atlas).
7. Releases: bump "Version:" in all three SKILL.md files and both plugin manifests, add a CHANGELOG section, then push a tag v<version>.

Bug reports are most useful with the library's _kb.json (without folder IDs), the request you made and the reply you got.
