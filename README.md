# Yours Resume

An AI agent that builds a resume tailored to any job description  with one strict rule: it can never make anything up. Every claim on the resume has to be backed by real evidence you provide.

## Live Links

- **Frontend (the app):** https://at-sresume-seven.vercel.app
- **Backend (API):** https://atsresume-4q81.onrender.com

## What It Does

1. You add your real work experience, projects, skills, and achievements — either by typing them in, or by uploading your existing resume and letting the AI read it for you.
2. You paste the job description you're applying for.
3. The AI agent checks which of your real experiences match the job, and honestly flags anything you're missing.
4. It writes a resume using only your real evidence, then fact-checks every single line before it's allowed onto the page.
5. It makes sure the resume is formatted in a way that automated hiring software (ATS) can actually read.
6. You can chat with it in plain English to fine-tune anything — it only edits using real facts.
7. You download the finished resume as a PDF. Every past version is saved so you can revisit it later.

## Why It's Different

- **Zero fabrication**  every claim is fact-checked against your own evidence before it's added.
- **ATS-friendly**  built to actually get past automated resume screening.
- **Honest about gaps**  instead of hiding weaknesses, it tells you where your experience falls short.
- **You stay in control**  nothing is added to your profile without your review and approval.

## Tech Stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS  hosted on Vercel
**Backend:** FastAPI (Python), ChromaDB (vector database for evidence search), Playwright (PDF rendering)  hosted on Render

**AI Services:**
- **Groq**  powers the main AI pipeline (parsing, writing, fact-checking)
- **Gemini**  powers the resume chat/edit feature
- **Tavily**  used for researching the company you're applying to

## A Note on Speed

The backend runs on a free hosting tier with limited processing power, so a full run may take some time or occasionally need a retry. The app runs faster locally, where it has full system resources available.
