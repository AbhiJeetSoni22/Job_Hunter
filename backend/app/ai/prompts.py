"""
Gemini prompt templates.

Both prompts live here as module-level string constants so they can be
imported, tested, and iterated independently of the client.

Design rules (from docs/PROMPTS.md):
  - Structured JSON only — no markdown, no preamble, no code fences.
  - Exact output schema embedded in every prompt.
  - Bounded output (max 30 skills, max 5 missing skills, exactly 2 sentences).
  - No hallucination — only explicit information from the input.
  - Placeholders use {curly_brace} format for str.format() substitution.

Temperature: both prompts should be called with temperature=0.1 to
maximise consistency and minimise hallucination in structured output.
"""

# ---------------------------------------------------------------------------
# Prompt 1 — Skill extraction
#
# Used by: gemini_client.extract_skills(resume_text)
# Called from: resume_service.upload_resume() → Phase 2B
#
# Input substitution:
#   {resume_text}  — full plain text extracted from the PDF by PyMuPDF
#
# Expected output schema:
#   { "skills": ["Skill1", "Skill2", ...] }
# ---------------------------------------------------------------------------

SKILL_EXTRACTION_PROMPT = """You are a resume parser.

Extract technical skills from the resume text below.

Rules:
- Include only technical skills: programming languages, frameworks, libraries, databases, cloud platforms, developer tools, DevOps tools, testing tools, and software methodologies.
- Do not include soft skills, company names, job titles, or degree names.
- Do not infer or guess skills. Include a skill only if it appears explicitly in the text.
- Normalize names: use "PostgreSQL" not "Postgres", "React" not "React.js", "TypeScript" not "TS", "JavaScript" not "JS".
- Remove duplicates.
- Return at most 30 skills.

Return ONLY this exact JSON structure with no preamble, explanation, or markdown:

{{
  "skills": [
    "Skill1",
    "Skill2"
  ]
}}

Resume Text:

{resume_text}"""


# ---------------------------------------------------------------------------
# Prompt 2 — Job match scoring
#
# Used by: gemini_client.match_job(job_description, resume_skills)
# Called from: match_service.score_job() → Phase 2C
#
# Input substitutions:
#   {skills_list}      — comma-separated string of candidate skills
#   {job_description}  — full plain text of the job listing
#
# Expected output schema:
#   {
#     "match_score": 0-100,
#     "missing_skills": ["Skill1", ...],
#     "match_summary": "Sentence one. Sentence two."
#   }
# ---------------------------------------------------------------------------

JOB_MATCH_PROMPT = """You are a technical recruiter evaluating a candidate's fit for a role.

Candidate Skills:
{skills_list}

Job Description:
{job_description}

Return ONLY this exact JSON structure with no preamble, explanation, or markdown:

{{
  "match_score": 75,
  "missing_skills": [
    "Skill1",
    "Skill2"
  ],
  "match_summary": "Sentence one about strongest alignment. Sentence two about largest gaps."
}}

Scoring Rules:
- match_score is an integer 0 to 100. Score technical fit only.
- Ignore location, salary, company prestige, cultural fit, and years of experience.
- 80-100: candidate satisfies most or all technical requirements.
- 60-79: candidate satisfies core requirements but has some gaps.
- 40-59: candidate partially satisfies requirements with important gaps.
- 0-39: candidate lacks several required skills.
- Do not inflate scores. A candidate missing multiple required technologies should rarely score above 80.

Missing Skills Rules:
- List at most 5 skills.
- Include only skills explicitly mentioned in the job description.
- Do not invent or infer skills.

Summary Rules:
- Exactly 2 sentences.
- Sentence 1: strongest area of technical alignment.
- Sentence 2: largest technical gaps or concerns.""""""
Gemini prompt templates.

Both prompts live here as module-level string constants so they can be
imported, tested, and iterated independently of the client.

Design rules (from docs/PROMPTS.md):
  - Structured JSON only — no markdown, no preamble, no code fences.
  - Exact output schema embedded in every prompt.
  - Bounded output (max 30 skills, max 5 missing skills, exactly 2 sentences).
  - No hallucination — only explicit information from the input.
  - Placeholders use {curly_brace} format for str.format() substitution.

Temperature: both prompts should be called with temperature=0.1 to
maximise consistency and minimise hallucination in structured output.
"""

# ---------------------------------------------------------------------------
# Prompt 1 — Skill extraction
#
# Used by: gemini_client.extract_skills(resume_text)
# Called from: resume_service.upload_resume() → Phase 2B
#
# Input substitution:
#   {resume_text}  — full plain text extracted from the PDF by PyMuPDF
#
# Expected output schema:
#   { "skills": ["Skill1", "Skill2", ...] }
# ---------------------------------------------------------------------------

SKILL_EXTRACTION_PROMPT = """You are a resume parser.

Extract technical skills from the resume text below.

Rules:
- Include only technical skills: programming languages, frameworks, libraries, databases, cloud platforms, developer tools, DevOps tools, testing tools, and software methodologies.
- Do not include soft skills, company names, job titles, or degree names.
- Do not infer or guess skills. Include a skill only if it appears explicitly in the text.
- Normalize names: use "PostgreSQL" not "Postgres", "React" not "React.js", "TypeScript" not "TS", "JavaScript" not "JS".
- Remove duplicates.
- Return at most 30 skills.

Return ONLY this exact JSON structure with no preamble, explanation, or markdown:

{{
  "skills": [
    "Skill1",
    "Skill2"
  ]
}}

Resume Text:

{resume_text}"""


# ---------------------------------------------------------------------------
# Prompt 2 — Job match scoring
#
# Used by: gemini_client.match_job(job_description, resume_skills)
# Called from: match_service.score_job() → Phase 2C
#
# Input substitutions:
#   {skills_list}      — comma-separated string of candidate skills
#   {job_description}  — full plain text of the job listing
#
# Expected output schema:
#   {
#     "match_score": 0-100,
#     "missing_skills": ["Skill1", ...],
#     "match_summary": "Sentence one. Sentence two."
#   }
# ---------------------------------------------------------------------------

JOB_MATCH_PROMPT = """You are a technical recruiter evaluating a candidate's fit for a role.

Candidate Skills:
{skills_list}

Job Description:
{job_description}

Return ONLY this exact JSON structure with no preamble, explanation, or markdown:

{{
  "match_score": 75,
  "missing_skills": [
    "Skill1",
    "Skill2"
  ],
  "match_summary": "Sentence one about strongest alignment. Sentence two about largest gaps."
}}

Scoring Rules:
- match_score is an integer 0 to 100. Score technical fit only.
- Ignore location, salary, company prestige, cultural fit, and years of experience.
- 80-100: candidate satisfies most or all technical requirements.
- 60-79: candidate satisfies core requirements but has some gaps.
- 40-59: candidate partially satisfies requirements with important gaps.
- 0-39: candidate lacks several required skills.
- Do not inflate scores. A candidate missing multiple required technologies should rarely score above 80.

Missing Skills Rules:
- List at most 5 skills.
- Include only skills explicitly mentioned in the job description.
- Do not invent or infer skills.

Summary Rules:
- Exactly 2 sentences.
- Sentence 1: strongest area of technical alignment.
- Sentence 2: largest technical gaps or concerns."""