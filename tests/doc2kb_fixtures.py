"""Small Office, mail and PDF files built with the standard library, for the doc2kb tests.

Each builder writes one file and returns its path. The content is fictional and covers the
cases the converter must handle: headings by style, tables with merged and nested cells,
content controls, both image mechanisms, embedded workbooks (one referenced twice) and an
embedded document, dates in a workbook, blank rows, slides with and without text, and a
MIME mail with an encoded subject, an HTML-only body, an inline image and an attachment.
"""
import os
import struct
import zipfile
import zlib

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
V = "urn:schemas-microsoft-com:vml"
O = "urn:schemas-microsoft-com:office:office"
CORE = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dcterms="http://purl.org/dc/terms/">'
        '<dcterms:modified>{}</dcterms:modified></cp:coreProperties>')


def png(width, height, shade=0):
    """A valid grey PNG of the given size."""
    raw = b"".join(b"\x00" + bytes([shade % 256]) * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _rels(items):
    body = "".join(f'<Relationship Id="{i}" Type="x" Target="{t}"/>' for i, t in items)
    return f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PR}">{body}</Relationships>'


def _zip(path, parts):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        for name, data in parts.items():
            z.writestr(name, data)
    return path


def xlsx_bytes(rows_by_sheet, dates=True):
    """A workbook: {sheet name: [[cell, ...], ...]}; ints stay numbers, the string 'DATE' becomes
    a date cell (serial 46024 = 2026-01-02), None leaves the cell out."""
    import io
    shared, index = [], {}
    sheets_xml = []
    for rows in rows_by_sheet.values():
        out = []
        for r, row in enumerate(rows, 1):
            cells = []
            for c, val in enumerate(row):
                ref = chr(ord("A") + c) + str(r)
                if val is None:
                    continue
                if val == "DATE":
                    cells.append(f'<c r="{ref}" s="1"><v>46024</v></c>')
                elif isinstance(val, int):
                    cells.append(f'<c r="{ref}"><v>{val}</v></c>')
                else:
                    if val not in index:
                        index[val] = len(shared)
                        shared.append(val)
                    cells.append(f'<c r="{ref}" t="s"><v>{index[val]}</v></c>')
            out.append(f'<row r="{r}">{"".join(cells)}</row>')
        sheets_xml.append(f'<worksheet xmlns="{S}"><sheetData>{"".join(out)}</sheetData></worksheet>')
    names = list(rows_by_sheet)
    wb = (f'<workbook xmlns="{S}" xmlns:r="{R}"><sheets>'
          + "".join(f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
          + "</sheets></workbook>")
    sst = (f'<sst xmlns="{S}">' + "".join(f"<si><t>{s}</t></si>" for s in shared) + "</sst>")
    styles = (f'<styleSheet xmlns="{S}"><cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>'
              if dates else f'<styleSheet xmlns="{S}"/>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", wb)
        # absolute targets, as some exporters write them
        z.writestr("xl/_rels/workbook.xml.rels",
                   _rels([(f"rId{i}", f"/xl/worksheets/sheet{i}.xml") for i in range(1, len(names) + 1)]))
        z.writestr("xl/sharedStrings.xml", sst)
        z.writestr("xl/styles.xml", styles)
        for i, x in enumerate(sheets_xml, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", x)
    return buf.getvalue()


def _p(text, style=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _img_p(rid, vml=False):
    if vml:
        return f'<w:p><w:r><w:pict><v:shape><v:imagedata r:id="{rid}"/></v:shape></w:pict></w:r></w:p>'
    return f'<w:p><w:r><w:drawing><a:blip r:embed="{rid}"/></w:drawing></w:r></w:p>'


def _ole_p(rid):
    return f'<w:p><w:r><w:object><o:OLEObject r:id="{rid}"/></w:object></w:r></w:p>'


def _doc(body):
    return (f'<w:document xmlns:w="{W}" xmlns:r="{R}" xmlns:a="{A}" xmlns:v="{V}" xmlns:o="{O}">'
            f"<w:body>{body}</w:body></w:document>")


STYLES = (f'<w:styles xmlns:w="{W}">'
          '<w:style w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>'
          '<w:style w:styleId="2"><w:name w:val="heading 2"/></w:style>'
          '<w:style w:styleId="a3"><w:name w:val="标题 3"/></w:style></w:styles>')


def docx(path, english=False, modified="2026-03-04T05:06:07Z", intro=None):
    """A report with headings, a merged-cell table with a nested table, a content control,
    one described and one undescribed picture (DrawingML and VML), the same workbook embedded
    twice, an embedded document and an old-format embedded object."""
    if english:
        t = dict(h1="Project Atlas report", h2="Scope", h3="Details", intro="This report covers the pilot.",
                 described="The menu is shown below.", plain="Owner list follows.", cover="Cover text",
                 a="Item", b="Value", nested="inner")
        t["intro"] = intro or t["intro"]
    else:
        t = dict(h1="示例项目报告", h2="范围", h3="细节", intro="本报告说明试点情况。",
                 described="菜单如下图所示。", plain="负责人名单如下。", cover="封面文字",
                 a="项目", b="数值", nested="内层")
    nested = (f"<w:tbl><w:tr><w:tc>{_p(t['nested'] + '1')}</w:tc><w:tc>{_p(t['nested'] + '2')}</w:tc></w:tr></w:tbl>")
    table = ("<w:tbl>"
             f"<w:tr><w:tc>{_p(t['a'])}</w:tc><w:tc>{_p(t['b'])}</w:tc><w:tc>{_p('C')}</w:tc></w:tr>"
             f'<w:tr><w:tc><w:tcPr><w:gridSpan w:val="2"/></w:tcPr>{_p("x|y")}</w:tc><w:tc>{nested}</w:tc></w:tr>'
             "</w:tbl>")
    body = (_p(t["h1"], "Heading1") + _p(t["intro"])
            + f"<w:sdt><w:sdtContent>{_p(t['cover'])}</w:sdtContent></w:sdt>"
            + _p(t["h2"], "2") + _p(t["described"]) + _img_p("rId1")
            + _p(t["h3"], "a3") + table + _p(t["plain"]) + _img_p("rId2", vml=True)
            + _ole_p("rId3") + _ole_p("rId4") + _ole_p("rId5") + _ole_p("rId6"))
    book = xlsx_bytes({"Sheet1": [["k", "v"], ["a", 1], ["d", "DATE"]]})
    inner_doc = _inner_docx(t)
    parts = {
        "word/document.xml": _doc(body),
        "word/styles.xml": STYLES,
        "word/_rels/document.xml.rels": _rels([("rId1", "media/image1.png"), ("rId2", "media/image2.png"),
                                               ("rId3", "embeddings/book1.xlsx"), ("rId4", "embeddings/book2.xlsx"),
                                               ("rId5", "embeddings/inner.docx"), ("rId6", "embeddings/old.bin")]),
        "word/media/image1.png": png(300, 200, 10),
        "word/media/image2.png": png(320, 240, 20),
        "word/embeddings/book1.xlsx": book,
        "word/embeddings/book2.xlsx": book,
        "word/embeddings/inner.docx": inner_doc,
        "word/embeddings/old.bin": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64,
        "docProps/core.xml": CORE.format(modified),
    }
    return _zip(path, parts)


def _inner_docx(t):
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", _doc(_p(t["h2"] + "!", "Heading1") + _p(t["intro"])))
        z.writestr("word/styles.xml", STYLES)
    return buf.getvalue()


def xlsx(path, english=False):
    """Two sheets; the first has a date cell, trailing empty columns and many blank rows."""
    name = "Data" if english else "数据"
    rows = [["Name" if english else "名称", "Date" if english else "日期", None], ["a", "DATE"], ["b", 7]]
    rows += [[None, None, None]] * 60 + [["c", 8]]
    parts = _unzip(xlsx_bytes({name: rows, "Two": [["x", "y"]]}))
    parts["docProps/core.xml"] = CORE.format("2026-02-01T00:00:00Z")
    return _zip(path, parts)


def _unzip(data):
    import io
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist()}


def pptx(path, english=False):
    """Slide 1: text and a picture; slide 2: shapes only, no text (a drawn chart)."""
    title = "Quarterly plan" if english else "季度计划"
    s1 = (f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:cSld><p:spTree>'
          f"<p:sp><p:txBody><a:p><a:r><a:t>{title}</a:t></a:r></a:p></p:txBody></p:sp>"
          '<p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill></p:pic>'
          "</p:spTree></p:cSld></p:sld>")
    s2 = (f'<p:sld xmlns:p="{P}" xmlns:a="{A}"><p:cSld><p:spTree><p:sp/><p:sp/></p:spTree></p:cSld></p:sld>')
    return _zip(path, {
        "ppt/slides/slide1.xml": s1, "ppt/slides/slide2.xml": s2,
        "ppt/slides/_rels/slide1.xml.rels": _rels([("rId1", "../media/image1.png")]),
        "ppt/media/image1.png": png(400, 300, 30),
        "docProps/core.xml": CORE.format("2026-01-05T08:00:00Z"),
    })


def eml(path, english=False):
    """HTML-only body, an inline picture, a tiny signature icon and an attachment."""
    import base64
    subject = "=?utf-8?B?" + base64.b64encode(("Weekly sync" if english else "周会纪要").encode()).decode() + "?="
    hello = "Hello team" if english else "大家好"
    html = f"<html><body><p>{hello}</p><p>Line two &amp; more</p><script>x()</script></body></html>"
    big = base64.b64encode(png(400, 300, 40)).decode()
    tiny = base64.b64encode(png(20, 20, 50)).decode()
    att = base64.b64encode(b"PK\x03\x04 not really a document").decode()
    text = (f"From: Alice <alice@example.com>\nTo: Bob <bob@example.com>\nSubject: {subject}\n"
            "Date: Tue, 03 Mar 2026 10:00:00 -0000\nMIME-Version: 1.0\n"
            'Content-Type: multipart/mixed; boundary="B"\n\n'
            '--B\nContent-Type: text/html; charset="utf-8"\n\n' + html + "\n"
            '--B\nContent-Type: image/png\nContent-Disposition: inline; filename="chart.png"\n'
            "Content-Transfer-Encoding: base64\n\n" + big + "\n"
            '--B\nContent-Type: image/png\nContent-Disposition: inline; filename="logo.png"\n'
            "Content-Transfer-Encoding: base64\n\n" + tiny + "\n"
            '--B\nContent-Type: application/octet-stream\nContent-Disposition: attachment; filename="plan.docx"\n'
            "Content-Transfer-Encoding: base64\n\n" + att + "\n--B--\n")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


def pdf(path, lines):
    """A one-page PDF with a text layer (ASCII only, Helvetica)."""
    content = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(
        "(" + ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '" for ln in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>",
            "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
             "/Contents 5 0 R >>"),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"]
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    with open(path, "wb") as f:
        f.write(out)
    return path


def build_all(folder, english=False):
    """Every fixture in one folder; returns {kind: path}."""
    os.makedirs(folder, exist_ok=True)
    tag = "en" if english else "zh"
    out = {
        "docx": docx(os.path.join(folder, f"report-{tag}.docx"), english),
        "xlsx": xlsx(os.path.join(folder, f"book-{tag}.xlsx"), english),
        "pptx": pptx(os.path.join(folder, f"slides-{tag}.pptx"), english),
        "eml": eml(os.path.join(folder, f"mail-{tag}.eml"), english),
        "pdf": pdf(os.path.join(folder, f"notes-{tag}.pdf"), [f"Project Atlas notes ({tag})"] + [f"Line {i} of the minutes" for i in range(30)]),
    }
    with open(os.path.join(folder, f"legacy-{tag}.doc"), "wb") as f:
        f.write(b"\xd0\xcf\x11\xe0")
    out["legacy"] = os.path.join(folder, f"legacy-{tag}.doc")
    return out
