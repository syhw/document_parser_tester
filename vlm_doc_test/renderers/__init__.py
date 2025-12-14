"""
Document renderers for creating visual representations.

This module provides renderers for converting documents to images
for visual regression testing and VLM analysis.
"""

from .web_renderer import WebRenderer

__all__ = [
    "WebRenderer",
]
