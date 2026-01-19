"""Parser registry and base classes."""

from etl.parsers.registry import ParserRegistry, register_parser, get_parser
from etl.parsers.base import BaseParser, CarRecord, ParseResult

__all__ = [
    "ParserRegistry",
    "register_parser",
    "get_parser",
    "BaseParser",
    "CarRecord",
    "ParseResult",
]
