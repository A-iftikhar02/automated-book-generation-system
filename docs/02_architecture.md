# Architecture Overview: Automated Book Generation System

## System Overview
The **Automated Book Generation System** is an AI-assisted backend service that facilitates the iterative creation of long-form books. It leverages state management to allow human-in-the-loop (HITL) review at critical points in the generation process.

## The 3 Stages

### 1. Outline Generation
The system generates a high-level book structure based on a primary prompt or concept. This phase results in a list of chapters, each with a title and a brief description of its intended content. This stage requires user approval before starting chapter generation.

### 2. Chapter-by-Chapter Generation
The core generation engine produces one chapter at a time. To maintain context, it uses:
- **Primary Concept:** The foundational book premise.
- **Chapter Summary:** A summary of all previous chapters generated so far.
- **Human Notes:** Optional instructions from the user provided during review pauses.

### 3. Final Compilation
Once all chapters are finalized, the system aggregates the individual chapters into a single `.txt` formatted document for the final draft.

## Human-in-the-Loop Logic
The system is designed with intentional "checkpoints." After any stage (or after each chapter), the process pauses. The generated content is stored in Supabase with a `status == 'pending_review'`. The user can then:
- Approve the content (`status = 'approved'`).
- Provide feedback/notes to regenerate the content (`status = 'refining'`).
- Resume the workflow only once approval is granted.

## Pause/Resume/Continue Behavior
All progress is persisted in the database. If the server restarts or the user leaves the session, the system reads the last finalized chapter and its state from Supabase to resume from the exact point where it was left.

## Context Chaining: Summaries vs. Full Text
Rather than feeding the entire previous content into the prompt (which would eventually exceed token limits or increase noise), the system generates a summary of every chapter it creates. These summaries are chained together as "Last Chapter Summaries" to maintain the narrative arc.

## Why This Stack is Suitable for the MVP
- **FastAPI:** Provides a lightweight, high-performance async framework for AI API interactions.
- **Supabase:** Offers a "backend as a service" that simplifies PostgreSQL database management, realtime updates, and future file storage for draft exports.
- **Gemini:** A state-of-the-art LLM with a large context window and powerful reasoning, ideal for long-form narrative consistency and complex summarization.
