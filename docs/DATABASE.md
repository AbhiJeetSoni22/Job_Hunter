# Database Design

## users

id
name
email
created_at

---

## resume_profiles

id
user_id
resume_url
skills_json
projects_json
experience_json
created_at

---

## companies

id
name
website
industry
location

---

## jobs

id
company_id
title
location
salary
job_url
source
description
required_skills
posted_at
created_at

---

## job_matches

id
job_id
user_id
match_score
missing_skills
strengths
created_at

---

## applications

id
job_id
user_id
status

Possible Status Values:

* saved
* applied
* interview
* offer
* rejected

created_at
updated_at
