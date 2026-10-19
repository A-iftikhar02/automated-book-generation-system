"""Shared text helpers used by generation, QA and export."""

import re

WORD_RE = re.compile(r"[A-Za-z0-9À-ɏ]+(?:['’][A-Za-z]+)*")
SCENE_BREAK_RE = re.compile(r"^\s*(\*\s*\*\s*\*|#|~+|\*{3,}|-{3,}|•\s*•\s*•)\s*$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])[\"'”’)]*\s+(?=[\"'“‘(]*[A-Z0-9])")
SCENE_BREAK = "* * *"


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def words(text: str) -> list[str]:
    return WORD_RE.findall(text or "")


def paragraphs(text: str) -> list[str]:
    """Split on blank lines. Normalises Windows line endings."""
    text = (text or "").replace("\r\n", "\n").strip()
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def is_scene_break(paragraph: str) -> bool:
    return bool(SCENE_BREAK_RE.match(paragraph))


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in paragraphs(text):
        if is_scene_break(para):
            continue
        out.extend(s.strip() for s in SENTENCE_SPLIT_RE.split(para.replace("\n", " ")) if s.strip())
    return out


_PREAMBLE_RE = re.compile(
    r"^(?:sure|certainly|of course|absolutely|here(?:'s| is| are)|below is|okay|ok)\b[^\n]*\n+",
    re.IGNORECASE,
)
_NUMBER_WORD = (
    r"(?:\d+|[ivxlc]+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
    r"sixteen|seventeen|eighteen|nineteen|(?:twenty|thirty|forty|fifty|sixty)(?:[\s-]\w+)?)"
)
_HEADING_RE = re.compile(
    rf"^\s*(?:#{{1,6}}\s+.*|(?:chapter|part|story|scene|poem)\s+{_NUMBER_WORD}\b(?:\s*[:.\-–—]\s*.{{0,80}})?)$",
    re.IGNORECASE,
)
_TRAILER_RE = re.compile(
    r"\n+(?:\(?word count[^\n]*|\[?end of (?:chapter|story|scene|part)[^\n]*|---+\s*$|note:[^\n]*)\s*$",
    re.IGNORECASE,
)


def clean_generated_prose(text: str, *, keep_line_breaks: bool = False, title: str | None = None) -> str:
    """Strip common LLM wrapping: preambles, markdown headings, bold markers, trailers.

    The only markup kept is *single asterisks* for italics, which exporters render as italic text.
    `keep_line_breaks` preserves single newlines (poetry); otherwise lines inside a paragraph are joined.
    If `title` is given, a leading paragraph that just repeats the title is removed.
    """
    text = (text or "").replace("\r\n", "\n").strip()
    text = re.sub(r"^```[a-z]*\n|```$", "", text, flags=re.MULTILINE)
    text = _PREAMBLE_RE.sub("", text, count=1)

    paras = paragraphs(text)
    # Drop leading heading lines like "Chapter 3: The Storm" or "# The Storm"
    norm_title = normalize_whitespace(title or "").strip("*#\"' ").lower()
    while paras and len(paras[0].split()) <= 12 and (
        _HEADING_RE.match(paras[0]) or (norm_title and normalize_whitespace(paras[0]).strip("*#\"' ").lower() == norm_title)
    ):
        paras.pop(0)

    cleaned = []
    for p in paras:
        if is_scene_break(p):
            cleaned.append(SCENE_BREAK)
            continue
        p = re.sub(r"^#{1,6}\s+", "", p)
        p = re.sub(r"\*\*(.+?)\*\*", r"\1", p, flags=re.DOTALL)
        p = re.sub(r"__(.+?)__", r"\1", p, flags=re.DOTALL)
        if not keep_line_breaks:
            p = re.sub(r"\s*\n\s*", " ", p)
        p = re.sub(r"[ \t]{2,}", " ", p).strip()
        if p:
            cleaned.append(p)
    # No scene break at the very start or end
    while cleaned and cleaned[0] == SCENE_BREAK:
        cleaned.pop(0)
    while cleaned and cleaned[-1] == SCENE_BREAK:
        cleaned.pop()
    result = "\n\n".join(cleaned)
    return _TRAILER_RE.sub("", result).strip()


def tail_words(text: str, n: int) -> str:
    """Last ~n words of text, starting at a paragraph boundary when possible."""
    paras = paragraphs(text)
    out: list[str] = []
    count = 0
    for p in reversed(paras):
        out.insert(0, p)
        count += word_count(p)
        if count >= n:
            break
    return "\n\n".join(out)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
