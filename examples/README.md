# Examples

sample-life-kb/ is a small, entirely fictional life library with local backend settings. Open it in Obsidian, or register it and try the skills:

```json
{"schema": 1, "libraries": [{"id": "sample", "label": "Sample Life",
  "scope": "a fictional person's health, money, home and subscriptions (demo only)",
  "backend": {"type": "local", "root": "<path to>/examples/sample-life-kb"}}]}
```

Try, in order:
1. "What is my cholesterol trend?" (kb-query reads the status card and the 2025 checkup)
2. "Note this: the boiler service is due in March." (kb-note writes to Quick-Notes/)
3. "File this" with sample-materials/checkup_2026.txt (kb-incremental: new material in partition 02, triggers a value change in the status card)
4. "File my quick notes" (kb-incremental note filing)
5. "Health check" (kb-incremental lint)

Work on a copy if you want to keep the sample unchanged. The test suite uses this folder read-only.
