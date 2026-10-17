# Writing cards

A card is one claim taken from one source, with the exact sentence it rests on. Cards are the only way material reaches the topic pages and the answers, so a claim that is not on a card is lost, and a card whose sentence is not in the source is refused by the quote check.

## What the batch file looks like

- Each source is a section headed "# Snn <file name>"; a source cut into parts is marked "· k/n" and keeps its number in every part.
- Paragraphs and list items end with an anchor such as ^s01-p2; a table has its anchor on the line below it.
- Lines starting with ">" are notes from the converter (original path, times, notes about attachments). They are not source text: never quote them.

## One card per line

{"source": "S01", "anchor": "s01-p2", "quote": "Riverside Clinic will host the pilot.", "conclusion": "Riverside Clinic hosts the Project Atlas pilot.", "topic": "Pilot", "entities": ["Riverside Clinic", "Project Atlas"]}

- source: the source number from the section heading.
- anchor: the anchor at the end of the paragraph, list item or table the quote comes from.
- quote: the sentence copied character for character from that one paragraph, list item or table. Do not shorten words inside it, translate it, fix its spelling or join two paragraphs. Leave out the anchor itself. 6 to 300 characters: take the shortest whole sentence or clause that carries the claim; from a table, the cells that carry it.
- conclusion: the claim in one plain sentence, in the library language. It says what the quote says and nothing more: no inference, no advice, no judgement.
- topic: one topic from the topic list of the library (<work>/topics.txt), spelled as there. When none fits, write the closest category name; the user decides about it later.
- entities: names of organisations, projects, systems or products the quote mentions, as written in the source. [] when there are none. Never personal data.
- entity_types: only for entities that are not in the spec's Table E (its names and aliases), your suggested type for each: {"Riverside Clinic": "organisation"}. One of project, team (a department or team), organisation, system (a system or product) or other. Leave it out when every entity is in the table; the user confirms the types in the preview.
- event_date: only when the quote itself states the date of the event, as YYYY-MM-DD. Leave it out otherwise; never guess a year.

## What deserves a card

- Facts that may be asked about later: decisions, dates and deadlines, owners by role, figures, scope, status, rules, changes.
- One claim per card. A paragraph with three facts gives three cards with the same anchor and different quotes.
- Skip greetings, headings, tables of contents, page furniture, signatures and the converter's notes.
- Never put a claim from one source on another source's card, even when they say the same.

## Weak tier: one source at a time

Read one source section (or one part), write its cards, then move on. Do not carry claims over from a source read earlier. A source that holds nothing worth a card gets no cards; say so in the report.

## Fixing a rejected card

The report names the reason. Go back to the paragraph of the card's anchor and:

- quote not found / across paragraphs: copy the sentence again, character for character, from one paragraph only.
- quote found in several paragraphs: keep the quote and give the anchor of the paragraph you mean.
- quote too short: take the whole sentence; too long: take the part that carries the claim.
- missing field, unknown source, bad anchor: fill the field from the section heading and the anchor at the end of the paragraph.

Write the corrected card once. A card that still fails is dropped.
