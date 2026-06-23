"""
Gemini AI client.

Wraps the google-generativeai SDK with:
  - Typed method signatures
  - Structured JSON response parsing
  - Retry logic on transient failures (429, 500, 502, 503)
  - Exponential backoff: 1s → 2s → 4s
  - Custom AIError after all retries exhausted
  - Response validation (rejects malformed or empty output)
  - Logging at every step (never logs API keys or raw resume text)

Two public methods:
  extract_skills(resume_text)            → list[str]
  match_job(job_description, skills)     → MatchResult dict

Architecture rule:
  Services import GeminiClient and call its methods.
  GeminiClient never imports from services, models, or schemas.
  All Gemini API concerns are isolated here.

google-generativeai import note:
  Installed as 'google-generativeai', imported as 'google.generativeai'.
  The SDK is synchronous. For a personal-use single-user tool this is
  sufficient — no async wrapping needed.
"""

import json
import logging
import re
import time
from typing import Any, TypedDict

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.ai.prompts import JOB_MATCH_PROMPT, SKILL_EXTRACTION_PROMPT
from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Retry configuration ────────────────────────────────────────────────────

# HTTP status codes that indicate a transient failure worth retrying
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503})

# Backoff delays in seconds between attempts (3 attempts total)
_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)

# Maximum skills to accept from Gemini (matches prompt constraint)
_MAX_SKILLS = 30

# Maximum missing skills to accept from Gemini (matches prompt constraint)
_MAX_MISSING_SKILLS = 5


# ── Custom exception ───────────────────────────────────────────────────────

class AIError(Exception):
    """
    Raised when the Gemini API fails after all retry attempts.

    Callers (resume_service, match_service) catch this and decide
    whether to degrade gracefully or propagate.
    """

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


# ── Typed return shapes ────────────────────────────────────────────────────

class MatchResult(TypedDict):
    """Structured output from match_job()."""
    match_score: int
    missing_skills: list[str]
    match_summary: str


# ── Client ─────────────────────────────────────────────────────────────────

