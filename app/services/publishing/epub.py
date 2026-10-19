"""EPUB 3 export accepted by Apple Books, Amazon KDP (ebook), Kobo and Google Play Books."""

import html
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from ebooklib import epub

from ...config import settings
from .manuscript import Manuscript, to_html

logger = logging.getLogger(__name__)

CSS = """
body { margin: 0 4%; line-height: 1.5; orphans: 2; widows: 2; }
p { margin: 0; text-indent: 1.4em; text-align: justify; hyphens: auto; -webkit-hyphens: auto; }
p.first { text-indent: 0; }
p.break { text-indent: 0; text-align: center; margin: 1.2em 0; letter-spacing: 0.4em; }
div.verse p { text-indent: 0; text-align: left; margin: 0 0 1em 0; hyphens: none; }
section.part { page-break-before: always; break-before: page; }
p.part-label { text-indent: 0; text-align: center; text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.85em; margin-top: 3em; }
h1.part-title { text-align: center; font-weight: normal; font-size: 1.6em; line-height: 1.25; margin: 0.4em 0 2em 0; }
h1.part-title.solo { margin-top: 3em; }
.titlepage { text-align: center; margin-top: 25%; }
.titlepage h1 { font-size: 2em; font-weight: normal; margin-bottom: 0.3em; }
.titlepage p.subtitle { text-indent: 0; text-align: center; font-style: italic; margin-bottom: 2.5em; }
.titlepage p.author { text-indent: 0; text-align: center; font-size: 1.15em; letter-spacing: 0.1em; text-transform: uppercase; }
.copyright p { text-indent: 0; text-align: left; font-size: 0.8em; margin-bottom: 0.8em; }
.dedication { margin-top: 30%; text-align: center; }
.dedication p { text-indent: 0; text-align: center; font-style: italic; }
.backmatter h2 { text-align: center; font-weight: normal; margin: 3em 0 1.5em; }
.backmatter p { margin-bottom: 0.6em; }
nav#toc ol { list-style-type: none; padding-left: 0; }
nav#toc li { margin: 0.4em 0; }
"""


def _blocks_html(part) -> str:
    out = []
    verse_open = False
    for b in part.blocks:
        if b.kind == "verse":
            if not verse_open:
                out.append('<div class="verse">')
                verse_open = True
            lines = "<br/>".join(to_html(line) for line in b.text.split("\n"))
            out.append(f"<p>{lines}</p>")
            continue
        if verse_open:
            out.append("</div>")
            verse_open = False
        if b.kind == "break":
            out.append('<p class="break">* * *</p>')
        else:
            out.append(f'<p class="{"first" if b.first else "body"}">{to_html(b.text)}</p>')
    if verse_open:
        out.append("</div>")
    return "\n".join(out)


def _page(uid: str, file_name: str, title: str, body: str, lang: str, css: epub.EpubItem, epub_type: str) -> epub.EpubHtml:
    item = epub.EpubHtml(uid=uid, file_name=file_name, title=title, lang=lang)
    item.content = f'<section epub:type="{epub_type}">{body}</section>'
    item.add_item(css)
    return item


