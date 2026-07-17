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


# ---------------------------------------------------------------------------
# Prompt 3 — Resume Gap Analyzer (new, isolated feature)
#
# Used by: gemini_client.analyze_resume_gap(resume_text, job_description)
# Called from: resume_analysis_service.py (new — Resume Gap Analyzer)
#
# This is a dedicated prompt, separate from JOB_MATCH_PROMPT. It does not
# replace or alter job match scoring in any way — match_service and
# JOB_MATCH_PROMPT are untouched. This prompt is used only by the new
# POST /api/resume/analyze endpoint.
#
# Input substitutions:
    #   {resume_text}      — full plain text extracted from the active resume
    #   {job_description}  — full plain text pasted by the user
    #
    # Expected output schema:
        #   {
            #     "match_score": 0-100,
            #     "summary": "...",
            #     "missing_skills": ["Skill1", ...],
            #     "strengths": ["Skill1", ...],
            #     "suggestions": ["...", ...],
            #     "ats_tips": ["...", ...]
            #   }
            # ---------------------------------------------------------------------------

RESUME_GAP_ANALYSIS_PROMPT = """You are a career coach and technical recruiter helping a candidate improve their resume for a specific job.

            Resume Text:
                {resume_text}

                Job Description:
                    {job_description}

                    Analyze how well the resume aligns with the job description and return ONLY this exact JSON structure with no preamble, explanation, or markdown:

                        {{
                            "match_score": 75,
                            "summary": "One to two sentences on overall fit for this specific role.",
                            "missing_skills": [
                                "Skill1",
                                "Skill2"
                            ],
                            "strengths": [
                                "Skill1",
                                "Skill2"
                            ],
                            "suggestions": [
                                "Actionable resume improvement 1",
                                "Actionable resume improvement 2"
                            ],
                            "ats_tips": [
                                "ATS optimization tip 1",
                                "ATS optimization tip 2"
                            ]
                        }}

                        Scoring Rules:
                            - match_score is an integer 0 to 100. Score technical fit only.
                            - Ignore location, salary, company prestige, and cultural fit.
                            - Do not inflate scores. A resume missing multiple required technologies should rarely score above 80.

                            Missing Skills Rules:
                                - List at most 5 skills explicitly required by the job description but not found in the resume.
                                - Do not invent or infer skills not mentioned in the job description.

                                Strengths Rules:
                                    - List at most 5 skills or experiences from the resume that directly match the job description.
                                    - Only include items explicitly present in the resume text.

                                    Suggestions Rules:
                                        - List at most 5 concrete, actionable ways the candidate could improve their resume for THIS specific role.
                                        - Focus on content and framing (e.g. quantifying impact, adding relevant projects, reordering sections) — not generic advice.
                                        - Do not suggest fabricating experience the candidate does not have.

                                        ATS Tips Rules:
                                            - List at most 5 concrete Applicant Tracking System optimization tips specific to this job description.
                                            - Focus on keyword alignment, formatting, and terminology matching the job posting.

                                            General Rules:
                                                - Base every claim only on the resume text and job description provided. Do not hallucinate.
                                                - Keep each list item concise — one sentence or short phrase."""
# ---------------------------------------------------------------------------
# Prompt 4 — AI Interview Preparation Generator (new, isolated feature)
#
# Used by: gemini_client.generate_interview_prep(resume_text, job_description,
#           job_title, company_name)
# Called from: interview_prep_service.py (new — AI Interview Prep Generator)
#
# This is a dedicated prompt, separate from JOB_MATCH_PROMPT and
# RESUME_GAP_ANALYSIS_PROMPT. It does not replace or alter job match
# scoring or resume gap analysis in any way. Used only by the new
# POST /api/jobs/{job_id}/interview-prep endpoint.
#
# Input substitutions:
    #   {resume_text}      — full plain text of the active resume
    #   {job_description}  — full plain text of the job listing
    #   {job_title}        — job title as stored on the Job row
    #   {company_name}     — company name as stored on the Job row
    #
    # Expected output schema:
        #   {
            #     "technical_questions": ["...", ...],
            #     "behavioral_questions": ["...", ...],
            #     "project_questions": ["...", ...],
            #     "topics_to_revise": ["...", ...],
            #     "interview_tips": ["...", ...]
            #   }
            # ---------------------------------------------------------------------------

INTERVIEW_PREP_PROMPT = """You are an interviewer at a startup preparing to interview a candidate for an internship-level role. You write specific, grounded questions — never generic "tell me about a time" filler unless the situation calls for it.

            Resume Text:
                {resume_text}

                Job Title: {job_title}
                Company: {company_name}

                Job Description:
                    {job_description}

                    Generate interview preparation material tailored to THIS candidate and THIS role. Return ONLY this exact JSON structure with no preamble, explanation, or markdown:

                        {{
                            "project_questions": [
                                "Project question 1",
                                "Project question 2"
                            ],
                            "technical_questions": [
                                "Technical question 1",
                                "Technical question 2"
                            ],
                            "behavioral_questions": [
                                "Behavioral question 1",
                                "Behavioral question 2"
                            ],
                            "topics_to_revise": [
                                "Topic 1",
                                "Topic 2"
                            ],
                            "interview_tips": [
                                "Tip 1",
                                "Tip 2"
                            ]
                        }}

                        Project Questions Rules (HIGHEST PRIORITY — generate these first, put the most effort here):
                            - Derive every question directly from specific projects, tools, and experience named in the resume text. Never invent a project.
                            - Reference the candidate's own project names, stack choices, and stated outcomes when writing each question.
                            - Ask about architecture/design decisions, why one technology was chosen over an alternative, how a specific hard part was implemented, and how a challenging bug or tradeoff was handled.
                            - Write these the way a real engineer conducting the interview would — specific and pointed, e.g. "Why did you choose FastAPI instead of Express for [project]?" not "Tell me about a project."
                            - List at most 8.

                            Technical Questions Rules:
                                - Derive every question from the specific technologies, frameworks, and requirements explicitly stated in the job description.
                                - Favor technologies required by the job description that appear weakly or not at all in the resume — these are the real gaps an interviewer would probe.
                                - Avoid generic textbook questions ("what is a REST API") unless the job description's seniority level makes that appropriate.
                                - List at most 8.

                                Behavioral Questions Rules:
                                    - List at most 6 situational/behavioral questions relevant to this role's seniority and team context (internship/startup pace, ambiguity, ownership).
                                    - Do not invent candidate history — keep these role-general, not resume-specific.

                                    Topics To Revise Rules:
                                        - List at most 8 concrete technical concepts or tools from the job description the candidate should brush up on.
                                        - Prioritize gaps: required by the job description but weak or absent in the resume.

                                        Interview Tips Rules:
                                            - List at most 6 concrete, actionable tips specific to this role, company, and interview stage — not generic advice like "be confident."

                                            General Rules:
                                                - Base every item only on the resume text, job title, company name, and job description provided. Do not hallucinate projects, companies, or skills.
                                                - Prioritize realism over volume — an interviewer would rather ask 3 sharp project questions than 8 shallow ones. It's fine to return fewer than the max if the resume doesn't support more.
                                                - Keep each item concise — one sentence or short phrase."""