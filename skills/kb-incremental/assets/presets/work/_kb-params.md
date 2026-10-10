# Parameters: work library

These are the process parameters kb-incremental reads for this library. Edit them to suit the library; the skill never overwrites this file. Add your own organisation's rules under "Extra hard rules".

## Reading conditions

Open decisions: read only when the new material supplies a conclusion, basis or date an open decision is missing. If unsure, do not read it and write "open decisions not checked" in the delivery note.
Change log: read when step 4 decides "same-name new version" or step 5 decides "trigger".
Glossary: read when this run has term fixes or new issues to add.

## Extra hard rules

None by default.

## Step 1: dates and output fields

Document date: the file's last-modified time to the minute. If unavailable, a date stated in the body, marked "date from body". Neither: "date not in material"; never use today's date instead.
Type: from Table A if it lists types; otherwise the material's actual form (minutes, design, plan, list, table, report, reference).
Short title: the period for recurring material (daily, weekly, monthly reports and statistics); the reporting party for one template filled by several parties ("-Payments"); a distinguishing word for parallel material.

Output (fixed):
  Material: <source file name>
  Document date: YYYY-MM-DD HH:MM
  Partition: XX
  Topic: <topic from Table A>
  Type: <type>
  Short title: <short title>
  Proposed file name: <partition>_<topic>_<type>_<short title>.md
With an expansion, put the line "Expansion: partition XX gets topic "…" (reason: one sentence)" before the partition line.

## Fallback partition

09 (Reference and frameworks). Wording precedent: Table A lists each partition's topics as one running description; append a short phrase at the end of the description, with examples in brackets if useful, such as "office logistics (parking, building access)".

## Step 2: extra cleaning

None.

## Step 3: close-reading list

Solution designs, review minutes, decision records, feedback dispositions, core process diagrams, ownership and handover documents, and anything with key numbers (data volumes, capacity, node counts, resource specifications, amounts, dates, thresholds).

## Step 4: additions

Weakly related material is judged against the spec's scope clause, not against the index.

## Step 5: five trigger classes

Values: data volume, capacity, node counts, resource specifications, amount limits, thresholds
Ownership: owning team, data ownership, responsibility boundaries, lead team
Terms: official terms, system identifiers, role names, organisation names changed or added
Milestones: go-live dates, release batches, delivery dates
Approvals: initiation, review, resource requests moving forward, sent back or paused

Output: all five classes, four lines each, twenty lines in all:
  <class>
    New material: <quote, or: no such information in the new material>
    Status card: <quote, or: no matching entry>
    Consistent: <yes / no / not applicable>
    Decision: <trigger / no trigger>

Process data never triggers: daily progress, test pass rates, ticket counts and similar rolling numbers.
New information you cannot match to a status-card quote goes to open decisions instead.
The third overall decision is "open decisions only": rewrite only the open-decisions list. On a trigger rewrite the status card and change log.

## Metadata

YAML mode. Field order as in spec section 8. Entity field: systems (filter with Table F, then map with Table E). Core entities: Table E rows with core = yes.

## Text-mode header (only if the library switches metadata to text)

  Document date: YYYY-MM-DD HH:MM
  Partition | topic | type:
  Systems:
  Keywords:
  Status: <current / in doubt>
  Source file:
  Source path:
  Source characters | source images:

## Issue categories

A person's or system's name written inconsistently; an unusual document date; two opposite statements of one principle; one number under two definitions.

## Readme (four sections)

1. New files
2. Updated files (the file index always; the spec when rewritten for expansion, new entities or Table F additions)
3. Changes (three to five lines; new entities and updated entity pages; "Topics added this run (please review)" with partition, topic, source, reason and that the user may move or undo it)
4. Library files read (and why any optional file was not read)
