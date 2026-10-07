# 🧪 Manual Testing Checklist — AI Resume Intelligence Platform

Run through this list after every major change. Tick each box when it passes.

---

## 🏠 Dashboard
- [ ] Page loads without error
- [ ] 4 metric cards visible (Overall, ATS, Skills, Job Match)
- [ ] Metric values reflect DB history (or `—` if empty)
- [ ] 5 Quick Action buttons work and navigate correctly
- [ ] System Status panel shows correct model name
- [ ] After analyzing a resume, dashboard cards update

## 📄 Resume Analyzer
- [ ] Upload PDF → text extracted, preview shows
- [ ] Upload DOCX → text extracted, preview shows
- [ ] Upload wrong file type → friendly error
- [ ] Upload empty file → friendly error
- [ ] **Analyze with AI** runs and shows progress
- [ ] 7 score cards render correctly
- [ ] Radar chart renders
- [ ] Strengths / Weaknesses / Recommendations display
- [ ] Skills categorized + pie chart
- [ ] ATS keyword chips (matched/missing/important)
- [ ] Keyword density bar chart
- [ ] **Send to Builder** button transfers data
- [ ] Analysis auto-saved to history

## ✨ Resume Builder
- [ ] Personal tab — all fields editable
- [ ] **Generate with AI** creates summary (needs some input first)
- [ ] Education — add/remove rows work
- [ ] Skills — "Suggest Skills" returns recommendations
- [ ] Experience — "Improve with AI" generates bullets
- [ ] Projects — "Improve with AI" generates bullets
- [ ] Extras — Certifications/Achievements/Languages/Interests
- [ ] Template selector changes preview
- [ ] HTML preview renders styled (no raw HTML)
- [ ] **Generate PDF** → download button appears
- [ ] **Generate DOCX** → download button appears
- [ ] **Reset Builder** clears data

## 🎯 Job Matcher
- [ ] "Use last analyzed resume" mode works
- [ ] "Upload a new resume" mode works
- [ ] Character count feedback shows
- [ ] **Match with AI** runs with progress
- [ ] Gauge chart renders with score
- [ ] Matched / Missing skills chips
- [ ] Matched / Missing keywords chips
- [ ] Recommendations list
- [ ] "View Skill Gap Analysis" button navigates

## 🧠 Skill Gap
- [ ] 4 metric cards (Have / Improve / Missing / Readiness)
- [ ] Donut chart renders
- [ ] Proficiency bar chart renders
- [ ] 3 skill bucket columns (chips)
- [ ] Learning roadmap expanders work
- [ ] "Re-run Job Matcher" navigates back
- [ ] "Open Resume Builder" navigates

## 📊 Analytics
- [ ] 4 KPI cards
- [ ] Multi-score trend chart renders (if 1+ analyses)
- [ ] Skills per version bar chart
- [ ] Latest skills pie chart
- [ ] Job match trend chart (if 1+ matches)
- [ ] Empty state message when no data

## 🕒 Resume History
- [ ] Resume list appears after analysis
- [ ] Latest analysis score shows next to each resume
- [ ] Delete individual resume works
- [ ] Select a resume → version trend chart
- [ ] Version comparison table
- [ ] "Delete ALL history" clears DB

## 🤖 AI Career Assistant
- [ ] Context badges show resume/JD status
- [ ] Suggested questions clickable
- [ ] Custom question via chat input works
- [ ] AI reply appears in chat bubble
- [ ] Chat history persists across page navigation
- [ ] **Clear chat** empties history

## ⚙️ Settings
- [ ] Ollama connection test shows status
- [ ] Model dropdown lists installed models
- [ ] Model switch works
- [ ] Live AI test returns response
- [ ] **Run Diagnostics** shows system health
- [ ] Privacy note visible

---

## 🐛 Edge Cases

- [ ] Kill Ollama → sidebar shows "Offline", app doesn't crash
- [ ] Try analysis with Ollama offline → friendly error
- [ ] Upload 15 MB PDF → size error
- [ ] Upload `.txt` file → type error
- [ ] Paste empty JD → validation error
- [ ] Press buttons rapidly → no crash
- [ ] Navigate between all pages quickly → no crash
- [ ] Restart app → history persists (SQLite)
- [ ] Delete `data/resume_ai.db` → app recreates on next run

---

## 🚀 Performance

- [ ] First AI call takes < 3 minutes on `llama3.2`
- [ ] Subsequent AI calls are faster
- [ ] Page navigation is instant
- [ ] Charts render under 1 second
- [ ] No memory leak after 20+ navigations