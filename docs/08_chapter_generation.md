# Chapter Generation Workflow

## Overview
The **Chapter Generation** stage is the core of the Automated Book Generation System. It focuses on maintaining narrative consistency by chaining summaries of previously generated chapters into the context of the current chapter being written.

## Implementation Details

### Workflow Steps
1.  **Validation**: The system verifies that the book exists and that an approved outline is available.
2.  **Duplicate Prevention**: A check is performed to ensure a chapter with the same number hasn't already been generated for that book.
3.  **Context Chaining (Summary Gathering)**:
    -   The system fetches all previously stored chapters for the `book_id`.
    -   Summaries from these chapters are extracted and formatted into a context block.
4.  **Draft Generation (Mocked)**:
    -   A structured draft is created (currently mocked) that includes the Book Title, Chapter Number, and the context of previous summaries.
5.  **Persistence**:
    -   The draft content and a newly generated summary are stored in the Supabase `chapters` table.
    -   The book's status is updated to `chapter_X_generated`.

## Context Chaining Logic
Instead of feeding the entire text of all previous chapters into the AI (which would exceed token limits and introduce noise), we store a concise **summary** for every chapter.
When generating Chapter 3, the prompt context looks like:
- `Chapter 1 Summary: ...`
- `Chapter 2 Summary: ...`

This "Summary Chaining" ensures the AI stays aware of the plot progression without losing focus.

## Validation Rules
- **Book Existence**: Returns `404` if the `book_id` is invalid.
- **Outline Required**: Returns `400` if the generation is attempted before the outline is finalized.
- **Sequential Guard**: While users can request any chapter number, the system prevents overwriting existing chapters (Duplicate `chapter_number` check).

## Current Status
- **Supabase Integration**: ✅ Complete. Records are saved with `status = 'draft_generated'`.
- **Logic & Flow**: ✅ Complete. Context chaining helper is implemented and used.
- **Gemini Integration**: ⏳ Planned. Current content is generated using a structured string template.
