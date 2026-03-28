from typing import List, Dict, Any, Optional
from .supabase_client import supabase

def create_book(title: str, notes_on_outline_before: str = "") -> Dict[str, Any]:
    """Inserts a new book record and returns the created book."""
    response = supabase.table("books").insert({
        "title": title,
        "status": "outline_phase",
        "notes_on_outline_before": notes_on_outline_before
    }).execute()
    return response.data[0]

def create_outline(book_id: str, outline_text: str, status_outline_notes: str = "pending_review", version: int = 1, notes_on_outline_after: str | None = None) -> Dict[str, Any]:
    """Inserts an outline for a specific book with versioning and review status."""
    response = supabase.table("outlines").insert({
        "book_id": book_id,
        "outline_text": outline_text,
        "status_outline_notes": status_outline_notes,
        "version": version,
        "notes_on_outline_after": notes_on_outline_after
    }).execute()
    return response.data[0]

def get_book_by_id(book_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a book by its UUID."""
    response = supabase.table("books").select("*").eq("id", book_id).execute()
    return response.data[0] if response.data else None

def get_latest_outline_by_book_id(book_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the latest outline for a specific book (highest version)."""
    response = supabase.table("outlines").select("*").eq("book_id", book_id).order("version", desc=True).limit(1).execute()
    return response.data[0] if response.data else None

def get_next_outline_version(book_id: str) -> int:
    """Calculates the next version number for a book outline."""
    latest = get_latest_outline_by_book_id(book_id)
    if not latest:
        return 1
    return latest.get("version", 0) + 1

def update_outline_review(book_id: str, status_outline_notes: str, notes_on_outline_after: str | None = None) -> Dict[str, Any]:
    """Updates the latest outline row with review status and optional notes."""
    latest = get_latest_outline_by_book_id(book_id)
    if not latest:
        raise ValueError("No outline found to review.")
        
    update_data = {"status_outline_notes": status_outline_notes}
    if notes_on_outline_after is not None:
        update_data["notes_on_outline_after"] = notes_on_outline_after
        
    response = supabase.table("outlines").update(update_data).eq("id", latest["id"]).execute()
    return response.data[0]

def get_outline_by_book_id(book_id: str) -> Optional[Dict[str, Any]]:
    """Alias for getting latest outline (backwards compatibility)."""
    return get_latest_outline_by_book_id(book_id)

def create_chapter(book_id: str, chapter_number: int, content: str, summary: str, chapter_title: str | None = None) -> Dict[str, Any]:
    """Inserts a new chapter record with correct schema column names."""
    response = supabase.table("chapters").insert({
        "book_id": book_id,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title or f"Chapter {chapter_number}",
        "content": content,
        "summary": summary,
        "chapter_notes_status": "pending_review",
        "status": "draft_generated"
    }).execute()
    return response.data[0]

def get_chapters_by_book_id(book_id: str) -> List[Dict[str, Any]]:
    """Returns all chapters for a book, ordered by chapter number ascending."""
    response = supabase.table("chapters").select("*").eq("book_id", book_id).order("chapter_number", desc=False).execute()
    return response.data

def get_chapter_by_book_and_number(book_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single chapter record by book ID and chapter number."""
    response = supabase.table("chapters").select("*").eq("book_id", book_id).eq("chapter_number", chapter_number).execute()
    return response.data[0] if response.data else None

def update_chapter_review(book_id: str, chapter_number: int, chapter_notes_status: str, chapter_notes: str | None = None, status: str | None = None) -> Dict[str, Any]:
    """Updates the review status, notes, and workflow status for a specific chapter."""
    update_data = {"chapter_notes_status": chapter_notes_status}
    if chapter_notes is not None:
        update_data["chapter_notes"] = chapter_notes
    if status is not None:
        update_data["status"] = status
        
    response = supabase.table("chapters").update(update_data).eq("book_id", book_id).eq("chapter_number", chapter_number).execute()
    return response.data[0]

def update_chapter_content(book_id: str, chapter_number: int, chapter_title: str, content: str, summary: str, chapter_notes_status: str = "pending_review") -> Dict[str, Any]:
    """Updates chapter content, title, and summary during regeneration."""
    update_data = {
        "chapter_title": chapter_title,
        "content": content,
        "summary": summary,
        "chapter_notes_status": chapter_notes_status
    }
    response = supabase.table("chapters").update(update_data).eq("book_id", book_id).eq("chapter_number", chapter_number).execute()
    return response.data[0]


def get_final_draft_by_book_id(book_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the latest final draft record for a book."""
    response = supabase.table("final_drafts").select("*").eq("book_id", book_id).execute()
    return response.data[0] if response.data else None

def create_or_update_final_review(book_id: str, final_review_notes_status: str, final_review_notes: str | None = None) -> Dict[str, Any]:
    """Sets or updates the final review state for a book."""
    existing = get_final_draft_by_book_id(book_id)
    
    if not existing:
        # Create new record
        response = supabase.table("final_drafts").insert({
            "book_id": book_id,
            "final_review_notes": final_review_notes,
            "final_review_notes_status": final_review_notes_status,
            "output_file_path": None,
            "book_output_status": "paused"
        }).execute()
    else:
        # Update existing
        update_data = {"final_review_notes_status": final_review_notes_status}
        if final_review_notes is not None:
            update_data["final_review_notes"] = final_review_notes
            
        response = supabase.table("final_drafts").update(update_data).eq("book_id", book_id).execute()
        
    return response.data[0]

def update_final_output(book_id: str, output_file_path: str, book_output_status: str = "compiled") -> Dict[str, Any]:
    """Updates or creates a final draft record with the compiled output file path."""
    existing = get_final_draft_by_book_id(book_id)
    
    if not existing:
        response = supabase.table("final_drafts").insert({
            "book_id": book_id,
            "output_file_path": output_file_path,
            "book_output_status": book_output_status,
            "final_review_notes_status": "pending_review"
        }).execute()
    else:
        response = supabase.table("final_drafts").update({
            "output_file_path": output_file_path,
            "book_output_status": book_output_status
        }).eq("book_id", book_id).execute()
        
    return response.data[0]

def create_final_draft(book_id: str, output_file_path: str) -> Dict[str, Any]:
    """Legacy wrapper for update_final_output."""
    return update_final_output(book_id, output_file_path)

def update_book_status(book_id: str, status_value: str):
    """Updates the current workflow status for a book."""
    supabase.table("books").update({"status": status_value}).eq("id", book_id).execute()
