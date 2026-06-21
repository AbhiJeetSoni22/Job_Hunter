"""
YC Jobs scraper.

Source: Work at a Startup — https://www.workatastartup.com/jobs
Method: Playwright headless Chromium (page renders JS before scraping)

Phase 1B: stub only. Returns empty list so the scraper pipeline
works end-to-end without spinning up a browser.

Phase 1C implementation will:
  - Launch Playwright async_playwright
  - Navigate to workatastartup.com/jobs with internship filter
  - Wait for job cards to render
  - Extract title, company, description, url, location, posted_at
  - Close browser regardless of success/failure (finally block)
  - Normalise fields to JobUpsertData
"""

import logging

from app.scrapers.base import BaseScraper
from app.schemas.job import JobUpsertData

logger = logging.getLogger(__name__)


class YCJobsScraper(BaseScraper):
    """Scrapes internship listings from YC Work at a Startup."""

    source = "yc_jobs"

    def run(self) -> list[JobUpsertData]:
        """
        Scrape jobs from YC Work at a Startup.

        Phase 1B: stub — returns empty list.
        Replace body with real implementation in Phase 1C.
        """
        logger.info("[STUB] YCJobsScraper.run() — returning empty list")
        return []