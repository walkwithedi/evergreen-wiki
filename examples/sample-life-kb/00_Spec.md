00_Spec
Version: v1
Last updated: 2026-10-10
Note: read by the kb-incremental skill. Tables A to F are read as structured data; when editing, keep table names and column names unchanged. Topic files carry YAML front matter and link entities, so the library can be opened directly in Obsidian.

1. Table A: partitions and topics

Partition | Partition name | Topic | Scope
00 | Spec and status card | fixed files | only the spec and the status card
01 | Indexes and logs | fixed files | only the file index, open items, change log, glossary
02 | Health | Checkups | checkup reports, lab results, follow-up results
02 | Health | Visits | outpatient and hospital records, diagnoses, imaging and test reports
02 | Health | Medication | prescriptions, medication records
02 | Health | Vaccines | vaccination records
02 | Health | Claims and reimbursement | health insurance claims and reimbursement results
03 | Money | Accounts | account overview (never account numbers)
03 | Money | Investments | trades, holdings snapshots, reasons for decisions
03 | Money | Income and spending | monthly summaries, large expenses
03 | Money | Taxes | tax statements, annual returns
03 | Money | Loans | loan agreements, repayment schedules, payoff letters
04 | Insurance | Policies | policies, terms, coverage summaries, premium schedules
04 | Insurance | Claims | claim forms, settlement documents
05 | Home | Primary home | ownership or lease, building management, utilities, repairs
05 | Home | Other residences | ownership or lease, building management, utilities, repairs
06 | Family | Errands for family | things done on a family member's behalf, with the papers
06 | Family | Key dates | birthdays, anniversaries and other family dates
07 | IDs and legal | ID documents | summary of each document and its expiry date (scans follow section 9)
07 | IDs and legal | Contracts | contracts other than loans and housing
07 | IDs and legal | Powers of attorney | notarised documents, powers of attorney
07 | IDs and legal | Originals register | where paper originals and class-A information are kept
08 | Devices, subscriptions and travel | Devices | receipts, warranties
08 | Devices, subscriptions and travel | Subscriptions | services and renewal dates
08 | Devices, subscriptions and travel | Travel and vehicles | vehicles, trips
09 | Learning | Courses | course material and notes
09 | Learning | Reading | reading notes
09 | Learning | Certificates and exams | registrations, results, certificates
09 | Learning | Plans and reviews | learning plans and reviews
10 | Reference | Money principles | general personal finance material
10 | Reference | Health literacy | general medical information
10 | Reference | Policies and rules | public rules on health cover, tax, pensions and the like

Type list: report, receipt, contract, record, list, notes, plan, review, reference, summary
Every partition can be used directly; the first item filed under a topic needs no registration.

2. Table B: term fixes

Original | Fixed | Note
No entries yet. When one person, organisation or item is named inconsistently and the owner confirms the standard form, add it here.

3. Table C: open issues

No. | Issue | Files | Date logged
No entries yet.

4. Table D: thresholds

Parameter | Value
Heading demotion limit (characters) | 90
File name length limit (characters) | 120
Large file threshold (bytes) | 1000000
ID document expiry reminder | 90 days
Policy renewal reminder | 30 days
Contract expiry reminder | 30 days
Subscription renewal reminder | 7 days
Expiry scan window | next 6 months
Annual tax filing window | not set

5. Table E: entities

Name | Type | Aliases | Core | Note
Self | person | | no | the library owner
Riverside Clinic | organisation | Riverside | no | registered 2026-10-10, annual checkup provider

Types: person, organisation, project, document, other. Family members are named by their relation (Father, Mother, Child).
Only names in Table E may be written as links. A new entity met during intake may be registered in the same run and listed in the readme for review; until registered it stays plain text.
Separate aliases with semicolons. If one wording refers to several entities, list it under each.

6. Naming

Topic files: <partition>_<topic>_<type>_<short title>.md, with spaces inside each part written as hyphens. No date in the name: the same name means the same document in successive versions, and older versions are archived.
Embed what tells similar material apart in the short title:
(1) Recurring material (annual checkup, monthly spending, yearly tax return): the period, as in 02_Checkups_report_2026-annual.md or 03_Income-and-spending_list_2026-09.md.
(2) Family material: the relation, as in 02_Checkups_report_2026-annual-Father.md.
(3) Similar topics with different content: a distinguishing word.
Summary files have fixed names; see _kb.json names.
Entity pages live in the entities folder, named after the entity, as Entities/Father.md.
Older versions move to the archive folder with the old suffix and a time stamp; temporary snapshots start with the snapshot prefix; run logs start with an underscore.

7. Metadata

Topic files start with YAML front matter between two --- lines, fields in this order:
event_date: YYYY-MM-DD (unquoted)
file_date: YYYY-MM-DDTHH:MM (unquoted; leave out if unknown)
partition: "02"
topic: "Checkups"
type: "report"
people: ["[[Self]]"] (Table E names as quoted links, others as plain text)
organisations: [] (same rule)
people_note / organisations_note: "…" (only when the field is empty or wording was dropped; keeps the source wording)
keywords: ["…"] (Table E names as links, others plain)
sensitivity: "B"
status: "current"
size: "large" (only at the Table D large file threshold)
source_file: "…"
source_characters: number
source_images: number
After the front matter: key conclusions, then the cleaned body. No links in the body.
Duplicate and trigger judgements go into the readme only, never into knowledge files.

8. Entity pages

Each Table E entity has a page in the entities folder with type: "entity", entity_type, core and aliases in its front matter, and an Obsidian Bases query listing every file that links to it (archive and entities folders excluded).
Core entities also have an Overview section maintained by kb-incremental: every sentence cites a source link; where it disagrees with the status card, the status card wins; it is updated only when filed material links to the entity and triggers.
This library has no core entities yet.

9. Sensitivity

Class A: ID numbers, card and account numbers, passwords, one-time codes. Never stored in clear. Masked before filing (at most the last 4 characters kept) and the masking is logged in the glossary; material that is mostly class A (an ID scan) is not filed, only its storage place is recorded in the originals register.
Class B: medical records, diagnoses, income, asset details. May be filed; keep the library private and review sharing every quarter.
Class C: everything else.

10. Scope

Not filed: advertising; general news with no direct bearing on the owner or family (useful general material goes to partition 10); material that is mostly class A; repeated uploads.

11. Evidence

Health and money conclusions rest only on original documents. Hearsay and guesses are marked "to verify", logged as issues and kept out of the status card.
Family material is stored with the person's consent, carries the relation in the short title and is never written into the owner's own status card entries.
Every entry in the status card, change log and open items cites its source as a link, such as basis: [[02_Checkups_report_2026-annual]].

12. Rhythm

Daily: intake as material arrives.
Monthly: asset snapshot, spending summary, learning progress; health check for broken links, orphan entities and wording outside Table E.
Quarterly: expiry scan, sharing review.
Yearly: checkup comparison, tax return, asset review, coverage gaps, learning review.
