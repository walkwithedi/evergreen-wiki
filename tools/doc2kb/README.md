# doc2kb: documents to a Markdown knowledge base

Turns Word, Excel and PowerPoint files, PDFs and mail (.eml) into Markdown an AI assistant can search: one merged file with an index, one file per document, or batch files for knowledge-base intake. Headings, tables, embedded workbooks and the position of every picture are kept; duplicate copies are filed once.

Python 3 standard library only: no pandoc, LibreOffice, python-docx, openpyxl or python-pptx. The kb-incremental skill uses the same converter (`doc2kb_core.py`) to read uploads as Markdown; this folder is the stand-alone tool for converting whole folders on a Linux desktop or in a cron job.

[中文说明](README.zh-CN.md)

## Files

| File | What it is |
| --- | --- |
| `doc2kb_core.py` | the converter: parsing, extraction, picture export and output. Command line with options for everything, no interface code. A copy of `shared/scripts/doc2kb_core.py`; edit it there. |
| `kb_batch.py` | the batch file format: writes batch files for `doc2kb_core.py` and splits them back into one file per source. A copy of `shared/scripts/kb_batch.py`; edit it there. |
| `quote_check.py` | checks the cards an assistant took from batch files (each quote must occur in its anchor's paragraph) and writes the ones that pass, one Markdown file per source. A copy of `shared/scripts/quote_check.py`; edit it there. |
| `doc2kb.sh` | entry script: without arguments a dialog (folder batch, chosen files, incremental tasks); with arguments the incremental command-line mode for cron |
| `doc2kb_dedup.py` | removes sections from a merged or incremental file whose text is already in other output files, after a folder was moved or renamed |
| `SPEC.md` | the behaviour contract: inputs, outputs and edge cases, for rebuilding or understanding the design |

## Requirements

- Python 3.7 or newer, standard library only.
- Optional, each feature is skipped with a message when missing:
  - `pdftotext`, `pdfimages`, `pdfinfo` (poppler-utils): PDF
  - `zenity`: the dialogs only; the command-line mode does not need it
  - `montage` (ImageMagick): contact sheets only
- Run `doc2kb.sh` with bash, not sh.

Get it from [Releases](https://github.com/walkwithedi/evergreen-wiki/releases) (`doc2kb-<version>.zip`) or this folder.

## Language

Messages and the labels written into the output (headings, notes, table headers) are English or Chinese. `doc2kb.sh` follows `DOC2KB_LANG` (en or zh), else the locale: a `zh` locale gives Chinese. `doc2kb_core.py` takes `--lang en|zh` (default `DOC2KB_LANG`, else en). Chinese labels and file names stay fixed between versions, so existing output folders and fingerprint files keep working.

## Usage

### Dialogs

```bash
./doc2kb.sh
```

Choose a mode: folder batch, chosen files or incremental tasks. Ticking "KB batch files" among the options writes batch files instead of merged output and asks for the tier (weak or strong).

### Incremental command line (cron)

```bash
# first run: set the watermark, take the last 30 days
./doc2kb.sh -s SOURCE -o OUTPUT -d 30

# every later run: only what changed since the last run
./doc2kb.sh -s SOURCE -o OUTPUT
```

cron example (every day at 18:30, absolute paths):

```
30 18 * * * /home/user/tools/doc2kb.sh -s /home/user/Documents -o /home/user/tools/output/wd >> /home/user/tools/output/wd/cron.out 2>&1
```

Options (each long option has a one-letter short form; type the short ones):

| Option | Effect |
| --- | --- |
| `-d N` | documents changed in the last N days (window) |
| `-t DATE` | from `YYYY-MM-DD` or `"YYYY-MM-DD HH:MM"` |
| `-i` / `-I` | export / do not export pictures (default: text only, faster) |
| `-E` | do not expand embedded workbooks |
| `-x SUFFIX` | output name suffix (default `incremental`, `增量` in Chinese) |
| `-n` | only list what would be processed (dry run) |
| `-h` | help |

Exit codes: 0 done (also when nothing was new), 1 option or environment error, 2 processing failed, 3 first run without a time range.

### The converter directly

```bash
python3 doc2kb_core.py --batch SOURCE -o OUTPUT --merge   # a folder, merged into one md
python3 doc2kb_core.py --files list.txt -o OUTPUT          # the files named in a list
python3 doc2kb_core.py report.docx -o OUTPUT --lang zh     # one file, Chinese labels
python3 doc2kb_core.py -h                                  # every option
```

### Knowledge-base batch files

```bash
python3 doc2kb_core.py --batch SOURCE -o OUTPUT --kb-batch --tier weak      # 20,000 characters per batch
python3 doc2kb_core.py --batch SOURCE -o OUTPUT --kb-batch --library LIB    # tier and limit from LIB/_kb.json
python3 kb_batch.py split OUTPUT/SOURCE_20261017_b*.md -o SPLIT              # back to one file per source
```

`--kb-batch` writes the documents into batch files for knowledge-base intake, `<source folder>_YYYYMMDD_b01.md`, `_b02.md` and so on (a second run on the same day adds the time: `_YYYYMMDD-HHMM_b01.md`):

- Each file starts with the batch name, the tier, the character limit, a note for the reader and a table of its sources (number, file, original path, last modified, characters, part).
- Sources are numbered S01, S02, ... over the run and appear oldest first (document last-modified time); each is a section headed `# S01 <file name>` with the original path and times as quoted lines, and the document's own headings one level lower.
- Paragraphs and list items end with an anchor such as `^s01-p2`; a table has one anchor on its own line below it. Headings, quoted notes, rules and picture placeholders carry none. These are Obsidian block references, so `[[file#^p2]]` reaches the paragraph once the source is split back.
- A batch holds at most the limit: `--batch-chars N`, else `--tier` (weak 20,000, strong 100,000 characters), else `batch_chars` and `tier` from the `_kb.json` of `--library`, else weak. A document longer than the limit is cut at its highest heading level that divides it, then lower levels, then between paragraphs; its parts keep the source number, are marked `· 1/3` and so on, and may land in different batches. A single paragraph or table longer than the limit is not cut: it becomes a batch of its own and the run and the report say so.
- No picture files are exported (`--kb-batch` implies `--no-images`); placeholders stay in the text.
- Date filter, `--only`, duplicate removal and the fingerprint file (`--fp-db`) work as in merged mode; a fingerprint line names the batch file that holds the document.

`kb_batch.py split` joins the parts of each source, restores the heading levels and rewrites `^s01-p2` to `^p2`; a source with a part missing from the files given is not written (exit code 3). Output files are named after the original file (`report.docx` becomes `report.md`); `--names MAP.json` maps a source number or original file name to another name.

Besides the human summary, batch runs print `STAT<TAB>key<TAB>value` lines (new, kept, failed, written, dup, moved, chars, images) and `FAILED<TAB>path` lines for scripts.

### Cleaning up duplicates after a folder move

When a subfolder is moved, renamed or copied, its files look new to the incremental mode. Their text is then recognised by the fingerprint file `.doc2kb_watch_fp` in the output folder and only their paths are listed. For an incremental file written before that file existed:

```bash
# 1. dry run: writes the report (target_dedup-report.txt) and changes nothing
python3 doc2kb_dedup.py OUTPUT/Documents_20261007_incremental.md -n

# 2. after checking the report: the original is backed up as .bak-<time>, and
#    .doc2kb_watch_fp is created so later incremental runs skip known text
python3 doc2kb_dedup.py OUTPUT/Documents_20261007_incremental.md
```

- By default the other md files in the target's folder are compared (earlier incremental files, merged full runs, one-file-per-document output); `-b FILE_OR_FOLDER` (repeatable) names others.
- Only sections whose text is identical are removed (metadata, heading levels, picture paths and whitespace are ignored); documents changed during the move stay.
- Removed sections appear in the index's "Documents moved, content unchanged" table with current path, old path and the file holding the text.
- Source documents and pictures are never touched; picture folders used by removed sections are listed in the report.
- If the file was already imported into a knowledge base, replace it there with the cleaned one.

## Formats

- Supported: `.docx`, `.xlsx`, `.xlsm`, `.pptx`, `.pdf`, `.eml`.
- Legacy binary formats (`.doc`, `.xls`, `.ppt`, `.msg`) do not crash a run: they are listed under "need a new format first".
- Archives: `.zip`, `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`/`.tbz2`, `.tar.xz`/`.txz` are read like folders. The documents inside appear as `pack.zip/a/report.docx` in the scan, the index and the report, and work with `--only` and incremental tasks; an archive can also be named directly (`python3 doc2kb_core.py pack.zip`). Archives inside archives are opened up to 3 levels deep. Members are unpacked into a private temporary folder that is removed when the run ends; nothing is written next to the archive and member paths never leave it. Encrypted members, members over 512 MB unpacked, more than 2 GB of documents in one archive, damaged archives and `.7z`/`.rar` (no standard-library reader) are listed as failed with the reason. Zip names written by Chinese Windows without the UTF-8 flag are decoded as GBK.
- Duplicates, within one run: files with identical bytes (SHA-256, archive members included) are parsed once, preferring a copy whose output exists, then one outside any archive, then the first path; files whose extracted text is identical are then kept once (newest document time). Both kinds are listed in the report's "Duplicate files" section and in a note at the top of the kept copy. `-D` keeps every copy. Across runs, incremental tasks skip text already filed (see above).
- Merged output (index plus every text in one Markdown file) by default; one file per document or knowledge-base batch files as options.
- Incremental mode keeps the time of the last successful run as its watermark; every successful run moves it. A file counts as changed by the latest of its file system modification time, change time and the document's own time, so old files newly copied in are found.
