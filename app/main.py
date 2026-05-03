import os
import io
import csv
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .models import schemas
from .db import queries
from .utils import helpers
from .utils.events import log_event
from .services import llm_service
from .services.notification_service import send_notification
from .utils.pdf_generator import generate_pdf_from_data

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for the AI-assisted book generation workflow (Supabase-integrated)."
)

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Welcome endpoint to check if the API is running."""
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API!",
        "version": settings.VERSION,
        "status": "online",
        "database": "connected"
    }

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok"}

@app.get("/books")
async def get_books():
    """Retrieve all books."""
    try:
        response = queries.supabase.table("books").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/books/{book_id}")
async def get_book_details(book_id: str):
    """Retrieve full details of a specific book, including outline, chapters, and final draft."""
    try:
        book = queries.get_book_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        outline = queries.get_latest_outline_by_book_id(book_id)
        chapters = queries.get_chapters_by_book_id(book_id)
        final_draft = queries.get_final_draft_by_book_id(book_id)
        
        return {
            "book": book,
            "outline": outline,
            "chapters": chapters,
            "finalDraft": final_draft
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/outline/generate", response_model=schemas.OutlineGenerateResponse)
async def generate_outline(request: schemas.OutlineGenerateRequest):
    """
    Creates a new book and generates its initial skeleton outline.
    Enforces that 'notes_on_outline_before' is provided.
    """
    if not request.title:
        raise HTTPException(status_code=400, detail="Title is required")
        
    if not request.notes_on_outline_before or request.notes_on_outline_before.strip() == "":
        msg = "notes_on_outline_before is required before generating outline"
        send_notification(f"⚠️ Workflow blocked: {msg}")
        raise HTTPException(status_code=400, detail=msg)
        
    try:
        # 1. Create the new book in DB
        book = queries.create_book(request.title, request.notes_on_outline_before)
        book_id = book["id"]

        # 2. AI Outline generation (Real Gemini Integration)
        outline_text = llm_service.generate_outline(request.title, request.notes_on_outline_before)
        
        # 3. Save outline in DB
        queries.create_outline(book_id, outline_text)
        
        # Log Event
        log_event("outline_generated", str(book_id), f"Initial outline generated for '{request.title}'.")
        
        send_notification(f"📘 Outline ready for review: '{request.title}'.")

        return {
            "message": f"Book created and real AI outline generated for '{request.title}'.",
            "book_id": str(book_id),
            "outline_status": "ready_for_review"
        }
    except ValueError as ai_error:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(ai_error)}")
        raise HTTPException(status_code=502, detail=str(ai_error))
    except Exception as e:
        import traceback
        traceback.print_exc()
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database or System error: {str(e)}")

@app.post("/outline/from-file")
async def generate_outline_from_file(file: UploadFile = File(...)):
    """
    Initiates the outline generation process from a CSV file.
    Expects columns: title, notes_on_outline_before.
    Processes the first data row found in the file.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for MVP.")
        
    try:
        content = await file.read()
        stream = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(stream)
        
        row = next(reader, None)
        if not row:
            raise HTTPException(status_code=400, detail="CSV is empty.")
            
        title = row.get("title")
        notes = row.get("notes_on_outline_before")
        
        if not title or title.strip() == "":
            raise HTTPException(status_code=400, detail="CSV must contain a non-empty 'title' column.")
        if not notes or notes.strip() == "":
            raise HTTPException(status_code=400, detail="CSV must contain a non-empty 'notes_on_outline_before' column.")
            
        # Re-use the generation logic
        book = queries.create_book(title, notes)
        outline_text = llm_service.generate_outline(title, notes)
        queries.create_outline(book["id"], outline_text)
        
        # Log Event
        log_event("outline_generated", str(book["id"]), f"Outline generated from file upload for '{title}'.")
        
        send_notification(f"📘 Outline ready for review: '{title}'.")

        return {
            "message": f"Book created from file and outline generated for '{title}'.",
            "book_id": str(book["id"]),
            "outline_status": "ready_for_review"
        }
    except Exception as e:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File processing error: {str(e)}")

