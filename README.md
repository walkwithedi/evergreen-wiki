# evergreen-wiki

An LLM-maintained knowledge base that stays current, cites its sources and is easy for an assistant to search. Three agent skills keep a folder of Markdown files in order, in Google Drive or on disk (an Obsidian vault works as is):

| Skill | You say | It does |
| --- | --- | --- |
| kb-note | "note this" | saves a piece of the conversation as a quick note, to be filed later |
| kb-incremental | "file these", "file my quick notes", "archive old versions", "health check", "set up a knowledge base" | sorts material into partitions, de-duplicates it, keeps one current version per document, updates the status card when facts change, checks the library's health |
| kb-query | any question the library may answer | searches the library first and answers with the file it came from, never from memory |

[中文说明](README.zh-CN.md)

## Why

A knowledge base an assistant maintains goes stale or drifts unless the rules are strict. These skills follow a few that hold up in daily use:

- One file name per document. A new version replaces the old one under the same name; the old one moves to the archive folder. Nothing is ever deleted.
- One status card per library holds the current answer to every recurring question, each line linked to its source. The assistant rewrites it only when new material actually contradicts it, and a script checks that no line was lost in the rewrite.
- Every judgement (duplicate, new version, change of fact) needs a quote as evidence; without one the skill takes the conservative choice.
- Partitions and topics come from the library's own spec, which grows when material does not fit, and tells you each time.
- Entities (people, systems, organisations) get their own pages with backlinks, readable in Obsidian.

The full reasoning is in [docs/methodology.md](docs/methodology.md).

## Quick start (5 minutes)

1. Install the skills.
   - Claude Code: `/plugin marketplace add walkwithedi/evergreen-wiki`, then `/plugin install evergreen-wiki@evergreen-wiki`.
   - claude.ai or the Claude apps: download kb-note, kb-query and kb-incremental zips from [Releases](../../releases) and upload each in Settings > Capabilities > Skills (Chinese trigger phrases: the -zh zips).
   - Codex, Gemini CLI, OpenCode and other agents that read Agent Skills: `python3 install.py --target agents` (or `--target gemini`, `opencode`, `codex`, `claude-code`, or `--dest <folder>`).
2. Create a library. Ask your assistant: "set up a new knowledge base". It asks where (a Drive folder or a local folder), which preset (work or life), language and timezone, shows you everything it will create, and writes it after you confirm.
3. Register your libraries (the assistant offers to do this at the end of setup). A registry is a small JSON file listing each library and what belongs in it:

   ```json
   {
     "schema": 1,
     "preferences": {"output": "markdown"},
     "libraries": [
       {"id": "life", "label": "Life", "scope": "me and my family: IDs, health, insurance, money, home",
        "backend": {"type": "local", "root": "~/Documents/life-kb"}},
       {"id": "work", "label": "Work", "scope": "team projects, decisions, owners, specs",
        "backend": {"type": "gdrive", "root": "<drive folder id>"}}
     ]
   }
   ```

   Put it in `~/.config/kb/kb-libraries.json` (or point `KB_LIBRARIES` at it). On claude.ai, paste it into your Project instructions, or build private zips that carry it: `python3 scripts/build_skill.py --config my-libraries.json` (never publish those).
4. Use it: "note this", "file these" with attachments, or just ask.

Try everything first on the fictional [sample library](examples/).

## How a library looks

```text
life-kb/
  _kb.json                 settings: language, timezone, names, sensitivity
  _kb-params.md            process parameters: what to close-read, what counts as a change
  00_Spec.md               partitions and topics, term fixes, thresholds, entities
  00_Status-Card.md        current facts, each linked to its source
  01_File-Index.md         every filed document with its source file and hash
  01_Open-Items.md         due dates and to-dos (life) or open decisions (work)
  01_Change-Log.md         how facts changed over time
  01_Glossary-Issues.md    term fixes, masking log, open issues
  02_Checkups_report_2026-annual.md
  ...
  Entities/                one page per person, organisation or system
  Archive/                 older versions and run logs
  Quick-Notes/             notes waiting to be filed
```

Every name is configurable in `_kb.json`, so an existing library in another language keeps its own file names.

## Backends

| | Google Drive | Local folder |
| --- | --- | --- |
| Works in | claude.ai and Claude apps with the Drive connector; other agents with a Drive MCP server | any agent with file access (Claude Code, Codex, Gemini CLI, OpenCode, Claude desktop with file access) |
| Delivery of filed material | one zip you upload, then "archive old versions" | written directly after you confirm a preview; old versions archived on the spot |
| Obsidian | via Google Drive for desktop sync | open the folder as a vault |

Details: [docs/backends.md](docs/backends.md).

## Compatibility

| Environment | Status |
| --- | --- |
| Claude Code, local backend | scripts covered by unit tests on Linux, macOS and Windows; end-to-end run with the sample library pending |
| claude.ai / Claude apps, Drive backend | the design this kit grew out of; English build not yet re-tested |
| Codex, Gemini CLI, OpenCode | not yet verified; reports welcome |

Scripts need Python 3.8+ and nothing outside the standard library. Without Python the skills do the same work by hand and say so.

## Development

```bash
python3 -m unittest discover -s tests     # script tests
python3 scripts/check_repo.py             # skill and manifest consistency
python3 scripts/sync_shared.py            # copy shared/ into every skill after editing it
python3 scripts/sensitive_scan.py         # personal data check
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Licence: [MIT](LICENSE).
