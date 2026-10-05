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
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from app.schemas.job import JobUpsertData


@dataclass
class ScraperResult:
    """
    Contract returned by scrapers to distinguish success, partial, empty, or failed states.

    Maintains backwards compatibility by behaving as an iterable sequence of JobUpsertData.
    """

    source: str
    jobs: list[JobUpsertData] = field(default_factory=list)
    success: bool = True
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    is_suspicious: bool = False
    details: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[JobUpsertData]:
        return iter(self.jobs)

    def __len__(self) -> int:
        return len(self.jobs)

    def __getitem__(self, index: int) -> JobUpsertData:
        return self.jobs[index]


class BaseScraper(ABC):
    """Abstract base class for all job scrapers."""

    #: Must match a value in SCRAPER_SOURCE_VALUES ('remoteok' | 'yc_jobs')
    source: str

    @abstractmethod
    def run(self) -> list[JobUpsertData] | ScraperResult:
        """
        Execute the scraper and return normalised job data.

        Returns:
            ScraperResult or list of JobUpsertData. Empty on no results.

        Raises:
            Exception: on unrecoverable network failure, parse failure, or timeout.
        """
        ...