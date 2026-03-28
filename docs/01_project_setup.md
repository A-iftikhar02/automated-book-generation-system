# Project Setup: Automated Book Generation System

## Project Title
**Automated Book Generation System**

## Trial Task Summary
This project is an AI-assisted workflow designed to streamline the creation of long-form content (books). It breaks down the book generation process into manageable stages (outline, chapter-by-chapter generation, and final compilation) while incorporating human-in-the-loop checkpoints to ensure high-quality output and artistic direction.

## Chosen Stack
- **Backend:** FastAPI (Python)
- **Database:** Supabase (PostgreSQL + Auth + Storage)
- **AI Engine:** Google Gemini (Generative AI)
- **Environment:** python-dotenv for secret management

## MVP Scope
The initial version targets:
- A command-based or minimal API-driven workflow.
- Generation of a full book as a series of `.txt` files compiled into one final document.
- Basic state management for pause/resume functionality.
- Context chaining between chapters.

## Progress Checklist
- [x] Initial Project Structure Setup
- [x] Documentation & Design (Ready 01-15)
- [x] FastAPI Backend Skeleton Setup
- [x] Supabase Connection & Schema Creation
- [x] Chapter Generation Logic (Context Chaining MVP)
- [x] Final Compilation MVP
- [x] Google Gemini AI Integration (Real Generation)
- [x] Stage 1: Input & Outline Stage (100% Complete)
- [x] Human-in-the-Loop Outline Review & Gating
- [x] Stage 2: Chapter Drafting & Review (100% Complete)
- [x] Human-in-the-Loop Chapter Review, Regenerate & Gating
- [x] Stage 3: Final Compilation Stage (100% Complete)
- [x] Human-in-the-Loop Final Review & Gating Logic
- [x] Slack Webhook Notification Integration

## Decision Log
| Date | Decision | Rationale |
| :--- | :--- | :--- |
| 2026-03-28 | Folder Structure | Standard FastAPI modular setup (app/services, app/models, app/db). |
| 2026-03-28 | Markdown Documentation | Ensured high observability for project walkthroughs. |
| 2026-03-28 | Context Chaining Strategy | Decided to use summaries of previous chapters to keep context within Gemini's window without noise. |
| 2026-03-28 | FastAPI Backend Skeleton | Used Pydantic for rigid request/response contracts for AI tasks. |
| 2026-03-28 | Supabase Integration | Connected backend to Supabase and replaced mock endpoints with real DB operations. |
| 2026-03-28 | Chapter Chaining Logic | Implemented summary-based context chaining to maintain narrative consistency between chapters. |
| 2026-03-28 | Final Compilation | Implemented file-system orchestration to aggregate chapter drafts into structured .txt drafts. |
| 2026-03-28 | Gemini Integration | Replaced all mock generation paths with real Gemini calls for outlines and chapters. |
| 2026-03-28 | HITL Review & Gating | Implemented strict gating for chapter generation based on outline approval status ("no_notes_needed"). |
| 2026-03-28 | Stage 1 Finalization | Added CSV support, strict validation, and automated milestone event logging. |
| 2026-03-28 | Stage 2: Chapter Review & Regeneration | Implemented sequential gating, feedback-based regeneration, and HITL chapter review workflow. |
| 2026-03-28 | Stage 3: Final Compilation Stage | Completed strict gating for book compilation and final review notes support. |
| 2026-03-28 | Slack Notifications | Integrated Slack webhooks for real-time alerting on project status. |
