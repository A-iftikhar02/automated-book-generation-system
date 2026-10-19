"""Static catalog of book formats, genres, audiences and print options.

A *category* is the format/length of the book (short story, novel, ...). A *genre* is what it is about.
`structure` controls how parts are presented:
  - chapters: numbered chapters with titles
  - scenes:   one continuous piece split into untitled scene sections (short stories)
  - stories:  a collection of standalone titled stories
  - poems:    a collection of titled poems
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    description: str
    fiction: bool
    structure: str
    min_words: int
    max_words: int
    default_words: int
    min_parts: int
    max_parts: int
    default_parts: int
    part_label: str
    writing_notes: str
    allowed_audiences: tuple[str, ...] = ("adult", "new_adult", "young_adult", "middle_grade")


CATEGORIES: dict[str, Category] = {
    c.key: c
    for c in [
        Category(
            key="flash_fiction_collection",
            label="Flash Fiction Collection",
            description="A collection of very short standalone stories (300-1,000 words each).",
            fiction=True, structure="stories",
            min_words=5_000, max_words=20_000, default_words=10_000,
            min_parts=8, max_parts=30, default_parts=15, part_label="Story",
            writing_notes="Each piece is a complete standalone story with a twist, punchline or resonant final image. "
            "Economy of language matters: every sentence must earn its place.",
        ),
        Category(
            key="short_story",
            label="Short Story",
            description="A single standalone story, sold as an ebook single (3,000-10,000 words).",
            fiction=True, structure="scenes",
            min_words=3_000, max_words=10_000, default_words=6_000,
            min_parts=2, max_parts=6, default_parts=4, part_label="Scene",
            writing_notes="One central conflict, few characters, a tight timeframe. Open with a hook, "
            "build to a single climax and land a satisfying ending. Sections flow as one continuous story.",
            allowed_audiences=("adult", "new_adult", "young_adult", "middle_grade", "children"),
        ),
        Category(
            key="short_story_collection",
            label="Short Story Collection",
            description="An anthology of standalone short stories linked by theme or setting.",
            fiction=True, structure="stories",
            min_words=25_000, max_words=70_000, default_words=40_000,
            min_parts=6, max_parts=15, default_parts=10, part_label="Story",
            writing_notes="Each story stands alone with its own characters and arc, while sharing the collection's "
            "theme. Vary openings, structures and voices so the collection never feels repetitive.",
        ),
        Category(
            key="novelette",
            label="Novelette",
            description="A long short story told in a handful of chapters (10,000-20,000 words).",
            fiction=True, structure="chapters",
            min_words=10_000, max_words=20_000, default_words=15_000,
            min_parts=4, max_parts=10, default_parts=6, part_label="Chapter",
            writing_notes="A focused plot with one main arc and at most one subplot. Brisk pacing.",
        ),
        Category(
            key="novella",
            label="Novella",
            description="A short novel, a fast read in one or two sittings (20,000-50,000 words).",
            fiction=True, structure="chapters",
            min_words=20_000, max_words=50_000, default_words=30_000,
            min_parts=8, max_parts=20, default_parts=12, part_label="Chapter",
            writing_notes="A complete character arc with room for one or two subplots. Every chapter moves the plot.",
        ),
        Category(
            key="novel",
            label="Novel",
            description="A full-length novel (50,000-100,000 words), the standard for most genres.",
            fiction=True, structure="chapters",
            min_words=50_000, max_words=100_000, default_words=75_000,
            min_parts=18, max_parts=40, default_parts=25, part_label="Chapter",
            writing_notes="Three-act structure with rising stakes, multiple subplots that pay off, and chapter endings "
            "that pull the reader forward.",
        ),
        Category(
            key="epic_novel",
            label="Long / Epic Novel",
            description="A long, sweeping novel (100,000-150,000 words); common for epic fantasy and sagas.",
            fiction=True, structure="chapters",
            min_words=100_000, max_words=150_000, default_words=115_000,
            min_parts=35, max_parts=60, default_parts=40, part_label="Chapter",
            writing_notes="Multiple POV threads and deep worldbuilding are allowed, but every thread must converge. "
            "Keep a rigorous continuity of names, places and timeline.",
            allowed_audiences=("adult", "new_adult", "young_adult"),
        ),
        Category(
            key="childrens_chapter_book",
            label="Children's Chapter Book",
            description="An illustrated-style chapter book for early independent readers aged 6-9.",
            fiction=True, structure="chapters",
            min_words=4_000, max_words=15_000, default_words=8_000,
            min_parts=6, max_parts=15, default_parts=10, part_label="Chapter",
            writing_notes="Short sentences and paragraphs, simple vocabulary, lots of dialogue and action, humour, "
            "and a gentle, age-appropriate problem the child protagonist solves themselves.",
            allowed_audiences=("children",),
        ),
        Category(
            key="nonfiction_guide",
            label="Non-fiction Guide / How-to",
            description="A practical non-fiction book that teaches the reader something (20,000-60,000 words).",
            fiction=False, structure="chapters",
            min_words=20_000, max_words=60_000, default_words=35_000,
            min_parts=8, max_parts=20, default_parts=12, part_label="Chapter",
            writing_notes="Promise a clear transformation. Each chapter teaches one idea with concrete examples, "
            "actionable steps and a short recap. Never invent statistics, studies, quotes or sources.",
        ),
        Category(
            key="nonfiction_short_read",
            label="Non-fiction Short Read",
            description="A focused short non-fiction book on a single topic (7,000-20,000 words).",
            fiction=False, structure="chapters",
            min_words=7_000, max_words=20_000, default_words=12_000,
            min_parts=5, max_parts=12, default_parts=7, part_label="Chapter",
            writing_notes="Tight focus on one problem and its solution. Skimmable structure, practical takeaways. "
            "Never invent statistics, studies, quotes or sources.",
        ),
        Category(
            key="poetry_collection",
            label="Poetry Collection",
            description="A themed collection of original poems.",
            fiction=True, structure="poems",
            min_words=3_000, max_words=15_000, default_words=6_000,
            min_parts=20, max_parts=80, default_parts=35, part_label="Poem",
            writing_notes="Original poems with varied forms (free verse, sonnet, haiku sequences...) unified by the "
            "collection's theme. Fresh imagery; avoid cliché and forced rhyme. Preserve line breaks.",
            allowed_audiences=("adult", "new_adult", "young_adult", "middle_grade", "children"),
        ),
    ]
}

FICTION_GENRES = {
    "literary": "Literary Fiction",
    "fantasy": "Fantasy",
    "science_fiction": "Science Fiction",
    "mystery": "Mystery",
    "thriller": "Thriller / Suspense",
    "romance": "Romance",
    "horror": "Horror",
    "historical": "Historical Fiction",
    "adventure": "Action & Adventure",
    "dystopian": "Dystopian",
    "paranormal": "Paranormal",
    "humor": "Humor",
    "womens_fiction": "Women's Fiction",
    "contemporary": "Contemporary",
    "fairy_tale": "Fairy Tale / Fable",
}

NONFICTION_GENRES = {
    "self_help": "Self-Help",
    "business": "Business & Money",
    "health": "Health & Wellness",
    "personal_finance": "Personal Finance",
    "productivity": "Productivity",
    "relationships": "Relationships",
    "parenting": "Parenting",
    "education": "Education & Study Skills",
    "technology": "Computers & Technology",
    "cooking": "Cooking & Food",
    "travel": "Travel",
    "history": "History",
    "spirituality": "Spirituality",
    "hobbies": "Crafts & Hobbies",
}

AUDIENCES = {
    "children": {"label": "Children (6-9)", "max_grade": 4.0, "max_avg_sentence": 12},
    "middle_grade": {"label": "Middle Grade (8-12)", "max_grade": 6.5, "max_avg_sentence": 15},
    "young_adult": {"label": "Young Adult (12-18)", "max_grade": 8.5, "max_avg_sentence": 18},
    "new_adult": {"label": "New Adult (18-25)", "max_grade": 10.0, "max_avg_sentence": 22},
    "adult": {"label": "Adult", "max_grade": 12.0, "max_avg_sentence": 24},
}

CONTENT_RATINGS = {
    "clean": "Clean: no profanity, no sexual content, mild peril only",
    "moderate": "Moderate: mild language, fade-to-black romance, non-graphic violence",
    "mature": "Mature: strong language and intense themes, but no explicit sexual content",
}

POVS = {
    "first": "First person (I)",
    "second": "Second person (you)",
    "third_limited": "Third person limited",
    "third_omniscient": "Third person omniscient",
}

TENSES = {"past": "Past tense", "present": "Present tense"}

# KDP paperback trim sizes in inches (width, height)
TRIM_SIZES = {
    "5x8": (5.0, 8.0),
    "5.25x8": (5.25, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "4.25x6.87": (4.25, 6.87),
}

PAPER_TYPES = {
    # KDP spine width per page in inches
    "white": 0.002252,
    "cream": 0.0025,
}

EXPORT_FORMATS = {
    "epub": "EPUB 3 (Apple Books, Kindle, Kobo, Google Play)",
    "print_pdf": "Print-ready PDF interior (KDP paperback)",
    "cover_wrap_pdf": "Full-wrap paperback cover PDF (KDP)",
    "docx": "Word manuscript (DOCX)",
    "txt": "Plain text",
}


def get_category(key: str) -> Category:
    if key not in CATEGORIES:
        raise KeyError(f"Unknown category '{key}'")
    return CATEGORIES[key]


def genre_label(key: str) -> str:
    return FICTION_GENRES.get(key) or NONFICTION_GENRES.get(key) or key.replace("_", " ").title()


def catalog_payload() -> dict:
    return {
        "categories": [asdict(c) for c in CATEGORIES.values()],
        "fiction_genres": FICTION_GENRES,
        "nonfiction_genres": NONFICTION_GENRES,
        "audiences": AUDIENCES,
        "content_ratings": CONTENT_RATINGS,
        "povs": POVS,
        "tenses": TENSES,
        "trim_sizes": {k: {"width": w, "height": h} for k, (w, h) in TRIM_SIZES.items()},
        "paper_types": list(PAPER_TYPES),
        "export_formats": EXPORT_FORMATS,
    }
