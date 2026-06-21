"""
RemoteOK scraper — Phase 1C.

Source  : RemoteOK public JSON API
Endpoint: https://remoteok.com/api
Method  : httpx GET — no browser, no auth, no API key required

API contract (confirmed from live response):
  Response is a JSON array. First element is a legal notice dict (no 'slug').
  Every subsequent element is a job with these fields:
    slug          str   — unique id, e.g. "86711-remote-frontend-developer-..."
    id            str   — numeric id as string
    epoch         str   — unix timestamp as string
    date          str   — ISO 8601 date string
    company       str   — company name
    company_logo  str   — logo URL (may be empty string)
    position      str   — job title
    tags          list  — list of tag strings (may include salary like "$80k-$100k")
    description   str   — HTML job description (strip tags before storing)
    url           str   — canonical RemoteOK URL for this job

ToS note (remoteok.com/api legal field):
  Must mention RemoteOK as source and link back to job URL with a DIRECT link.
  We store the direct URL in job.url — compliant.

Rate limiting:
  RemoteOK requests a User-Agent header that is not a generic browser string.
  We send a custom user-agent identifying this application.
  Jobs are delayed 24h vs the web listing — expected behaviour.
"""

import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import httpx

from app.scrapers.base import BaseScraper
from app.schemas.job import JobUpsertData

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

API_URL = "https://remoteok.com/api"

# RemoteOK asks integrators to identify themselves properly
USER_AGENT = (
    "AI-Internship-Hunter/1.0 "
    "(personal internship tracker; https://github.com/yourusername/ai-internship-hunter)"
)

# Request timeout: connect 10s, read 30s (API can be slow)
TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)

# Keyword filter — only ingest jobs relevant to internships / entry-level roles.
# Matching is case-insensitive against the position string and tags.
INTERNSHIP_KEYWORDS: frozenset[str] = frozenset({
    "intern",
    "internship",
    "junior",
    "entry level",
    "entry-level",
    "graduate",
    "new grad",
    "fresher",
    "Backend Intern",
    "Node.js Intern",
    "Software Engineer Intern"
})

# Minimum description length — skip jobs that are clearly malformed/empty
MIN_DESCRIPTION_LENGTH = 50


# ── HTML stripping ─────────────────────────────────────────────────────────

