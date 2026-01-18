"""
Confidence scoring schemas for adaptive PDF parsing.

These schemas represent confidence levels and metrics for determining
when to escalate from fast local parsers to expensive VLM analysis.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Discrete confidence levels for extraction quality."""
    HIGH = "high"          # >= 0.85: Extraction is reliable
    MEDIUM = "medium"      # >= 0.70: Acceptable, minor issues
    LOW = "low"            # >= 0.50: Significant issues, consider escalation
    VERY_LOW = "very_low"  # < 0.50: Unreliable, escalation recommended

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Convert numeric score to confidence level."""
        if score >= 0.85:
            return cls.HIGH
        elif score >= 0.70:
            return cls.MEDIUM
        elif score >= 0.50:
            return cls.LOW
        else:
            return cls.VERY_LOW


class TextQualityMetrics(BaseModel):
    """Metrics for text extraction quality."""
    # Character-level metrics
    alphanumeric_ratio: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        description="Ratio of alphanumeric chars to total chars"
    )
    replacement_char_ratio: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of replacement/unknown chars (encoding issues)"
    )
    whitespace_ratio: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of whitespace to total chars"
    )

    # Word-level metrics
    avg_word_length: float = Field(
        default=5.0,
        ge=0.0,
        description="Average word length (low = OCR artifacts)"
    )
    broken_word_ratio: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of likely broken words (single chars, isolated punctuation)"
    )

    # Content metrics
    empty_block_ratio: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of empty text blocks"
    )


class LayoutMetrics(BaseModel):
    """Metrics for layout complexity and extraction reliability."""
    # Complexity indicators
    x_position_variance: float = Field(
        default=0.0,
        ge=0.0,
        description="Variance in x-positions of text blocks (high = multi-column)"
    )
    block_density: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of page area covered by text blocks"
    )
    image_density: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of page area covered by images"
    )

    # Structure indicators
    heading_count: int = Field(default=0, ge=0)
    has_multi_column: bool = Field(default=False)
    has_overlapping_blocks: bool = Field(default=False)


class TableConfidenceMetrics(BaseModel):
    """Metrics for table extraction confidence."""
    has_visible_borders: bool = Field(
        default=False,
        description="Whether table has visible cell borders"
    )
    empty_cell_ratio: float = Field(
        default=0.0,
        ge=0.0, le=1.0,
        description="Ratio of empty cells (high = possible extraction failure)"
    )
    row_consistency: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        description="Consistency of column count across rows"
    )
    cell_content_quality: float = Field(
        default=1.0,
        ge=0.0, le=1.0,
        description="Quality of cell text content"
    )


class FigureConfidenceMetrics(BaseModel):
    """Metrics for figure/image extraction confidence."""
    has_caption: bool = Field(default=False)
    has_label: bool = Field(default=False)
    bbox_valid: bool = Field(
        default=True,
        description="Whether bounding box coordinates are valid"
    )
    is_decorative: bool = Field(
        default=False,
        description="Whether image appears to be decorative (logo, icon)"
    )


class PageConfidence(BaseModel):
    """Confidence metrics for a single page."""
    page_number: int = Field(ge=1)

    # Component scores (0.0 - 1.0)
    text_score: float = Field(default=1.0, ge=0.0, le=1.0)
    layout_score: float = Field(default=1.0, ge=0.0, le=1.0)
    table_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    figure_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Overall page score
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0)

    # Detailed metrics (optional)
    text_metrics: Optional[TextQualityMetrics] = None
    layout_metrics: Optional[LayoutMetrics] = None

    # Flags
    needs_vlm: bool = Field(
        default=False,
        description="Whether this page needs VLM analysis"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of detected issues"
    )

    @property
    def level(self) -> ConfidenceLevel:
        """Get confidence level from overall score."""
        return ConfidenceLevel.from_score(self.overall_score)


class ExtractionConfidence(BaseModel):
    """
    Overall extraction confidence for a document.

    Aggregates per-page confidence scores and provides
    document-level assessment for escalation decisions.
    """
    # Document-level scores (0.0 - 1.0)
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0)
    content_score: float = Field(default=1.0, ge=0.0, le=1.0)
    structure_score: float = Field(default=1.0, ge=0.0, le=1.0)
    table_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    figure_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    # Per-page breakdown
    page_confidences: List[PageConfidence] = Field(default_factory=list)

    # Summary metrics
    total_pages: int = Field(default=0, ge=0)
    pages_needing_vlm: int = Field(default=0, ge=0)

    # Issues detected
    issues: List[str] = Field(default_factory=list)

    @property
    def level(self) -> ConfidenceLevel:
        """Get confidence level from overall score."""
        return ConfidenceLevel.from_score(self.overall_score)

    @property
    def vlm_page_ratio(self) -> float:
        """Ratio of pages that need VLM analysis."""
        if self.total_pages == 0:
            return 0.0
        return self.pages_needing_vlm / self.total_pages

    @property
    def needs_full_vlm(self) -> bool:
        """Whether document needs full VLM analysis (>30% bad pages)."""
        return self.vlm_page_ratio > 0.30

    def get_vlm_pages(self) -> List[int]:
        """Get list of page numbers that need VLM analysis."""
        return [pc.page_number for pc in self.page_confidences if pc.needs_vlm]

    def get_good_pages(self) -> List[int]:
        """Get list of page numbers with good extraction."""
        return [pc.page_number for pc in self.page_confidences if not pc.needs_vlm]

    def summary(self) -> Dict[str, Any]:
        """Get summary dict for reporting."""
        return {
            "overall_score": round(self.overall_score, 3),
            "level": self.level.value,
            "total_pages": self.total_pages,
            "pages_needing_vlm": self.pages_needing_vlm,
            "vlm_page_ratio": round(self.vlm_page_ratio, 3),
            "needs_full_vlm": self.needs_full_vlm,
            "issues": self.issues,
        }
