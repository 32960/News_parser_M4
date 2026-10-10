from __future__ import annotations

from app.models import SourceType
from app.parsers import get_parser
from app.parsers.habr_parser import HabrParser


def test_habr_parser_selected_for_feed_url():
    parser = get_parser(SourceType.SITE, "https://habr.com/ru/rss/articles/")
    assert parser is not None
    assert isinstance(parser, HabrParser)


def test_unknown_site_has_no_parser():
    parser = get_parser(SourceType.SITE, "https://example.com/rss")
    assert parser is None


def test_telegram_parser_accepts_username_link():
    parser = get_parser(SourceType.TELEGRAM, "https://t.me/durov")
    assert parser is not None
