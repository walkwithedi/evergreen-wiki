# doc2kb: requirements specification

> Purpose: enough for another developer, or an AI, to build a functionally equivalent tool from scratch.
> It describes the behaviour contract only (what goes in, what comes out, how edge cases are handled)
> and does not prescribe a language, an interface toolkit or libraries. Any stack will do as long as
> it meets the constraints in section 1 and passes the acceptance scenarios in section 8.

---

## 1. Background and constraints

### 1.1 What it is for

Turn accumulated Office documents, PDFs and mail into a plain-text knowledge base that an AI
assistant can search and answer from. The kb-incremental skill uses the same converter to read
uploads as Markdown instead of reading the binary files.

### 1.2 Constraints

| Constraint | Meaning | Effect on the design |
| --- | --- | --- |
| No dependencies | Nothing beyond the language's standard library: no document converters, no office suite on the command line, no third-party parsing libraries | Office formats are parsed from their zip packages and XML directly |
| Plain-text output | The output is read by an AI assistant | Markdown, no HTML; pictures are separate files |
| Non-ASCII everywhere | File names, folder names and content are often Chinese; paths contain spaces and brackets | Every step must handle non-ASCII text and special characters |
| Linux desktop | Ubuntu and similar | The dialog mode uses what such a desktop has (zenity); the command-line mode needs only bash and Python |

> The dependency rule is the strongest one. If the environment happens to have better tools, the
> implementation may use them (poppler-utils for PDF, ImageMagick for contact sheets), but it must not
> require them: without them the affected feature is skipped with a clear message.

### 1.3 Who reads the output

The text files end up in an AI assistant's knowledge base or project files. The output therefore
serves machine retrieval rather than human layout:

- plain text or light markup (Markdown) beats rich text or HTML (tags use up context without adding meaning)
- a clear structure, so a passage can be located
- an index the assistant reads first to decide which document answers a question

---

## 2. Components

Two deliverables, with separate responsibilities:

1. **Parsing engine**: parses documents, extracts content, writes the output. Callable from the command
   line, every behaviour controlled by options, no interface code. Other programs (the kb-incremental
   skill) import it.
2. **Entry script**: two ways to run
   - without arguments -> dialogs (everyday manual use)
   - with arguments -> command line without any interface (scheduled runs)

> Why: scheduled jobs have no display and a minimal environment; an interface dependency makes them fail.
> Both entry points share one engine so the logic never forks.

---

## 3. Parsing

### 3.1 Input formats

Required: current Office formats (word processing, spreadsheet, presentation), PDF, and the standard mail
archive format (MIME mail, usually `.eml`).

Explicitly **not** supported: legacy binary Office formats and mail clients' private binary formats (such
as `.msg`). They do not crash the run: they are recognised, skipped, and listed in the report under
"need a new format first", asking the user to save them in a current format.

> Current Office formats are zip packages of XML. Legacy binary formats are a different compound-file
> structure that is costly to parse for little gain. Detect the real type from the file's **magic number**,
> not only its extension: users rename old files to new extensions.

### 3.1a Archives

Material often arrives packed. Archives the standard library can read (zip; tar, also gzip, bzip2 or xz
compressed) are read **like folders**: each supported document inside is a scan item whose path is the
archive's path followed by the path inside it (`pack.zip/a/report.docx`). That path is used everywhere a
file path is: the scan list, dialog selection, the "only these files" list, incremental bookkeeping, the
index and the report. An archive named directly on the command line stands for its documents.

- **Nested archives** are opened too, up to 3 levels.
- **Nothing is unpacked in place.** Members are copied into one private temporary folder, which is removed
  when the run ends. The member's stored path is never used to build a file path (a name with `..`, an
  absolute path or a drive letter cannot leave the folder); folders, links and devices are left out.
- **Size limits** guard against archives that unpack to enormous sizes: one member at most 512 MB unpacked,
  the documents of one archive at most 2 GB together. Members over a limit are not opened.
- **Not readable**: encrypted members, damaged archives, archives over the limits and formats that need a
  third-party tool (`.7z`, `.rar`) are listed as failed with the reason; the rest of the archive and the
  batch go on. Legacy formats inside an archive go to "need a new format first" as usual.
