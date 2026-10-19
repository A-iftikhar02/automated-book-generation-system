"""Cover generation.

- Ebook cover: 1600 x 2560 JPEG (Amazon's recommended 1:1.6 ratio; Apple Books accepts it too).
- Artwork comes from an OpenRouter image model (optional) or a genre-coloured gradient; title/author are
  typeset by us because image models misspell text.
- Paperback full-wrap cover PDF sized from trim, page count and paper type (KDP spine formula), with bleed,
  spine text when the book is thick enough and a clear barcode area on the back.
"""

import io
import logging
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from reportlab.lib.colors import white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Frame, Paragraph

from ...catalog import PAPER_TYPES, TRIM_SIZES, get_category
from ...config import ASSETS_DIR
from ...db.models import Book
from .. import llm, prompts
from ..generation import editor_model
from .print_pdf import FONT, register_fonts, to_rl

logger = logging.getLogger(__name__)

EBOOK_SIZE = (1600, 2560)
BLEED = 0.125
KDP_SPINE_TEXT_MIN_PAGES = 79
FONT_DIR = ASSETS_DIR / "fonts"

PALETTES = {
    "fantasy": ((24, 20, 56), (120, 60, 140)),
    "science_fiction": ((6, 18, 40), (20, 110, 150)),
    "mystery": ((15, 18, 26), (70, 80, 95)),
    "thriller": ((12, 12, 14), (140, 20, 25)),
    "romance": ((120, 30, 70), (240, 150, 160)),
    "horror": ((5, 5, 5), (90, 10, 10)),
    "historical": ((60, 40, 20), (180, 140, 90)),
    "literary": ((30, 45, 60), (190, 175, 150)),
    "humor": ((250, 190, 40), (240, 90, 60)),
    "fairy_tale": ((40, 70, 120), (230, 200, 120)),
    "self_help": ((10, 60, 90), (40, 170, 160)),
    "business": ((15, 25, 45), (60, 90, 140)),
    "health": ((20, 90, 70), (150, 210, 160)),
}
DEFAULT_PALETTE = ((25, 30, 45), (90, 100, 130))


def _gradient(size: tuple[int, int], top: tuple, bottom: tuple) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        base.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    img = base.resize((w, h))
    noise = Image.effect_noise((w // 4, h // 4), 18).resize((w, h)).convert("RGB")
    return Image.blend(img, noise, 0.06)


def _fit_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.45))


def _wrap_to_fit(draw: ImageDraw.ImageDraw, text: str, font_path: Path, max_w: int, max_lines: int, start: int, min_size: int):
    size = start
    while size >= min_size:
        font = ImageFont.truetype(str(font_path), size)
        avg = max(1, font.getlength("ABCDEFGHIJKLMNOPQRSTUVWXYZ") / 26)
        lines = textwrap.wrap(text, width=max(4, int(max_w / avg)))
        if len(lines) <= max_lines and all(draw.textlength(line, font=font) <= max_w for line in lines):
            return font, lines
        size -= 6
    font = ImageFont.truetype(str(font_path), min_size)
    return font, textwrap.wrap(text, width=max(4, int(max_w / (min_size * 0.5))))[:max_lines]


def _draw_lines(img: Image.Image, lines: list[str], font, y: int, fill=(255, 255, 255), spacing: float = 1.05) -> int:
    w = img.width
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    draw = ImageDraw.Draw(img)
    line_h = int(font.size * spacing)
    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=font)
        sd.text(((w - lw) / 2 + 4, y + i * line_h + 6), line, font=font, fill=(0, 0, 0, 170))
    img.paste(Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(8))).convert("RGB"))
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        lw = draw.textlength(line, font=font)
        draw.text(((w - lw) / 2, y + i * line_h), line, font=font, fill=fill)
    return y + len(lines) * line_h


def compose_cover(book: Book, art: Image.Image | None, size: tuple[int, int] = EBOOK_SIZE, typeset: bool = True) -> Image.Image:
    w, h = size
    top, bottom = PALETTES.get(book.genre, DEFAULT_PALETTE)
    img = _fit_cover(art, size) if art is not None else _gradient(size, top, bottom)
    if not typeset:
        return img
    # Legibility scrims at top and bottom
    scrim = Image.new("L", (1, h))
    for y in range(h):
        t = y / h
        alpha = 170 * max(0.0, 1 - t / 0.38) + 190 * max(0.0, (t - 0.78) / 0.22)
        scrim.putpixel((0, y), int(min(200, alpha)))
    img = Image.composite(Image.new("RGB", size, (0, 0, 0)), img, scrim.resize(size))

    draw = ImageDraw.Draw(img)
    margin = int(w * 0.08)
    title_font, title_lines = _wrap_to_fit(draw, book.title.upper(), FONT_DIR / "BebasNeue-Regular.ttf", w - 2 * margin, 3,
                                           int(w * 0.17), int(w * 0.07))
    y = _draw_lines(img, title_lines, title_font, int(h * 0.07), spacing=0.95)
    if book.subtitle:
        sub_font, sub_lines = _wrap_to_fit(draw, book.subtitle, FONT_DIR / "CrimsonText-Italic.ttf", w - 2 * margin, 3,
                                           int(w * 0.045), int(w * 0.03))
        _draw_lines(img, sub_lines, sub_font, y + int(h * 0.015), fill=(235, 235, 235), spacing=1.2)
    author = (book.author_name or "").upper()
    if author:
        a_font, a_lines = _wrap_to_fit(draw, author, FONT_DIR / "BebasNeue-Regular.ttf", w - 2 * margin, 1, int(w * 0.075), int(w * 0.04))
        _draw_lines(img, a_lines, a_font, int(h * 0.885))
    if book.series_name:
        s_font = ImageFont.truetype(str(FONT_DIR / "CrimsonText-Italic.ttf"), int(w * 0.035))
        label = f"{book.series_name}{f' · Book {book.series_number}' if book.series_number else ''}"
        _draw_lines(img, [label], s_font, int(h * 0.845), fill=(230, 230, 230))
    return img


