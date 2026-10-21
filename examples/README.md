# Examples

[中文](README.zh-CN.md)

sample-work-kb/ is a small, entirely fictional work library about Project Atlas, a pilot run with Riverside Clinic. It holds three sources with their cards and the topic pages built from them. Open it in Obsidian, or register it and try the skills.

To register it, first copy sample-work-kb/ to a folder of your own, so that the sample stays unchanged (the skills write into the library they use). Then choose that copy as the library folder in Set up of the knowledge base client, or in `python3 install.py`: a folder that already holds a library is registered as it is, and nothing in it changes. To register it by hand instead, add an entry to the registry:

```json
{"schema": 1, "libraries": [{"id": "sample", "label": "Sample Work",
  "scope": "Project Atlas, a fictional pilot run with Riverside Clinic (demo only)",
  "backend": {"type": "local", "root": "<path to your copy of sample-work-kb>"}}]}
```

Try, in order:
1. "When does the Atlas pilot end?" (kb-query: the topic pages and cards; the extension is on the decision logs page)
2. "Note this: the pilot review moved to Thursday." (kb-note: the note becomes a source in Sources/ with its cards, and the topic page it touches is rebuilt)
3. "Ingest: <path to>/examples/new-material" (kb-ingest: batch file, cards, quote check, then the pages of the topics touched are rebuilt), or Ingest under the library in the client with that folder

How it is made: sample-materials/ holds the three source documents (mails, which the converter reads as plain text), and sample-work-cards.jsonl the cards written for them. tests/test_examples.py runs the converter, the quote check and ingest.py on them and checks that the result is the sample library; after a change to the scripts, rebuild it with SAMPLE_UPDATE=1 python3 -m unittest tests.test_examples.
