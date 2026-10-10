# Parameters: life library

These are the process parameters kb-incremental reads for this library. Edit them to suit the library; the skill never overwrites this file.

## Reading conditions

Open items (due dates and to-dos): read when the material contains an expiry, renewal, follow-up, payment or exam date, or settles a to-do. If unsure, do not read it and write "open items not checked" in the delivery note.
Change log: read when step 4 decides "same-name new version" or step 5 decides "trigger".
Glossary: read when this run has term fixes, masking or issues to add.

## Extra hard rules

1. No health, money or investment advice; no interpretation of results, diagnoses, returns or coverage.
2. Class-A data (ID, card and account numbers, passwords, one-time codes) is always masked with asterisks before output, keeping at most the last 4 characters. Masking does not break the "never edit source text" rule. Material that is mostly class A (an ID scan) gets no file and no index row; the delivery note tells the user to record its storage place in the originals register (partition 07).
3. Class-A data never appears in clear in replies, readme or delivery notes.

## Step 1: dates and output fields

Apply the scope clause of the spec first.
Event date: the date the thing happened (checkup, visit, signing, statement period, certificate issue). Not recorded: "event date not in material".
File date: the file's last-modified time to the minute; unknown: "file date unknown". Photos and scans carry capture or scan time, which is not the event date.
People: Self or the family relation.
Sensitivity: A, B or C by spec section 9.
Type: from the Table A type list.
Short title: the period for recurring material (2026-annual checkup, 2026-09); the relation for family material (-Father); a distinguishing word for parallel material.

Output (fixed):
  Material: <source file name>
  Event date: YYYY-MM-DD
  File date: YYYY-MM-DD HH:MM
  Partition: XX
  Topic: <topic from Table A>
  Type: <type>
  People: <Self / relation>
  Sensitivity: <A / B / C>
  Short title: <short title>
  Proposed file name: <partition>_<topic>_<type>_<short title>.md
With an expansion, put the line "Expansion: partition XX gets topic "…" (reason: one sentence)" before the partition line.

## Fallback partition

06 (Family). Wording precedent: Table A has one row per topic (partition | name | topic | scope); add a row after the partition's last row with a one-sentence scope. If the spec has no revision notes yet, add "Revision:" under the version line. Material that is mostly class A is never expanded for; follow extra hard rule 2.

## Step 2: extra cleaning: masking

Find and mask class-A data by reading, not by bulk regex. Log each one: file | section heading | class, never the original value. None: "Masking: none this run".

## Step 3: close-reading list and extraction

Close-read: checkup reports and lab results, diagnoses and medical records, policies and terms, contracts, tax documents, claim, reimbursement and loan payoff documents, anything with amounts, due dates, cover amounts or measured values.
Copy numbers with units and reference ranges; copy the material's own flags (high/low arrows, positive) without judging them. For policies, extract only stated cover, amounts, term, premium schedule and beneficiaries.

## Step 4: additions

Photos often have camera-generated names: a content-hash hit means duplicate upload; a source-name hit alone (hash differs or row has no hash) needs a content comparison; only the same document is a duplicate, otherwise it is new material.
Event date not recorded and a file-name hit: always rename to distinguish.

## Step 5: five trigger classes

Values: checkup and lab values, asset and debt amounts, cover amounts, premiums, learning progress
Due dates: expiry or renewal of IDs, policies, contracts, subscriptions, certificates
Ownership: beneficiary, policyholder, owner, account holder, person handling an errand
Status: progress or closing of claims, reimbursements, loans, exams, follow-ups
Definitions: corrected diagnoses, changed counting rules, unified naming

Output: for each class present in the new material, four lines:
  <class>
    New material: <quote, masked>
    Status card: <quote, or: no matching entry>
    Consistent: <yes / no / not applicable>
    Decision: <trigger / no trigger>
Classes not present, in one line: Not present: <classes>, all no trigger.

Process data never triggers: single purchases, self-measured readings (blood pressure, weight, steps), single study check-ins.
Family material is never compared with the owner's status card and never triggers; its due dates go to open items.
The third overall decision is "open items only": rewrite only the open-items list; new entries take their reminder lead time from Table D, else "reminder not set".
On a trigger rewrite the status card and change log; if the material also has due dates or settles a to-do, rewrite open items too.

## Metadata

YAML mode. Fields and order as in spec section 7; entity fields: people, organisations. Family members are named by relation. No core entities yet.

## Glossary and issue list

The glossary has three sections: 1. Term fixes; 2. Masking log; 3. Open issues.
Issue categories: inconsistent naming of a person, unusual date, two opposite statements of one thing, one value under two definitions, unreadable text.

## Open-items format

Item | Partition | Due date | Reminder | Status | Basis. Section 1: due in the next 6 months; section 2: recurring items; section 3: done.

## Failure additions

Image text unreadable: no file for that item; the delivery note says "unreadable, please provide a clearer copy or the text".
Glossary not found: do not rewrite it; put this run's fixes, masking and issues in readme section 3 and flag them for manual entry.

## Readme (five sections)

1. New files
2. Updated files (the file index always; the spec when rewritten for expansion or new entities)
3. Changes (three to five lines, including items not filed and mostly class-A material, new entities; "Topics added this run (please review)" with partition, topic, source, reason and that the user may move or undo it)
4. New due dates (item | due date | reminder, for syncing with a reminders app; "none" if none)
5. Library files read (and why any optional file was not read)
