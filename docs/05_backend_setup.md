# Backend Setup: FastAPI Skeleton

## Implementation Summary
In this phase, we have integrated the **Supabase** database into the FastAPI backend. The endpoints now perform real database operations, persisting books, outlines, chapters, and final drafts throughout the generation workflow.

### What Was Implemented
- **Supabase Client:** `app/db/supabase_client.py` initializes the connection using environment variables.
- **Database Queries:** `app/db/queries.py` implements the core CRUD operations for the book generation lifecycle.
- **Integrated Endpoints:** `app/main.py` replaced mock responses with real database logic for:
    - Creating books and outlines.
    - Storing generated chapters and summaries.
    - Aggregating chapters and recording final draft paths.
- **Error Handling:** Added `HTTPException` handling for missing records (404) or invalid workflow states (400).

### End-to-End Mock Workflow
The backend now supports a complete (mocked) end-to-end generation workflow:
1.  **Outline Stage**: `/outline/generate` creates the book root and initial skeleton.
2.  **Generation Stage**: `/chapters/generate` creates sequenced drafts with narrative context chaining.
3.  **Compilation Stage**: `/book/compile` aggregates all draft chapters into a single formatted `.txt` file and stores the draft path in Supabase.

### Database vs. AI Logic
While the database and file orchestration layers are now fully operational, the **AI (LLM) logic remains mocked**. The generation endpoints use hardcoded string templates to simulate Gemini's output. This allows for testing the workflow state and persistence independently of AI API latency or cost.

## How to Run the Server
...

To launch the development server, run the following command from the project root:

```bash
uvicorn app.main:app --reload
```

### Expected Starter Responses
- **GET `/`**:
  ```json
  {
      "message": "Welcome to the Automated Book Generation System API!",
      "version": "0.1.0",
      "status": "online"
  }
  ```
- **GET `/health`**:
  ```json
  {
      "status": "ok"
  }
  ```

## MVP Assumptions
- **Synchronous Mocking:** Currently, post-processing endpoints (generate chapter/outline) return immediately; future versions will integrate with background tasks or Supabase state changes.
- **No Persistence:** Data is not yet persisted to a database; this will be added in the next phase of development.
