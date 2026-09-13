# Gemini Prompts & AI Integration Specification

All AI capabilities use Google Gemini via `GeminiClient` (`backend/app/ai/gemini_client.py`) with module-level prompt template constants defined in `backend/app/ai/prompts.py`.

---

## 1. Global AI Execution Settings

- **SDK**: `google-generativeai` (imported as `google.generativeai`).
- **Model**: Configured via `GEMINI_MODEL` (default: `gemini-2.5-flash`).
- **Temperature**: `0.1` (low temperature to maximize JSON structure predictability and minimize hallucinations).
- **Max Output Tokens**: `8192` tokens.
- **Top-P / Top-K**: `top_p=0.95`, `top_k=40`.
- **Retry Strategy**:
  - Maximum attempts: 3.
  - Backoff delays: 1.0s → 2.0s → 4.0s.
  - Retryable status codes / signals: HTTP 429, 500, 502, 503, quota limits, connection timeouts.
  - Custom Exception: Raises `AIError` after 3 failed retries.
- **JSON Parsing & Extraction**:
  - `_extract_json_str()` uses a three-stage parsing strategy:
    1. Fenced markdown block extraction (` ```json ... ``` `).
    2. Delimiter scanning (first `{` or `[` to matching closing `}` or `]`).
    3. Full stripped string fallback to `json.loads()`.

---

## 2. Implemented Gemini Prompts

### 2.1 Prompt 1: Skill Extraction (`SKILL_EXTRACTION_PROMPT`)

- **Used By**: `GeminiClient.extract_skills(resume_text)`
- **Caller**: `ResumeService.upload_resume()`
- **Input Parameters**: `{resume_text}` (plain text extracted from PDF by PyMuPDF)
- **Output JSON Schema**:
  ```json
  {
    "skills": ["Python", "FastAPI", "PostgreSQL"]
  }
  ```
- **Constraints & Rules**:
  - Technical skills only (languages, frameworks, databases, cloud, tools).
  - Normalizes names (e.g. "PostgreSQL" not "Postgres").
  - Deduplicated list, maximum 30 items.
- **Error Behavior**: Degrades gracefully — returns `[]` on parse failure so resume upload succeeds even if AI extraction fails.

---

### 2.2 Prompt 2: Job Match Scoring (`JOB_MATCH_PROMPT`)

- **Used By**: `GeminiClient.match_job(job_description, resume_skills)`
- **Caller**: `match_service.score_job()`
- **Input Parameters**: `{skills_list}` (comma-separated skills), `{job_description}`
- **Output JSON Schema**:
  ```json
  {
    "match_score": 85,
    "missing_skills": ["Docker", "Kubernetes"],
    "match_summary": "Sentence one alignment. Sentence two gap."
  }
  ```
- **Constraints & Rules**:
  - `match_score`: Integer 0–100 evaluating technical fit only (clamped).
  - `missing_skills`: List of at most 5 explicit requirements missing from candidate skills.
  - `match_summary`: Exactly two sentences (Sentence 1: strongest alignment, Sentence 2: largest gaps).
- **Error Behavior**: Strict — raises `ValueError` on malformed schema; service catches and raises `AIError` (mapped to HTTP 502).

---

### 2.3 Prompt 3: Resume Gap Analysis (`RESUME_GAP_ANALYSIS_PROMPT`)

- **Used By**: `GeminiClient.analyze_resume_gap(resume_text, job_description)`
- **Caller**: `ResumeAnalysisService.analyze()`
- **Endpoint**: `POST /api/resume/analyze`
- **Input Parameters**: `{resume_text}`, `{job_description}`
- **Output JSON Schema**:
  ```json
  {
    "match_score": 75,
    "summary": "One to two sentences overall fit summary.",
    "missing_skills": ["Skill1", "Skill2"],
    "strengths": ["Skill1", "Skill2"],
    "suggestions": ["Actionable improvement 1", "Actionable improvement 2"],
    "ats_tips": ["ATS tip 1", "ATS tip 2"]
  }
  ```
- **Constraints & Rules**:
  - Bounded list caps: `missing_skills` (max 5), `strengths` (max 5), `suggestions` (max 5), `ats_tips` (max 5).
  - Operates statelessly without persisting results or altering job records.

---

### 2.4 Prompt 4: AI Interview Preparation Generator (`INTERVIEW_PREP_PROMPT`)

- **Used By**: `GeminiClient.generate_interview_prep(resume_text, job_description, job_title, company_name)`
- **Caller**: `InterviewPrepService.generate()`
- **Endpoint**: `POST /api/jobs/{job_id}/interview-prep`
- **Input Parameters**: `{resume_text}`, `{job_description}`, `{job_title}`, `{company_name}`
- **Output JSON Schema**:
  ```json
  {
    "project_questions": ["Question 1", "Question 2"],
    "technical_questions": ["Question 1", "Question 2"],
    "behavioral_questions": ["Question 1", "Question 2"],
    "topics_to_revise": ["Topic 1", "Topic 2"],
    "interview_tips": ["Tip 1", "Tip 2"]
  }
  ```
- **Constraints & Rules**:
  - `project_questions`: Max 8 questions grounded in projects/technologies explicitly named in resume.
  - `technical_questions`: Max 8 questions derived from job requirements.
  - `behavioral_questions`: Max 6 questions.
  - `topics_to_revise`: Max 8 concept topics.
  - `interview_tips`: Max 6 actionable interview tips.
  - Permissive parsing: Defaults individual unparseable lists to `[]` to maximize usability of partial results.