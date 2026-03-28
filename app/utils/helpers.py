from datetime import datetime
import re

def get_current_timestamp() -> str:
    """Returns the current ISO formatted timestamp."""
    return datetime.utcnow().isoformat()

def clean_gen_ai_text(text: str) -> str:
    """Basic cleanup for generated AI text (stripping markdown or trailing whitespace)."""
    # Remove excessive whitespace
    text = text.strip()
    # Basic cleanup for common markdown artifacts if any
    text = re.sub(r'```[a-zA-Z]*\n?', '', text)
    text = text.replace('```', '')
    return text

def format_previous_summaries(chapters: list[dict]) -> str:
    """Formats a list of previous chapters into a readable summary block for context chaining."""
    if not chapters:
        return "No previous chapters yet."
        
    summary_blocks = []
    for chapter in chapters:
        num = chapter.get("chapter_number", "?")
        summary = chapter.get("summary", "No summary available.")
        summary_blocks.append(f"Chapter {num} Summary: {summary}")
        
    return "\n".join(summary_blocks)

def build_compiled_book_text(book: dict, chapters: list[dict]) -> str:
    """Aggregates book details and all chapters into a single readable string."""
    title = book.get("title", "Untitled Book")
    compiled_text = [
        f"Book Title: {title}",
        "Outline / Draft Compilation",
        "=" * 20,
        ""
    ]
    
    for chapter in chapters:
        num = chapter.get("chapter_number", "?")
        ch_title = chapter.get("chapter_title", f"Chapter {num}")
        content = chapter.get("content", "No content available.")
        
        compiled_text.append(f"Chapter {num}: {ch_title}")
        compiled_text.append("-" * 20)
        compiled_text.append(content)
        compiled_text.append("\n")
        
    return "\n".join(compiled_text)
