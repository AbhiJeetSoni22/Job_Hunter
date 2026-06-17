# API Specification

Base URL

/api/v1

---

## Resume APIs

POST /resume/upload

Upload resume PDF.

---

GET /resume/profile

Get parsed resume profile.

---

## Job APIs

GET /jobs

Get all jobs.

---

GET /jobs/{id}

Get job details.

---

POST /jobs/sync

Run scraper manually.

---

## Match APIs

POST /match/{job_id}

Generate match score.

---

GET /matches

Get all scored jobs.

---

## Application APIs

POST /applications

Create application record.

---

PATCH /applications/{id}

Update status.

---

GET /applications

Get all applications.
