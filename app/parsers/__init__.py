from app.models import SourceType
from app.parsers.base_parser import BaseParser
from app.parsers.habr_parser import HabrParser
from app.parsers.telegram_parser import TelegramParser

PARSERS: list[BaseParser] = [
    HabrParser(),
    TelegramParser()
]


def get_parser(source_type: SourceType, url: str) -> BaseParser:
    for parser in PARSERS:
        if parser.source_type == source_type and parser.can_handle(url):
            return parser
    return None
