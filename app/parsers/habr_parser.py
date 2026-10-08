from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup

from app.parsers.base_parser import SiteParser
from app.utils import is_absolute_http_url, title_from_text, utc_now

logger = logging.getLogger(__name__)


class HabrParser(SiteParser):
    # Exact feed address our API accepts for type=site
    parse_url = "https://habr.com/ru/rss/articles/"

    def can_handle(self, url: str) -> bool:
        return url.strip() == self.parse_url

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()

        articles: list[dict] = []
        root = ET.fromstring(response.text)

        for item in root.findall("./channel/item")[:limit]:
            article = self._parse_item(item)
            if article is not None:
                articles.append(article)

        logger.info("Habr parser collected %s articles", len(articles))
        return articles

    def _parse_item(self, item: ET.Element) -> dict | None:
        link = (item.findtext("link") or "").strip()
        raw_description = item.findtext("description")
        raw_text = self.clean_html(raw_description)

        # Spec: skip materials without text; skip site news without absolute URL
        if not raw_text:
            return None
        if not is_absolute_http_url(link):
            logger.warning("Skip Habr item without absolute URL: %r", link)
            return None

        title = title_from_text(raw_text, fallback_title=item.findtext("title"))
        published_at = self._parse_pub_date(item.findtext("pubDate"))

        return {
            "title": title,
            "url": link,
            "raw_text": raw_text,
            "summary": None,  # Habr RSS has no separate summary field
            "published_at": published_at,
            "collected_at": utc_now(),
        }

    def _parse_pub_date(self, value: str | None):
        """Convert RSS pubDate to UTC or return None if missing/broken."""
        if not value or not value.strip():
            return None
        try:
            # RSS dates look like: Tue, 07 Oct 2025 12:34:56 GMT
            return parsedate_to_datetime(value.strip())
        except (TypeError, ValueError, IndexError):
            logger.warning("Could not parse Habr pubDate: %r", value)
            return None

    def clean_html(self, raw_description: str | None) -> str:
        soup = BeautifulSoup(raw_description or "", "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        return soup.get_text(" ", strip=True)
