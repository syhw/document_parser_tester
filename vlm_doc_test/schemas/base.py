"""
Base schema types shared across all schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class DocumentFormat(str, Enum):
    """Document format: the file format/extension/representation."""
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    MARKDOWN = "markdown"
    LATEX = "latex"
    DOCX = "docx"
    PPTX = "pptx"
    JUPYTER = "jupyter"
    OTHER = "other"


class DocumentCategory(str, Enum):
    """Document category: the semantic type/purpose of the document."""
    ACADEMIC_PAPER = "academic_paper"
    BLOG_POST = "blog_post"
    NEWS_ARTICLE = "news_article"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    BOOK_CHAPTER = "book_chapter"
    PRESENTATION = "presentation"
    REPORT = "report"
    TUTORIAL = "tutorial"
    PLOT_VISUALIZATION = "plot_visualization"
    INFOGRAPHIC = "infographic"
    WEBPAGE_GENERAL = "webpage_general"
    OTHER = "other"


class BoundingBox(BaseModel):
    """
    Bounding box coordinates for visual elements.

    Uses a consistent coordinate system per page/screen with origin at top-left corner.
    Coordinates are in pixels or PDF points (72 DPI).
    """
    # Page or screen number (1-indexed)
    page: int

    # Coordinates in pixels or PDF points (72 DPI)
    x: float  # Left edge
    y: float  # Top edge
    width: float  # Width of box
    height: float  # Height of box

    # Optional: confidence score from extraction tool
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
