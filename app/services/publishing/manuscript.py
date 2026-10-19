"""Format-independent manuscript assembly shared by all exporters (EPUB, print PDF, DOCX, TXT)."""

import html
import re
from dataclasses import dataclass, field
from datetime import date

from ...catalog import get_category
from ...db.models import Book, Chapter
from ..qa.fixes import normalize_typography
from ..text import is_scene_break, paragraphs

NUMBER_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve",
                "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty"]
TENS = {2: "Twenty", 3: "Thirty", 4: "Forty", 5: "Fifty", 6: "Sixty", 7: "Seventy", 8: "Eighty", 9: "Ninety"}
ITALIC_RE = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")


def number_to_words(n: int) -> str:
    if 0 <= n < len(NUMBER_WORDS):
        return NUMBER_WORDS[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return TENS[tens] + (f"-{NUMBER_WORDS[ones]}" if ones else "")
    return str(n)


@dataclass
class Block:
    kind: str  # para | break | verse
    text: str  # may contain *italic* markup
    first: bool = False  # first paragraph after a heading or scene break (no indent)


@dataclass
class Part:
    number: int | None
    label: str  # e.g. "Chapter One" ("" for untitled sections)
    title: str
    blocks: list[Block]

    @property
    def toc_title(self) -> str:
        if self.label and self.title:
            return f"{self.label}: {self.title}"
        return self.title or self.label


@dataclass
class Manuscript:
    title: str
    subtitle: str | None
    author: str
    language: str
    identifier: str
    publisher: str | None
    year: int
    description: str | None
    series: str | None
    fiction: bool
    structure: str
    copyright_lines: list[str]
    dedication: str | None
    parts: list[Part]
    acknowledgments: str | None
    author_bio: str | None
    keywords: list[str] = field(default_factory=list)
    show_toc: bool = True


def inline_segments(text: str) -> list[tuple[str, bool]]:
    """Split text into (segment, is_italic) pairs from *italic* markup."""
    out: list[tuple[str, bool]] = []
    pos = 0
    for m in ITALIC_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos : m.start()], False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def to_html(text: str) -> str:
    return "".join(f"<em>{html.escape(s)}</em>" if it else html.escape(s) for s, it in inline_segments(text))


def to_plain(text: str) -> str:
    return "".join(s for s, _ in inline_segments(text))


def to_blocks(content: str, *, verse: bool) -> list[Block]:
    """Split text into typeset blocks. Typography (curly quotes, ellipses, dashes) is normalised for output only;
    the stored manuscript is left untouched."""
    blocks: list[Block] = []
    first = True
    for p in paragraphs(normalize_typography(content)):
        if is_scene_break(p):
            if blocks and blocks[-1].kind != "break":
                blocks.append(Block("break", "* * *"))
            first = True
            continue
        if verse:
            blocks.append(Block("verse", p.strip("\n"), first))
        else:
            blocks.append(Block("para", re.sub(r"\s*\n\s*", " ", p), first))
        first = False
    while blocks and blocks[-1].kind == "break":
        blocks.pop()
    return blocks


def copyright_lines(book: Book, fiction: bool, kind: str, poetry: bool = False) -> list[str]:
    year = book.publication_year or date.today().year
    holder = book.copyright_holder or book.author_name or "the author"
    lines = [f"{book.title}"]
    if book.subtitle:
        lines.append(book.subtitle)
    lines.append(f"Copyright © {year} {holder}")
    lines.append("All rights reserved.")
    lines.append(
        "No part of this book may be reproduced, stored in a retrieval system, or transmitted in any form or by any means "
        "without the prior written permission of the copyright holder, except for brief quotations in reviews."
    )
    if fiction and not poetry:
        lines.append(
            "This is a work of fiction. Names, characters, places and incidents are products of the author's imagination "
            "or are used fictitiously. Any resemblance to actual persons, living or dead, events or locales is entirely coincidental."
        )
    else:
        lines.append(
            "This book is for informational purposes only and is not a substitute for professional advice. The author and "
            "publisher disclaim liability for any loss or damage arising from the use of its contents."
        )
    isbn = book.isbn_print if kind == "print" else book.isbn_ebook
    if isbn:
        lines.append(f"ISBN: {isbn}")
    if book.edition:
        lines.append(book.edition)
    if book.publisher:
        lines.append(f"Published by {book.publisher}")
    return lines


def build_manuscript(book: Book, chapters: list[Chapter], kind: str = "ebook") -> Manuscript:
    category = get_category(book.category)
    chapters = sorted(chapters, key=lambda c: c.number)
    verse = category.structure == "poems"
    parts: list[Part] = []
    if category.structure == "scenes":
        # A short story reads as one continuous piece; parts become scene breaks.
        joined = "\n\n* * *\n\n".join(c.content for c in chapters if c.content.strip())
        parts.append(Part(number=None, label="", title=book.title, blocks=to_blocks(joined, verse=False)))
    else:
        for c in chapters:
            if category.structure == "chapters":
                label = f"Chapter {number_to_words(c.number)}"
            else:
                label = ""
            parts.append(Part(number=c.number, label=label, title=c.title, blocks=to_blocks(c.content, verse=verse)))
    isbn = book.isbn_print if kind == "print" else book.isbn_ebook
    series = f"{book.series_name}, Book {book.series_number}" if book.series_name and book.series_number else book.series_name
    return Manuscript(
        title=book.title,
        subtitle=book.subtitle,
        author=book.author_name or "Anonymous",
        language=book.language or "en-US",
        identifier=f"urn:isbn:{isbn}" if isbn else f"urn:uuid:{book.id}",
        publisher=book.publisher,
        year=book.publication_year or date.today().year,
        description=book.description,
        series=series,
        fiction=category.fiction,
        structure=category.structure,
        copyright_lines=copyright_lines(book, category.fiction, kind, poetry=verse),
        dedication=book.dedication,
        parts=parts,
        acknowledgments=book.acknowledgments,
        author_bio=book.author_bio,
        keywords=list(book.keywords or []),
        show_toc=category.structure != "scenes",
    )
