# Automated Book Generation System

"AI-powered system for generating books with human-in-the-loop review and workflow control."

## Demo Overview
The Automated Book Generation System is designed to seamlessly integrate AI creativity with human oversight. 
- The user provides an initial concept, title, and notes.
- The system generates a comprehensive outline.
- An editor reviews, requests changes, or approves the outline.
- Chapters are generated sequentially, using context chaining from previous chapters to maintain narrative consistency.
- The final draft is compiled and exported natively as a raw TXT file and a fully styled, professional PDF manuscript.

## Features
- AI-generated outline with editor feedback loop
- Chapter-by-chapter generation with context awareness
- Human-in-the-loop workflow (approve / regenerate)
- Context chaining using previous chapter summaries
- Final draft compilation
- Export as TXT and styled PDF
- Clean dashboard UI (Next.js)
- FastAPI backend
- Supabase/PostgreSQL
- Slack webhook notifications

## Tech Stack

**Frontend:**
- Next.js
- Tailwind CSS
- shadcn/ui

**Backend:**
- FastAPI
- Python

**AI:**
- Google Gemini

**Database:**
- Supabase / PostgreSQL

## Workflow

**Step 1: Create Book**
Provide the initial concept, title, and any guiding notes.

**Step 2: Generate Outline**
The AI constructs a high-level book structure.

**Step 3: Review & Approve Outline**
Editors review the outline, provide feedback, and regenerate if necessary.

**Step 4: Generate Chapters (with context)**
Once the outline is locked, chapters are generated sequentially. Each chapter is aware of previous summaries.

**Step 5: Review Chapters**
Each chapter is subjected to a human-in-the-loop review process before proceeding to the next.

**Step 6: Compile Final Draft**
Approved chapters are aggregated into a final manuscript.

**Step 7: Download TXT / PDF**
The compiled manuscript is available for export as a clean plain-text file or a polished, publish-ready PDF.



## Setup Instructions

### Backend
Navigate to the root directory and install dependencies:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
Navigate to the `frontend` directory:
```bash
cd frontend
npm install
npm run dev
```

**Environment Variables:**
Ensure the following is set in your frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
Your backend `.env` will also require the appropriate API keys for Google Gemini and Supabase.

## Project Structure
```text
/
├── app/                  # FastAPI backend code
│   ├── main.py           # Core API routes
│   └── utils/            # Utilities (PDF generator, helpers)
├── frontend/             # Next.js web application
├── outputs/              # Compiled book exports
└── requirements.txt      # Backend dependencies
```

## Future Improvements
- Better PDF styling (cover, TOC improvements)
- Multi-user support
- Authentication
- Rich text editor for chapters
- More export formats

---

Developed by Abdullah Iftikhar  
Data Science / AI Engineering
