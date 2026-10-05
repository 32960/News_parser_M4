from datetime import datetime
import asyncio
import httpx

from app.parsers.base_parser import SiteParser
import xml.etree.ElementTree as ET


class HabrParser(SiteParser):
    parse_url = 'https://habr.com/ru/rss/articles/'

    def can_handle(self, url: str) -> bool:
        return url == self.parse_url

    async def parse(self, url: str, limit: int=10) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})

        articles = []
        root = ET.fromstring(response.text)
        for item in root.findall("./channel/item")[:limit]:
            title = item.find('title').text
            link = item.find('link').text
            raw_description = item.find('description').text
            description = self.clean_html(raw_description)

            if not description or not link:
                continue

            articles.append(
                {
                    'title': title,
                    'url': link,
                    'raw_text': description,
                    'collected_at': datetime.now(),
                }
            )
        print(len(articles))
        return articles

    def clean_html(self, raw_description):
        # TODO: implement html cleaning
        return raw_description
