"""Prompt builders. Kept in one place so tone and rules stay consistent across the pipeline."""

import json

from ..catalog import AUDIENCES, CONTENT_RATINGS, POVS, TENSES, Category, genre_label
from ..db.models import Book

# Phrases that readers and reviewers recognise as machine-written. The writer is told to avoid them
# and QA flags them (see qa/style.py).
BANNED_PHRASES = [
    "delve", "tapestry", "testament to", "a symphony of", "palpable", "unwavering", "in the realm of",
    "couldn't help but", "barely above a whisper", "a breath she didn't know she was holding",
    "a breath he didn't know he was holding", "sent shivers down", "eyes widened", "the air was thick with",
    "a dance of", "little did they know", "it's important to note", "in conclusion", "navigate the complexities",
    "embark on a journey", "unlock the secrets", "ever-evolving", "game-changer", "in today's fast-paced world",
]

WRITER_SYSTEM = """You are an award-winning professional author and ghostwriter whose books sell well on Amazon \
Kindle and Apple Books. You write polished, publication-ready prose: vivid, specific, emotionally resonant, with \
natural dialogue and varied sentence rhythm. You never break the fourth wall, never add commentary, notes, headings \
or word counts, and never mention being an AI. You follow the style guide and continuity facts exactly."""

EDITOR_SYSTEM = """You are a meticulous senior editor at a major publishing house. You give precise, actionable, \
evidence-based feedback. You quote the manuscript verbatim when pointing to a problem and never invent problems \
that are not there."""


def _style_rules(book: Book, category: Category) -> str:
    audience = AUDIENCES.get(book.audience, {})
    rules = [
        f"Point of view: {POVS.get(book.pov, book.pov)}." if category.fiction else "Address the reader directly as 'you' where natural.",
        f"Tense: {TENSES.get(book.tense, book.tense)}." if category.fiction else "",
        f"Audience: {audience.get('label', book.audience)}. Keep vocabulary and themes appropriate.",
        f"Content rating: {CONTENT_RATINGS.get(book.content_rating, book.content_rating)}.",
        f"Language/spelling convention: {book.language}.",
        "Formatting: plain prose paragraphs separated by a blank line. Use *single asterisks* only for italics "
        "(sparingly). Mark scene breaks with a line containing only '* * *'. No headings, bold, lists or markdown.",
        "Never include the chapter number or title at the top; it is added during typesetting.",
        "Avoid these overused phrases entirely: " + "; ".join(BANNED_PHRASES) + ".",
        "Avoid clichés, filler words (very, really, just, suddenly), purple prose and repeating the same sentence openings.",
        "Do not quote song lyrics, poems or passages from other copyrighted works. Do not use real living people as characters.",
    ]
    if category.structure == "poems":
        rules[5] = "Formatting: poem lines separated by single line breaks, stanzas separated by a blank line. No title, no commentary."
    if not category.fiction:
        rules.append("Never invent statistics, studies, experts, quotes or URLs. If evidence is needed, state the general principle without fabricated citations.")
    if book.tone:
        rules.append(f"Tone: {book.tone}.")
    if book.style_notes:
        rules.append(f"Author's style notes: {book.style_notes}")
    return "\n".join(f"- {r}" for r in rules if r)


def book_brief(book: Book, category: Category) -> str:
    return f"""BOOK BRIEF
Title: {book.title}{f" — {book.subtitle}" if book.subtitle else ""}
Format: {category.label} ({category.description})
Genre: {genre_label(book.genre)}
Target length: about {book.target_word_count:,} words in {book.target_chapter_count} {category.part_label.lower()}s
Premise / author direction:
{book.premise}

FORMAT GUIDANCE
{category.writing_notes}

STYLE RULES
{_style_rules(book, category)}"""


