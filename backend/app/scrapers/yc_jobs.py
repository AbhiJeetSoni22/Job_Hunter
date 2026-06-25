"""
YC Jobs scraper — Phase 3A.

Source  : Work at a Startup — https://www.workatastartup.com/jobs
Method  : Playwright headless Chromium

Selector strategy (2025)
─────────────────────────
workatastartup.com is a React SPA. Class names have changed since the original
selectors were written. This version uses a two-layer strategy:

Layer 1 — Structural selectors that don't depend on class names:
  Job cards  : any <a> whose href matches /jobs/\d+  (each card links to a job)
               grouped by nearest common ancestor
  Title      : the <a href="/jobs/\d+"> itself — its text IS the title
  Company    : sibling/parent <a href="/companies/..."> near the job link
  Location   : text nodes near the job link containing location patterns
  Description: text content of the card container

Layer 2 — Known class name patterns as hints (tried first, fall back to Layer 1):
  These are attempted but not required. If the site redesigns, Layer 1 still works.

DOM dump on failure:
  After every run the scraper saves yc_dom_dump.html and yc_debug.txt
  in cwd so the caller can inspect the actual DOM and update selectors.
"""

import logging
import platform
import asyncio
import re
from datetime import datetime, timezone

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from app.scrapers.base import BaseScraper
from app.schemas.job import JobUpsertData

logger = logging.getLogger(__name__)

BASE_URL = "https://www.workatastartup.com"
JOBS_URL = f"{BASE_URL}/jobs?role=eng&type=intern"

PAGE_LOAD_TIMEOUT_MS   = 30_000
CARD_WAIT_MS           = 15_000
LAZY_LOAD_WAIT_MS      = 3_000
MIN_DESCRIPTION_LENGTH = 30

# ── Selector candidates (tried in order, first match wins) ─────────────────
# Job card containers — wraps one job posting
CARD_SELECTORS = [
    "div.job",           # original
    "div[class*='job-']",
    "li[class*='job']",
    "div[class*='listing']",
    "div[class*='posting']",
    "div[class*='result']",
    # Last resort: any element that directly contains an /jobs/NNN link
    # (handled separately in _find_cards_structural)
]

# Job title link — must have href=/jobs/NNN
TITLE_SELECTORS = [
    "a.job-name",
    "a[class*='job-name']",
    "a[class*='title']",
    "a[class*='job-title']",
    "h2 a",
    "h3 a",
    "a[href*='/jobs/']",   # broadest: any link to a job detail page
]

# Company name link — href=/companies/NNN
COMPANY_SELECTORS = [
    "a.company-name",
    "a[class*='company-name']",
    "a[class*='company']",
    "a[href*='/companies/']",
]

# Location text container
LOCATION_SELECTORS = [
    ".job-detail",
    "[class*='job-detail']",
    "[class*='location']",
    "[class*='remote']",
    "[class*='locale']",
    "[class*='region']",
]

# Description text container
DESCRIPTION_SELECTORS = [
    ".job-description",
    "[class*='job-description']",
    "[class*='description']",
    "[class*='snippet']",
    "[class*='summary']",
    "p",
]


