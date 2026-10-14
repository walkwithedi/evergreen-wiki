# Converting uploads to Markdown

Reading an Office or PDF file directly costs many tokens and is slow. With conversion on, a script turns each file into Markdown first, and you read only that text. Everything after Check 1 (placement, cleaning, duplicates, triggers) is unchanged.

When: _kb.json convert.enabled is true, or the user asks for conversion in this request. Skip it when the user says not to convert this batch. Without Python there is no conversion: read the originals and put "Conversion: not run (no Python)" in the delivery note.

## 1. Convert

Take the limits from the library (python3 scripts/kbconf.py show <library root or _kb.json>, key convert), then:

  python3 scripts/convert.py <work>/converted <file> [<file> ...] --lang <library language> --image-limit <image_limit> --min-pdf-chars <min_pdf_chars_per_page> --min-chars-per-image <min_chars_per_image> --outline-chars <outline_chars>

Pass every uploaded file of the batch in one run, so the picture count covers the batch. One line per file:
- converted: read <work>/converted/<name>.md and never the original. That text is the material from here on; step 2.1 cleans it like any other material.
- fallback: read the original as before. The reason says why: the conversion failed, a PDF has little text per page (probably a scan), or the document is mostly pictures. For "mostly pictures", the converted text plus every picture in its image folder is the same content as the original and cheaper to read; read the pictures whatever the picture decision below says.
- as-is: a format the script does not convert (pictures, plain text, legacy .doc/.xls/.ppt); read it as before. Not a failure.

### Outline first

A converted file longer than outline_chars also has "| outline <path>" on its line: <work>/converted/<name>.outline.txt with its size, the opening text and its headings with their line numbers in <name>.md. Read the outline first, not the converted file. The topic file still gets the whole text: the body file is cleaned from the converted file and assembled by script (SKILL.md), so nothing is lost by not reading it.

Read the full text, or the sections concerned by their line numbers, when any of these holds:
- the material is on the params close-reading list (step 3 reads it section by section);
- a status-card search below hits, or the outline shows the material touches a status-card item or a trigger class (step 5 must quote the material, never the outline);
- the outline does not settle partition, topic, type or the version relation (steps 1 and 4);
- its pictures are to be read (section 2).

Two searches are required for every file handled from its outline, in its converted text, with your search tool, never by reading it through:
- Entities: search every Table E name and alias. Each hit is a candidate for the entity fields, mapped as entity-yaml.md says, together with the entities the outline shows.
- Status card: search the subjects of the status-card items (names of systems, projects, bodies, indicators, deadlines). Read the section around every hit before judging the triggers. Only when nothing hits is there no trigger from this file.

In doubt, read the full text. Count how many files were handled from their outline and how many read in full.

A file with warnings: <work>/converted/convert.json lists them. Record those that say content could not be read (an embedded object that could not be opened, slides drawn with shapes, a sheet cut off) as issues, like unreadable parts of any material.

Conversion is not an edit of the source text (hard rule 5). Step 4 still hashes the original upload (--file <original>), never the converted file.

## 2. Pictures

Each picture in a converted file is one placeholder line, "[Image: <file>]" ("[图片：<file>]" in Chinese), and the file is in <work>/converted/images/<name>/. The last line of the script's output counts the pictures in converted files against the image limit:

- read (at or under the limit): open each picture and replace its placeholder line with what it shows: every text, number and label in it, as text or a table; one sentence for a photo or decoration. Keep the file name at the start, for example "[Image: img_003.png] Login page with fields user name, password and a Sign in button".
- ask (over the limit): before going on, ask the user once, as a choice between two answers: "<N> pictures in <M> files. Read them all (more time and tokens) / leave placeholders". The answer covers the whole batch.
  - Read them: as under "read".
  - Leave placeholders: the placeholder lines stay in the text. For each file record "pictures not read: <count>" as an issue.

Pictures inside a fallback file are read as part of the original, whatever was decided here.

## 3. Report

Add one line to the delivery note (the readme's issue section gets the per-file issues as usual):
  Conversion: <n> converted, <n> read as originals (<file: reason>; ...), <n> as is | outline: <n> from the outline, <n> read in full | pictures: <read n / not read n / none>
