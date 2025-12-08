"""
Schema definitions for document structures.

This module provides Pydantic models for representing parsed documents,
including both the full schema (schema.py) and simplified schema (schema_simple.py).
"""

from .base import BoundingBox, DocumentFormat, DocumentCategory
from .schema_simple import SimpleDocument, Author as SimpleAuthor
# from .schema import Document  # Will be implemented

__all__ = [
    "BoundingBox",
    "DocumentFormat",
    "DocumentCategory",
    "SimpleDocument",
    "SimpleAuthor",
]
