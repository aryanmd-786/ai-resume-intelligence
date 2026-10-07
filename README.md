# 🧠 AI Resume Intelligence Platform

> **AI Resume Analyzer + Smart Resume Builder + Job Matcher + Skill Gap + Career Assistant**
>
> A **college major project** demonstrating AI/LLM integration, NLP, document processing, information extraction, recommendation systems, and modern SaaS UI — **fully local, private, and powered by Ollama**.

![Status](https://img.shields.io/badge/status-complete-success)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.39-red)
![Ollama](https://img.shields.io/badge/AI-Ollama%20local-orange)
![License](https://img.shields.io/badge/license-academic-lightgrey)

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Architecture](#-architecture)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Ollama Setup](#-ollama-setup)
- [How to Run](#-how-to-run)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Testing](#-testing)
- [Privacy & Security](#-privacy--security)
- [Troubleshooting](#-troubleshooting)
- [Future Enhancements](#-future-enhancements)
- [Acknowledgments](#-acknowledgments)

---

## 🎯 Overview

**AI Resume Intelligence** is a professional, local-first platform that combines **two systems** into one integrated application:

1. **AI Resume Analyzer** — scores resumes, extracts skills, and simulates ATS keyword analysis
2. **AI Resume Builder** — helps users build, improve, and export professional resumes

Plus four supporting modules:

3. **Job Description Matcher** — compares a resume to a JD and scores the fit
4. **Skill Gap Analysis** — shows what skills are missing and provides a learning roadmap
5. **AI Career Assistant** — context-aware chatbot that knows your resume
6. **Resume Analytics + History** — tracks every version and shows improvement over time

**All AI processing runs locally through [Ollama](https://ollama.com)**. Nothing is sent to OpenAI, Gemini, Anthropic, or any cloud AI service.

---

## ✨ Features

### 📄 AI Resume Analyzer
- Upload **PDF** (PyMuPDF) or **DOCX** (python-docx) resumes
- Safe text extraction with friendly error handling
- **7 AI-generated scores**: Overall, ATS, Content, Skills, Experience, Projects, Formatting
- Strengths, Weaknesses, and actionable Recommendations
- Categorized skill extraction (Programming, Frameworks, Databases, Cloud, Tools, Technical, Soft Skills)
- **ATS-style keyword analysis**: matched / missing / important keywords + density chart
- Score radar chart + skills pie chart + keyword density bar chart
- **"Send to Builder"** one-click handoff

### ✨ AI Resume Builder
- Multi-section form (Personal, Summary, Education, Skills, Experience, Projects, Certifications, Achievements, Languages, Interests)
- **AI assist buttons**: Generate Summary, Improve Experience, Improve Project, Suggest Skills
- **Strict no-fabrication rule**: AI only *rephrases* what the user provides — it never invents companies, dates, or achievements
- **3 templates**: Modern, Minimal, Professional
- Live HTML preview
- **Export to PDF** (ReportLab) and **DOCX** (python-docx)
- Auto-prefill from an analyzed resume

### 🎯 Job Description Matcher
- Match score (0–100%) with gauge visualization
- Matched / missing skills
- Matched / missing keywords
- Experience relevance & Education relevance (bar chart)
- Tailored AI recommendations

### 🧠 Skill Gap Analysis
- **Already Have / Need Improvement / Missing** buckets
- Proficiency bar chart (color-coded)
- Distribution donut chart
- Role-readiness metric
- **AI Learning Roadmap** — phase-by-phase plan

### 📊 Resume Analytics
- Multi-metric score trend (7 lines: Overall, ATS, Content, Skills, Experience, Projects, Formatting)
- Skills detected per version
- Latest skills distribution pie
- Job match trend line

### 🕒 Resume History
- SQLite-backed version management
- Score history with trend chart
- Side-by-side version comparison table
- Delete individual or all history

### 🤖 AI Career Assistant
- Chat UI with message history
- **Auto-injects current resume + JD as context**
- Suggested questions for quick start
- Persistent chat history within session

### ⚙️ Settings & Diagnostics
- Ollama connection status
- Switch active model at runtime
- Live AI test prompt
- **System Health Diagnostics** — 7 checks (Ollama, model, DB, folders, disk space, CSS)
- Clear privacy statement

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **UI Framework** | Streamlit 1.39 |
| **AI Engine** | Ollama (local) with `llama3.2:latest` |
| **HTTP Client** | `requests` (direct Ollama REST API) |
| **PDF Extraction** | PyMuPDF (`fitz`) |
| **DOCX Read/Write** | python-docx |
| **PDF Generation** | ReportLab |
| **Database** | SQLite 3 (stdlib `sqlite3`) |
| **Data Analysis** | Pandas |
| **Charts** | Plotly |
| **Styling** | Custom CSS (SaaS-style) |

---

## 🏗️ Architecture

### High-Level Flow

```
┌────────────────────────────────────────────────────┐
│                  Streamlit UI                      │
│  app.py  →  views/*.py                             │
│  (sidebar nav · pages · session state)             │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│              Service Layer                          │
│  ollama_service · resume_parser · resume_analyzer  │
│  resume_generator · resume_pdf · resume_docx       │
│  job_matcher · career_assistant                    │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│         Local Ollama Server (HTTP)                 │
│         http://localhost:11434                     │
│         Model: llama3.2:latest                     │
└──────────────────────┬─────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────┐
│    SQLite DB   +   Outputs Folder (PDF/DOCX)       │
└────────────────────────────────────────────────────┘
```

### Data Flow — Resume Analysis

```
User uploads resume (PDF/DOCX)
    ↓
resume_parser.parse_resume()  →  clean text
    ↓
resume_analyzer.analyze_resume()  →  Ollama (JSON)  →  7 scores + feedback
resume_analyzer.extract_skills()  →  Ollama (JSON)  →  categorized skills
resume_analyzer.ats_keyword_analysis()  →  Ollama  →  keyword breakdown
    ↓
Save to SQLite (resumes + analyses tables)
    ↓
Display on Analyzer page + Dashboard + History + Analytics
```

### Data Flow — Resume Improvement → Builder

```
Analyzer results
    ↓
"Send to Builder" button
    ↓
session_state.builder_seed
    ↓
Builder auto-prefills Summary + Skills
    ↓
User edits + adds more
    ↓
AI polish (Summary, Experience, Projects)
    ↓
Template selection → HTML preview → PDF/DOCX export
```

---

## 📸 Screenshots

> Add real screenshots after running the app. Place them in `docs/` folder.

| Screen | File |
|---|---|
| Dashboard | `docs/screenshot_dashboard.png` |
| Resume Analyzer — Scores | `docs/screenshot_analyzer.png` |
| Resume Builder — Form | `docs/screenshot_builder.png` |
| Resume Builder — Preview | `docs/screenshot_preview.png` |
| Job Matcher — Gauge | `docs/screenshot_matcher.png` |
| Skill Gap — Roadmap | `docs/screenshot_skillgap.png` |
| Analytics — Trends | `docs/screenshot_analytics.png` |
| History — Versions | `docs/screenshot_history.png` |
| Career Assistant — Chat | `docs/screenshot_chat.png` |

---

## 📦 Installation

### Prerequisites
- **Python 3.10+** (Python 3.11 recommended)
- **Ollama** installed and running (see below)
- **Windows 10/11** (tested), Linux/macOS should also work

### Steps

```powershell
# 1. Navigate to project folder
cd path\to\AI_Resume_Project

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
.\.venv\Scripts\Activate.ps1

# 4. Upgrade pip
python -m pip install --upgrade pip

# 5. Install dependencies
python -m pip install -r requirements.txt
```

---

## 🦙 Ollama Setup

### 1. Install Ollama
Download from **https://ollama.com/download**

### 2. Start Ollama server
```powershell
ollama serve
```
> Keep this terminal open. It runs at `http://localhost:11434`.

### 3. Pull the model (new terminal)
```powershell
ollama pull llama3.2:latest
```

### 4. Verify
```powershell
ollama list
```
You should see `llama3.2:latest` in the list.

### 5. Change the model (optional)
Edit `config.py`:
```python
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
```
Or switch at runtime in the **Settings** page.

---

## ▶️ How to Run

### Terminal 1 — Ollama
```powershell
ollama serve
```

### Terminal 2 — Streamlit
```powershell
cd "path\to\AI_Resume_Project"
.\.venv\Scripts\Activate.ps1
python -m streamlit run app.py
```

App opens at **http://localhost:8501**.

---

## 📁 Project Structure

```
AI_Resume_Project/
│
├── app.py                          # Entry point + sidebar + routing
├── config.py                       # Central configuration
├── requirements.txt
├── README.md
├── .gitignore
│
├── services/                       # Business logic (all AI calls here)
│   ├── ollama_service.py           # Single point of contact for Ollama
│   ├── resume_parser.py            # PDF/DOCX → text
│   ├── resume_analyzer.py          # 3 AI analysis functions
│   ├── resume_generator.py         # Builder AI helpers
│   ├── resume_pdf.py               # ReportLab PDF generator
│   ├── resume_docx.py              # python-docx generator
│   ├── job_matcher.py              # Match + skill gap AI
│   └── career_assistant.py         # Chat AI
│
├── database/                       # SQLite persistence
│   ├── __init__.py
│   └── database.py
│
├── views/                          # One module per page
│   ├── dashboard.py
│   ├── analyzer.py
│   ├── builder.py
│   ├── job_matcher.py
│   ├── skill_gap.py
│   ├── analytics.py
│   ├── history.py
│   ├── career_assistant.py
│   └── settings.py
│
├── templates/                      # Resume theme definitions
│   ├── __init__.py
│   ├── modern.py
│   ├── minimal.py
│   └── professional.py
│
├── utils/                          # Cross-cutting helpers
│   ├── helpers.py
│   ├── validators.py
│   ├── error_handlers.py
│   └── health_check.py
│
├── tests/                          # Smoke + manual tests
│   ├── __init__.py
│   ├── smoke_test.py
│   └── manual_checklist.md
│
├── assets/
│   └── style.css                   # Custom SaaS-style CSS
│
├── data/                           # SQLite DB lives here
│   └── resume_ai.db
│
└── outputs/                        # Generated PDF/DOCX files
```

> **Note:** The UI folder is `views/` (not `pages/`) — Streamlit auto-detects
> a folder named `pages/` and would conflict with our custom sidebar navigation.

---

## 🗄️ Database Schema

SQLite database: `data/resume_ai.db`

### `resumes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto |
| name | TEXT | file name |
| file_type | TEXT | pdf/docx |
| resume_text | TEXT | truncated to 50K chars |
| created_at | TEXT | timestamp |

### `analyses`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto |
| resume_id | INTEGER FK | → resumes.id |
| overall_score | INTEGER | 0–100 |
| ats_score | INTEGER | 0–100 |
| content_score | INTEGER | 0–100 |
| skills_score | INTEGER | 0–100 |
| experience_score | INTEGER | 0–100 |
| projects_score | INTEGER | 0–100 |
| formatting_score | INTEGER | 0–100 |
| skills_count | INTEGER | total skills |
| analysis_json | TEXT | full AI response |
| skills_json | TEXT | categorized skills |
| ats_json | TEXT | keyword breakdown |
| created_at | TEXT | timestamp |

### `job_matches`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto |
| resume_id | INTEGER FK | → resumes.id |
| jd_snippet | TEXT | first 2K chars of JD |
| match_score | INTEGER | 0–100 |
| exp_relevance | INTEGER | 0–100 |
| edu_relevance | INTEGER | 0–100 |
| result_json | TEXT | full AI response |
| created_at | TEXT | timestamp |

### `generated_resumes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | auto |
| full_name | TEXT | |
| template | TEXT | Modern/Minimal/Professional |
| file_path | TEXT | |
| data_json | TEXT | full form data |
| created_at | TEXT | timestamp |

---

## 🧪 Testing

### Automated Smoke Test

```powershell
python tests\smoke_test.py
```

Runs 5 checks:
- ✅ Module imports
- ✅ SQLite initialization
- ✅ Template definitions
- ✅ Ollama connection
- ✅ System health

### Manual Checklist

See `tests/manual_checklist.md` for a full feature-by-feature test plan.

---

## 🔒 Privacy & Security

- ✅ **100% local AI** — resumes never leave the machine
- ✅ No OpenAI / Gemini / Anthropic / cloud AI calls
- ✅ No telemetry, no analytics, no tracking
- ✅ Only local HTTP calls to `localhost:11434` (Ollama)
- ✅ SQLite database stored locally in `data/`
- ✅ File upload validation (type + size limit)
- ✅ Resume text truncated in storage (50K chars)

> **Note:** Ollama itself does not phone home. Resume content stays on your machine.

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Sidebar shows "Ollama Offline" | Run `ollama serve` in a separate terminal |
| `Model not found` | `ollama pull llama3.2:latest` |
| `ModuleNotFoundError: No module named 'X'` | `python -m pip install -r requirements.txt` |
| Streamlit port in use | `python -m streamlit run app.py --server.port 8502` |
| `from __future__ imports must occur at the beginning` | Move `from __future__ import annotations` to top (after docstring) |
| Emojis/special chars garbled (`ðŸŽ¯`) | Save files as **UTF-8** in Notepad |
| `packaging` or `pip` corrupted | Delete `.venv`, recreate, reinstall |
| First AI call is slow | Normal — model loads into RAM on first call |
| Charts not rendering | `python -m pip install plotly` |
| History not saving | Check `data/` folder exists and is writable |

---

## 🚀 Future Enhancements

- [ ] **Multi-user support** — accounts, login, per-user data isolation
- [ ] **Cover letter generator** using the same AI pipeline
- [ ] **Interview question generator** based on resume + JD
- [ ] **LinkedIn profile optimization** suggestions
- [ ] **Salary range estimation** (with disclaimers)
- [ ] **Multi-language resumes** (Hindi, Spanish, etc.)
- [ ] **Advanced ATS simulation** with weighted keyword scoring
- [ ] **More resume templates** (10+)
- [ ] **Export to `.html`** (shareable web version)
- [ ] **Cloud deployment** (Docker + Streamlit Cloud + Ollama remote)
- [ ] **Fine-tuned model** for resume-specific tasks
- [ ] **Vector similarity** for JD matching (embeddings)
- [ ] **Bulk analysis** (upload 10 resumes, get a comparison table)

---

## 🎓 Academic Context

This project was built as a **college major project** and demonstrates:

- **AI/LLM integration** — Ollama local inference with JSON-mode prompts
- **Natural Language Processing** — text extraction, keyword analysis, skill categorization
- **Information Extraction** — parsing unstructured resume data into structured fields
- **Recommendation System** — skill gap analysis + learning roadmap
- **Similarity/Matching** — resume ↔ JD comparison scoring
- **Database Design** — normalized SQLite schema
- **Data Visualization** — Plotly charts across 4 pages
- **Professional UI** — custom SaaS-style design
- **File Generation** — PDF (ReportLab) + DOCX (python-docx)
- **Software Architecture** — layered modular structure
- **Error Handling** — centralized, consistent, user-friendly
- **Privacy Considerations** — fully local processing

---

## 🙏 Acknowledgments

- **Ollama** — for making local LLM inference easy
- **Streamlit** — for the rapid UI framework
- **Meta AI** — for the Llama 3.2 model
- **ReportLab**, **python-docx**, **PyMuPDF**, **Plotly** — for the file/chart libraries

---

## 📄 License

Academic use — college major project. Free to use for learning and reference.

---

**Built with 💜 for college submission and demonstration.**