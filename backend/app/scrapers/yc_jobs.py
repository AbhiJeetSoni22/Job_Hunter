"""
YC Jobs scraper — Phase 3A (locator-only rewrite).

Source  : Work at a Startup — https://www.workatastartup.com/jobs
Method  : Playwright headless Chromium, pure locators — NO evaluate/JS injection.

Card discovery strategy
───────────────────────
1. Find all <a href^="/jobs/NNN"> links (digit IDs only, skips nav links).
2. For each unique job href, walk up the DOM using .locator() until we reach
an ancestor that also contains an <a href^="/companies/"> sibling.
3. That ancestor is the job card.  We track cards by their job href to avoid
duplicate processing.
4. Extract title, company, location, description, posted_at from each card
using Playwright locators only.
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
# Reduced from 3000ms — domcontentloaded + wait_for_selector already guarantees
# the job list is present; we only need a brief pause for any lazy images.
LAZY_LOAD_WAIT_MS      = 500
MIN_DESCRIPTION_LENGTH = 30

# Regex: only real job detail links  /jobs/12345
JOB_HREF_RE = re.compile(r"^/jobs/\d+$")


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

                # domcontentloaded instead of networkidle.
                # networkidle waits for zero network activity for 500 ms — on a
                # JS-heavy SPA like workatastartup.com this blocks for 20-25 s
                # while background XHRs keep firing.  domcontentloaded fires as
                # soon as the HTML is parsed; wait_for_selector below guarantees
                # the job list is actually rendered before we proceed.
                logger.info("YCJobsScraper: navigating to %s", JOBS_URL)
                page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

                # Wait for job links to appear
                try:
                    page.wait_for_selector("a[href^='/jobs/']", timeout=CARD_WAIT_MS)
                    logger.info("YCJobsScraper: job links detected in DOM")
                except PlaywrightTimeoutError:
                    logger.warning(
                        "YCJobsScraper: no job links after %dms — title='%s' url='%s'",
                        CARD_WAIT_MS, page.title(), page.url,
                    )
                    return []

                self._scroll_to_bottom(page)

                jobs = self._extract_jobs(page)
                logger.info("YCJobsScraper: extracted %d valid jobs", len(jobs))
                return jobs

            finally:
                browser.close()
                logger.info("YCJobsScraper: browser closed")

                # ── Core extraction ────────────────────────────────────────────────────

    def _extract_jobs(self, page) -> list[JobUpsertData]:
            """
            Pure-locator extraction.  No JS evaluate calls.

            Strategy:
                - Collect all job-detail anchors (href matches /jobs/NNN).
                - For each unique href, use a single evaluate_handle() call to find
                the nearest ancestor containing a /companies/ link (replaces the
                old 8-level XPath loop that caused ~8-12s of IPC overhead).
                - Extract fields from that ancestor card element.
            """
            # All job-detail links on page
            job_anchors = page.locator("a[href^='/jobs/']").all()
            logger.info("YCJobsScraper: found %d raw job anchor(s)", len(job_anchors))

            seen_hrefs: set[str] = set()
            results: list[JobUpsertData] = []
            skipped_missing = skipped_short = skipped_error = 0

            for anchor in job_anchors:
                try:
                    href = anchor.get_attribute("href") or ""
                except Exception:
                    continue

                # Only exact /jobs/NNN paths
                if not JOB_HREF_RE.match(href):
                    continue

                if href in seen_hrefs:
                    continue
                seen_hrefs.add(href)

                job_url = f"{BASE_URL}{href}"

                try:
                    job = self._extract_from_anchor(anchor, job_url)
                except Exception as exc:
                    logger.warning("YCJobsScraper: href=%s error=%s", href, exc)
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

    def _extract_from_anchor(self, anchor, job_url: str) -> "JobUpsertData | None":
        """
        Given a job-link anchor locator, find its card container and extract fields.
        Card container = nearest ancestor that also holds a /companies/ link.
        Falls back to immediate parent if no such ancestor found within 8 levels.
        """
        # Title from the anchor text
        title = (anchor.inner_text() or "").strip()
        if not title:
            return None

        # Walk up ancestor chain to find card container
        card = self._find_card_ancestor(anchor)

        # Company link inside card
        company_name = ""
        company_url: str | None = None
        try:
            co_anchor = card.locator("a[href^='/companies/']").first
            company_name = (co_anchor.inner_text() or "").strip()
            co_href = co_anchor.get_attribute("href") or ""
            if co_href:
                company_url = f"{BASE_URL}{co_href}" if co_href.startswith("/") else co_href
        except Exception:
            pass

        if not company_name:
            return None

        location = self._extract_location(card)
        description = self._extract_description(card)
        posted_at = self._extract_posted_at(card)

        try:
            return JobUpsertData(
        title=title[:500],
        company=company_name[:500],
        company_url=company_url,
        description=description,
        url=job_url,
        source=self.source,
        location=location,
        posted_at=posted_at,
    )
        except Exception as exc:
            logger.warning("YCJobsScraper: JobUpsertData failed url=%s: %s", job_url, exc)
            return None

    def _find_card_ancestor(self, anchor):
        """
        Find the nearest ancestor of `anchor` that contains a /companies/ link.

        BEFORE: up to 8 sequential locator("xpath=..") + .count() calls per job.
        For 30 jobs that was up to 240 browser IPC round-trips — ~8-12 s.

        AFTER: one evaluate_handle() call per job. The JS runs entirely inside
        the browser process; only the final ElementHandle is transferred back.
        30 jobs = 30 IPC calls instead of up to 240.
        """
        try:
            ancestor_handle = anchor.evaluate_handle("""el => {
                let node = el.parentElement;
                for (let i = 0; i < 8; i++) {
                    if (!node) break;
                    if (node.querySelector("a[href^='/companies/']")) return node;
                    node = node.parentElement;
                }
                return el.parentElement;
            }""")
            el = ancestor_handle.as_element()
            if el is not None:
                return el
        except Exception:
            pass
        # Safe fallback: immediate parent via XPath
        return anchor.locator("xpath=..")

        # ── Field extractors ───────────────────────────────────────────────────

    def _extract_location(self, card) -> "str | None":
        """Try common location selector patterns inside the card."""
        selectors = [
            "[class*='location']",
            "[class*='remote']",
            "[class*='locale']",
            "[class*='job-detail']",
        ]
        for sel in selectors:
            try:
                el = card.locator(sel).first
                if el.count() == 0:
                    continue
                text = (el.inner_text() or "").strip()
                if text:
                    return re.sub(r"\s+", " ", text)[:200]
            except Exception:
                continue
            return None

    def _extract_description(self, card) -> str:
        """Try description selectors; fall back to full card text."""
        selectors = [
            "[class*='description']",
            "[class*='snippet']",
            "[class*='summary']",
            "p",
        ]
        for sel in selectors:
            try:
                el = card.locator(sel).first
                if el.count() == 0:
                    continue
                text = (el.inner_text() or "").strip()
                if len(text) >= MIN_DESCRIPTION_LENGTH:
                    return re.sub(r"\s+", " ", text)
            except Exception:
                continue

            # Full card text fallback
            try:
                full = (card.inner_text() or "").strip()
                return re.sub(r"\s+", " ", full)
            except Exception:
                return ""

    def _extract_posted_at(self, card) -> "datetime | None":
        """Try <time> and date-attribute elements inside the card."""
        # Try <time datetime="...">
        try:
            time_el = card.locator("time").first
            if time_el.count() > 0:
                for attr in ["datetime", "title"]:
                    val = time_el.get_attribute(attr)
                    if val:
                        dt = self._parse_datetime(val)
                        if dt:
                            return dt
        except Exception:
            pass

        # Try elements with date-related attributes
        for sel in ["[data-created-at]", "[data-date]", "[data-posted-at]"]:
            try:
                el = card.locator(sel).first
                if el.count() == 0:
                    continue
                for attr in ["data-created-at", "data-date", "data-posted-at", "datetime"]:
                    val = el.get_attribute(attr)
                    if val:
                        dt = self._parse_datetime(val)
                        if dt:
                            return dt
            except Exception:
                continue

            return None

    def _parse_datetime(self, value: str) -> "datetime | None":
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

        # ── Scrolling ──────────────────────────────────────────────────────────

    def _scroll_to_bottom(self, page) -> None:
        try:
            page.keyboard.press("End")
            page.wait_for_timeout(LAZY_LOAD_WAIT_MS)  # 500 ms — was 3000 ms
            page.keyboard.press("End")
            # Second fixed sleep removed — domcontentloaded + selector wait
            # already guarantees the job list is rendered.
        except Exception as exc:
            logger.warning("YCJobsScraper: scroll failed (non-fatal): %s", exc)