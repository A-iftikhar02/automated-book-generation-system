# Automated Book Generation System (Trial Task)

## Project Overview
An AI-assisted backend system designed to generate long-form books through an iterative, chapter-by-chapter workflow. It leverages Gemini for high-quality content and Supabase for persistent state management and human-in-the-loop checkpoints.

## Folder Structure
```text
trial task/
├── app/            # FastAPI source code
│   ├── db/          # Database connection & models
│   ├── services/    # AI & business logic
│   ├── models/      # Pydantic schemas
│   └── utils/       # Shared utility functions
├── docs/           # Project documentation & design files
├── outputs/        # Generated drafts (.txt)
├── data/           # Any local data or prompts
├── README.md       # Root project documentation
├── requirements.txt # Python dependencies
├── .gitignore      # Ignored files
└── .env.example    # Environment variable placeholders
```

## Planned Stack
- **FastAPI:** High-performance web framework.
- **Supabase:** Postgres database and content storage.
- **Google Gemini:** Generative AI engine.

## MVP Features
- [x] Folder Structure & Documentation Setup
- [x] Outline Generation (AI-driven)
- [x] Chapter Generation with Summary-based Context Chaining
- [x] Human-in-the-Loop Review & Regeneration Workflow
- [x] Sequential Gating for Chapter Progression
- [x] Final `.txt` Draft Compilation
- [x] Slack Webhook Notification System

## Setup Plan
1. Configure `.env` with API keys and Supabase credentials.
2. Initialize Supabase schema based on `docs/03_database_design.md`.
3. Implement core GenAI services in `app/services/`.
4. Create API endpoints for book management and review.
5. Test the end-to-end generation loop.

*Note: This repository is being built incrementally as part of a backend developer trial task.*

## Current Progress
- [x] Project Structure & Folders Ready
- [x] Documentation Ready (01-15)
- [x] FastAPI Skeleton & Base Schemas Added
- [x] Database (Supabase) Integration Complete
- [x] Chapter Generation Logic (Context Chaining MVP)
- [x] Final Compilation & File Export Ready
- [x] Real Google Gemini AI Integration (LIVE)
- [x] Stage 1: Input & Outline Stage (100% Complete)
- [x] Stage 2: Drafting & Review Stage (100% Complete)
- [x] Stage 3: Final Compilation Stage (100% Complete)
- [x] Human-in-the-Loop Gating & Review Workflow (All Stages)
- [x] Real-time Notifications via Slack Webhook Integration
