# Examples

sample-work-kb/ is a small, entirely fictional 2.0 work library (tier weak) about Project Atlas, a pilot run with Riverside Clinic. It holds three sources with their cards and the topic pages built from them. Open it in Obsidian, or register it and try the skills:

```json
{"schema": 1, "libraries": [{"id": "sample", "label": "Sample Work",
  "scope": "Project Atlas, a fictional pilot run with Riverside Clinic (demo only)",
  "backend": {"type": "local", "root": "<path to>/examples/sample-work-kb"}}]}
```

Try, in order:
1. "When does the Atlas pilot end?" (kb-query: the topic pages and cards; the extension is on the decision logs page)
2. "Note this: the pilot review moved to Thursday." (kb-note: the note becomes a source in Sources/ with its cards, and the topic page it touches is rebuilt)
3. "Ingest this" with new-material/Atlas weekly status 2026-03-16.eml (kb-ingest: batch file, cards, quote check, then the pages of the topics touched are rebuilt)

Work on a copy if you want to keep the sample unchanged.

How it is made: sample-materials/ holds the three source documents (mails, which the converter reads as plain text), and sample-work-cards.jsonl the cards written for them. tests/test_examples.py runs the converter, the quote check and ingest.py on them and checks that the result is the sample library; after a change to the scripts, rebuild it with SAMPLE_UPDATE=1 python3 -m unittest tests.test_examples.