def story_bible_prompt(book: Book, category: Category) -> str:
    if category.fiction:
        schema = """{
  "logline": "one-sentence hook",
  "synopsis": "a full-arc synopsis of 2-4 paragraphs including the ending",
  "themes": ["..."],
  "voice": "description of the narrative voice and prose style to keep consistent",
  "characters": [{"name": "...", "role": "protagonist|antagonist|supporting|minor", "age": "...", "appearance": "...", "personality": "...", "voice": "how they speak", "arc": "how they change"}],
  "settings": [{"name": "...", "description": "..."}],
  "world_rules": ["facts about the world that must stay consistent"],
  "glossary": [{"term": "...", "meaning": "..."}]
}"""
    else:
        schema = """{
  "logline": "the book's promise to the reader in one sentence",
  "synopsis": "2-3 paragraphs describing what the book covers and the reader's transformation",
  "target_reader": "who this is for and what they struggle with",
  "themes": ["core ideas"],
  "voice": "description of the authorial voice to keep consistent",
  "key_concepts": [{"name": "...", "description": "..."}],
  "frameworks": ["named methods or step sequences the book teaches"],
  "glossary": [{"term": "...", "meaning": "..."}]
}"""
    extra = ""
    if category.structure in ("stories", "poems"):
        extra = f"\nThis is a collection: characters and settings may differ per {category.part_label.lower()}. Capture the unifying theme and voice."
    return f"""{book_brief(book, category)}

Create the STORY BIBLE for this book: the single source of truth for consistency during writing.{extra}
Use invented, distinctive names (avoid overused names such as Elara, Kael, Lyra, Seraphina, Thorne, Vex).

Return JSON with exactly this shape:
{schema}"""