class YCJobsScraper(BaseScraper):
    source = "yc_jobs"

    def run(self) -> list[JobUpsertData]:
        logger.info("YCJobsScraper: starting — url=%s", JOBS_URL)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                ],
            )
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                    locale="en-US",
                )
                page = context.new_page()

                page.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
                    lambda route: route.abort(),
                )

                logger.info("YCJobsScraper: navigating to %s", JOBS_URL)
                page.goto(JOBS_URL, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
                self._dump_debug(page)  # always-on: saves yc_dom_dump.html + yc_debug.txt

                # Wait for ANY job link to appear — more resilient than a specific class
                job_link_appeared = False
                try:
                    page.wait_for_selector("a[href*='/jobs/']", timeout=CARD_WAIT_MS)
                    job_link_appeared = True
                    logger.info("YCJobsScraper: job links detected in DOM")
                except PlaywrightTimeoutError:
                    pass

                if not job_link_appeared:
                    logger.warning(
                        "YCJobsScraper: no job links found after %dms — "
                        "page title='%s' url='%s'",
                        CARD_WAIT_MS, page.title(), page.url,
                    )
                    self._dump_dom(page)
                    return []

                self._scroll_to_bottom(page)

                # Try to find card containers; fall back to structural discovery
                cards, card_sel = self._find_cards(page)
                logger.info(
                    "YCJobsScraper: found %d cards using selector '%s'",
                    len(cards), card_sel,
                )

                if not cards:
                    logger.warning("YCJobsScraper: no card containers found — dumping DOM")
                    self._dump_dom(page)
                    return []

                jobs = self._normalise_all(cards, card_sel)
                logger.info("YCJobsScraper: normalised %d valid jobs", len(jobs))
                return jobs

            finally:
                browser.close()
                logger.info("YCJobsScraper: browser closed")

    # ── Card discovery ─────────────────────────────────────────────────────

    def _find_cards(self, page):
        """
        Try each card selector in order. Return (elements, selector_used).
        Falls back to structural discovery (parent of job links) if all fail.
        """
        for sel in CARD_SELECTORS:
            elements = page.query_selector_all(sel)
            if elements:
                logger.info("YCJobsScraper: card selector matched: '%s' (%d)", sel, len(elements))
                return elements, sel

        # Structural fallback: find all /jobs/NNN links, take their parent element
        logger.info("YCJobsScraper: trying structural card discovery via job links")
        return self._find_cards_structural(page)

    def _find_cards_structural(self, page):
        """
        Find all <a href='/jobs/NNN'> links, collect their parent elements
        as synthetic card containers. Each parent becomes one card.
        Deduplicates by element identity using JS.
        """
        job_links = page.query_selector_all("a[href*='/jobs/']")
        logger.info("YCJobsScraper: found %d raw job links", len(job_links))

        seen_parents = []
        seen_hrefs = set()

        for link in job_links:
            href = link.get_attribute("href") or ""
            # Only /jobs/NNN links (job detail pages), not /jobs as the list page
            if not re.search(r"/jobs/\d+", href):
                continue
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            # Walk up to find a meaningful container:
            # Use the parent that contains both a job link and a company link
            parent = page.evaluate_handle(
                """(el) => {
                    let node = el.parentElement;
                    for (let i = 0; i < 6; i++) {
                        if (!node) break;
                        // Good container: has both a job link and a company link
                        if (node.querySelector('a[href*="/jobs/"]') &&
                            node.querySelector('a[href*="/companies/"]')) {
                            return node;
                        }
                        node = node.parentElement;
                    }
                    // Fallback: immediate parent
                    return el.parentElement;
                }""",
                link,
            )
            if parent:
                seen_parents.append(parent.as_element())

        # Deduplicate parents that are the same DOM node
        unique = []
        seen_outer = set()
        for el in seen_parents:
            if el is None:
                continue
            outer = el.evaluate("e => e.outerHTML[:80]") if el else None
            if outer and outer not in seen_outer:
                seen_outer.add(outer)
                unique.append(el)

        return unique, "structural(a[href*='/jobs/NNN'] parent)"

    # ── Scrolling ──────────────────────────────────────────────────────────

    def _scroll_to_bottom(self, page) -> None:
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(LAZY_LOAD_WAIT_MS)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1_000)
        except Exception as exc:
            logger.warning("YCJobsScraper: scroll failed (non-fatal): %s", exc)

    # ── Normalisation ──────────────────────────────────────────────────────

    def _normalise_all(self, cards, card_sel: str) -> list[JobUpsertData]:
        results = []
        skipped_missing = skipped_short = skipped_error = 0

        for idx, card in enumerate(cards):
            try:
                job = self._normalise_one(card, idx)
            except Exception as exc:
                logger.warning("YCJobsScraper: card[%d] error — skipping: %s", idx, exc)
                skipped_error += 1
                continue

            if job is None:
                skipped_missing += 1
                continue

            if len(job.description) < MIN_DESCRIPTION_LENGTH:
                skipped_short += 1
                continue

            results.append(job)

        logger.info(
            "YCJobsScraper: kept=%d missing=%d short=%d error=%d",
            len(results), skipped_missing, skipped_short, skipped_error,
        )
        return results

    def _normalise_one(self, card, idx: int) -> JobUpsertData | None:
        # ── Title + URL ────────────────────────────────────────────────────
        title_el = self._query_first(card, TITLE_SELECTORS)
        if title_el is None:
            logger.debug("YCJobsScraper: card[%d] — no title element", idx)
            return None

        title = (title_el.inner_text() or "").strip()
        if not title:
            return None

        href = title_el.get_attribute("href") or ""
        if not href or not re.search(r"/jobs/", href):
            return None

        url = href if href.startswith("http") else f"{BASE_URL}{href}"

        # ── Company ────────────────────────────────────────────────────────
        company_el = self._query_first(card, COMPANY_SELECTORS)
        company = (company_el.inner_text() if company_el else "").strip()
        company_url: str | None = None
        if company_el:
            ch = company_el.get_attribute("href") or ""
            if ch:
                company_url = ch if ch.startswith("http") else f"{BASE_URL}{ch}"

        if not company:
            company = self._infer_company(card)

        if not company:
            logger.debug("YCJobsScraper: card[%d] '%s' — no company", idx, title)
            return None

        # ── Optional fields ────────────────────────────────────────────────
        location    = self._extract_location(card)
        description = self._extract_description(card)
        posted_at   = self._extract_posted_at(card, idx)

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
            logger.warning("YCJobsScraper: card[%d] JobUpsertData failed: %s", idx, exc)
            return None

    # ── Field extractors ───────────────────────────────────────────────────

    def _query_first(self, card, selectors: list[str]):
        """Try selectors in order, return first element found."""
        for sel in selectors:
            el = card.query_selector(sel)
            if el:
                return el
        return None

    def _extract_location(self, card) -> str | None:
        el = self._query_first(card, LOCATION_SELECTORS)
        if el:
            text = (el.inner_text() or "").strip()
            if text:
                return re.sub(r"\s+", " ", text).strip()[:200]
        return None

    def _extract_description(self, card) -> str:
        el = self._query_first(card, DESCRIPTION_SELECTORS)
        if el:
            text = (el.inner_text() or "").strip()
            if len(text) >= MIN_DESCRIPTION_LENGTH:
                return re.sub(r"\s+", " ", text).strip()
        # Last resort: full card text
        full = (card.inner_text() or "").strip()
        return re.sub(r"\s+", " ", full).strip()

    def _extract_posted_at(self, card, idx: int) -> datetime | None:
        for attr in ["data-created-at", "data-date", "data-posted-at", "datetime"]:
            val = card.get_attribute(attr)
            if val:
                dt = self._parse_datetime(val, idx)
                if dt:
                    return dt

        time_el = card.query_selector("time")
        if time_el:
            for attr in ["datetime", "title"]:
                val = time_el.get_attribute(attr)
                if val:
                    dt = self._parse_datetime(val, idx)
                    if dt:
                        return dt

        for sel in ["[class*='date']", "[class*='time']", "[class*='posted']"]:
            el = card.query_selector(sel)
            if el:
                for attr in ["datetime", "data-date", "title"]:
                    val = el.get_attribute(attr)
                    if val:
                        dt = self._parse_datetime(val, idx)
                        if dt:
                            return dt

        return None

    def _parse_datetime(self, value: str, idx: int) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            pass
        try:
            ts = float(value)
            if ts > 1_000_000_000:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass
        return None

    def _infer_company(self, card) -> str:
        for sel in ["h2", "h3", "h4", "[class*='company']", "[class*='startup']"]:
            el = card.query_selector(sel)
            if el:
                text = (el.inner_text() or "").strip()
                if text:
                    return text[:500]
        return ""

    # ── Debug helpers ──────────────────────────────────────────────────────

    def _dump_debug(self, page) -> None:
        """
        Always-on debug dump called once after page.goto() completes.
        Saves two files in cwd (project root — wherever uvicorn was launched):
          yc_dom_dump.html  — full rendered HTML for selector inspection
          yc_debug.txt      — metadata + all /jobs and /companies hrefs
        """
        self._dump_dom(page)
        self._dump_txt(page)

    def _dump_dom(self, page) -> None:
        """Save full rendered HTML to yc_dom_dump.html in cwd."""
        try:
            html = page.content()
            with open("yc_dom_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.info(
                "YCJobsScraper: DOM saved → yc_dom_dump.html (%d bytes)", len(html)
            )
        except Exception as exc:
            logger.warning("YCJobsScraper: DOM dump failed: %s", exc)

    def _dump_txt(self, page) -> None:
        """Save metadata + all job/company hrefs to yc_debug.txt in cwd."""
        try:
            title = page.title()
            url   = page.url

            all_anchors   = page.query_selector_all("a")
            total_anchors = len(all_anchors)

            jobs_hrefs    = []
            company_hrefs = []
            for a in all_anchors:
                href = a.get_attribute("href") or ""
                if "/jobs" in href:
                    jobs_hrefs.append(href)
                if "/companies" in href:
                    company_hrefs.append(href)

            lines = [
                f"url:            {url}",
                f"title:          {title}",
                f"total <a> tags: {total_anchors}",
                f"hrefs with /jobs ({len(jobs_hrefs)}):",
                *[f"  {h}" for h in jobs_hrefs],
                f"hrefs with /companies ({len(company_hrefs)}):",
                *[f"  {h}" for h in company_hrefs],
            ]

            with open("yc_debug.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(
                "YCJobsScraper: debug saved → yc_debug.txt "
                "(anchors=%d jobs_links=%d company_links=%d)",
                total_anchors, len(jobs_hrefs), len(company_hrefs),
            )
        except Exception as exc:
            logger.warning("YCJobsScraper: debug txt dump failed: %s", exc)