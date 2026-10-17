# Methodology

Why the skills work the way they do. Each rule below closes a way in which answers drift from what the documents say, go stale, or lose facts. The exact procedures are in the skills; [design-2.0.md](design-2.0.md) and [design-3.0.md](design-3.0.md) hold the design and its implementation steps. [中文](methodology.zh-CN.md)

## The problem

An assistant can answer from your documents, but documents disagree with each other: an old plan, a newer decision, a meeting that changed it again. Searching them at question time returns whichever matches best, not whichever is current, and a model summarising them can state something no document says. The library therefore does the reconciling once, when material arrives, keeps the result as plain files, and ties every statement in it to the sentence it comes from.

## The evidence chain

Every answer can be followed back, link by link, to a sentence in a document:

1. Source: a document converted to Markdown (by doc2kb), one file in Sources/, every paragraph with an anchor (`^p3`). Sources are never edited.
2. Card: one claim taken from a source. It holds a conclusion in the model's words and the exact sentence it rests on, linked to its paragraph (`[[Sources/<source>#^p3]]`), with its topic and entities. Cards live in Cards/, one file per source.
3. Topic page: everything the cards say about one topic, newest first, each statement with its quote and link. Pages are built from cards only and rebuilt when their cards change.
4. Status card: the library's home page, what is true now, one numbered item per fact, each citing its sources.

The spec holds the library's own rules beside them: partitions and topics (Table A), term fixes (Table B), open issues (Table C) and entities with their aliases (Table E).

## Principles

- Quote or no card. A card is written only when a script (quote_check.py) finds its quote in the cited paragraph, ignoring only white space, punctuation width and emphasis. A reworded quote fails. A rejected card is written once more from the source; one rejected twice is dropped and named.
- Scripts check, the model proposes. Whatever can be checked mechanically is checked by a script, not by the model's judgement: quotes, topic pages written by the model (check-page: every cited passage is a current card of the topic and every such card is cited), status-card rewrites (status-check: nothing removed, changed or left uncited without the owner seeing it) and quotes in answers (answer.py check).
- Name equals version. Source names carry no date, so the next version of a document arrives under the same name and replaces the previous one. Versions under different names are found as candidates (close names and shared paragraphs) and confirmed before they replace anything. Two different documents must never share a name.
- Archive, never delete. A replaced source and its cards move to Archive/ with a time stamp. Cards of the old version that the new one no longer carries are listed, and the owner can restore them; a restored card cites the archived source and says it is from an earlier version.
- The owner decides what changes. New topics, new entities, version pairs and lost cards are put to the owner before anything is written, together with one preview of the run; nothing grows silently. Status-card items that cite a replaced source get a review mark (⏳) and are not relied on until checked.
- Scripts do the mechanics. Everything that can be decided by a rule is done by a script, so a model of modest ability, run offline, is enough: batches of at most 20,000 characters read one source at a time, topic pages and answer material assembled by scripts, every answer checked before the reply. The model extracts cards and words the replies.
- Answers quote. Every statement of fact in an answer is followed by the exact source sentence it rests on and its link. Reading order is fixed (status card, then topic pages and cards, then sources) and the number of searches is capped; what the library does not record is said to be not recorded.
- No code, no writes. Every write goes through the scripts. Without a code environment (Python) the skills still read and answer, and write nothing to the library.

## The work preset

One starting point, adjusted during setup: a work library whose spec lists the partitions goals and plans, projects and tasks, proposals and deliverables, meetings and decisions, policies and procedures, organisation and roles, data and reports, reference and templates, each with its topics, and an empty status card of numbered items. Tables B, C and E start empty and grow as the owner confirms new terms, issues and entities; new topics are appended to their partition, never as a new partition.
