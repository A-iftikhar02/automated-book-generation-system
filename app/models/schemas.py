from pydantic import BaseModel
from typing import Optional

# --- Outline Generation ---

class OutlineGenerateRequest(BaseModel):
    title: str
    notes_on_outline_before: str = ""

class OutlineGenerateResponse(BaseModel):
    message: str
    book_id: Optional[str] = None
    outline_status: str

# --- Outline Review & Iteration ---

class OutlineReviewRequest(BaseModel):
    book_id: str
    status_outline_notes: str # yes, no, no_notes_needed
    notes_on_outline_after: Optional[str] = None

class OutlineReviewResponse(BaseModel):
    message: str
    review_status: str

class OutlineRegenerateRequest(BaseModel):
    book_id: str

class OutlineRegenerateResponse(BaseModel):
    message: str
    new_version: int
    outline_status: str

# --- Chapter Generation ---

class ChapterGenerateRequest(BaseModel):
    book_id: str
    chapter_number: int

class ChapterGenerateResponse(BaseModel):
    message: str
    chapter_number: int
    chapter_status: str

# --- Chapter Review & Regeneration ---

class ChapterReviewRequest(BaseModel):
    book_id: str
    chapter_number: int
    chapter_notes_status: str # yes, no, no_notes_needed
    chapter_notes: Optional[str] = None

class ChapterReviewResponse(BaseModel):
    message: str
    chapter_notes_status: str

class ChapterRegenerateRequest(BaseModel):
    book_id: str
    chapter_number: int

class ChapterRegenerateResponse(BaseModel):
    message: str
    chapter_number: int
    chapter_status: str

# --- Chapter Status (Optional) ---
class ChapterStatusResponse(BaseModel):
    chapter_exists: bool
    chapter_notes_status: Optional[str] = None
    summary_present: bool

# --- Final Compilation ---

class CompileBookRequest(BaseModel):
    book_id: str

class CompileBookResponse(BaseModel):
    message: str
    output_path: Optional[str] = None
    book_output_status: str

# --- Final Review & Status ---

class FinalReviewRequest(BaseModel):
    book_id: str
    final_review_notes_status: str # yes, no, no_notes_needed
    final_review_notes: Optional[str] = None

class FinalReviewResponse(BaseModel):
    message: str
    book_id: str
    final_review_notes_status: str
    book_output_status: Optional[str] = None