def generate_art(book: Book, custom_prompt: str | None) -> Image.Image:
    category = get_category(book.category)
    art_prompt = custom_prompt or llm.complete(
        model=editor_model(book),
        system="You write prompts for book-cover illustrators.",
        prompt=prompts.cover_art_prompt(book, category, book.story_bible or {}),
        max_tokens=300,
        temperature=0.8,
        book_id=book.id,
    ).text.strip().strip('"')
    data = llm.generate_image(prompt=art_prompt + " No text, no letters, no typography.", aspect_ratio="2:3", book_id=book.id)
    return Image.open(io.BytesIO(data)).convert("RGB")


def save_jpeg(img: Image.Image, path: Path, quality: int = 92) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=quality, optimize=True, progressive=True, dpi=(300, 300))


def spine_width_in(page_count: int, paper: str) -> float:
    return round(page_count * PAPER_TYPES.get(paper, PAPER_TYPES["white"]), 4)


def build_wrap_cover_pdf(
    book: Book, *, front: Image.Image, page_count: int, trim_key: str, paper: str, output: Path
) -> dict:
    trim_w, trim_h = TRIM_SIZES[trim_key]
    spine = spine_width_in(page_count, paper)
    full_w = 2 * trim_w + spine + 2 * BLEED
    full_h = trim_h + 2 * BLEED
    register_fonts()
    output.parent.mkdir(parents=True, exist_ok=True)
    c = rl_canvas.Canvas(str(output), pagesize=(full_w * inch, full_h * inch), initialFontName=FONT)
    c.setTitle(f"{book.title} - cover")

    # Background from the darker palette colour
    top, bottom = PALETTES.get(book.genre, DEFAULT_PALETTE)
    c.setFillColorRGB(*(v / 255 for v in top))
    c.rect(0, 0, full_w * inch, full_h * inch, stroke=0, fill=1)

    # Front cover: right panel including the outer bleed
    front_x = BLEED + trim_w + spine
    front_size = (int((trim_w + BLEED) * 300), int(full_h * 300))
    front_img = _fit_cover(front, front_size)
    c.drawImage(ImageReader(front_img), front_x * inch, 0, (trim_w + BLEED) * inch, full_h * inch)

    # Spine
    if page_count >= KDP_SPINE_TEXT_MIN_PAGES:
        c.saveState()
        c.translate((BLEED + trim_w + spine / 2) * inch, full_h / 2 * inch)
        c.rotate(-90)
        size = min(14, spine * 72 * 0.55)
        c.setFillColorRGB(1, 1, 1)
        c.setFont(f"{FONT}-Bold", size)
        c.drawString(-trim_h / 2 * inch + 0.5 * inch, -size / 3, book.title.upper()[:60])
        c.setFont(FONT, size * 0.85)
        c.drawRightString(trim_h / 2 * inch - 0.5 * inch, -size / 3, (book.author_name or "").upper()[:40])
        c.restoreState()

    # Back cover copy, keeping the bottom-right barcode area (2" x 1.2") clear
    copy = book.back_cover_copy or ""
    if copy:
        style = ParagraphStyle("back", fontName=FONT, fontSize=11.5, leading=16, textColor=white)
        frame = Frame((BLEED + 0.6) * inch, (BLEED + 1.8) * inch, (trim_w - 1.2) * inch, (trim_h - 2.6) * inch, showBoundary=0)
        frame.addFromList([Paragraph(to_rl(p), style) for p in copy.split("\n\n") if p.strip()], c)
    c.showPage()
    c.save()
    warnings = []
    if page_count < 24:
        warnings.append("KDP paperbacks need at least 24 pages.")
    if page_count < KDP_SPINE_TEXT_MIN_PAGES:
        warnings.append(f"No spine text: KDP only allows spine text on books with more than {KDP_SPINE_TEXT_MIN_PAGES - 1} pages.")
    return {
        "page_count": page_count,
        "trim_size": trim_key,
        "paper": paper,
        "spine_width_in": spine,
        "full_width_in": round(full_w, 4),
        "full_height_in": round(full_h, 4),
        "barcode_area": "Bottom-right of the back cover (2 in x 1.2 in) is left clear for KDP's barcode.",
        "warnings": warnings,
        "valid": page_count >= 24,
    }
