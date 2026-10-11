# Health check: report on the library

Trigger: "health check", "check the knowledge base". Monthly is a good rhythm. Check and report only; change nothing. Each fix is a suggestion the user decides on, then handled by intake or archive mode. Files whose topic is not in Table A are reported, never expanded.

## Scope

Files created or modified in the last 30 days by default. "All" checks everything; for a large library warn first that it takes a while.

## Checks

1. Stray files in the root: names containing old_suffix, starting with snapshot_prefix or an underscore, and files that are not .md. Expected and not reported: _kb.json, _kb-params.md, the registry file kb-libraries.json (Drive libraries), and the inbox configuration file named in _kb.json inbox.config (if any).
2. Same-name copies (Drive only): look up each name in scope exactly; list any with two or more copies and suggest archive mode.
3. Table E and entity pages: list the entities folder and compare with Table E names. List entities without a page and pages without an entity.
4. Format (YAML mode): read the start of each topic file in scope. Does it start with front matter; are required fields present; are dates ISO; do entity fields hold wording outside Table E (list wording and file); are partition and topic in Table A (report only).
5. Suspicious dates: a year-month in the file name more than two months later than the document or event date.
6. Basis lines in summary files: count status-card entries whose basis is not a link (count only); list every link whose target is missing from the file index (broken link).
7. Core entity overviews: sources cited that are not in the index; an overview older than the newest related material in the index (may be stale).
8. Index consistency: index rows with no file in the root, and files in scope missing from the index.
9. Settings: _kb.json passes python3 scripts/kbconf.py validate <root>; partitions.max and topic_start match Table A; metadata matches the spec; partitions.fallback is a partition in Table A; _kb-params.md exists. List current and expected values.
10. Possible duplicate entities (YAML mode): compare all Table E names and aliases in pairs for names that may mean one thing: translations, abbreviations and full names, short names, differences in case, hyphens or spaces, alternative spellings. Give each group a reason and a confidence (high: only the naming differs; medium: likely the same, depends on context; low: unsure). Different types are usually not grouped. Skip pairs the spec records as confirmed different. Suggest keeping one name and moving the others to aliases, for the user to decide; if the user says they differ, suggest recording that in the spec so it is not reported again.
11. Quick-note backlog: if the notes folder exists, count its .md files (not the filed subfolder) and the oldest creation date. Over 20 notes or older than 14 days: suggest filing them.

## Output (fixed structure)

Date, library, scope
1. Stray files: N (each)
2. Same-name copies: N
3. Table E and entity pages: N
4. Format problems: N
5. Suspicious dates: N
6. Basis lines: N not linked, N broken (each broken one)
7. Overviews possibly stale: N
8. Index mismatches: N
9. Settings: consistent / N mismatches (each)
10. Possible duplicate entities: N groups (each: name A, name B; reason; confidence)
11. Quick-note backlog: no notes folder / N notes, oldest YYYY-MM-DD
Suggested actions: three to five, by priority, each naming the mode that handles it.

When a check finds many items, count first and sample; over 20 in one check, list the first 20 and give the total.
