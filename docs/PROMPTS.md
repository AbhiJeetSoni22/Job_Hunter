# Prompts

Gemini is used in four operations:

1. Skill extraction (resume upload)
2. Job matching (job scoring)
3. Resume gap analysis (Resume Gap Analyzer)
4. Interview preparation generation (Job Detail → Generate Interview Prep)

All prompts live in:

```text
backend/app/ai/prompts.py
```

> **Known issue (cosmetic, not functional):** the source file currently has its docstring and the first two prompt constants duplicated back-to-back — likely from a bad merge. Python's last-assignment-wins behavior means the correct, final values of `SKILL_EXTRACTION_PROMPT` and `JOB_MATCH_PROMPT` (the ones documented below) are what the rest of the app actually uses; nothing is broken at runtime. The file should still be cleaned up to remove the dead duplicate block.

---

# Design Principles

## Structured JSON Only

All prompts must return valid JSON.

No markdown.

No explanations.

No code fences.

No conversational text.

---

## Explicit Schema

The exact output structure is provided inside every prompt.

Models produce more consistent outputs when given a strict schema.

---

## Bounded Output

### Skill Extraction

* Maximum 30 skills

### Job Matching

* Maximum 5 missing skills
* Exactly 2 summary sentences

### Resume Gap Analysis

* Match score: 0–100
* Summary: 1–2 sentences
* Missing skills: maximum 5
* Strengths: maximum 5
* Suggestions: maximum 5
* ATS tips: maximum 5

### Interview Preparation Generator

* Project questions: maximum 8
* Technical questions: maximum 8
* Behavioral questions: maximum 6
* Topics to revise: maximum 8
* Interview tips: maximum 6

---

## No Hallucinations

The model must not:

* invent skills
* infer technologies
* assume experience
* add requirements not present in input

Only explicit information should be used.

---

## Deterministic Behaviour

Prompts are optimized for consistency rather than creativity.

Use:

```python
temperature = 0.1
```

for all requests.

---

# Prompt 1 — Skill Extraction

Used in:

```text
resume_service.upload_resume()
↓
gemini_client.extract_skills()
```

```python
SKILL_EXTRACTION_PROMPT = """
You are a resume parser.

Extract technical skills from the resume text below.

Rules:

- Include only technical skills.
- Include programming languages, frameworks, libraries, databases, cloud platforms, developer tools, DevOps tools, testing tools, and software methodologies.
- Do not include soft skills.
- Do not include company names.
- Do not include job titles.
- Do not include degree names.
- Do not infer skills.
- Include a skill only if it appears explicitly.
- Normalize names:
    - PostgreSQL (not Postgres)
    - React (not React.js)
    - TypeScript (not TS)
    - JavaScript (not JS)
- Remove duplicates.
- Return at most 30 skills.

Return ONLY valid JSON:

{
  "skills": [
    "Skill1",
    "Skill2"
  ]
}

Resume Text:

{resume_text}
"""
```

---

## Example Output

```json
{
  "skills": [
    "Python",
    "FastAPI",
    "PostgreSQL",
    "SQLAlchemy",
    "Alembic",
    "React",
    "TypeScript",
    "Next.js",
    "Tailwind CSS",
    "Docker",
    "Git",
    "GitHub Actions",
    "REST APIs",
    "Pytest",
    "Linux",
    "AWS"
  ]
}
```

---

# Prompt 2 — Job Matching

Used in:

```text
match_service.score_job()
↓
gemini_client.match_job()
```

```python
JOB_MATCH_PROMPT = """
You are a technical recruiter evaluating a candidate's technical fit for a role.

Candidate Skills:

{skills_list}

Job Description:

{job_description}

Return ONLY valid JSON:

{
  "match_score": 75,
  "missing_skills": [
    "Skill1",
    "Skill2"
  ],
  "match_summary": "Sentence one. Sentence two."
}

Scoring Rules:

- Score from 0 to 100.
- Score technical fit only.
- Ignore location.
- Ignore salary.
- Ignore company prestige.
- Ignore cultural fit.
- Ignore years of experience.

Scoring Guide:

80-100
Candidate satisfies most technical requirements.

60-79
Candidate satisfies core requirements but has some gaps.

40-59
Candidate partially satisfies requirements and has important gaps.

0-39
Candidate lacks several required skills.

Missing Skills Rules:

- Maximum 5 skills.
- Include only skills explicitly mentioned in the job description.
- Do not invent skills.
- Do not infer skills.

Summary Rules:

- Exactly 2 sentences.
- Sentence 1:
  strongest technical alignment.
- Sentence 2:
  largest technical gaps.

Important:

Do not inflate scores.

A candidate missing multiple required technologies should rarely receive a score above 80.
"""
```

---

## Example Output

```json
{
  "match_score": 78,
  "missing_skills": [
    "GraphQL",
    "Kubernetes"
  ],
  "match_summary": "Strong alignment on Python backend development, FastAPI, and PostgreSQL requirements. The primary gaps are Kubernetes and GraphQL, both listed as preferred technologies."
}
```

---

# Prompt 3 — Resume Gap Analysis

Used in:

```text
resume_analysis_service.analyze()
↓
gemini_client.analyze_resume_gap()
```

