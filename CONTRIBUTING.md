# Contributing

Thanks for helping. A few rules keep the skills reliable:

0. Run `git config core.hooksPath .githooks` once after cloning. The pre-commit hook then runs scripts/run_checks.py (unit tests, repository checks, shared copies, personal-data scan) and stops a commit that fails any of them. Claude Code sessions run the same checks through .claude/settings.json: a baseline when a cloud session starts, and before every git commit Claude makes. CI runs them again on every pull request, and CodeQL (.github/workflows/codeql.yml) scans the Python scripts and workflows for bugs and security problems; findings show on the pull request and under Security > Code scanning.

1. Edit shared files only under shared/, then run python3 scripts/sync_shared.py. CI fails when a copy is stale.
2. Keep environment-specific tool names and paths in the backend and environment references; SKILL.md and other references use the abstract operations. scripts/check_repo.py enforces this.
3. Scripts use only the Python standard library, run on Python 3.8+, log to stderr in the format used by the other scripts and accept --log-level.
4. Never hard-code a library file or folder name in a script; take it from kbconf names.
5. Changing a rule in a SKILL.md changes behaviour for every user. Explain the failure it prevents in the pull request, and add a test where a script is involved.
6. No personal data, ever: run python3 scripts/sensitive_scan.py. Examples use obviously fictional names (Riverside Clinic, Project Atlas).
7. Releases: bump "Version:" in all three SKILL.md files and both plugin manifests and add a CHANGELOG section headed with the version, in one pull request. Merging it to main publishes v<version> (.github/workflows/release.yml creates the tag and the release); Actions > release > Run workflow does the same by hand.

Bug reports are most useful with the library's _kb.json (without folder IDs), the request you made and the reply you got.
