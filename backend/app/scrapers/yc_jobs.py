"""
YC Jobs scraper — Phase 3A.

Source  : Work at a Startup — https://www.workatastartup.com/jobs
Method  : Playwright headless Chromium — JS-rendered SPA requires a browser.

Target URL:
    https://www.workatastartup.com/jobs?role=eng&type=intern

Page structure (workatastartup.com as of mid-2025):
    Each job appears as a <div class="job"> inside a list container.
    Key sub-elements per job card:
        .company-name  — company name text
        .job-name a    — job title + href (relative, e.g. /jobs/12345)
        .job-detail    — location / remote flag
        .job-description (or inner paragraph) — description snippet
        data-url or href on .job-name a — used to build apply_url

Navigation strategy:
    1. Navigate to the filtered internship URL with networkidle wait.
    2. Wait up to 10s for first job card selector (.job) to appear.
    3. Scroll to bottom to trigger lazy-load of additional cards.
    4. Wait another 2s for lazy-loaded cards.
    5. Extract all .job cards.
    6. For each card: extract fields, normalise to JobUpsertData.
    7. Close browser in finally block regardless of outcome.

Error handling:
    - Browser launch failure → raises immediately (ScraperService logs it).
    - Navigation timeout → raises TimeoutError.
    - Individual card parse failure → logged + skipped; rest continue.
    - Missing required fields per card → logged + skipped.

Playwright version: 1.48.0 (sync_playwright, matches project deps).
Uses sync_playwright (not async) to match the synchronous scraper.run() interface.

Important: run `playwright install chromium` after `pip install playwright`.
Playwright stores browser binaries in ~/.cache/ms-playwright by default.
In Docker, add this to the Dockerfile:
    RUN python -m playwright install --with-deps chromium
"""

import logging
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.base import BaseScraper
from app.schemas.job import JobUpsertData

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

BASE_URL = "https://www.workatastartup.com"

# Filtered to engineering internships. Adjust role/type as needed.
JOBS_URL = f"{BASE_URL}/jobs?role=eng&type=intern"

# How long to wait for page to load and for job cards to appear (ms)
PAGE_LOAD_TIMEOUT_MS = 30_000  # 30s for initial navigation
JOB_CARD_WAIT_MS = 15_000      # 15s for first job card to appear after load
LAZY_LOAD_WAIT_MS = 3_000      # 3s after scrolling for lazy-loaded cards

# Minimum description length — cards with less are skipped as malformed
MIN_DESCRIPTION_LENGTH = 30

# CSS selectors — versioned against workatastartup.com layout as of 2025
# If the site updates their classes, update these selectors.
SEL_JOB_CARD = "div.job"
SEL_JOB_TITLE = "a.job-name"
SEL_COMPANY_NAME = "a.company-name"
SEL_LOCATION = ".job-detail"
SEL_DESCRIPTION = ".job-description"

# Alternative selectors used as fallbacks if primary selectors miss
ALT_SEL_JOB_TITLE = "[class*='job-name'] a, .job-details a[href*='/jobs/']"
ALT_SEL_DESCRIPTION = "p, .description, [class*='description']"


