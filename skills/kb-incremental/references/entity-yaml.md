# YAML front matter and entities (metadata = yaml)

Field names and order come from the library spec (its metadata section). The examples below use the English preset names; a library may call them anything.

## Front matter

The file starts with ---, then one property per line, then ---, a blank line, the key conclusions and the body. General rules:
- Dates (document date, event date, file date): ISO without quotes, such as 2026-09-20T14:09 or 2026-09-20. A date that cannot be found: leave the whole line out and say so in the delivery note.
- partition: "07" (quoted, keeps the leading zero). topic, type, status, sensitivity, source file name, source path: quoted strings.
- source characters, source images: numbers, unquoted.
- Entity fields (whatever the spec lists, for example systems, or people and organizations) and keywords: lists, such as ["[[Payments Gateway]]", "[[Project Atlas]]", "unregistered wording"].
- Empty entity field: write [] and add a line "<field>_note" that keeps the source wording, such as systems_note: "none".
- size: "large" only when the file reaches the Table D large-file threshold; otherwise leave the line out.
- Escape double quotes and backslashes inside strings. Building the front matter with a short script avoids mistakes.

## Entity mapping (during step 1)

1. Split entity fields and keywords on commas, semicolons and enumeration marks (not inside brackets).
1a. If the spec has Table F (value filters), apply it to entity fields (not keywords) first: wording that matches an empty-value form or a noise value is not listed; whenever wording is dropped or the value was empty, add the "<field>_note" line with the full source wording. Wording that is clearly not an entity but missing from Table F (SQL keywords, placeholders, codes, generic terms) is added to Table F under its maintenance clause, which counts as a spec change and is listed in the readme's updated-files section.
2. Look each wording up among Table E names and aliases (exact match; brackets around an alias are not part of it). A hit becomes "[[Name]]". One wording mapping to several entities: list all, without duplicates.
3. No hit:
   - In an entity field: first decide whether it is an entity at all (system, project, organization, person). If not (descriptive text), keep it as plain text. If it is, register it only if all three hold:
     a. Identity is clear: the material or the library says what it is, in one sentence of definition (not its role in this material). A bare name is not enough.
     b. Worth its own page: it is one of the main subjects, appears repeatedly with real information, or will plainly appear in other material. Passing mentions, generic roles ("the vendor", "the relevant team") and temporary code names are not registered.
     c. Not another name for an existing entity: compare with Table E names and aliases across languages, abbreviation and full name, short names, case, hyphen and space differences. If it is one, do not register it; list it in the readme's change section as "possible alias" for the user to decide.
     Registered: add a Table E row (name in the most standard form found in the material; never transliterate, translate or invent; type from the Table E types), write it as a link, and in step 1 write "New: <name> (<one-line identity>; <reason>)"; the readme lists "New entities" for review. Otherwise keep plain text and write "Kept as text: <wording> (reason: identity unclear / not a main subject / possible alias)".
   - In keywords: always plain text, never registered.
4. Never add links in body text.

Registering an entity changes the spec (a Table E row), so read the spec in full, rewrite it, deliver it and list it in the readme's updated-files section. With topic expansions in the same run, make one rewrite (SKILL.md "Topic expansion", rule 4).

## Entity pages

Each Table E entity has a page in the entities folder, named "<Name>.md". Registering an entity creates its page in <out>/<entities_dir>/. Template (field labels may be localised by the spec; keep the keys type, entity_type, core and aliases unless the spec says otherwise):

---
type: "entity"
entity_type: "<Table E type>"
core: false
aliases: ["alias 1", "alias 2"]
---

# <Name>

## Related files

```base
filters:
  and:
    - file.hasLink(this.file)
    - '!file.inFolder("<archive_dir>")'
    - '!file.inFolder("<entities_dir>")'
views:
  - type: table
    name: Related files
    order:
      - file.name
      - date
      - type
      - status
```

Replace the placeholders with the library's folder names and list the date fields the spec uses. The base block is an Obsidian Bases query; other editors show it as a code block.

Core entities (Table E core = yes): core: true, and at the end:

## Overview

<text>

Overview rules:
- Update only when material linked to the entity is filed and step 5 decides "trigger"; read the whole page first.
- End every sentence with its source, such as (basis: [[05_Decisions_Minutes_Release-Review-2026-09]]).
- Current-state statements only cite the status card, such as (see status card item 12); never a conclusion of its own. If they disagree, the status card wins and the mismatch is logged as an issue.
- Subject boundaries: when material covers several entities, each conclusion, number or judgement goes only into the overview of the entity it describes. Shared keywords (same metric, term or meeting) are no reason to copy one entity's facts to another. A comparison is written as a comparison, with a basis for each side.
- After updating, run card_check.py as in SKILL.md "Rewrite check".
- Structure: what it is, current state, key conclusions, history (newest first).
- Updated pages go to <out>/<entities_dir>/ and are listed in the readme's updated-files section.

## Basis lines in summary files

In the status card, change log and open-items list, every basis is a link to the source file without .md, such as basis: [[02_Checkups_Report_2026-Annual]]. Existing plain-text bases need not be converted when a file is rewritten; new and changed entries must use links.