def outline_prompt(book: Book, category: Category, bible: dict, feedback: str | None = None, previous: list | None = None) -> str:
    per_part = max(200, book.target_word_count // max(1, book.target_chapter_count))
    revision = ""
    if feedback and previous:
        revision = f"""
PREVIOUS OUTLINE
{json.dumps(previous, indent=1)}

EDITOR FEEDBACK TO APPLY
{feedback}

Revise the outline to fully address the feedback while keeping what works."""
    part = category.part_label.lower()
    return f"""{book_brief(book, category)}

STORY BIBLE
{json.dumps(bible, indent=1)}
{revision}
Create a detailed outline with exactly {book.target_chapter_count} {part}s. Each {part} needs a compelling title,
a synopsis of 2-4 sentences, 3-6 concrete beats (what happens, in order) and a target word count (around {per_part}
words; vary it for pacing, but the total must be close to {book.target_word_count}).
{"For a collection, each entry is a standalone piece with its own title and premise." if category.structure in ("stories", "poems") else ""}
{"For a short story, entries are consecutive scenes of one continuous story; titles are internal labels only." if category.structure == "scenes" else ""}

Return JSON:
{{"synopsis": "overall summary", "chapters": [{{"number": 1, "title": "...", "synopsis": "...", "beats": ["..."], "target_words": {per_part}}}]}}"""


def _outline_digest(outline_chapters: list, current: int) -> str:
    lines = []
    for ch in outline_chapters:
        marker = ">>" if ch.get("number") == current else "  "
        lines.append(f"{marker} {ch.get('number')}. {ch.get('title')}: {ch.get('synopsis')}")
    return "\n".join(lines)


def chapter_prompt(
    *,
    book: Book,
    category: Category,
    bible: dict,
    outline_chapters: list,
    chapter: dict,
    previous_summaries: list[tuple[int, str, str]],
    previous_tail: str,
    part_index: int,
    part_count: int,
    beats: list[str],
    words: int,
    written_so_far: str,
    notes: str | None = None,
) -> str:
    part = category.part_label.lower()
    summaries = "\n".join(f"{n}. {t}: {s}" for n, t, s in previous_summaries) or "(this is the first one)"
    position = ""
    if part_count > 1:
        position = f"\nYou are writing segment {part_index + 1} of {part_count} of this {part}. Cover ONLY these beats now; later segments will continue."
    continuation = ""
    if written_so_far:
        continuation = f"""
THIS {part.upper()} SO FAR (continue seamlessly from the last sentence; do not repeat or summarise it)
{written_so_far}
"""
    elif previous_tail and category.structure in ("chapters", "scenes"):
        continuation = f"""
END OF THE PREVIOUS {part.upper()} (for voice and continuity; do not repeat it)
{previous_tail}
"""
    is_last = chapter.get("number") == len(outline_chapters) and part_index == part_count - 1
    ending = ""
    if category.structure in ("chapters", "scenes"):
        ending = (
            "This is the final segment of the book: deliver a satisfying, earned resolution."
            if is_last
            else ("End this segment at a natural point." if part_index < part_count - 1 else f"End the {part} with forward momentum (a hook, question or turn) without cliffhanger clichés.")
        )
    return f"""{book_brief(book, category)}

STORY BIBLE (canonical facts; never contradict)
{json.dumps(bible, indent=1)}

FULL OUTLINE (>> marks the current {part})
{_outline_digest(outline_chapters, chapter.get("number"))}

WHAT HAPPENED BEFORE
{summaries}
{continuation}
NOW WRITE {category.part_label.upper()} {chapter.get("number")}: "{chapter.get("title")}"
Synopsis: {chapter.get("synopsis")}
Beats to cover in this segment:
{chr(10).join(f"- {b}" for b in beats)}{position}
{f"{chr(10)}EDITOR NOTES FOR THIS DRAFT (must be applied){chr(10)}{notes}{chr(10)}" if notes else ""}
Length: about {words} words (this matters: do not stop early and do not pad).
{ending}
Output only the {part} text."""


def continue_prompt(book: Book, category: Category, chapter: dict, text_so_far: str, missing_words: int) -> str:
    return f"""{book_brief(book, category)}

You are writing {category.part_label} {chapter.get("number")}: "{chapter.get("title")}".
Synopsis: {chapter.get("synopsis")}
Beats: {"; ".join(chapter.get("beats") or [])}

The draft so far ends here:
{text_so_far}

The {category.part_label.lower()} is about {missing_words} words too short. Continue seamlessly from the last sentence,
deepening scenes that were rushed and covering any beats not yet written, then bring it to a natural close.
Output only the continuation text (do not repeat earlier text)."""


def revise_prompt(
    *,
    book: Book,
    category: Category,
    bible: dict,
    chapter: dict,
    previous_summaries: list[tuple[int, str, str]],
    current_text: str,
    instructions: str,
    target_words: int,
) -> str:
    summaries = "\n".join(f"{n}. {t}: {s}" for n, t, s in previous_summaries) or "(none)"
    return f"""{book_brief(book, category)}

STORY BIBLE
{json.dumps(bible, indent=1)}

WHAT HAPPENED BEFORE
{summaries}

{category.part_label.upper()} {chapter.get("number")}: "{chapter.get("title")}"
Synopsis: {chapter.get("synopsis")}

CURRENT DRAFT
{current_text}

REVISION INSTRUCTIONS
{instructions}

Rewrite the {category.part_label.lower()} applying every instruction. Keep everything that is not affected by the
instructions (plot events, names, facts, voice). Keep it about {target_words} words.
Output only the full revised text."""


def summary_prompt(book: Book, category: Category, chapter: dict, text: str, bible: dict) -> str:
    known = [c.get("name") for c in bible.get("characters", []) if isinstance(c, dict)]
    return f"""Book: "{book.title}" ({category.label}, {genre_label(book.genre)}).
{category.part_label} {chapter.get("number")}: "{chapter.get("title")}"

TEXT
{text}

Known characters: {", ".join(n for n in known if n) or "none recorded"}

Return JSON:
{{
  "summary": "3-5 sentence summary of what happens, including important reveals, decisions and the ending state",
  "new_characters": [{{"name": "...", "role": "...", "description": "appearance/personality facts stated in the text"}}],
  "continuity_facts": ["specific facts established here that later text must respect (injuries, objects, relationships, dates, locations)"]
}}"""


def editorial_qa_prompt(
    *,
    book: Book,
    category: Category,
    bible: dict,
    chapter: dict,
    previous_summaries: list[tuple[int, str, str]],
    text: str,
) -> str:
    summaries = "\n".join(f"{n}. {t}: {s}" for n, t, s in previous_summaries) or "(none)"
    fiction_checks = """
- continuity: contradictions with the story bible or earlier events (names, ages, appearance, injuries, objects, locations, who knows what)
- timeline: impossible sequencing, time-of-day or travel-time errors
- plot_logic: plot holes, unmotivated actions, coincidences that strain belief
- characterization: characters acting or speaking out of established character
- pov_tense: point-of-view slips (head-hopping) or tense shifts in the narration
- dialogue: stilted, expository or indistinguishable dialogue
- pacing: rushed key moments, dragging passages, info-dumps
- show_vs_tell: emotions or events summarised where they should be dramatised
- anachronism: objects, phrases or technology that do not fit the setting""" if category.fiction else """
- accuracy: statements that are factually wrong or misleading
- fabrication: invented statistics, studies, experts, quotes, URLs or sources
- clarity: confusing explanations, undefined jargon, missing steps
- structure: missing promised content, poor flow between sections
- actionability: advice too vague to act on
- legal_risk: medical, legal or financial advice stated without appropriate care"""
    return f"""{book_brief(book, category)}

STORY BIBLE
{json.dumps(bible, indent=1)}

PREVIOUS {category.part_label.upper()}S
{summaries}

OUTLINE FOR THIS {category.part_label.upper()}
{json.dumps(chapter, indent=1)}

TEXT OF {category.part_label.upper()} {chapter.get("number")}
{text}

Review this {category.part_label.lower()} as a professional editor preparing it for sale. Check:
- outline_adherence: missing or contradicted beats from the outline{fiction_checks}
- audience_fit: content inappropriate for the audience or content rating
- copyright: quoted lyrics/poetry/passages from real works, trademarks used disparagingly, real living people portrayed
- ai_tells: generic, repetitive or machine-sounding prose patterns

Report only real problems, at most 15, most important first. "excerpt" must be copied VERBATIM from the text (5-25 words)
so it can be located. Severity: critical (must fix before publishing), major (should fix), minor (polish).

Return JSON:
{{"issues": [{{"check": "continuity", "severity": "major", "excerpt": "...", "message": "what is wrong", "suggestion": "how to fix it"}}],
  "strengths": ["..."], "overall": "one-paragraph editorial assessment"}}"""


def book_qa_prompt(book: Book, category: Category, bible: dict, outline: list, chapters: list[tuple[int, str, str]], opening: str) -> str:
    digest = "\n".join(f"{n}. {t}: {s}" for n, t, s in chapters)
    return f"""{book_brief(book, category)}

STORY BIBLE
{json.dumps(bible, indent=1)}

PLANNED OUTLINE
{_outline_digest(outline, -1)}

WHAT WAS ACTUALLY WRITTEN (summaries)
{digest}

OPENING PAGES (what readers see in the store's free sample / "Look Inside")
{opening}

Review the WHOLE book as an acquisitions editor deciding whether it is ready to sell. Check:
- structure: does the book deliver its premise and the reader promise of the genre?
- unresolved_threads: plot threads, mysteries or setups that never pay off
- arc: do main characters (or, for non-fiction, the reader) complete a meaningful arc/transformation?
- repetition: repeated scenes, beats, revelations or chapter patterns
- timeline: cross-chapter timeline or continuity contradictions
- ending: is the ending satisfying and earned?
- opening_hook: does the opening hook a browsing reader within the first page?
- market_fit: anything that would draw bad reviews or violate store content guidelines

Report only real problems (max 12). Use "chapter_number" when a problem is located in one place, otherwise null.

Return JSON:
{{"issues": [{{"check": "unresolved_threads", "severity": "major", "chapter_number": null, "message": "...", "suggestion": "..."}}],
  "verdict": "ready|needs_work|not_ready", "summary": "one-paragraph assessment"}}"""


def metadata_prompt(book: Book, category: Category, bible: dict, chapter_summaries: list[tuple[int, str, str]]) -> str:
    digest = "\n".join(f"{n}. {t}: {s}" for n, t, s in chapter_summaries[:60])
    return f"""{book_brief(book, category)}

STORY BIBLE
{json.dumps({k: bible.get(k) for k in ("logline", "synopsis", "themes", "target_reader") if bible.get(k)}, indent=1)}

CONTENTS
{digest}

Write the retail metadata to sell this book on Amazon KDP and Apple Books.
- description: a compelling product description of 150-300 words. Open with a hook line, introduce the
  protagonist/problem and stakes (or the reader's problem and the promise), end with a call to action.
  Never spoil the ending. You may use simple HTML allowed by KDP: <p>, <b>, <i>, <br>. Max 4000 characters.
- back_cover_copy: 120-180 words of plain text for the paperback back cover.
- subtitle: an optional subtitle that improves discoverability (non-fiction especially) or "" for none.
- keywords: exactly 7 search phrases (each under 50 characters) that real readers type, not repeating words
  from the title, no competitor author names, no "kindle"/"ebook"/"bestseller".
- store_categories: 3 specific browse category paths (e.g. "Fiction / Fantasy / Epic"), most specific first.

Return JSON: {{"description": "...", "back_cover_copy": "...", "subtitle": "...", "keywords": ["..."], "store_categories": ["..."]}}"""


def cover_art_prompt(book: Book, category: Category, bible: dict) -> str:
    return f"""Write a single image-generation prompt (max 90 words) for the front-cover ARTWORK of this book.
Title: {book.title}
Format: {category.label}; Genre: {genre_label(book.genre)}; Audience: {AUDIENCES.get(book.audience, {}).get('label', book.audience)}
Logline: {bible.get("logline", "")}
Themes: {", ".join(bible.get("themes", [])[:5]) if isinstance(bible.get("themes"), list) else ""}

The prompt must describe one striking, genre-appropriate focal image in the visual style of current bestsellers in
this genre, portrait orientation, with calm negative space in the top third (title) and bottom fifth (author name).
It must say: no text, no letters, no typography, no watermark, no border. Return only the prompt."""
