#!/usr/bin/env python3
"""
Parser registry for dynamic parser discovery and instantiation.

This module provides:
- Parser registration via decorator
- Parser lookup by name
- Dynamic loading of parser modules
"""

import importlib
from typing import Dict, Type, Optional

from etl.parsers.base import BaseParser


class ParserRegistry:
    """Registry for data source parsers."""

    _parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a parser class.

        Usage:
            @ParserRegistry.register("caranddriver.review_specs")
            class ReviewSpecsParser(BaseParser):
                ...

        Args:
            name: Unique name for the parser (e.g., "caranddriver.review_specs")

        Returns:
            Decorator function
        """

        def decorator(parser_class: Type[BaseParser]):
            cls._parsers[name] = parser_class
            return parser_class

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Type[BaseParser]]:
        """Get parser class by name.

        If the parser isn't registered, attempts to import the module
        to trigger registration.

        Args:
            name: Parser name (e.g., "caranddriver.review_specs")

        Returns:
            Parser class, or None if not found
        """
        # Handle dot-notation names (e.g., "caranddriver.review_specs")
        if name not in cls._parsers:
            # Try to import the module to trigger registration
            parts = name.rsplit(".", 1)
            if len(parts) == 2:
                module_name = f"etl.parsers.{parts[0]}.{parts[1]}"
                try:
                    importlib.import_module(module_name)
                except ImportError:
                    pass

        return cls._parsers.get(name)

    @classmethod
    def list_parsers(cls) -> list[str]:
        """List all registered parser names.

        Returns:
            List of parser names
        """
        return list(cls._parsers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a parser is registered.

        Args:
            name: Parser name

        Returns:
            True if parser is registered
        """
        return name in cls._parsers

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a parser.

        Args:
            name: Parser name

        Returns:
            True if parser was unregistered, False if not found
        """
        if name in cls._parsers:
            del cls._parsers[name]
            return True
        return False

    @classmethod
    def clear(cls):
        """Clear all registered parsers."""
        cls._parsers.clear()


# Convenience functions
def register_parser(name: str):
    """Decorator to register a parser class.

    Alias for ParserRegistry.register()

    Args:
        name: Unique name for the parser

    Returns:
        Decorator function
    """
    return ParserRegistry.register(name)


def get_parser(name: str) -> Optional[Type[BaseParser]]:
    """Get parser class by name.

    Alias for ParserRegistry.get()

    Args:
        name: Parser name

    Returns:
        Parser class, or None if not found
    """
    return ParserRegistry.get(name)


def list_parsers() -> list[str]:
    """List all registered parser names.

    Alias for ParserRegistry.list_parsers()

    Returns:
        List of parser names
    """
    return ParserRegistry.list_parsers()
