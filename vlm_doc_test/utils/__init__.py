"""
Utility functions for document testing.

This module provides helper utilities for web scraping, image processing,
and document manipulation.
"""

from .web_scraper import WebScraper, ScrapeResult
from .markdown_utils import (
    parse_markdown_to_content,
    extract_title_from_markdown,
    count_headings_by_level,
)

__all__ = [
    "WebScraper",
    "ScrapeResult",
    "parse_markdown_to_content",
    "extract_title_from_markdown",
    "count_headings_by_level",
]