This is a dedicated prompt used by the Resume Gap Analyzer feature (`POST /api/resume/analyze`). It runs independently from job scoring and does not replace or modify the existing Job Match prompt.

Input substitutions:

```text
{resume_text}      — full plain text extracted from the active resume
{job_description}  — full plain text pasted by the user
```

Expected output schema:

```json
{
  "match_score": 75,
  "summary": "One to two sentences on overall fit for this specific role.",
  "missing_skills": ["Skill1", "Skill2"],
  "strengths": ["Skill1", "Skill2"],
  "suggestions": ["Actionable suggestion 1", "Actionable suggestion 2"],
  "ats_tips": ["ATS tip 1", "ATS tip 2"]
}
```

Key differences from Job Match prompt:

- Includes `summary` (1–2 sentences vs. exactly 2)
- Includes `strengths` (skills/experience in resume matching the job)
- Includes `suggestions` (concrete, actionable resume improvements for this specific role)
- Includes `ats_tips` (Applicant Tracking System optimization tips specific to the job description)
- Takes full resume text (not just extracted skills) — allows richer analysis
- Bounded to 5 items each for missing_skills, strengths, suggestions, and ats_tips

## Example Output

```json
{
  "match_score": 78,
  "summary": "Strong fit for a backend role. Your FastAPI and PostgreSQL experience aligns well with the core requirements. Primary gaps are in DevOps tooling.",
  "missing_skills": [
    "Kubernetes",
    "Docker Compose",
    "Terraform",
    "CI/CD Pipelines",
    "AWS ECS"
  ],
  "strengths": [
    "FastAPI",
    "PostgreSQL",
    "REST APIs",
    "Python",
    "Docker"
  ],
  "suggestions": [
    "Highlight containerization work prominently in your projects section",
    "Add deployment/infrastructure experience if you have any, even personal projects",
    "Quantify performance improvements you've made to backend systems",
    "Mention any experience with configuration management or infrastructure-as-code",
    "Add a DevOps or infrastructure project to your portfolio"
  ],
  "ats_tips": [
    "Use 'Kubernetes' not 'K8s' for ATS matching",
    "Match the exact job title from the posting (e.g., 'Backend Engineer' vs 'Backend Developer')",
    "Include both full names and common abbreviations (e.g., 'PostgreSQL (Postgres)')",
    "Use standard cloud platform names: 'AWS', 'Google Cloud', 'Azure'",
    "List technologies in a dedicated 'Technical Skills' section near the top"
  ]
}
```

---

# Prompt 4 — Interview Preparation Generator

Used in:

```text
interview_prep_service.generate()
↓
gemini_client.generate_interview_prep()
```

This prompt is dedicated to the Job Detail interview-prep flow. It uses the active resume text along with the selected job's title, company, and description to return practical interview preparation guidance.

Input substitutions:

```text
{resume_text}      — full plain text extracted from the active resume
{job_description}  — full plain text of the selected job listing
{job_title}        — job title from the saved job row
{company_name}     — company name from the saved job row
```

Expected output schema:

```json
{
  "project_questions": ["Question 1", "Question 2"],
  "technical_questions": ["Question 1", "Question 2"],
  "behavioral_questions": ["Question 1", "Question 2"],
  "topics_to_revise": ["Topic 1", "Topic 2"],
  "interview_tips": ["Tip 1", "Tip 2"]
}
```

The prompt is optimized to stay structured, specific to the job, and grounded in the active resume without introducing any persistence or state beyond the immediate request.

---

# Gemini Client Notes

Implementation:

```text
gemini_client.py
```

---

## Model

Default:

```python
MODEL_NAME = "gemini-2.5-flash"
```

Store model name in settings:

```env
GEMINI_MODEL=gemini-2.5-flash
```

Avoid hardcoding model names.

---

## Response Parsing

````python
import json
import re

def parse_json_response(raw: str) -> dict:
    cleaned = re.sub(
        r"```(?:json)?|```",
        "",
        raw
    ).strip()

    return json.loads(cleaned)
````

---

## Retry Policy

Retry on:

```text
429
500
502
503
```

Maximum attempts:

```text
3
```

Backoff:

```text
1 second
2 seconds
4 seconds
```

Raise:

```python
AIError
```

after final failure.

---

## Temperature

```python
temperature = 0.1
```

Reason:

* More consistent JSON
* Less hallucination
* Better scoring consistency

---

## Safety Settings

Default Gemini safety settings are sufficient.

No custom overrides required.

---

# Prompt Iteration Log

Track prompt changes here.

| Version | Date    | Change                                                        | Reason                 |
| ------- | ------- | ------------------------------------------------------------- | ---------------------- |
| v1      | Initial | Base prompts                                                  | Initial implementation |
| v2      | Current | Added duplicate removal, score strictness, configurable model | Better consistency     |

---

# Common Failure Modes

### Markdown Fences

Bad:

````text
```json
{
}
```
````

Solution:

Strip fences before parsing.

---

### Inflated Scores

Bad:

```json
{
  "match_score": 95
}
```

despite missing multiple required skills.

Solution:

Use strict scoring rubric.

---

### Invented Skills

Bad:

```json
{
  "missing_skills": [
    "AWS"
  ]
}
```

when AWS does not appear in the job description.

Solution:

Prompt explicitly forbids inference.