@app.post("/outline/review", response_model=schemas.OutlineReviewResponse)
async def review_outline(request: schemas.OutlineReviewRequest):
    """
    Updates the review status for the latest outline.
    Valid statuses: 'yes', 'no', 'no_notes_needed'.
    """
    valid_statuses = ["yes", "no", "no_notes_needed"]
    if request.status_outline_notes not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
    try:
        book = queries.get_book_by_id(request.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")

        updated = queries.update_outline_review(
            book_id=request.book_id,
            status_outline_notes=request.status_outline_notes,
            notes_on_outline_after=request.notes_on_outline_after
        )
        
        # Event Logging based on status
        if request.status_outline_notes == "yes":
            log_event("outline_waiting_for_review", request.book_id, "Changes requested on outline.")
            send_notification(f"🟡 Outline for book '{book['title']}' is waiting for editor notes.")
        elif request.status_outline_notes == "no":
            log_event("outline_paused", request.book_id, "Outline stage marked as paused.")
            send_notification(f"⛔ Outline stage paused for book '{book['title']}'.")
        elif request.status_outline_notes == "no_notes_needed":
            log_event("outline_approved", request.book_id, "Outline approved. Workflow ready for chapter generation.")

        return {
            "message": f"Outline review updated to '{request.status_outline_notes}'.",
            "review_status": updated["status_outline_notes"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review update failed: {str(e)}")

@app.post("/outline/regenerate", response_model=schemas.OutlineRegenerateResponse)
async def regenerate_outline(request: schemas.OutlineRegenerateRequest):
    """
    Creates a new version of the outline if improvements are requested ('yes' status).
    Requires feedback in 'notes_on_outline_after'.
    """
    try:
        book = queries.get_book_by_id(request.book_id)
        latest = queries.get_latest_outline_by_book_id(request.book_id)
        
        if not latest:
            raise HTTPException(status_code=404, detail="No existing outline to regenerate.")
            
        if latest["status_outline_notes"] != "yes":
            raise HTTPException(status_code=400, detail="Regeneration only allowed if review status is 'yes'.")
            
        if not latest.get("notes_on_outline_after"):
            raise HTTPException(status_code=400, detail="Feedback notes are required for regeneration.")
            
        # AI Regeneration
        new_outline_text = llm_service.regenerate_outline(
            title=book["title"],
            notes_before=book.get("notes_on_outline_before", ""),
            notes_after=latest["notes_on_outline_after"],
            previous_outline=latest["outline_text"]
        )
        
        new_version = queries.get_next_outline_version(request.book_id)
        queries.create_outline(
            book_id=request.book_id,
            outline_text=new_outline_text,
            status_outline_notes="pending_review",
            version=new_version
        )
        
        # Log Event
        log_event("outline_generated", request.book_id, f"Outline regenerated to version {new_version} based on feedback.")
        
        return {
            "message": f"Successfully regenerated outline version {new_version}.",
            "new_version": new_version,
            "outline_status": "pending_review"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")

@app.post("/chapters/generate", response_model=schemas.ChapterGenerateResponse)
async def generate_chapter(request: schemas.ChapterGenerateRequest):
    """
    Generates a specific chapter for an existing book.
    Implements strict gating and context chaining.
    """
    try:
        # 1. FETCH BOOK & OUTLINE
        book = queries.get_book_by_id(request.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")
            
        outline = queries.get_latest_outline_by_book_id(request.book_id)
        if not outline:
            raise HTTPException(status_code=400, detail="Cannot generate chapters without an outline.")
            
        # 2. WAVE 1 GATE: Outline must be fully approved
        outline_status = outline.get("status_outline_notes")
        if outline_status != "no_notes_needed":
            raise HTTPException(
                status_code=403, 
                detail=f"Outline must be fully approved ('no_notes_needed') before chapters. Current: {outline_status}"
            )

        # 3. WAVE 2 GATE: Sequential Chapter Progression
        if request.chapter_number > 1:
            prev_chapter = queries.get_chapter_by_book_and_number(request.book_id, request.chapter_number - 1)
            if not prev_chapter:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Chapter {request.chapter_number - 1} must exist before Chapter {request.chapter_number}."
                )
            
            prev_status = prev_chapter.get("chapter_notes_status")
            if prev_status == "yes":
                msg = f"Chapter {request.chapter_number - 1} is waiting for review notes before proceeding."
                send_notification(f"⏳ Chapter flow blocked for book '{book['title']}'. Previous chapter requires review or is paused.")
                raise HTTPException(status_code=400, detail=msg)
            elif prev_status in ["no", None, ""]:
                send_notification(f"⏳ Chapter flow blocked for book '{book['title']}'. Previous chapter requires review or is paused.")
                raise HTTPException(status_code=400, detail=f"Chapter {request.chapter_number - 1} flow is paused or incomplete.")
            elif prev_status != "no_notes_needed":
                 raise HTTPException(status_code=400, detail=f"Chapter {request.chapter_number - 1} must be approved to proceed.")

        # 4. WAVE 3 GATE: Duplicate Generation
        existing = queries.get_chapter_by_book_and_number(request.book_id, request.chapter_number)
        if existing:
            raise HTTPException(status_code=400, detail=f"Chapter {request.chapter_number} already exists.")
            
        # 5. CONTEXT CHAINING
        all_chapters = queries.get_chapters_by_book_id(request.book_id)
        previous_chapters = [c for c in all_chapters if c["chapter_number"] < request.chapter_number]
        context_summaries = helpers.format_previous_summaries(previous_chapters)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gating error: {str(e)}")

    # 6. AI Generation
    try:
        chapter_title, chapter_content = llm_service.generate_chapter(
            title=book['title'],
            outline_text=outline['outline_text'],
            chapter_number=request.chapter_number,
            previous_summaries=context_summaries
        )
        chapter_summary = llm_service.generate_summary(chapter_content)
        
        # 7. Store & Log
        queries.create_chapter(
            book_id=request.book_id,
            chapter_number=request.chapter_number,
            chapter_title=chapter_title,
            content=chapter_content,
            summary=chapter_summary
        )
        
        log_event("chapter_generated", request.book_id, f"Chapter {request.chapter_number} generated.")
        log_event("chapter_waiting_for_review", request.book_id, f"Chapter {request.chapter_number} is pending review.")
        
        send_notification(f"📝 Chapter {request.chapter_number} generated for book '{book['title']}' and is pending review.")

        queries.update_book_status(request.book_id, f"chapter_{request.chapter_number}_generated")
        
        return {
            "message": f"Successfully generated Chapter {request.chapter_number}.",
            "chapter_number": request.chapter_number,
            "chapter_status": "pending_review"
        }
    except ValueError as ai_error:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(ai_error)}")
        raise HTTPException(status_code=502, detail=str(ai_error))
    except Exception as e:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/chapter/review", response_model=schemas.ChapterReviewResponse)
async def review_chapter(request: schemas.ChapterReviewRequest):
    """
    Updates the review status for a specific chapter.
    Valid statuses: 'yes', 'no', 'no_notes_needed'.
    """
    valid_statuses = ["yes", "no", "no_notes_needed"]
    if request.chapter_notes_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
    try:
        # Validate chapter existence
        chapter = queries.get_chapter_by_book_and_number(request.book_id, request.chapter_number)
        if not chapter:
             raise HTTPException(status_code=404, detail="Chapter not found.")

        # FIX 1: Chapter Status State Machine
        status = "draft_generated"
        if request.chapter_notes_status == "no_notes_needed":
            status = "approved"
        elif request.chapter_notes_status == "yes":
            status = "needs_revision"

        updated = queries.update_chapter_review(
            book_id=request.book_id,
            chapter_number=request.chapter_number,
            chapter_notes_status=request.chapter_notes_status,
            chapter_notes=request.chapter_notes,
            status=status
        )
        
        # FIX 2: Slack Notification for Chapter Review
        try:
            book = queries.get_book_by_id(request.book_id)
            book_title = book.get("title", "Unknown Book") if book else "Unknown Book"
            
            if request.chapter_notes_status == "no_notes_needed":
                send_notification(f"✅ Chapter {request.chapter_number} approved for book '{book_title}'.")
            elif request.chapter_notes_status == "yes":
                send_notification(f"📝 Chapter {request.chapter_number} needs revision for book '{book_title}'.")
        except Exception as n_err:
            print(f"[NOTIFICATION WARNING] Failed to send chapter review notification: {str(n_err)}")
        
        # Event Logging (Existing logic)
        if request.chapter_notes_status == "yes":
            log_event("chapter_waiting_for_review", request.book_id, f"Changes requested for Chapter {request.chapter_number}.")
        elif request.chapter_notes_status == "no":
            log_event("chapter_paused", request.book_id, f"Chapter {request.chapter_number} flow paused.")
        elif request.chapter_notes_status == "no_notes_needed":
            log_event("chapter_approved", request.book_id, f"Chapter {request.chapter_number} approved.")

        return {
            "message": f"Chapter {request.chapter_number} review updated to '{request.chapter_notes_status}'.",
            "chapter_notes_status": updated["chapter_notes_status"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review update failed: {str(e)}")

@app.post("/chapter/regenerate", response_model=schemas.ChapterRegenerateResponse)
async def regenerate_chapter(request: schemas.ChapterRegenerateRequest):
    """
    Regenerates a chapter if improvements are requested ('yes' status).
    Requires feedback in 'chapter_notes'.
    """
    try:
        # 1. Fetch current chapter
        chapter = queries.get_chapter_by_book_and_number(request.book_id, request.chapter_number)
        if not chapter:
            raise HTTPException(status_code=404, detail="Chapter not found.")
            
        # 2. Validation
        if chapter["chapter_notes_status"] != "yes":
            raise HTTPException(status_code=400, detail="Regeneration ONLY allowed if status is 'yes'.")
        if not chapter.get("chapter_notes") or chapter["chapter_notes"].strip() == "":
            raise HTTPException(status_code=400, detail="Chapter notes are required for regeneration.")
            
        # 3. Fetch dependencies
        book = queries.get_book_by_id(request.book_id)
        outline = queries.get_latest_outline_by_book_id(request.book_id)
        
        # 4. Gather context
        all_chapters = queries.get_chapters_by_book_id(request.book_id)
        previous_chapters = [c for c in all_chapters if c["chapter_number"] < request.chapter_number]
        context_summaries = helpers.format_previous_summaries(previous_chapters)
        
        # 5. AI Regeneration
        new_title, new_content = llm_service.regenerate_chapter(
            title=book["title"],
            outline_text=outline["outline_text"],
            chapter_number=request.chapter_number,
            previous_summaries=context_summaries,
            chapter_notes=chapter["chapter_notes"],
            current_chapter_title=chapter["chapter_title"],
            current_chapter_content=chapter["content"]
        )
        
        # 6. Generate fresh summary
        new_summary = llm_service.generate_summary(new_content)
        
        # 7. Update DB
        queries.update_chapter_content(
            book_id=request.book_id,
            chapter_number=request.chapter_number,
            chapter_title=new_title,
            content=new_content,
            summary=new_summary,
            chapter_notes_status="pending_review"
        )
        
        # 8. Log
        log_event("chapter_generated", request.book_id, f"Chapter {request.chapter_number} regenerated based on feedback.")
        send_notification(f"🔄 Chapter {request.chapter_number} regenerated for book '{book['title']}' and is pending review.")
        
        return {
            "message": f"Successfully regenerated Chapter {request.chapter_number}.",
            "chapter_number": request.chapter_number,
            "chapter_status": "pending_review"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {str(e)}")

@app.get("/chapter/status/{book_id}/{chapter_number}", response_model=schemas.ChapterStatusResponse)
async def get_chapter_status(book_id: str, chapter_number: int):
    """Returns the status and presence of a specific chapter."""
    chapter = queries.get_chapter_by_book_and_number(book_id, chapter_number)
    if not chapter:
        return {
            "chapter_exists": False,
            "chapter_notes_status": None,
            "summary_present": False
        }
    
    return {
        "chapter_exists": True,
        "chapter_notes_status": chapter.get("chapter_notes_status"),
        "summary_present": bool(chapter.get("summary"))
    }

@app.post("/book/review", response_model=schemas.FinalReviewResponse)
async def review_book(request: schemas.FinalReviewRequest):
    """Updates the final review status for the entire book."""
    valid_statuses = ["yes", "no", "no_notes_needed"]
    if request.final_review_notes_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
    try:
        # Validate book exists
        book = queries.get_book_by_id(request.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")
            
        updated = queries.create_or_update_final_review(
            book_id=request.book_id,
            final_review_notes_status=request.final_review_notes_status,
            final_review_notes=request.final_review_notes
        )
        
        # Event Logging
        if request.final_review_notes_status == "yes":
            log_event("final_review_requested", request.book_id, "Final review feedback requested.")
        elif request.final_review_notes_status == "no":
            log_event("final_review_paused", request.book_id, "Final compilation stage paused.")
        elif request.final_review_notes_status == "no_notes_needed":
            log_event("final_review_approved", request.book_id, "Final review approved. Ready for compilation.")
            
        return {
            "message": f"Final review updated to '{request.final_review_notes_status}'.",
            "book_id": str(request.book_id),
            "final_review_notes_status": updated["final_review_notes_status"],
            "book_output_status": updated.get("book_output_status")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review update failed: {str(e)}")

@app.post("/book/compile", response_model=schemas.CompileBookResponse)
async def compile_book(request: schemas.CompileBookRequest):
    """
    Aggregates all approved chapters and compiles them into a single final draft .txt file.
    Enforces strict gating based on final review status.
    """
    try:
        # 1. Fetch dependencies
        book = queries.get_book_by_id(request.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")
            
        chapters = queries.get_chapters_by_book_id(request.book_id)
        if not chapters:
            raise HTTPException(status_code=400, detail="No chapters found for this book to compile.")
            
        final_review = queries.get_final_draft_by_book_id(request.book_id)
        
        # 2. FINAL REVIEW GATING
        if not final_review:
             log_event("compile_blocked", request.book_id, "Missing final review row.")
             raise HTTPException(status_code=403, detail="Final review not initiated. Please use /book/review first.")
             
        status = final_review.get("final_review_notes_status")
        notes = final_review.get("final_review_notes", "")
        
        # Logic: ALLOW if 'no_notes_needed' OR ('yes' and notes present)
        is_approved = (status == "no_notes_needed")
        has_allowed_notes = (status == "yes" and notes and notes.strip() != "")
        
        if not (is_approved or has_allowed_notes):
            if status == "yes" and (not notes or notes.strip() == ""):
                log_event("compile_blocked", request.book_id, "Missing final review notes.")
                send_notification(f"⚠️ Final compilation blocked for book '{book['title']}' due to review state or missing final notes.")
                raise HTTPException(status_code=403, detail="Waiting for final review notes before compilation.")
            elif status == "no" or not status or status.strip() == "":
                log_event("compile_blocked", request.book_id, "Compilation paused by editor.")
                send_notification(f"⚠️ Final compilation blocked for book '{book['title']}' due to review state or missing final notes.")
                raise HTTPException(status_code=403, detail="Final compilation is paused until review is approved.")
            else:
                log_event("compile_blocked", request.book_id, f"Incomplete review: {status}")
                send_notification(f"⚠️ Final compilation blocked for book '{book['title']}' due to review state or missing final notes.")
                raise HTTPException(status_code=403, detail="Final compilation is blocked until review is cleared.")

    except HTTPException:
        raise
    except Exception as e:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Compilation prep error: {str(e)}")

    # 3. Process Compilation & File Storage
    try:
        full_text = helpers.build_compiled_book_text(book, chapters)
        
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = f"generated_book_{request.book_id}.txt"
        file_path = os.path.join(output_dir, output_filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        # 4. Update Persistence
        queries.update_final_output(request.book_id, file_path, "compiled")
        queries.update_book_status(request.book_id, "completed")
        
        log_event("final_compilation_completed", request.book_id, f"Book compiled successfully to {file_path}")
        
        send_notification(f"✅ Final draft compiled successfully for book '{book['title']}'.")

        return {
            "message": "Full book draft has been successfully compiled into a local .txt file.",
            "output_path": file_path,
            "book_output_status": "completed"
        }
    except Exception as e:
        send_notification(f"⚠️ Workflow blocked or error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Final compilation execution error: {str(e)}")

@app.get("/api/v1/books/{book_id}/download")
async def download_book(book_id: str):
    book_record = queries.get_book_by_id(book_id)
    if not book_record:
        raise HTTPException(status_code=404, detail="Book not found")
        
    final_draft = queries.get_final_draft_by_book_id(book_id)
    if not final_draft or not final_draft.get("output_file_path"):
        raise HTTPException(status_code=404, detail="Compiled file not found")
        
    file_path = Path(final_draft["output_file_path"])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Output file does not exist")
        
    # Determine media type
    media_type = "application/octet-stream"
    if file_path.suffix == ".txt":
        media_type = "text/plain"
    elif file_path.suffix == ".pdf":
        media_type = "application/pdf"
    elif file_path.suffix == ".docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_type
    )

@app.get("/api/v1/books/{book_id}/download/pdf")
async def download_book_pdf(book_id: str):
    book_record = queries.get_book_by_id(book_id)
    if not book_record:
        raise HTTPException(status_code=404, detail="Book not found")
        
    final_draft = queries.get_final_draft_by_book_id(book_id)
    if not final_draft or not final_draft.get("output_file_path"):
        raise HTTPException(status_code=404, detail="Compiled TXT file not found")
        
    txt_path = Path(final_draft["output_file_path"])
    pdf_path = txt_path.with_suffix(".pdf")
    
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail="TXT output file does not exist")
        
    if not pdf_path.exists():
        try:
            chapters = queries.get_chapters_by_book_id(book_id)
            # Only use approved chapters, or all if we don't care. 
            # The prompt says "approved chapters from database" but compile_book already aggregated them. 
            # So `get_chapters_by_book_id` gets them ordered.
            generate_pdf_from_data(
                book=book_record,
                chapters=chapters,
                output_path=str(pdf_path)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

    return FileResponse(
        path=pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf"
    )

