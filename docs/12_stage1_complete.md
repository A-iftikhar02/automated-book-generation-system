# Stage 1 Complete: Input and Outline Phase

## Overview
Stage 1 of the Automated Book Generation System is now 100% complete and verified. This phase covers everything from initial project kickoff (manual or file-based) to the finalized structure of the book draft.

## Features Delivered

### 1. Multi-Channel Input Support
- **Manual Input**: via `POST /outline/generate`.
- **File-Based Initiation**: via `POST /outline/from-file`.
    - Supports CSV uploads.
    - Requires `title` and `notes_on_outline_before`.
    - Validates that fields are present and non-empty.

### 2. Strict Outline Validation
- The system now rejects any attempt to generate an initial outline if the `notes_on_outline_before` field is missing or empty (HTTP 400).

### 3. Human-in-the-Loop (HITL) Review Flow
The `status_outline_notes` field acts as the state-machine for the project:
- **`pending_review`**: (Initial state) Requires human action.
- **`yes`**: Changes are requested. Editor provides `notes_on_outline_after`.
- **`no`**: The outline stage is paused.
- **`no_notes_needed`**: The outline is approved. This is the **only** status that unlocks the Chapter Generation stage.

### 4. Robust Outline Iteration
- **Versioning**: Every regeneration creates a new row in the `outlines` table with an incremented version number.
- **History Preservation**: No previous drafts are deleted; the system always uses the highest version number for the current workflow.
- **Branching Logic**: Regeneration is only allowed if the current status is `yes` and feedback notes are provided.

### 5. Automated Gating
- **Strict Checks**: The `POST /chapters/generate` endpoint now fetches the absolute latest outline and validates the status before proceeding.
- **Informative Errors**: 
    - `403 Forbidden`: "Waiting for outline review notes" (Status: yes).
    - `403 Forbidden`: "Outline stage is paused" (Status: no).
    - `403 Forbidden`: "Outline check required" (Status: pending).

### 6. Milestone Event Logging
A lightweight notification system is implemented in `app/utils/events.py`. Milestones are logged with the book UUID for auditability:
- Outline Generated (Initial or Regenerated)
- Review Transitions (Approved, Paused, or Awaiting Changes)

## How to Test Stage 1 End-to-End
1.  **File Input**: Upload a CSV with `title` and `notes_on_outline_before`.
2.  **Validation**: Try to call `/outline/generate` with empty notes to confirm the 400 error.
3.  **Gating**: Try to call `/chapters/generate` immediately after creation; expect a 403.
4.  **Review**: Call `/outline/review` with `"status_outline_notes": "yes"` and feedback.
5.  **Regenerate**: Call `/outline/regenerate` to see Version 2 created.
6.  **Proceed**: Approve via `/outline/review` (`no_notes_needed`) and confirm chapters can now be generated.

---

Stage 1 establishes the bedrock of the project, ensuring that AI generation is always aligned with human editorial direction.
