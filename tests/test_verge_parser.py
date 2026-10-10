from __future__ import annotations

from app.models import SourceType
from app.parsers import get_parser
from app.parsers.verge_parser import VergeParser

VERGE_URL = "https://www.theverge.com/rss/index.xml"

SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>The Verge</title>
  <entry>
    <title type="html">Sample Verge Headline</title>
    <link rel="alternate" type="text/html"
          href="https://www.theverge.com/2026/10/10/sample-article"/>
    <published>2026-10-10T14:52:07-04:00</published>
    <summary type="html">Short <b>teaser</b> from the feed.</summary>
    <content type="html">
      <p>Full article body with <em>HTML</em> markup.</p>
    </content>
  </entry>
  <entry>
    <title>No text entry</title>
    <link rel="alternate" href="https://www.theverge.com/2026/10/10/empty"/>
    <summary type="html"></summary>
    <content type="html"></content>
  </entry>
</feed>
"""


def test_verge_parser_selected_for_feed_url():
    parser = get_parser(SourceType.SITE, VERGE_URL)
    assert parser is not None
    assert isinstance(parser, VergeParser)


def test_parse_feed_xml_keeps_valid_entry_and_skips_empty():
    parser = VergeParser()
    articles = parser.parse_feed_xml(SAMPLE_ATOM, limit=10)

    assert len(articles) == 1
    article = articles[0]
    assert article["title"] == "Sample Verge Headline"
    assert article["url"] == "https://www.theverge.com/2026/10/10/sample-article"
    assert "Full article body" in article["raw_text"]
    assert "<" not in article["raw_text"]
    assert article["summary"] == "Short teaser from the feed."
    assert article["published_at"] is not None
    assert article["published_at"].tzinfo is not None


def test_create_verge_source_201(client):
    response = client.post(
        "/api/sources/",
        json={
            "type": "site",
            "name": "The Verge",
            "url": VERGE_URL,
            "enabled": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "The Verge"
    assert body["url"] == VERGE_URL