class _HTMLStripper(HTMLParser):
    """Minimal HTML-to-text converter. Avoids adding beautifulsoup4 as a dep."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts).strip()


def _strip_html(html: str) -> str:
    """
    Strip HTML tags from a string and return plain text.

    Handles HTML entities (e.g. &rsquo; → ') via HTMLParser's built-in
    entity handling. Falls back to the raw string if parsing fails.
    """
    if not html:
        return ""
    try:
        stripper = _HTMLStripper()
        stripper.feed(html)
        text = stripper.get_text()
        # Collapse multiple whitespace characters into single spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        # If HTML parsing fails for any reason, return raw string
        return html.strip()


# ── Main scraper class ─────────────────────────────────────────────────────

class RemoteOKScraper(BaseScraper):
    """
    Fetches internship-relevant job listings from the RemoteOK public API.

    Filtering strategy:
      Only jobs that contain at least one INTERNSHIP_KEYWORDS match (in the
      position title or tags list) are normalised and returned. All other jobs
      are counted as skipped but do not cause errors.

    Error handling:
      - A malformed individual job record is logged and skipped.
      - An HTTP error or network failure raises an exception, which
        ScraperService catches and records in scrape_runs.error.
    """

    source = "remoteok"

    def run(self) -> list[JobUpsertData]:
        """
        Fetch and normalise internship-relevant jobs from RemoteOK API.

        Returns:
            List of JobUpsertData for jobs matching internship keywords.
            Empty list if the API returns no matching jobs.

        Raises:
            httpx.HTTPStatusError : non-2xx response from RemoteOK
            httpx.TimeoutException: request timed out
            httpx.RequestError    : network-level failure
        """
        logger.info("RemoteOKScraper: starting fetch from %s", API_URL)

        raw_records = self._fetch()
        logger.info(
            "RemoteOKScraper: fetched %d raw records (includes legal notice)",
            len(raw_records),
        )

        jobs = self._normalise_all(raw_records)
        logger.info(
            "RemoteOKScraper: normalised %d internship-relevant jobs",
            len(jobs),
        )

        return jobs

    # ── Private: HTTP fetch ────────────────────────────────────────────────

    def _fetch(self) -> list[dict]:  # type: ignore[type-arg]
        """
        Perform the HTTP GET to RemoteOK API.

        Returns the parsed JSON array. The first element is the legal notice
        dict — it will be filtered out in _normalise_all().

        Raises:
            httpx.HTTPStatusError on non-2xx response.
            httpx.TimeoutException on timeout.
            httpx.RequestError on network failure.
            ValueError if response is not a JSON array.
        """
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(
                API_URL,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )

        logger.debug(
            "RemoteOKScraper: HTTP %s from %s",
            response.status_code, API_URL,
        )

        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            raise ValueError(
                f"RemoteOK API returned unexpected type {type(data).__name__}, "
                "expected a JSON array"
            )

        return data  # type: ignore[return-value]

    # ── Private: normalisation ─────────────────────────────────────────────

    def _normalise_all(self, records: list[dict]) -> list[JobUpsertData]:  # type: ignore[type-arg]
        """
        Filter, validate, and normalise all raw API records.

        - Skips the legal notice dict (no 'slug' key).
        - Skips records missing required fields.
        - Skips records not matching internship keywords.
        - Skips records with descriptions too short to be useful.
        - Logs a warning for every skipped record with reason.

        Returns only successfully normalised JobUpsertData instances.
        """
        results: list[JobUpsertData] = []
        skipped_legal = 0
        skipped_missing = 0
        skipped_keyword = 0
        skipped_malformed = 0

        for record in records:
            # Skip the legal notice (first element — no 'slug')
            if "slug" not in record:
                skipped_legal += 1
                continue

            job = self._normalise_one(record)

            if job is None:
                skipped_missing += 1
                continue

            if not self._is_relevant(record):
                skipped_keyword += 1
                continue

            if len(job.description) < MIN_DESCRIPTION_LENGTH:
                logger.debug(
                    "RemoteOKScraper: skipping %s — description too short (%d chars)",
                    record.get("slug", "unknown"),
                    len(job.description),
                )
                skipped_malformed += 1
                continue

            results.append(job)

        logger.info(
            "RemoteOKScraper: filter summary — "
            "kept=%d skipped_keyword=%d skipped_missing=%d skipped_malformed=%d",
            len(results),
            skipped_keyword,
            skipped_missing,
            skipped_malformed,
        )

        return results

    def _normalise_one(
        self,
        record: dict,  # type: ignore[type-arg]
    ) -> JobUpsertData | None:
        """
        Normalise a single raw API record into JobUpsertData.

        Returns None if the record is missing any required field.
        Logs a warning for every skipped record.

        Required fields: position (title), company, url
        Optional:        date/epoch (posted_at), company_logo (company_url),
                         description, tags
        """
        slug = record.get("slug", "<no-slug>")

        # ── Required field extraction ──────────────────────────────────────
        title: str = (record.get("position") or "").strip()
        company: str = (record.get("company") or "").strip()
        url: str = (record.get("url") or "").strip()

        if not title:
            logger.warning(
                "RemoteOKScraper: skipping %s — missing 'position' (title)", slug
            )
            return None

        if not company:
            logger.warning(
                "RemoteOKScraper: skipping %s — missing 'company'", slug
            )
            return None

        if not url:
            logger.warning(
                "RemoteOKScraper: skipping %s — missing 'url'", slug
            )
            return None

        # Ensure URL is absolute (API returns absolute URLs but guard anyway)
        if not url.startswith("http"):
            url = f"https://remoteok.com{url}"

        # ── Optional field extraction ──────────────────────────────────────
        raw_description: str = record.get("description") or ""
        description: str = _strip_html(raw_description)

        # Append tags to description for better AI matching context
        tags: list[str] = record.get("tags") or []
        if tags:
            tag_line = "Tags: " + ", ".join(str(t) for t in tags)
            description = f"{description}\n\n{tag_line}" if description else tag_line

        company_url: str | None = (record.get("company_logo") or "").strip() or None

        posted_at: datetime | None = self._parse_posted_at(record, slug)

        # ── Location ───────────────────────────────────────────────────────
        # RemoteOK does not have a dedicated location field — all listings
        # are remote-only. We hardcode "Remote" as the canonical value.
        location = record.get("location") or "Remote"

        try:
            return JobUpsertData(
                title=title[:500],
                company=company[:500],
                company_url=company_url,
                description=description,
                url=url,
                source=self.source,
                location=location,
                posted_at=posted_at,
            )
        except Exception as exc:
            logger.warning(
                "RemoteOKScraper: failed to build JobUpsertData for %s: %s",
                slug, exc,
            )
            return None

    def _parse_posted_at(
        self,
        record: dict,  # type: ignore[type-arg]
        slug: str,
    ) -> datetime | None:
        """
        Parse posted_at from the record's 'epoch' or 'date' field.

        Preference order:
          1. 'epoch' (unix timestamp string) — most reliable
          2. 'date'  (ISO 8601 string)       — fallback

        Returns None if neither field can be parsed — caller handles gracefully.
        """
        # Try epoch first (most reliable)
        epoch_raw = record.get("epoch")
        if epoch_raw:
            try:
                return datetime.fromtimestamp(int(epoch_raw), tz=timezone.utc)
            except (ValueError, OSError, OverflowError) as exc:
                logger.debug(
                    "RemoteOKScraper: could not parse epoch '%s' for %s: %s",
                    epoch_raw, slug, exc,
                )

        # Fall back to date string
        date_raw = record.get("date")
        if date_raw:
            try:
                # API returns ISO 8601 with timezone offset e.g. "2020-06-27T04:41:52-07:00"
                return datetime.fromisoformat(str(date_raw)).astimezone(timezone.utc)
            except ValueError as exc:
                logger.debug(
                    "RemoteOKScraper: could not parse date '%s' for %s: %s",
                    date_raw, slug, exc,
                )

        return None

    def _is_relevant(self, record: dict) -> bool:  # type: ignore[type-arg]
        """
        Return True if this job matches at least one internship keyword.

        Checks both the position title and the tags array.
        Matching is case-insensitive.
        """
        position: str = (record.get("position") or "").lower()
        tags: list[str] = [str(t).lower() for t in (record.get("tags") or [])]

        # Build a single searchable string from all text fields
        searchable = position + " " + " ".join(tags)

        return any(keyword in searchable for keyword in INTERNSHIP_KEYWORDS)