- **Names**: zip files made on Chinese Windows store GBK names without the UTF-8 flag; decode them as GBK
  so the paths are readable. Hidden entries and the `__MACOSX` folder are skipped, like hidden files.
- **Times**: a member's file system time is its time stored in the archive. For change detection
  (section 6.3) a member also counts as changed when the archive file itself changed.
- **Output names** follow the member's file name. Files outside archives get their names first, so a new
  archive with a same-named document does not rename existing output.

### 3.2 Word processing documents

Extract:

- **Heading levels.** Read the style definitions and map style id to heading level. Localised office
  suites name styles inconsistently (digits, English words, localised names); accept all of them. When no
  level can be recognised, the text must not be lost.
- **Body paragraphs**, in order.
- **Tables**, as Markdown tables. Escape the column separator inside cells, or the table breaks.
- **Picture positions.** Documents reference pictures through **two different mechanisms** (current
  drawing objects and older vector markup); support both. Some office suites default to the older one,
  and supporting only the newer one loses every picture.
- **Embedded objects** (see 3.5).
- **Content controls and wrappers.** Cover pages, tables of contents and form templates wrap paragraphs
  and tables in content controls; unwrap them or whole blocks disappear silently.
- **Nested tables in cells.** Do not read only a cell's direct paragraphs; keep the nested table's text
  (it may be flattened into one line).
- **Horizontally merged cells.** A cell spanning several columns takes that many columns, or every later
  cell shifts.
- **One copy of text boxes.** Text boxes and shapes often carry a current and a compatibility copy;
  reading both duplicates the text.
- **Both package path forms.** Relationship files may use relative paths or absolute paths inside the
  package (starting with /, as some libraries write them); accepting only one silently skips whole sheets
  or pictures.

### 3.3 Spreadsheets

- Sheet by sheet, keeping sheet names.
- Resolve the shared string table: a cell value may be an index into a string pool, not the text itself.
- Output Markdown tables with a row count.
- **Dates come back as dates.** Spreadsheets store dates as serial numbers and display them through the
  cell format; printing the raw number shows something like 46024. Tell dates, times and date-times apart
  by the format, and support the 1904 date system. Elapsed-time formats (such as [h]:mm) are not dates.

**Drop empty rows**: spreadsheets often carry thousands of formatted but empty rows that would bloat the
output. Also drop trailing columns that are empty in every row.

Cap the rows per sheet (a few thousand); truncate beyond it and say so in the text.
**Empty rows do not count toward the cap**, or leading blanks would push real data out.

### 3.4 Presentations

- Text and pictures of every slide.
- Slides often carry their information in pictures and only a title in text, so both are kept.
- **Detect one special case**: a slide whose chart is drawn with shapes (vector) has no bitmap to export.
  Warn "this slide may hold a chart drawn with shapes; take a screenshot", so the user does not assume the
  content is complete.

### 3.5 Expanding embedded attachments

Word processing documents often embed spreadsheets or sub-documents. These attachments frequently carry
the substance (detail tables, definitions) while the body is only a frame; without them the knowledge base
is badly incomplete.

1. Recognise embedded objects and their real type (magic number again, not the extension).
2. An embedded **spreadsheet** becomes Markdown tables inline at that position.
3. An embedded **sub-document** is parsed recursively for text and tables and inlined. Its headings are
   demoted (to bold text, say) so they do not disturb the main outline. Its pictures are not extracted,
   but their number is stated.
4. An embedded **legacy binary format** or unknown container cannot be opened: insert a clear warning at
   that position and list it as a "hard gap", asking the user to save it by hand and convert it separately.

### 3.6 De-duplicating embedded attachments (essential, or the output explodes)

The same attachment can be referenced in several sections of one document, and each reference stores
its own copy in the package; expanding every copy repeats the same text many times.

