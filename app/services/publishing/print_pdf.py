"""Print-ready PDF interior for Amazon KDP paperbacks.

- Trim sizes from the catalog; no bleed (text-only interior).
- Mirrored margins; the inside (gutter) margin follows KDP's minimums for the final page count (two-pass build).
- All fonts are embedded TrueType (KDP rejects PDFs with non-embedded fonts).
- Title page and every chapter start on a right-hand (recto) page; blank pages carry no header or folio.
- Running heads (author on verso, title on recto) and page numbers in the body only.
"""

import html
import logging
import re
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, TableStyle
from reportlab.platypus.flowables import DocIf, Flowable
from reportlab.platypus.tableofcontents import TableOfContents

from ...catalog import TRIM_SIZES
from ...config import ASSETS_DIR
from .manuscript import Manuscript, inline_segments

logger = logging.getLogger(__name__)

KDP_MIN_PAGES = 24
KDP_MAX_PAGES = 828
FONT = "CrimsonText"

try:  # pyphen ships with textstat; enables proper hyphenation of justified text
    import pyphen  # noqa: F401

    HYPHENATION = "en_US"
except ImportError:  # pragma: no cover
    HYPHENATION = None


def register_fonts() -> str:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return FONT
    fonts = ASSETS_DIR / "fonts"
    pdfmetrics.registerFont(TTFont(FONT, str(fonts / "CrimsonText-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT}-Bold", str(fonts / "CrimsonText-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT}-Italic", str(fonts / "CrimsonText-Italic.ttf")))
    pdfmetrics.registerFont(TTFont(f"{FONT}-BoldItalic", str(fonts / "CrimsonText-BoldItalic.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=f"{FONT}-Bold", italic=f"{FONT}-Italic", boldItalic=f"{FONT}-BoldItalic")
    return FONT


def kdp_inside_margin(pages: int) -> float:
    """KDP minimum inside (gutter) margin in inches for a page count."""
    if pages <= 150:
        return 0.375
    if pages <= 300:
        return 0.5
    if pages <= 500:
        return 0.625
    if pages <= 700:
        return 0.75
    return 0.875


def to_rl(text: str) -> str:
    """ReportLab paragraph markup: escape, then *italic* -> <i>."""
    return "".join(f"<i>{html.escape(s, quote=False)}</i>" if it else html.escape(s, quote=False) for s, it in inline_segments(text))


class Marker(Flowable):
    """Zero-size flowable that records a page role on the document when laid out."""

    def __init__(self, role: str, toc_text: str | None = None):
        super().__init__()
        self.role = role
        self.toc_text = toc_text

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        doc = self.canv._doctemplate
        if self.role == "chapter":
            doc.chapter_pages.add(doc.page)
            if doc.body_start is None:
                doc.body_start = doc.page
        elif self.role == "nofolio":
            doc.nofolio_pages.add(doc.page)


class BookDoc(BaseDocTemplate):
    def __init__(self, filename: str, ms: Manuscript, trim: tuple[float, float], inside: float, **kw):
        self.ms = ms
        self.chapter_pages: set[int] = set()
        self.nofolio_pages: set[int] = set()
        self.body_start: int | None = None
        width, height = trim[0] * inch, trim[1] * inch
        top, bottom, outside = 0.75 * inch, 0.75 * inch, 0.6 * inch
        inside_pt = (inside + 0.25) * inch
        frame_w, frame_h = width - inside_pt - outside, height - top - bottom
        recto = Frame(inside_pt, bottom, frame_w, frame_h, id="recto", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        verso = Frame(outside, bottom, frame_w, frame_h, id="verso", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        # initialFontName: ReportLab otherwise references (non-embedded) Helvetica on every page, which KDP flags.
        super().__init__(filename, pagesize=(width, height), title=ms.title, author=ms.author, subject=ms.subtitle or "",
                         creator="BookPilot", initialFontName=register_fonts(), **kw)
        self.addPageTemplates([
            PageTemplate(id="recto", frames=[recto], onPageEnd=self._decorate, autoNextPageTemplate="verso"),
            PageTemplate(id="verso", frames=[verso], onPageEnd=self._decorate, autoNextPageTemplate="recto"),
        ])
        self._emptyPagesAllowed = 3

    def beforeDocument(self):
        self.chapter_pages, self.nofolio_pages, self.body_start = set(), set(), None
        self.canv._doctemplate = self

    def folio(self, page: int) -> int | None:
        if self.body_start is None or page < self.body_start:
            return None
        return page - self.body_start + 1

    def afterFlowable(self, flowable):
        if isinstance(flowable, Marker) and flowable.toc_text:
            self.notify("TOCEntry", (0, flowable.toc_text, self.folio(self.page) or self.page))

    def _decorate(self, canv, doc):
        page = doc.page
        if doc._curPageFlowableCount == 0 or page in doc.nofolio_pages:
            return  # blank or front-matter page
        folio = doc.folio(page)
        if folio is None:
            return
        width, height = doc.pagesize
        canv.saveState()
        canv.setFont(FONT, 9)
        if page not in doc.chapter_pages:
            head = doc.ms.author.upper() if page % 2 == 0 else doc.ms.title.upper()
            canv.drawCentredString(width / 2, height - 0.5 * inch, head[:70])
        canv.drawCentredString(width / 2, 0.45 * inch, str(folio))
        canv.restoreState()


def _styles(font: str, large_print: bool) -> dict[str, ParagraphStyle]:
    size, leading = (13, 19) if large_print else (11, 15)
    body = ParagraphStyle("Body", fontName=font, fontSize=size, leading=leading, alignment=TA_JUSTIFY,
                          firstLineIndent=0.25 * inch, allowWidows=0, allowOrphans=0)
    if HYPHENATION:
        body.hyphenationLang = HYPHENATION
        body.embeddedHyphenation = 1
        body.uriWasteReduce = 0.3
    return {
        "body": body,
        "first": ParagraphStyle("First", parent=body, firstLineIndent=0),
        "verse": ParagraphStyle("Verse", parent=body, alignment=TA_LEFT, firstLineIndent=0, spaceAfter=leading,
                                hyphenationLang=None),
        "break": ParagraphStyle("Break", parent=body, alignment=TA_CENTER, firstLineIndent=0, spaceBefore=leading * 0.6,
                                spaceAfter=leading * 0.6),
        "label": ParagraphStyle("Label", fontName=font, fontSize=size - 1, leading=size + 4, alignment=TA_CENTER, spaceAfter=6),
        "chapter": ParagraphStyle("Chapter", fontName=f"{font}-Bold", fontSize=size + 9, leading=size + 14, alignment=TA_CENTER,
                                  spaceAfter=0.45 * inch),
        "title": ParagraphStyle("Title", fontName=f"{font}-Bold", fontSize=30, leading=36, alignment=TA_CENTER, spaceAfter=14),
        "subtitle": ParagraphStyle("Subtitle", fontName=f"{font}-Italic", fontSize=14, leading=18, alignment=TA_CENTER),
        "author": ParagraphStyle("Author", fontName=font, fontSize=15, leading=20, alignment=TA_CENTER),
        "small": ParagraphStyle("Small", fontName=font, fontSize=8.5, leading=11.5, alignment=TA_LEFT, spaceAfter=6),
        "dedication": ParagraphStyle("Dedication", fontName=f"{font}-Italic", fontSize=size, leading=leading, alignment=TA_CENTER),
        "heading": ParagraphStyle("Heading", fontName=f"{font}-Bold", fontSize=size + 5, leading=size + 10, alignment=TA_CENTER,
                                  spaceAfter=0.35 * inch),
        "toc": ParagraphStyle("TOC", fontName=font, fontSize=size, leading=leading + 3, leftIndent=0, rightIndent=0.3 * inch),
    }


def _recto_break() -> list:
    """Break to the next page, adding a blank page if that would be a left-hand page."""
    return [PageBreak(), DocIf("doc.page % 2 == 0", [Marker("nofolio"), PageBreak()])]


def _story(ms: Manuscript, trim: tuple[float, float], large_print: bool, with_toc: bool) -> list:
    font = register_fonts()
    st = _styles(font, large_print)
    height = trim[1] * inch
    s: list = []

    # Title page (recto, page 1)
    s += [Marker("nofolio"), Spacer(1, height * 0.22), Paragraph(to_rl(ms.title), st["title"])]
    if ms.subtitle:
        s.append(Paragraph(to_rl(ms.subtitle), st["subtitle"]))
    if ms.series:
        s += [Spacer(1, 8), Paragraph(to_rl(ms.series), st["subtitle"])]
    s += [Spacer(1, height * 0.25), Paragraph(to_rl(ms.author), st["author"])]

    # Copyright page (verso, page 2), set low on the page
    s += [PageBreak(), Marker("nofolio"), Spacer(1, height * 0.3)]
    s += [Paragraph(to_rl(line), st["small"]) for line in ms.copyright_lines]

    if ms.dedication:
        s += _recto_break() + [Marker("nofolio"), Spacer(1, height * 0.25), Paragraph(to_rl(ms.dedication), st["dedication"])]

    if with_toc:
        # Table cells default to (non-embedded) Helvetica even when they hold paragraphs.
        toc = TableOfContents(dotsMinLevel=0, tableStyle=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("FONTNAME", (0, 0), (-1, -1), font),
        ]))
        toc.levelStyles = [st["toc"]]
        s += _recto_break() + [Marker("nofolio"), Spacer(1, 0.6 * inch), Paragraph("Contents", st["heading"]), toc]

    for part in ms.parts:
        s += _recto_break()
        s += [Marker("chapter", toc_text=html.escape(part.toc_title or ms.title)), Spacer(1, 1.4 * inch)]
        if part.label:
            s.append(Paragraph(html.escape(part.label.upper()), st["label"]))
        s.append(Paragraph(to_rl(part.title), st["chapter"]) if part.title else Spacer(1, 0.45 * inch))
        for b in part.blocks:
            if b.kind == "break":
                s.append(Paragraph("*&nbsp;&nbsp;&nbsp;*&nbsp;&nbsp;&nbsp;*", st["break"]))
            elif b.kind == "verse":
                s.append(Paragraph("<br/>".join(to_rl(line) for line in b.text.split("\n")), st["verse"]))
            else:
                s.append(Paragraph(to_rl(b.text), st["first" if b.first else "body"]))

    for heading, text in (("Acknowledgments", ms.acknowledgments), ("About the Author", ms.author_bio)):
        if text:
            s += _recto_break() + [Marker("chapter"), Spacer(1, 1.0 * inch), Paragraph(heading, st["heading"])]
            s += [Paragraph(to_rl(p), st["first"] if i == 0 else st["body"])
                  for i, p in enumerate(re.split(r"\n\s*\n", text)) if p.strip()]
    return s


def build_print_pdf(ms: Manuscript, output: Path, *, trim_key: str = "6x9", large_print: bool = False) -> dict:
    if trim_key not in TRIM_SIZES:
        raise ValueError(f"Unknown trim size '{trim_key}'")
    trim = TRIM_SIZES[trim_key]
    with_toc = (not ms.fiction) or ms.structure in ("stories", "poems")
    output.parent.mkdir(parents=True, exist_ok=True)

    inside = 0.375
    pages = 0
    for _ in range(3):  # converge the gutter on the final page count
        doc = BookDoc(str(output), ms, trim, inside)
        doc.multiBuild(_story(ms, trim, large_print, with_toc))
        pages = doc.page
        needed = kdp_inside_margin(pages)
        if needed <= inside:
            break
        inside = needed

    warnings = []
    if pages < KDP_MIN_PAGES:
        warnings.append(f"{pages} pages is below KDP's paperback minimum of {KDP_MIN_PAGES}. Publish as ebook only, "
                        "use a smaller trim size, or turn on large print.")
    if pages > KDP_MAX_PAGES:
        warnings.append(f"{pages} pages exceeds KDP's paperback maximum of {KDP_MAX_PAGES}. Use a larger trim size or split the book.")
    return {
        "page_count": pages,
        "trim_size": trim_key,
        "inside_margin_in": inside + 0.25,
        "kdp_min_inside_margin_in": kdp_inside_margin(pages),
        "fonts_embedded": True,
        "warnings": warnings,
        "valid": not warnings,
    }
