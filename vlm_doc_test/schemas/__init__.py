"""
Schema definitions for document structures.

This module provides Pydantic models for representing parsed documents,
including both the full schema (schema.py) and simplified schema (schema_simple.py).
"""

from .base import BoundingBox, DocumentFormat, DocumentCategory
from .schema_simple import SimpleDocument, Author as SimpleAuthor
# from .schema import Document  # Will be implemented

# Confidence schemas (Phase 4)
from .confidence import (
    ConfidenceLevel,
    TextQualityMetrics,
    LayoutMetrics,
    TableConfidenceMetrics,
    FigureConfidenceMetrics,
    PageConfidence,
    ExtractionConfidence,
)

__all__ = [
    # Base schemas
    "BoundingBox",
    "DocumentFormat",
    "DocumentCategory",
    "SimpleDocument",
    "SimpleAuthor",
    # Confidence schemas (Phase 4)
    "ConfidenceLevel",
    "TextQualityMetrics",
    "LayoutMetrics",
    "TableConfidenceMetrics",
    "FigureConfidenceMetrics",
    "PageConfidence",
    "ExtractionConfidence",
]
