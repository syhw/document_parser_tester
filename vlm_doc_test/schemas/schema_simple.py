"""
Simplified document schema - a strict subset of the full schema.

This schema is designed for:
- Quick prototyping and testing
- Simple documents without complex structure
- Faster iteration during development
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from .base import DocumentFormat, DocumentCategory, BoundingBox


class ContentElement(BaseModel):
    """Simple content element - just id, type, and text."""
    id: str
    type: str  # "heading", "paragraph", "section", etc.
    content: str
    bbox: Optional[BoundingBox] = None
    level: Optional[int] = None  # For headings, hierarchy


class Figure(BaseModel):
    """Simple figure with caption and location."""
    id: str
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Figure 1"
    bbox: Optional[BoundingBox] = None


class Table(BaseModel):
    """Simple table representation."""
    id: str
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Table 1"
    bbox: Optional[BoundingBox] = None
    # Raw content representation
    rows: List[List[str]] = Field(default_factory=list)


class Link(BaseModel):
    """Simple link with text and URL."""
    id: str
    text: str
    url: str


class Author(BaseModel):
    """Simple author representation."""
    name: str
    affiliation: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Minimal document metadata."""
    title: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    date: Optional[datetime] = None
    keywords: List[str] = Field(default_factory=list)


class DocumentSource(BaseModel):
    """Document source information."""
    url: Optional[str] = None
    file_path: Optional[str] = None
    accessed_at: datetime


class SimpleDocument(BaseModel):
    """
    Simplified document representation.

    This is a strict subset of the full Document schema,
    containing only the most essential fields.
    """
    # Required fields
    id: str
    format: DocumentFormat
    source: DocumentSource

    # Optional categorization
    category: Optional[DocumentCategory] = None

    # Metadata
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    # Content (flat list of elements)
    content: List[ContentElement] = Field(default_factory=list)

    # Visual elements
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)

    # Links
    links: List[Link] = Field(default_factory=list)
