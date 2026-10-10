from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from app.parsers.base_parser import SiteParser
from app.utils import as_utc, blank_to_none, is_absolute_http_url, title_from_text, utc_now

logger = logging.getLogger(__name__)

ATOM_NS = "{http://www.w3.org/2005/Atom}"


class VergeParser(SiteParser):
    """The Verge main Atom feed (bonus site source)."""

    parse_url = "https://www.theverge.com/rss/index.xml"

    def can_handle(self, url: str) -> bool:
        return url.strip() == self.parse_url

    async def parse(self, url: str, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            response.raise_for_status()

        articles = self.parse_feed_xml(response.text, limit=limit)
        logger.info("The Verge parser collected %s articles", len(articles))
        return articles

    def parse_feed_xml(self, xml_text: str, limit: int = 10) -> list[dict]:
        """Parse Atom XML into article dicts (used by tests without network)."""
        root = ET.fromstring(xml_text)
        articles: list[dict] = []

        for entry in root.findall(f"{ATOM_NS}entry")[:limit]:
            article = self._parse_entry(entry)
            if article is not None:
                articles.append(article)

        return articles

    def _parse_entry(self, entry: ET.Element) -> dict | None:
        link = self._entry_link(entry)
        content_html = self._element_html(entry.find(f"{ATOM_NS}content"))
        summary_html = self._element_html(entry.find(f"{ATOM_NS}summary"))

        raw_text = self.clean_html(content_html) or self.clean_html(summary_html)
        summary = blank_to_none(self.clean_html(summary_html))

        # Spec: skip materials without text; skip site news without absolute URL
        if not raw_text:
            return None
        if not is_absolute_http_url(link):
            logger.warning("Skip The Verge entry without absolute URL: %r", link)
            return None

        title_html = self._element_html(entry.find(f"{ATOM_NS}title"))
        title = title_from_text(
            raw_text,
            fallback_title=self.clean_html(title_html) or None,
        )
        published_at = self._parse_datetime(
            entry.findtext(f"{ATOM_NS}published")
            or entry.findtext(f"{ATOM_NS}updated")
        )

        return {
            "title": title,
            "url": link,
            "raw_text": raw_text,
            "summary": summary,
            "published_at": published_at,
            "collected_at": utc_now(),
        }

    def _entry_link(self, entry: ET.Element) -> str:
        fallback = ""
        for link in entry.findall(f"{ATOM_NS}link"):
            href = (link.attrib.get("href") or "").strip()
            if not href:
                continue
            rel = link.attrib.get("rel", "alternate")
            if rel == "alternate":
                return href
            if not fallback:
                fallback = href
        return fallback

    def _element_html(self, element: ET.Element | None) -> str:
        if element is None:
            return ""
        # Serialize the whole Atom node; BeautifulSoup then strips tags
        return ET.tostring(element, encoding="unicode")

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value or not value.strip():
            return None
        try:
            # Atom: 2026-10-10T14:52:07-04:00
            return as_utc(datetime.fromisoformat(value.strip()))
        except ValueError:
            logger.warning("Could not parse The Verge datetime: %r", value)
            return None

    def clean_html(self, raw_html: str | None) -> str:
        soup = BeautifulSoup(raw_html or "", "html.parser")
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        return soup.get_text(" ", strip=True)
