from abc import ABC, abstractmethod

from app.models import SourceType


class BaseParser(ABC):
    source_type: SourceType

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        pass

    @abstractmethod
    async def parse(self, url: str, limit: int) -> list[dict]:
        pass


class SiteParser(BaseParser, ABC):
    source_type = SourceType.SITE
    parse_url: str

    def can_handle(self, url: str) -> bool:
        pass

    async def parse(self, url: str, limit: int) -> list[dict]:
        pass