class YCJobsScraper(BaseScraper):
    """
    Scrapes engineering internship listings from YC Work at a Startup.

    Uses Playwright sync API with headless Chromium. Filters to internship
    roles via URL parameter. Extracts and normalises job cards to JobUpsertData.

    No auth required. Page is publicly accessible.
    """

    source = "yc_jobs"

    def run(self) -> list[JobUpsertData]:
        """
        Launch browser, scrape job cards, return normalised list.

        Returns:
            List of JobUpsertData. May be empty if no internships found.

        Raises:
            playwright.sync_api.TimeoutError: page/selector timeout
            Exception: browser launch failure or unrecoverable parse error
        """
        logger.info("YCJobsScraper: starting — url=%s", JOBS_URL)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",  # Required in Docker
                    "--disable-gpu",
                    "--disable-extensions",
                ],
            )
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                )
                page = context.new_page()

                # Block images/fonts/media to speed up page load
                page.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
                    lambda route: route.abort(),
                )

                logger.info("YCJobsScraper: navigating to %s", JOBS_URL)
                page.goto(JOBS_URL, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)

                # Wait for at least one job card — indicates JS rendered the list
                try:
                    page.wait_for_selector(SEL_JOB_CARD, timeout=JOB_CARD_WAIT_MS)
                    logger.info("YCJobsScraper: job cards detected in DOM")
                except PlaywrightTimeoutError:
                    logger.warning(
                        "YCJobsScraper: no job cards found using selector '%s' "
                        "after %dms — page may have changed layout or returned 0 results",
                        SEL_JOB_CARD, JOB_CARD_WAIT_MS,
                    )
                    # Try to capture the page state for debugging
                    logger.debug(
                        "YCJobsScraper: page title='%s' url='%s'",
                        page.title(), page.url,
                    )
                    return []

                # Scroll to bottom to trigger lazy loading of all cards
                self._scroll_to_bottom(page)

                # Extract all job cards
                raw_cards = page.query_selector_all(SEL_JOB_CARD)
                logger.info("YCJobsScraper: found %d job card elements", len(raw_cards))

                jobs = self._normalise_all(page, raw_cards)
                logger.info("YCJobsScraper: normalised %d valid jobs", len(jobs))
                return jobs

            finally:
                browser.close()
                logger.info("YCJobsScraper: browser closed")

    # ── Private: scrolling ─────────────────────────────────────────────────

    def _scroll_to_bottom(self, page) -> None:  # type: ignore[type-arg]
        """
        Scroll the page to the bottom to trigger lazy loading.

        Uses JS execution rather than keyboard events for reliability.
        """
        logger.debug("YCJobsScraper: scrolling to trigger lazy load")
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(LAZY_LOAD_WAIT_MS)
            # Scroll once more in case of infinite scroll
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1_000)
        except Exception as exc:
            # Scroll failure is not fatal — we still have cards already in DOM
            logger.warning("YCJobsScraper: scroll failed (non-fatal): %s", exc)

    # ── Private: normalisation ─────────────────────────────────────────────

    def _normalise_all(self, page, cards) -> list[JobUpsertData]:  # type: ignore[type-arg]
        """
        Iterate over job card elements and normalise each one.

        Per-card failures are logged and skipped — they do not abort the run.
        """
        results: list[JobUpsertData] = []
        skipped_missing = 0
        skipped_short = 0
        skipped_error = 0

        for idx, card in enumerate(cards):
            try:
                job = self._normalise_one(card, idx)
            except Exception as exc:
                logger.warning(
                    "YCJobsScraper: card[%d] raised unexpected error — skipping: %s",
                    idx, exc,
                )
                skipped_error += 1
                continue

            if job is None:
                skipped_missing += 1
                continue

            if len(job.description) < MIN_DESCRIPTION_LENGTH:
                logger.debug(
                    "YCJobsScraper: card[%d] description too short (%d chars) — skipping",
                    idx, len(job.description),
                )
                skipped_short += 1
                continue

            results.append(job)

        logger.info(
            "YCJobsScraper: filter summary — kept=%d skipped_missing=%d "
            "skipped_short=%d skipped_error=%d",
            len(results), skipped_missing, skipped_short, skipped_error,
        )
        return results

    def _normalise_one(self, card, idx: int) -> JobUpsertData | None:  # type: ignore[type-arg]
        """
        Extract and normalise a single job card element.

        Returns None if required fields (title, company, url) are missing.
        All optional fields are populated where available, defaulting to None.
        """
        # ── Title + URL ────────────────────────────────────────────────────
        title_el = card.query_selector(SEL_JOB_TITLE)
        if title_el is None:
            # Fallback: any anchor with /jobs/ in href
            title_el = card.query_selector("a[href*='/jobs/']")

        if title_el is None:
            logger.debug("YCJobsScraper: card[%d] — no title element found", idx)
            return None

        title = (title_el.inner_text() or "").strip()
        if not title:
            logger.debug("YCJobsScraper: card[%d] — empty title", idx)
            return None

        href = title_el.get_attribute("href") or ""
        if not href:
            logger.debug("YCJobsScraper: card[%d] '%s' — no href on title anchor", idx, title)
            return None

        # Build absolute URL
        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        # ── Company ────────────────────────────────────────────────────────
        company_el = card.query_selector(SEL_COMPANY_NAME)
        if company_el is None:
            company_el = card.query_selector("a[href*='/company/']")

        company = (company_el.inner_text() if company_el else "").strip()
        company_url: str | None = None
        if company_el:
            company_href = company_el.get_attribute("href") or ""
            if company_href:
                company_url = (
                    company_href if company_href.startswith("http")
                    else f"{BASE_URL}{company_href}"
                )

        if not company:
            # Attempt to infer company from URL slug or data attributes
            company = self._infer_company(card, href)

        if not company:
            logger.debug("YCJobsScraper: card[%d] '%s' — no company found", idx, title)
            return None

        # ── Location ───────────────────────────────────────────────────────
        location = self._extract_location(card, idx)

        # ── Description ────────────────────────────────────────────────────
        description = self._extract_description(card, idx)

        # ── posted_at ──────────────────────────────────────────────────────
        posted_at = self._extract_posted_at(card, idx)

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
                "YCJobsScraper: card[%d] failed to build JobUpsertData: %s",
                idx, exc,
            )
            return None

    # ── Private: field extractors ──────────────────────────────────────────

    def _extract_location(self, card, idx: int) -> str | None:  # type: ignore[type-arg]
        """Extract location string from job card."""
        location_el = card.query_selector(SEL_LOCATION)
        if location_el:
            location_text = (location_el.inner_text() or "").strip()
            if location_text:
                # Normalise whitespace
                location_text = re.sub(r"\s+", " ", location_text).strip()
                return location_text[:200]

        # Secondary: look for any element containing "Remote" or "New York" etc.
        for sel in ["[class*='location']", "[class*='remote']"]:
            el = card.query_selector(sel)
            if el:
                text = (el.inner_text() or "").strip()
                if text:
                    return text[:200]

        return None

    def _extract_description(self, card, idx: int) -> str:  # type: ignore[type-arg]
        """
        Extract job description text from the card.

        Tries the primary selector first, then falls back to the card's full
        inner text, minus title and company text (to avoid duplication).
        """
        desc_el = card.query_selector(SEL_DESCRIPTION)
        if desc_el:
            desc = (desc_el.inner_text() or "").strip()
            if desc:
                return re.sub(r"\s+", " ", desc).strip()

        # Fallback: try common description containers
        for sel in ALT_SEL_DESCRIPTION.split(", "):
            el = card.query_selector(sel)
            if el:
                text = (el.inner_text() or "").strip()
                if len(text) >= MIN_DESCRIPTION_LENGTH:
                    return re.sub(r"\s+", " ", text).strip()

        # Last resort: full card text (will include title/company but better than empty)
        full_text = (card.inner_text() or "").strip()
        return re.sub(r"\s+", " ", full_text).strip()

    def _extract_posted_at(self, card, idx: int) -> datetime | None:  # type: ignore[type-arg]
        """
        Extract posted date from card if available.

        workatastartup.com sometimes shows relative dates ("2 days ago") or
        stores ISO dates in data attributes. Returns None if not determinable.
        """
        # Try data attributes first — most reliable
        for attr in ["data-created-at", "data-date", "data-posted-at", "datetime"]:
            val = card.get_attribute(attr)
            if val:
                dt = self._parse_datetime(val, idx)
                if dt:
                    return dt

        # Try <time> elements
        time_el = card.query_selector("time")
        if time_el:
            dt_attr = time_el.get_attribute("datetime") or time_el.get_attribute("title")
            if dt_attr:
                dt = self._parse_datetime(dt_attr, idx)
                if dt:
                    return dt

        # Try elements with date-like class names
        for sel in ["[class*='date']", "[class*='time']", "[class*='posted']"]:
            el = card.query_selector(sel)
            if el:
                # Check data attributes on this element
                for attr in ["datetime", "data-date", "title"]:
                    val = el.get_attribute(attr)
                    if val:
                        dt = self._parse_datetime(val, idx)
                        if dt:
                            return dt

        return None

    def _parse_datetime(self, value: str, idx: int) -> datetime | None:
        """Attempt to parse a datetime string. Returns None on failure."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
        # Try unix timestamp
        try:
            ts = float(value)
            if ts > 1_000_000_000:  # Sanity check: after year 2001
                return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass
        logger.debug("YCJobsScraper: card[%d] could not parse datetime '%s'", idx, value)
        return None

    def _infer_company(self, card, job_href: str) -> str:  # type: ignore[type-arg]
        """
        Last-resort company name inference.

        Some cards embed company name in the heading text or URL path.
        Only called when the primary company selector fails.
        """
        # Try any heading element in the card
        for heading_sel in ["h2", "h3", "h4", "[class*='company']"]:
            el = card.query_selector(heading_sel)
            if el:
                text = (el.inner_text() or "").strip()
                if text:
                    return text[:500]
        return ""