class GeminiClient:
    """
    Reusable Gemini API client.

    Instantiated once and reused across calls. Configuration is read
    from Settings at instantiation time — no per-call config needed.

    Usage:
        client = GeminiClient()
        skills = client.extract_skills(raw_text)
        result = client.match_job(description, skills)
    """

    def __init__(self) -> None:
        settings = get_settings()
        # Configure the SDK with the API key. genai.configure() is idempotent.
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model_name = settings.GEMINI_MODEL
        self._generation_config = GenerationConfig(
            temperature=0.1,        # Low temperature → deterministic JSON output
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192, # raised from 2048 — skill JSON ~300-600 tokens;
                                    # 2048 was causing MAX_TOKENS truncation mid-response
        )
        logger.debug("GeminiClient: initialised with model '%s'", self._model_name)

    # ── Public: skill extraction ───────────────────────────────────────────

    def extract_skills(self, resume_text: str) -> list[str]:
        """
        Extract technical skills from raw resume text.

        Sends the text to Gemini using SKILL_EXTRACTION_PROMPT and
        parses the JSON response into a list of skill strings.

        Args:
            resume_text: Plain text extracted from the PDF by PyMuPDF.

        Returns:
            List of normalised skill strings (up to 30).
            Returns an empty list if the response is malformed — never raises
            on parse failure so resume upload always succeeds.

        Raises:
            AIError: if all retry attempts fail (network, rate limit, server error).
        """
        if not resume_text or not resume_text.strip():
            logger.warning("GeminiClient.extract_skills: received empty text — returning []")
            return []

        prompt = SKILL_EXTRACTION_PROMPT.format(resume_text=resume_text)

        logger.info(
            "GeminiClient.extract_skills: calling Gemini (model=%s, text_len=%d)",
            self._model_name,
            len(resume_text),
        )

        raw_response = self._call_with_retry(prompt, operation="extract_skills")

        logger.debug(
            "GeminiClient.extract_skills: received response length=%d chars",
            len(raw_response),
        )

        try:
            skills = self._parse_skills(raw_response)
            logger.info(
                "GeminiClient.extract_skills: parsed %d skills successfully", len(skills)
            )
            return skills
        except (ValueError, KeyError, TypeError) as exc:
            # Parse failure: log and return empty list — upload must not fail
            logger.error(
                "GeminiClient.extract_skills: failed to parse response — returning []. "
                "Error: %s. Raw response (first 200 chars): %.200s",
                exc,
                raw_response,
            )
            return []

    # ── Public: job match scoring ──────────────────────────────────────────

    def match_job(
        self,
        job_description: str,
        resume_skills: list[str],
    ) -> MatchResult:
        """
        Score a job description against a candidate's skill list.

        Sends both to Gemini using JOB_MATCH_PROMPT and parses the
        structured JSON response.

        Args:
            job_description: Full plain text of the job listing.
            resume_skills:   List of skills from the candidate's resume.

        Returns:
            MatchResult TypedDict:
                match_score    (int)       0–100
                missing_skills (list[str]) up to 5 items
                match_summary  (str)       exactly 2 sentences

        Raises:
            AIError:    if all retry attempts fail.
            ValueError: if the Gemini response is structurally invalid
                        (caller should treat this as a scoring failure).
        """
        if not job_description.strip():
            raise ValueError("job_description must not be empty")
        if not resume_skills:
            raise ValueError("resume_skills must not be empty")

        skills_list = ", ".join(resume_skills)
        prompt = JOB_MATCH_PROMPT.format(
            skills_list=skills_list,
            job_description=job_description,
        )

        logger.info(
            "GeminiClient.match_job: calling Gemini (model=%s, skills=%d, desc_len=%d)",
            self._model_name,
            len(resume_skills),
            len(job_description),
        )

        raw_response = self._call_with_retry(prompt, operation="match_job")

        result = self._parse_match_result(raw_response)
        logger.info(
            "GeminiClient.match_job: score=%d missing_skills=%d",
            result["match_score"],
            len(result["missing_skills"]),
        )
        return result

    # ── Private: API call with retry ───────────────────────────────────────

    def _call_with_retry(self, prompt: str, *, operation: str) -> str:
        """
        Call the Gemini API with exponential backoff retry.

        Retries on transient errors (429, 500, 502, 503) using backoff
        delays of 1s, 2s, 4s. Raises AIError after all attempts fail.

        Args:
            prompt:    The fully-rendered prompt string.
            operation: Human-readable name for logging (e.g. "extract_skills").

        Returns:
            Raw text response from Gemini.

        Raises:
            AIError: after all retry attempts are exhausted.
        """
        model = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=self._generation_config,
        )

        last_exc: Exception | None = None

        for attempt, backoff in enumerate(_BACKOFF_SECONDS, start=1):
            try:
                logger.debug(
                    "GeminiClient.%s: attempt %d/%d",
                    operation, attempt, len(_BACKOFF_SECONDS),
                )
                response = model.generate_content(prompt)

                # ── Diagnostic: finish reason + token metadata ────────
                try:
                    candidate = (
                        response.candidates[0]
                        if response.candidates else None
                    )
                    finish_reason = (
                        candidate.finish_reason if candidate else "NO_CANDIDATE"
                    )
                    part_count = (
                        len(candidate.content.parts)
                        if candidate and candidate.content else 0
                    )
                    logger.info(
                        "GeminiClient.%s: finish_reason=%s "
                        "candidates=%d parts=%d",
                        operation,
                        finish_reason,
                        len(response.candidates) if response.candidates else 0,
                        part_count,
                    )
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        um = response.usage_metadata
                        logger.info(
                            "GeminiClient.%s: tokens prompt=%s output=%s total=%s",
                            operation,
                            getattr(um, "prompt_token_count", "?"),
                            getattr(um, "candidates_token_count", "?"),
                            getattr(um, "total_token_count", "?"),
                        )
                    finish_str = str(finish_reason)
                    if "MAX_TOKEN" in finish_str or finish_str == "2":
                        logger.warning(
                            "GeminiClient.%s: finish_reason=MAX_TOKENS — "
                            "response was cut before completion. "
                            "max_output_tokens may still be too low.",
                            operation,
                        )
                except Exception as diag_exc:
                    logger.debug(
                        "GeminiClient.%s: could not read response metadata: %s",
                        operation, diag_exc,
                    )

                text = response.text

                if not text or not text.strip():
                    raise ValueError("Gemini returned an empty response")

                logger.debug(
                    "GeminiClient.%s: attempt %d succeeded, response=%d chars",
                    operation, attempt, len(text),
                )
                return text

            except Exception as exc:
                last_exc = exc
                exc_str = str(exc)

                # Check if this is a retryable error
                is_retryable = self._is_retryable(exc)

                if attempt < len(_BACKOFF_SECONDS) and is_retryable:
                    logger.warning(
                        "GeminiClient.%s: attempt %d failed (%s) — "
                        "retrying in %.0fs",
                        operation, attempt, exc_str, backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "GeminiClient.%s: attempt %d failed (%s) — "
                        "%s",
                        operation,
                        attempt,
                        exc_str,
                        "no more retries" if attempt >= len(_BACKOFF_SECONDS)
                        else "non-retryable error, aborting",
                    )
                    break

        raise AIError(
            f"Gemini {operation} failed after {len(_BACKOFF_SECONDS)} attempts: "
            f"{last_exc}",
            cause=last_exc,
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """
        Determine whether an exception warrants a retry attempt.

        Checks for HTTP status codes in the exception message/type string,
        since google-generativeai surfaces errors in various ways depending
        on the error type (ResourceExhausted, ServiceUnavailable, etc.).
        """
        exc_str = str(exc).lower()
        exc_type = type(exc).__name__.lower()

        # Rate limit signals
        if "429" in exc_str or "resourceexhausted" in exc_type or "quota" in exc_str:
            return True

        # Server error signals
        for code in ("500", "502", "503"):
            if code in exc_str:
                return True

        if "unavailable" in exc_type or "unavailable" in exc_str:
            return True

        if "internalservererror" in exc_type:
            return True

        # Network-level transient errors
        if "timeout" in exc_str or "connection" in exc_str:
            return True

        return False

    # ── Private: response parsing ──────────────────────────────────────────

    @staticmethod
    @staticmethod
    def _extract_json_str(raw: str) -> str:
        """
        Extract the first JSON object or array from a raw string.

        Strategy (in order):
          1. Look for a fenced code block (```json ... ``` or ``` ... ```)
             and extract its contents. This handles Gemini responses that
             wrap JSON in markdown despite being told not to.
          2. Find the first '{' or '[' in the string and slice from there
             to the matching closing brace/bracket. This handles responses
             with leading prose like "Here are the extracted skills:\n{...}".
          3. Fall back to the full stripped string and let json.loads decide.

        Returns the extracted substring ready for json.loads().
        """
        stripped = raw.strip()

        # ── Strategy 1: fenced code block ─────────────────────────────────
        # Matches: ```json\n{...}\n``` or ```\n[...]\n```
        fence_match = re.search(
            r"```(?:json)?\s*([\s\S]*?)```",
            stripped,
            flags=re.IGNORECASE,
        )
        if fence_match:
            candidate = fence_match.group(1).strip()
            if candidate:
                logger.debug(
                    "_extract_json_str: extracted %d chars from fenced block "
                    "(raw=%d chars)",
                    len(candidate),
                    len(raw),
                )
                return candidate

        # ── Strategy 2: find first JSON structure delimiter ────────────────
        # Handles "Here are the skills:\n{...}" or any leading prose.
        first_brace = stripped.find("{")
        first_bracket = stripped.find("[")

        # Pick whichever delimiter appears first (ignore -1 = not found)
        candidates = [i for i in (first_brace, first_bracket) if i != -1]
        if candidates:
            start = min(candidates)
            opener = stripped[start]
            closer = "}" if opener == "{" else "]"

            # Walk from the end to find the matching closer
            end = stripped.rfind(closer)
            if end != -1 and end > start:
                candidate = stripped[start : end + 1]
                logger.debug(
                    "_extract_json_str: extracted %d chars via delimiter scan "
                    "(raw=%d chars, opener=%r)",
                    len(candidate),
                    len(raw),
                    opener,
                )
                return candidate

        # ── Strategy 3: full string fallback ──────────────────────────────
        logger.debug(
            "_extract_json_str: no structure found — using full string "
            "(%d chars)",
            len(stripped),
        )
        return stripped

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | list[Any]:
        """
        Extract and parse the first JSON value from a raw Gemini response.

        Returns either a dict or a list — callers must handle both.
        Raises ValueError with a safe (length-limited) snippet on failure.
        """
        logger.debug(
            "_parse_json: raw response length=%d chars", len(raw)
        )
        candidate = GeminiClient._extract_json_str(raw)
        logger.debug(
            "_parse_json: candidate length=%d chars", len(candidate)
        )
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            # Log a safe snippet — never the full response
            snippet = candidate[:200].replace("\n", " ")
            raise ValueError(
                f"Could not parse JSON from Gemini response: {exc}. "
                f"Candidate snippet (first 200 chars): {snippet!r}"
            ) from exc
        if not isinstance(parsed, (dict, list)):
            raise ValueError(
                f"Expected a JSON object or array, got {type(parsed).__name__}"
            )
        return parsed

    def _parse_skills(self, raw: str) -> list[str]:
        """
        Parse the extract_skills response into a list of skill strings.

        Accepts two formats:
          Format A — wrapped object: { "skills": ["Skill1", "Skill2", ...] }
          Format B — bare array:     ["Skill1", "Skill2", ...]

        Validation:
          - Each item must be a non-empty string
          - Truncated to _MAX_SKILLS items

        Returns an empty list rather than raising on schema mismatch,
        so that resume upload always succeeds even on unexpected output.
        """
        parsed = self._parse_json(raw)

        # ── Resolve to a list regardless of wrapping format ────────────────
        if isinstance(parsed, list):
            # Format B: bare array
            raw_skills = parsed
        elif isinstance(parsed, dict):
            # Format A: { "skills": [...] }
            # Also accept common Gemini variations: "skill_list", "extracted_skills"
            for key in ("skills", "skill_list", "extracted_skills", "technologies"):
                if key in parsed and isinstance(parsed[key], list):
                    raw_skills = parsed[key]
                    break
            else:
                logger.warning(
                    "_parse_skills: dict has no recognised skills key. "
                    "Keys found: %s — returning []",
                    list(parsed.keys()),
                )
                return []
        else:
            logger.warning(
                "_parse_skills: unexpected top-level type %s — returning []",
                type(parsed).__name__,
            )
            return []

        # ── Filter to non-empty strings only; truncate to maximum ──────────
        skills: list[str] = []
        for item in raw_skills[:_MAX_SKILLS]:
            if isinstance(item, str) and item.strip():
                skills.append(item.strip())

        logger.debug("_parse_skills: returning %d skills", len(skills))
        return skills

    def _parse_match_result(self, raw: str) -> MatchResult:
        """
        Parse the match_job response into a MatchResult TypedDict.

        Expected input:
          {
            "match_score": 75,
            "missing_skills": ["Skill1", "Skill2"],
            "match_summary": "Sentence one. Sentence two."
          }

        Validation:
          - match_score must be an integer 0–100
          - missing_skills must be a list of strings (up to 5)
          - match_summary must be a non-empty string

        Raises:
            ValueError: if any required field is missing or invalid.
        """
        parsed = self._parse_json(raw)
        if not isinstance(parsed, dict):
            raise ValueError(
                f"match_job response must be a JSON object, "
                f"got {type(parsed).__name__}"
            )
        data: dict[str, Any] = parsed

        # ── match_score ────────────────────────────────────────────────────
        if "match_score" not in data:
            raise ValueError("Response missing 'match_score'")
        raw_score = data["match_score"]
        if not isinstance(raw_score, (int, float)):
            raise ValueError(
                f"'match_score' must be a number, got {type(raw_score).__name__}"
            )
        match_score = max(0, min(100, int(raw_score)))  # Clamp to [0, 100]

        # ── missing_skills ─────────────────────────────────────────────────
        raw_missing = data.get("missing_skills", [])
        if not isinstance(raw_missing, list):
            raise ValueError(
                f"'missing_skills' must be a list, got {type(raw_missing).__name__}"
            )
        missing_skills: list[str] = []
        for item in raw_missing[:_MAX_MISSING_SKILLS]:
            if isinstance(item, str) and item.strip():
                missing_skills.append(item.strip())

        # ── match_summary ──────────────────────────────────────────────────
        if "match_summary" not in data:
            raise ValueError("Response missing 'match_summary'")
        raw_summary = data["match_summary"]
        if not isinstance(raw_summary, str) or not raw_summary.strip():
            raise ValueError(
                f"'match_summary' must be a non-empty string, got {raw_summary!r}"
            )
        match_summary = raw_summary.strip()

        return MatchResult(
            match_score=match_score,
            missing_skills=missing_skills,
            match_summary=match_summary,
        )