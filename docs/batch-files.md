# Batch files

Batch files feed an ingest step in which an assistant extracts claims with their exact source sentences and
a script checks each sentence against the source. The format therefore has to give every passage a stable
address, keep each file within what the assistant can read at once, and split back losslessly.

`kb_batch.py make` (in kb-ingest's scripts, from shared/scripts) converts the documents with the copy of
the [doc2kb](https://github.com/walkwithedi/doc2kb) converter beside it and writes the batch files;
`kb_batch.py split` splits them back. It takes the converter's options (`--batch`, `--files`, `--only`,
`--since`, `--fp-db`, `--lang`, ...) and these:

```bash
python3 kb_batch.py make --batch SOURCE -o OUTPUT                  # 20,000 characters per batch
python3 kb_batch.py make --batch SOURCE -o OUTPUT --library LIB    # limit from LIB/_kb.json (batch_chars)
python3 kb_batch.py split OUTPUT/SOURCE_20261017_b*.md -o SPLIT     # back to one file per source
```

## Format

- **Names**: `<source folder>_YYYYMMDD_b01.md`, `_b02.md`, ...; when the output folder already has batch
  files of that day, `<source folder>_YYYYMMDD-HHMM_b01.md`.
- **Header**: batch name with its number and the total, tier and character limit, one paragraph telling the
  reader how sources and anchors are marked and that quotes are copied exactly, and a table: source number,
  file name, original path, document last-modified time, characters, part (`k/n`, or `-`). The header holds
  no level 1 heading.
- **Sources**: numbered S01, S02, ... over the whole run, ordered by document last-modified time, oldest
  first (unknown times last, then by path), so an older version is always read before a newer one. Each source
  is a section headed `# Snn <file name>`, followed by the original path, the last-modified time with its
  source and the extraction time as quoted lines; the single-file metadata header is dropped and the
  document's headings are demoted by one level.
- **Anchors**: every paragraph and every list item ends with ` ^snn-pN`; a table gets one anchor on its own
  line after a blank line below it. Headings, quoted lines (notes the converter adds), rules, comments and
  picture placeholders get none. N counts from 1 over the whole source, across parts. The form is an Obsidian
  block reference, so after splitting back `[[file#^pN]]` reaches the passage.
- **Limit**: `--batch-chars`, else `--tier` (weak 20,000, strong 100,000; kept for older command lines),
  else `batch_chars` from the library settings file named by `--library`, else 20,000; a library's `tier`
  is ignored; below 1,000 is refused.
- **Cutting**: a source larger than the limit is cut at the highest heading level that divides it into more
  than one piece, pieces still too large at the next level, and without headings between blocks; pieces are
  then joined greedily back up to the limit. Parts keep the source number and are marked `· k/n` at the end
  of the section heading. A block (paragraph, list, table) is never cut: one larger than the limit becomes a
  part and a batch of its own, and the run output and the report name it.
- **Packing**: parts in source order; a batch closes when the next part would take it over the limit.
- **Pictures**: not exported; placeholders stay in the text.
- **Duplicates and increments**: as for merged output; a fingerprint line names the batch file holding the
  document's first part.
- **Splitting back** (`kb_batch.py split`): the parts of each source are joined in order (the quoted lines
  kept once), heading levels restored and `^snn-pN` rewritten to `^pN`. A source with a part missing is not
  written. The result equals the single-file conversion apart from the anchors, the quoted lines and blank
  lines.