- Hash each attachment's **content**; expand the same content in full only once.
- At later occurrences leave one line ("this attachment has the same content as the one above; not
  expanded again") instead of dropping it silently: the reader needs to know a reference is there.
- **Comparing raw bytes is not enough**: the same attachment repackaged has different bytes (time stamps
  and other metadata) but the same content. Hash the parsed text, or both bytes and text.

### 3.7 Mail

Mail is an important source: the body holds the discussion, the attachments the formal documents.

**Header fields**: from, to, cc, date, subject, as a field table. Subjects and names are often MIME encoded
words (Base64 or quoted-printable) and must be decoded, or they come out as gibberish.

**Body**: mails are nested multipart structures; walk them recursively. Prefer the plain-text part; with
only a rich-text part, reduce it to plain text (drop scripts and styles, block tags become line breaks,
decode entities). Decode by the part's declared charset and tolerate **wrong declarations**: mail often
declares one encoding and uses another, so try candidate encodings in turn.

**Attachments**: **not read**; a list below the body records them. Requirements:

- a table with number, attachment name, size and type
- three types: can be converted separately, legacy binary format that needs converting first, unsupported
- a note before the list saying the attachments were not read and how to get their content (save the
  attachment from the mail and convert that file)
- no section when there are no attachments

> Why: attachments recur across forwards and replies; inlining them all duplicates heavily, and their
> importance varies widely, so the user converts the ones that matter. The list tells readers (including
> the AI) that an attachment exists and what it is called, so nobody assumes the mail is complete.

**Pictures**: inline pictures and picture attachments are exported like any picture, with anchors. Mail
pictures are nearly always orphan pictures (no describing text) and are marked as such.

> **Filtering signature icons correctly**: signature logos and divider images must be dropped or they
> drown the list. **Filtering by byte size is wrong**: a 300×200 diagram may compress to under 2 KB.
> Read the **pixel size** from the image header (common bitmap formats keep width and height at fixed
> positions) and filter by that; fall back to byte size only for unknown formats.

The **mail date** is a reliable "last modified" source, on a level with document properties (no
"may be inaccurate" note). Mind the time zone: `-0000` in a mail header means "UTC, sender's zone
unknown", and some date parsers return a naive value for it; treat it as UTC explicitly before converting
to local time, or the result is off by hours.

### 3.8 Duplicate files within a run

The same document often exists in several places (backup folders, archive folders, "copy" suffixes).
Filing them all fills the knowledge base with repetition, wastes context and makes the assistant hit the
same material again and again.

**Two steps**, both before anything is written:

1. **Identical bytes, before parsing.** Hash every file (archive members included). Of a group with the same
   hash only one copy is parsed; the others are not parsed at all. Copy kept: one whose output already
   exists from an earlier run (so incremental runs keep their files), else one outside any archive, else
   the first relative path. When the kept copy fails, its identical copies are listed as failed with the
   same reason.
2. **Identical text, after parsing**, as below.

**Rule** for step 2: duplicates are files whose **extracted text** is identical, not whose bytes are. That
catches "same content, different bytes" (saved again, properties changed, packed with other settings).

The fingerprint must **normalise location information**, or no duplicate is ever found: each picture
anchor holds the copy's own mirrored path (`images/a/x/img_001.png` against `images/b/x/img_001.png`),
and in one-file mode the top heading comes from the file name. Both are **location, not content**;
replace them with placeholders before hashing.

Add the **number of pictures** to the fingerprint, so the same text with different pictures is not taken
for a duplicate.

**Which copy stays**: the newest document time; on a tie, the first relative path in sort order, so
repeated runs give the same result.

**Scope**: only the output changes; **source files are never touched** (deleted work documents cannot be
recovered, and the tool must not take that risk).

**Comparison range**: in full runs, the files of this run only. Incremental runs also compare with text
already filed (see "Across runs" in 6.3).

**Traces** (both required, the same for both steps; a group lists the copies of both kinds):

- the report lists each group: the copy kept and the copies left out, with their times
- the kept copy's text starts with "N more copies with the same content were left out: <paths>", so an
  assistant reading it knows the material exists in several places

**Switch**: on by default, with an option to keep every copy (it turns off both steps).

**Known cost**: step 2 decides after parsing, so copies with different bytes are still parsed in full and
only not written. That is inherent in judging by the text: without parsing there is no text to compare.
Step 1 removes that cost for plain copies, which are the common case.

### 3.9 PDF

PDF is a **lossy intermediate format**; warn the user clearly:

- embedded attachments are gone (converting to PDF drops them)
- vector graphics cannot be extracted
- heading levels are gone

If the original Office document is available, use it: converting from a PDF rebuilds the original from
a lossy copy.

PDF is still supported (sometimes there is nothing else): extract the text layer and the embedded bitmaps;
if the text layer is empty, warn "probably a scan" (the tool does no OCR).

---

## 4. Pictures

### 4.1 Export and anchors

- Pictures go to a separate folder that **mirrors the source folder structure**, which keeps them findable
  by project and avoids name clashes between documents.
- Spaces, brackets and full-width brackets in the mirrored path become underscores, so the path is safe in
  scripts and links. **The Markdown file name keeps the original readable name.**
- An **anchor** marks each picture's position in the text, such as
  `[Image 001: section name, see <relative path>]`
- An option skips exporting pictures: the **anchor stays**, with "image file not exported in this run"
  instead of the path, so a reader knows a picture was there.

### 4.2 Orphan pictures (heuristic)

Definition: an **orphan picture** has no text around it that describes it. Its information exists **only in
the picture**; without it the knowledge base misses that part. Conversely, when the text already lists the
fields and rules shown in a picture, the picture is redundant.

Method: look for referring phrases in the text before and after the picture ("as shown below", "see
figure", "the screen looks like this", and the Chinese equivalents). A hit means "described".

**Tell the user that this is a heuristic and can be wrong**, and:

- **never delete pictures for the user**. Export all of them; only mark likely orphans and list them first.
  Exporting costs nearly nothing; a wrong deletion loses information for good.
- typical mistake: text that says "the names contain the keywords in the picture" counts as "described"
  because it mentions the picture, yet that is exactly the picture that must be looked at (the keyword
  list exists only there).

### 4.3 Contact sheets

To browse many pictures at once, an option tiles them into a grid, each tile labelled with its number
(the same numbers as the image list, so people and an AI can refer to them).

**Tell the user the cost**: an AI usually scales an image down to a maximum long edge, so tiling shrinks
each picture by the grid density. A 4×4 sheet leaves each picture about a quarter of its long edge, and
body text in screenshots becomes unreadable. **A contact sheet is an index, not a replacement**; to have
an AI read a picture closely, give it the single picture.

### 4.4 Picture resolution for an AI

When pages are rendered as images for an AI to read, note that it scales images to a maximum long edge
(around 1500 pixels, varying by product):

- render so the page's long edge lands near that limit; more is waste (slower upload, more cost, no gain)
- use a lossless format: lossy compression rings around text edges and hurts recognition
- **do not stitch pages into long images**: scaled as a whole, each page's text blurs. One page per image
  works best.

---

## 5. Output

### 5.1 Two shapes

**Merged (default)**: the output folder gets **one** Markdown file named after the source folder:

1. first an **index part**: metadata, a document table, each document's opening text and outline
2. then the **text part**: the documents one after another, each under a top-level section heading

Headings inside each document are demoted by one level so they sit under the section heading. Each
section starts with the original path, the document's last-modified time and the extraction time.

**One file per document**: one Markdown file per source document, plus a separate index file.

> Why: merged output is easy to hand to an AI in one go; one file per document is easier to manage.
> Merged is the default because handing over is the main use.

### 5.2 File names

- merged: `<source folder>.md`
- per document: `<source document>.md`; clashing names get a number suffix and the report gives the
  original path
- incremental: `<source folder>_YYYYMMDD_<suffix>.md`; a second run on the same day adds the time, as in
  `<source folder>_YYYYMMDD-HHMM_<suffix>.md`

Labels inside the output (headings, notes, table headers) follow the chosen language (English or Chinese).

### 5.3 Metadata header

Each Markdown file starts with a metadata block holding:

- the source file name
- the **document's last-modified time** and **where it came from** (see 5.4)
- the extraction time
- one sentence telling "document last modified" and "extracted" apart, and saying that the authoritative
  version is given by the revision history in the text

> Why: an assistant reading the knowledge base must judge how current it is. The two times mean entirely
> different things and are easily confused without the note.

### 5.4 Three kinds of time

| Time | Source | Meaning |
| --- | --- | --- |
| document property time | metadata inside the document | how current the **content** is; copying and downloading do not change it |
| file system time | the file's modification or change time | when the **file changed on this machine**; copying refreshes it |
| extraction time | when the tool ran | when the knowledge base was made |

Rules:

- The "document last modified" in the header **prefers the document property time**; without it, fall
  back to the file system time and **say that it is unreliable** (copying may have changed it).
- In index and report tables, fallback times get a visible mark (such as `※`).
- Handle time zones: document metadata is usually stored in UTC and shown converted to local time; accept
  explicit offsets as well.

### 5.5 Reports and index

The **index file** (or the index part of a merged file) is what an AI reads first to decide which document
answers a question:

- a document table: name, last-modified time, original path, characters, pictures
- **sorted by document last-modified time, newest first**
- each document's opening text (the first characters, taken mechanically) and its level 1 and 2 headings
- a clear statement that opening text and headings are extracted mechanically, not summarised

**Batch report**: per document characters, tables, pictures, orphan pictures, status and original path, and
the lists: done, skipped, failed (with reason), needing a new format, excluded by date.

**Image list**: per document, orphan pictures marked and listed first.

---

## 6. Run modes

### 6.1 Dialog mode

Choose a mode first:

1. **Folder batch**: choose a folder -> walk it -> **show the file list to confirm or untick**
   -> choose the output folder -> choose options -> run
2. **Chosen files**: choose files by hand -> the rest as above
3. **Incremental tasks**: manage and run incremental tasks (see 6.3)

The walk skips hidden folders, lock files (the office suite's temporary files) and the tool's own output
folders (or it nests into itself).

Options at least: merge, expand embedded attachments, skip pictures, contact sheets.

**One failing file never stops a batch.** Record the reason in the report and continue. Failure types to
handle: damaged, encrypted, wrong format, parse error.

**Incremental skip**: an existing output is skipped by default, with a "redo everything" option. Skipped
entries **still appear in the index and report**; otherwise after an incremental run the summary files hold
only the few new documents, the history vanishes and the user thinks the knowledge base shrank.

### 6.2 Command-line mode

Arguments mean command-line mode, with no dependency on a desktop. It must work in a scheduler's minimal
environment without a display session.

**Option names**: input methods and copying from web pages can turn two hyphens into a dash (—). They
look alike but are different characters, and parsing fails with an unclear "unknown option: —days".

Two remedies, both required:

1. **a one-letter short option for every long option**; type short options by hand
2. **turn dashes back into two hyphens** while reading the options, so mistakes still run

For the same reason, help texts and documentation show short options in examples.

### 6.3 Incremental tasks

For scheduled runs: process only documents changed "since the last run" or "in the last N days".

**Two time ranges**:

- **watermark (default)**: documents changed after the last successful run. The watermark (time of the
  last run) is stored in the output folder.
- **window**: documents changed in the last N days, ignoring the watermark.

**The watermark must be able to start itself**: if window mode did not write it, watermark mode could
never start. So **every successful run moves the watermark**; only watermark mode reads it. After one window run,
plain runs carry on by themselves.

On a first run without a watermark, do not take the whole history at once; ask the user for a starting
range (and exit with a distinct code, so a caller can start with a default range).

**Which time decides (essential)**: a file copied into the folder keeps its document property time,
which can be older than the watermark; deciding by that time would **miss newly copied files**. Use
**the latest of three times**:

- file system modification time (content rewritten)
- file system change time (file copied in or moved)
- document property time

so both new files in the folder and edited files are found.

**Keep them apart**: this "detection time" is only for **filtering**; the "document last modified" in the
header remains the document property time (how current the content is).

**Boundary duplicates**: the watermark is precise to the minute, so files changed in the same minute as the
last run would be processed twice. Also record the last run's "path + change time" list and leave those out.

**Output behaviour**:

- each run merges what is new into **one** dated file
- **nothing new: exit quietly**, write no empty file, exit code success
- a run log records each run's mode, start, number scanned, number new, output file and duration;
  **a run with nothing new also gets a line** (to show the schedule really runs)
- each batch's report and image list are named after the batch, so the next run does not overwrite them
- on failure **the watermark does not move**; the next run retries the range and nothing is missed
- **a single file failing** (the batch itself succeeds): the watermark moves, but that file is not recorded
  as processed; it goes to a retry list and is processed again next run even though it is older than the
  watermark. After 3 failures in a row it is given up and logged; it comes back once the file changes.
  A batch left with only failing retries writes no empty incremental file, only the report.

**Across runs**: when a folder is moved or renamed, every path and change time changes, the processed
list (keyed by path) no longer matches, and the documents look new although their text is already filed.

Remedies:

- the output folder keeps a **text fingerprint file**: one line per filed document with "text fingerprint,
  original path, output file holding the text"
- the text fingerprint looks at the text only and normalises the metadata header, heading levels (demoted
  when merged), picture anchor paths and whitespace, so a single document's md and its section in a merged
  file give the same value; the file can therefore be rebuilt from earlier output
- in an incremental run, documents whose fingerprint is known are **not written again**; the incremental
  file's index lists them in a path table (current path, old path, file holding the text) and the report
  has a section for them; the moved documents get a new line so the table points to the latest location
- a batch with only such documents still writes an incremental file holding just the table, so the
  knowledge base learns where the documents went
- the decision comes after parsing, so skipped files are still parsed in full (the same cost as in 3.8)
- a separate clean-up tool removes duplicate sections from merged or incremental files made before this
  existed, by the same fingerprint, and builds the fingerprint file; it backs up the file before rewriting,
  writes a report, and never deletes source files or pictures

**Several tasks**: the dialogs keep several incremental tasks (name, source folder, output folder) with
add, edit, delete, run one and run all. Tasks are stored as plain text for direct editing. A task without a
watermark is started automatically (with a default range) instead of failing.

### 6.4 Date filter

Full runs also support "only documents changed after a date". Excluded files do not appear in the
confirmation list, but the report lists them in a section with the date used, the files and their times, so
the user can check nothing was excluded by mistake.

---

## 7. Robustness

### 7.1 Characters and paths

- non-ASCII paths and paths with spaces and brackets work throughout
- configuration and list files are tab-separated (tabs almost never occur in names)
- column separators inside Markdown table cells are escaped

### 7.2 File name encodings (must be handled, or whole batches stop)

Chinese file names copied from Windows are often GBK. Read on Linux, those non-UTF-8 bytes appear as
**surrogate characters**. Writing such a string to a UTF-8 file or to standard output raises a
"surrogates not allowed" encoding error.

Because a failed run does not move the watermark, one such file would make every later scheduled run
fail the same way.

Requirements:

1. **Keep "for opening the file" and "for display and output" apart.** Open files with the string the
   system returned; write repaired strings into output, logs and standard output.
2. **Repair path component by component.** Paths mix UTF-8 folder names with GBK file names; decoding the
   whole string with one encoding garbles it. Split at separators and repair each part.
3. Order: if the string encodes, keep it; otherwise take back the raw bytes and try the common Chinese
   encodings; replacement characters only as the last resort. A correct repair shows the real file name,
   not a row of question marks.
4. **Every write and print has a fallback**: text output tolerates encoding errors, and standard output and
   error are configured to replace what they cannot encode. That is the second line of defence: a missed
   repair shows replacement characters instead of crashing the run.

### 7.3 Shell pitfalls

If the entry script is written in a shell, mind these; in other languages the equivalent logic errors
still apply.

1. **Use a full shell (bash).** A minimal shell fails on arrays and pattern matching.
2. **"No match" exit codes**: text search tools return non-zero when nothing matches. That is a normal
   result; treating it as failure ("on error, fall back to all") triggers the fallback exactly when
   everything was filtered correctly, and incremental de-duplication then takes every file as new.

3. **Counting and empty values**: handle the output and exit code of counting commands on zero results, so
   a variable never holds several lines and breaks a numeric comparison.
4. **Pipes swallow exit codes**: when a run feeds a progress display, its result cannot come back through
   standard output; write it to an agreed temporary file. Likewise, parse machine-readable lines (such as
   `STAT<TAB>key<TAB>value`) rather than human messages, which change with the language.

### 7.4 Environment checks

Check required capabilities at start and give **clear, actionable** messages when one is missing (what is
missing, what to install, or which alternative to use) instead of failing halfway.

---

## 8. Acceptance scenarios

### 8.1 Parsing

1. Word processing: correct heading levels (several style naming conventions), complete tables, pictures
   from both reference mechanisms
2. Embedded spreadsheets are expanded inline, every sheet present
3. Embedded sub-documents are expanded recursively with demoted headings
4. An attachment referenced several times is expanded once, with a pointer at the other positions
5. A spreadsheet with thousands of empty rows: no empty rows and no trailing empty columns in the output
6. Presentations: text and pictures of every slide; slides drawn with shapes are warned about
6a. Mail: MIME-encoded subject decoded; rich-text-only body reduced to plain text; attachments listed, not
    read, with correct types, no section without attachments; signature icons dropped, real diagrams kept;
    damaged or empty mail does not crash
6b. Duplicates: copies with the same content but different bytes are found (anchor paths and file-name
    headings normalised); the newest is kept; the same text with a different number of pictures is **not**
    a duplicate; the left-out copies' md and picture folders are removed; the report and the kept copy both
    record it; with the switch off every copy is kept
6c. Identical bytes: a copy (also one inside an archive) is not parsed; the copy outside the archive is
    kept; the report and the kept copy record it like a text duplicate
6d. Archives: documents in zip and tar.gz archives and in a zip inside a zip are converted with paths like
    `pack.zip/inner.zip/x.pptx`; a member named `../../x.xlsx` is written nowhere outside the temporary
    folder; GBK zip names are readable; encrypted members, damaged archives and `.7z` are listed as failed
    with a reason; no temporary files remain after the run
7. Legacy binary formats: no crash, listed under "need a new format first"
8. Damaged or encrypted files: no crash, listed as failed, other files unaffected

### 8.2 Output structure

9. Merged mode writes one file, index first and text after, with no heading level clashes
10. Every picture anchor points to a path that exists
11. With pictures skipped no picture folder is created, the anchors remain, and the image list is still
    written and says so
12. The metadata header names the time source correctly (document properties / file system with the
    unreliability note)
13. Time zones are converted correctly (UTC metadata shown as local time)

### 8.3 Incremental logic

14. A first run without a watermark explains what to do and does not take the whole history
15. After one window run, plain runs carry on
16. **A document copied in whose own time is long past is detected** (time basis check)
17. An edited file is detected
18. Repeated runs without changes exit quietly and write no empty file
19. Incremental files from successive runs **do not overlap**
20. After an incremental run, the index and report still contain the earlier documents

### 8.4 Environment and robustness

21. The command-line mode works without a desktop and with a minimal environment
22. Short and long options both work; dash forms are corrected
23. Non-ASCII paths and paths with spaces and brackets work throughout
23a. **GBK-encoded Chinese file names**: scanning, parsing, writing and printing never crash; output and
     reports show the correct names, not question marks; such a file does not affect the rest of the batch
24. Large batches (dozens of documents, several folder levels, many identical names) are handled correctly;
    outputs with the same name do not overwrite each other

---

## 9. Out of scope

- **No OCR**: scans only get a "no text layer" note
- **No summarising**: the index's opening text is taken mechanically, not written by an AI
- **No deleting pictures for the user**: likely orphans are marked; all pictures are exported
- **No rich-text fidelity**: layout is not reproduced, only the information
- **No pictures inside the output text**: the output is plain text; pictures are separate files

---

## 10. Glossary

| Term | Meaning |
| --- | --- |
| orphan picture | a picture no surrounding text describes; its information exists only in the picture |
| watermark | the time of the last successful run, kept by incremental mode |
| inline | expand an embedded attachment as text at its position |
| anchor | the text marker of a picture's position |
| hard gap | content known to be unreadable automatically; needs a manual step |
| encoded word | non-ASCII text in a mail header encoded with Base64 or similar |
| detection time | the time used to filter incremental runs (latest of three) |
| document property time | the time recorded in the document's metadata; how current the content is |
