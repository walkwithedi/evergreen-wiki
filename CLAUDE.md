# Working on evergreen-wiki

This repository is public: code, history, commit e-mails, issues, pull requests and Actions logs can be read by anyone. CONTRIBUTING.md has the general rules; these are the ones an assistant must follow on top of them.

## Keeping private data out

- Never add personal data, details of anyone's workplace (organisation, host, system, project or people names, internal paths and addresses, business figures) or credentials. Examples use obviously fictional names (Riverside Clinic, Project Atlas), example.com addresses and the documentation IP ranges.
- Write rules and behaviour, not stories: README files, skill text, code comments, the changelog, commit messages and pull request descriptions say what something does and why in general terms. No accounts of where a rule came from, what happened to whom, or the environment a tool was built for, and no figures taken from real documents.
- scripts/sensitive_scan.py runs before every commit and push (.claude/hooks/pre_commit.py, .githooks) and in CI. When it blocks a commit or push, stop and report the findings to the user. Do not reword, delete or move the text to get past the check, and do not add the marker sensitive-scan: ignore unless the user confirms the line is harmless and agrees to the marker. Private-term findings cannot be allowed with the marker.
- When you notice something that looks private but the scan did not catch (a name, a system, a figure), report it to the user before doing anything else with it.
- The private-terms list (SENSITIVE_TERMS secret, ~/.config/evergreen-wiki/sensitive_terms.txt) never enters the repository, and its terms are never quoted in commits, issues or pull requests.

## Design before code

- Any task that changes files or has side effects (commits, pushes, pull requests, remote settings) starts with a design: the goal, the files to change, the approach and trade-offs considered, and how the result will be verified. A small change needs only a few lines.
- The user approves the design before any code is written: through the plan-mode approval when the session is in plan mode, otherwise by asking with AskUserQuestion.
- If the work needs to depart from the approved design (wider scope, a different approach), stop and ask again instead of widening the change.
- Questions and read-only investigation need no design.
- .claude/settings.json sets permissions.defaultMode to plan, so sessions start in plan mode and cannot edit files until a design is approved.
