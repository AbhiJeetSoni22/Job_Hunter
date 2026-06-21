"""
Base scraper interface.

Every scraper must:
  1. Inherit from BaseScraper
  2. Set a `source` class attribute matching a value in SCRAPER_SOURCE_VALUES
  3. Implement run() → list[JobUpsertData]

ScraperService calls run() and expects JobUpsertData objects back.
Scrapers never touch the database — that's job_service's responsibility.
"""

from abc import ABC, abstractmethod

from app.schemas.job import JobUpsertData


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    #: Must match a value in SCRAPER_SOURCE_VALUES ('remoteok' | 'yc_jobs')
    source: str

    @abstractmethod
    def run(self) -> list[JobUpsertData]:
        """
        Execute the scraper and return normalised job data.

        Returns:
            List of JobUpsertData. Empty list on no results.
            Must NOT raise on empty — only raise on unrecoverable errors.

        Raises:
            Exception: on network failure, parse failure, or timeout.
                       ScraperService catches and logs these.
        """
        ...