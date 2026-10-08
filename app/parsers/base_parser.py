from abc import ABC, abstractmethod

from app.models import SourceType


class BaseParser(ABC):
    """Common interface for every news parser (site or Telegram)."""
    source_type: SourceType

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this parser knows how to read this source URL."""

    @abstractmethod
    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        """Fetch up to `limit` articles from the source URL."""


class SiteParser(BaseParser, ABC):
    """Base for website parsers. Each site sets its own `parse_url`."""

    source_type = SourceType.SITE
    parse_url: str
