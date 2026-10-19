from app.services.qa import rules
from app.services.qa.book_rules import PartText, check_duplicates, check_names, check_spelling_consistency
from app.services.qa.editorial import locate
from app.services.qa.fixes import normalize_typography, smart_quotes
from app.services.text import clean_generated_prose, word_count


def ctx(**kw):
    base = dict(number=1, title="Storm", target_words=0, is_last=False, fiction=True, structure="chapters", audience="adult",
                content_rating="moderate", pov="third_limited", tense="past", language="en-US")
    base.update(kw)
    return rules.ChapterContext(**base)


def test_clean_generated_prose_strips_wrappers_but_keeps_real_openings():
    raw = "Sure! Here is the chapter:\n\n# Chapter 3: The Storm\n\nThe **sea** rose.\n\n***\n\nPart of me wanted to run.\n\n(Word count: 12)"
    out = clean_generated_prose(raw)
    assert out == "The sea rose.\n\n* * *\n\nPart of me wanted to run."
    assert clean_generated_prose("Part of me knew.\n\nThen it rained.") == "Part of me knew.\n\nThen it rained."
    assert clean_generated_prose("The Storm\n\nIt rained.", title="The Storm") == "It rained."
    assert clean_generated_prose("She saw *it* there.") == "She saw *it* there."


def test_word_count():
    assert word_count("Don't stop—ever, okay?") == 4


def test_smart_quotes():
    assert smart_quotes('"Don\'t," she said. \'Tis the \'90s.') == "“Don’t,” she said. ’Tis the ’90s."
    assert normalize_typography("Wait...  what -- now!!") == "Wait… what—now!"


def test_rule_checks_find_problems():
    text = ("He went went home.  Then he decided to delve deeper. **Bold** text. Visit www.example.com now.\n\n"
            "Damn it, she said. It was a dark and stormy night")
    issues, stats = rules.check_chapter(text, ctx(content_rating="clean", target_words=1000))
    checks = {i.check for i in issues}
    assert {"repeated_word", "double_space", "ai_tell_phrase", "markdown_bold", "url", "mild_profanity", "truncated_ending",
            "too_short"} <= checks, checks
    assert stats["words"] > 10


def test_tense_and_pov_drift():
    present = " ".join(["She walks to the door and looks outside. He says nothing and turns away. She knows he sees it."] * 10)
    issues, _ = rules.check_chapter(present + ".", ctx())
    assert any(i.check == "tense_drift" for i in issues)
    first = " ".join(["I walked to the door and I looked outside at my garden."] * 20)
    issues, _ = rules.check_chapter(first, ctx())
    assert any(i.check == "pov_slip" for i in issues)


def test_book_rules():
    para = " ".join(["The lantern burned with a pale and steady light over the drowned streets of the old harbour town."] * 4)
    parts = [PartText(1, "A", para + "\n\nCorwin ran. Corwin hid. Corwin wept. Corwin slept. Corwin woke."),
             PartText(2, "B", para + "\n\nThen Corwyn laughed.")]
    assert any(i.check in ("near_duplicate_passage", "duplicate_sentence") for i in check_duplicates(parts))
    assert any(i.check == "name_variant" for i in check_names(parts, {"characters": [{"name": "Corwin Hale"}]}))
    mixed = [PartText(1, "A", "The colour was grey. Her favorite color.")]
    assert any(i.check == "mixed_spelling_variants" for i in check_spelling_consistency(mixed, "en-US"))


def test_locate_excerpt():
    text = "The rain fell.\nIt   kept falling on the roofs of the harbour."
    start, length, matched = locate(text, "It kept falling on the roofs")
    assert matched and text[start:start + length].startswith("It")
