# Methodology

Why the skills work the way they do: every rule below exists because a looser one lets answers go stale or facts get lost.

## The problem

An assistant can answer from your documents, but raw documents disagree with each other: an old plan, a newer decision, a meeting that changed it again. Searching them at question time returns whichever matches best, not whichever is current. The fix is to do the reconciling once, when material arrives, and keep the result: an LLM-maintained wiki rather than retrieval over a pile.

## Four layers

1. Source documents, cleaned but never shortened, one file each, named <partition>_<topic>_<type>_<short title>.md.
2. Summary files: the status card (what is true now), the change log (how it changed), open items, the glossary. These answer most questions without opening a source document.
3. Entity pages: one per person, organisation, system or project, with backlinks from every document that mentions it.
4. The spec: the library's own rules (partitions, topics, terms, thresholds, entities). The skills hold the process; the spec holds the rules, and grows with the library.

## Rules that keep it evergreen

- Name equals version. Documents carry no date in their name, so the next version of the same document lands on the same name and the previous one is archived. Two different documents must never share a name; when unsure, rename. This single rule removes most "which version is current?" questions.
- Evidence or the conservative choice. Duplicate, new version or change of fact: each call needs a quote. No quote, no change.
- Three questions before touching the status card. Does the new material carry this kind of fact; does the card have an entry for it; do they disagree. Only three yeses trigger a rewrite. Rolling process data (daily progress, single purchases) never does.
- Rewrites are checked by a script. The old card and the new card are compared item by item; every missing item must be explained in a change list, and the new card may not shrink below 70% without the owner's consent.
- Never delete, never edit sources. Older versions move to the archive with a time stamp; issues are recorded, not silently fixed. Personal identifiers are the one exception: masked before anything is written.
- No silent growth. When material fits no topic, the skill adds a topic to the closest partition (never a new partition), rewrites the spec with a revision note, and lists the change for review.
- Quote or no card. Every conclusion written into the library is a card that carries the exact sentence it rests on; a script finds that sentence in the source before the card is written, and topic pages are built only from cards.
- Search caps and fixed reading order. The assistant reads the status card first, then the specific list, then sources, and stops after a fixed number of searches. Answers name their basis file.

## What the preset gives you

One starting point, editable during setup: a work library (goals and plans, projects and tasks, proposals and deliverables, meetings and decisions, policies and procedures, organisation and roles, data and reports, reference and templates).