def build_epub(ms: Manuscript, output: Path, cover_bytes: bytes | None) -> dict:
    book = epub.EpubBook()
    book.set_identifier(ms.identifier)
    book.set_title(ms.title)
    book.set_language(ms.language.split("-")[0] if ms.language else "en")
    book.add_author(ms.author)
    if ms.publisher:
        book.add_metadata("DC", "publisher", ms.publisher)
    book.add_metadata("DC", "date", str(ms.year))
    if ms.description:
        book.add_metadata("DC", "description", ms.description)
    for kw in ms.keywords[:7]:
        book.add_metadata("DC", "subject", kw)
    book.add_metadata("DC", "rights", f"Copyright © {ms.year} {ms.author}. All rights reserved.")
    if ms.series:
        book.add_metadata(None, "meta", ms.series.split(",")[0], {"property": "belongs-to-collection", "id": "series"})
        book.add_metadata(None, "meta", "series", {"refines": "#series", "property": "collection-type"})

    css = epub.EpubItem(uid="style", file_name="styles/book.css", media_type="text/css", content=CSS.encode("utf-8"))
    book.add_item(css)

    spine: list = []
    if cover_bytes:
        book.set_cover("images/cover.jpg", cover_bytes, create_page=True)
        spine.append("cover")

    lang = ms.language
    title_body = f'<div class="titlepage"><h1>{html.escape(ms.title)}</h1>'
    if ms.subtitle:
        title_body += f'<p class="subtitle">{html.escape(ms.subtitle)}</p>'
    if ms.series:
        title_body += f'<p class="subtitle">{html.escape(ms.series)}</p>'
    title_body += f'<p class="author">{html.escape(ms.author)}</p></div>'
    title_page = _page("titlepage", "title.xhtml", "Title Page", title_body, lang, css, "titlepage")
    copyright_page = _page(
        "copyright", "copyright.xhtml", "Copyright",
        '<div class="copyright">' + "".join(f"<p>{html.escape(line)}</p>" for line in ms.copyright_lines) + "</div>",
        lang, css, "copyright-page",
    )
    front = [title_page, copyright_page]
    if ms.dedication:
        front.append(_page("dedication", "dedication.xhtml", "Dedication",
                           f'<div class="dedication"><p>{to_html(ms.dedication)}</p></div>', lang, css, "dedication"))
    for item in front:
        book.add_item(item)
    spine += front

    nav = epub.EpubNav()
    nav.add_item(css)
    book.add_item(nav)
    book.add_item(epub.EpubNcx())
    if ms.show_toc:
        spine.append("nav")

    toc = []
    body_items = []
    for i, part in enumerate(ms.parts, start=1):
        heading = ""
        if part.label:
            heading += f'<p class="part-label">{html.escape(part.label)}</p>'
        if part.title:
            heading += f'<h1 class="part-title{"" if part.label else " solo"}">{html.escape(part.title)}</h1>'
        item = _page(f"part{i:03d}", f"part{i:03d}.xhtml", part.toc_title or ms.title,
                     f'<section class="part">{heading}{_blocks_html(part)}</section>', lang, css, "bodymatter chapter")
        book.add_item(item)
        body_items.append(item)
        toc.append(epub.Link(item.file_name, part.toc_title or ms.title, item.id))
    spine += body_items

    back = []
    if ms.acknowledgments:
        back.append(_page("acknowledgments", "acknowledgments.xhtml", "Acknowledgments",
                          '<div class="backmatter"><h2>Acknowledgments</h2>' +
                          "".join(f"<p>{to_html(p)}</p>" for p in ms.acknowledgments.split("\n\n") if p.strip()) + "</div>",
                          lang, css, "acknowledgments"))
    if ms.author_bio:
        back.append(_page("about", "about.xhtml", "About the Author",
                          '<div class="backmatter"><h2>About the Author</h2>' +
                          "".join(f"<p>{to_html(p)}</p>" for p in ms.author_bio.split("\n\n") if p.strip()) + "</div>",
                          lang, css, "appendix"))
    for item in back:
        book.add_item(item)
        toc.append(epub.Link(item.file_name, item.title, item.id))
    spine += back

    book.toc = toc
    book.spine = spine
    book.guide = [{"type": "text", "href": body_items[0].file_name, "title": "Start"}] if body_items else []
    if cover_bytes:
        book.guide.insert(0, {"type": "cover", "href": "cover.xhtml", "title": "Cover"})

    output.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output), book, {"epub3_pages": False})
    return validate_epub(output)


def validate_epub(path: Path) -> dict:
    """Run epubcheck (the validator Apple and other stores use) when configured."""
    jar = settings.EPUBCHECK_JAR
    if not jar or not Path(jar).exists() or not shutil.which("java"):
        return {"tool": None, "note": "epubcheck not configured; set EPUBCHECK_JAR to validate before uploading to Apple Books."}
    try:
        # epubcheck prints a text summary on stdout too, so the JSON report goes to its own file.
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.json"
            proc = subprocess.run(["java", "-jar", jar, str(path), "--json", str(report_path)],
                                  capture_output=True, text=True, timeout=180)
            if not report_path.exists():
                raise RuntimeError((proc.stderr or proc.stdout or "epubcheck produced no report").strip()[:500])
            report = json.loads(report_path.read_text(encoding="utf-8"))
        messages = [
            {"severity": m.get("severity"), "id": m.get("ID"), "message": m.get("message"),
             "location": (m.get("locations") or [{}])[0].get("path")}
            for m in report.get("messages", [])
        ]
        errors = sum(1 for m in messages if m["severity"] in ("ERROR", "FATAL"))
        warnings = sum(1 for m in messages if m["severity"] == "WARNING")
        return {"tool": "epubcheck", "valid": errors == 0, "errors": errors, "warnings": warnings, "messages": messages[:50]}
    except Exception as e:
        logger.warning("epubcheck failed: %s", e)
        return {"tool": "epubcheck", "valid": None, "error": str(e)}
