"""
Configuration for the adaptive PDF parser.

Defines thresholds, pipeline order, and behavior settings for
the adaptive parsing strategy.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

from ..schemas.base import DocumentCategory


class ParserType(str, Enum):
    """Available parser types in escalation order."""
    PYMUPDF = "pymupdf"      # ~0.01s/page, basic extraction
    MARKER = "marker"        # ~1s/page, high-fidelity markdown
    DOCLING = "docling"      # ~2s/page, hybrid approach
    VLM = "vlm"              # ~5s/page, vision model (expensive)


@dataclass
class EscalationThresholds:
    """
    Thresholds that control when to escalate to more expensive parsers.

    All values are confidence scores (0.0 - 1.0).
    """
    # Overall document confidence threshold
    min_overall_confidence: float = 0.70

    # Content-specific thresholds
    min_content_confidence: float = 0.75
    min_table_confidence: float = 0.65
    min_figure_confidence: float = 0.70

    # Per-page threshold
    min_page_confidence: float = 0.65

    # Threshold for full document VLM escalation
    # If more than this ratio of pages need VLM, escalate entire document
    max_vlm_page_ratio: float = 0.30

    def should_escalate(
        self,
        overall_score: float,
        content_score: Optional[float] = None,
        table_score: Optional[float] = None,
        figure_score: Optional[float] = None,
    ) -> bool:
        """
        Determine if scores indicate need for escalation.

        Returns True if ANY score falls below its threshold.
        """
        if overall_score < self.min_overall_confidence:
            return True

        if content_score is not None and content_score < self.min_content_confidence:
            return True

        if table_score is not None and table_score < self.min_table_confidence:
            return True

        if figure_score is not None and figure_score < self.min_figure_confidence:
            return True

        return False


@dataclass
class CategoryThresholds:
    """
    Category-specific threshold overrides.

    Different document types have different quality requirements.
    """
    # Academic papers need high accuracy for tables and metadata
    academic_paper: EscalationThresholds = field(default_factory=lambda: EscalationThresholds(
        min_overall_confidence=0.75,
        min_content_confidence=0.80,
        min_table_confidence=0.75,
        min_figure_confidence=0.75,
    ))

    # Plots/visualizations almost always need VLM for chart data
    plot_visualization: EscalationThresholds = field(default_factory=lambda: EscalationThresholds(
        min_overall_confidence=0.80,
        min_content_confidence=0.70,
        min_table_confidence=0.80,
        min_figure_confidence=0.90,  # Very high for figures
    ))

    # Technical docs need good code/content extraction
    technical_documentation: EscalationThresholds = field(default_factory=lambda: EscalationThresholds(
        min_overall_confidence=0.75,
        min_content_confidence=0.80,
        min_table_confidence=0.70,
        min_figure_confidence=0.70,
    ))

    # Blog posts and news are more forgiving
    blog_post: EscalationThresholds = field(default_factory=lambda: EscalationThresholds(
        min_overall_confidence=0.65,
        min_content_confidence=0.70,
        min_table_confidence=0.60,
        min_figure_confidence=0.60,
    ))

    # Default for other categories
    default: EscalationThresholds = field(default_factory=EscalationThresholds)

    def get_for_category(
        self, category: Optional[DocumentCategory]
    ) -> EscalationThresholds:
        """Get thresholds for a specific document category."""
        if category is None:
            return self.default

        category_map = {
            DocumentCategory.ACADEMIC_PAPER: self.academic_paper,
            DocumentCategory.PLOT_VISUALIZATION: self.plot_visualization,
            DocumentCategory.TECHNICAL_DOCUMENTATION: self.technical_documentation,
            DocumentCategory.BLOG_POST: self.blog_post,
            DocumentCategory.NEWS_ARTICLE: self.blog_post,  # Similar to blog
        }

        return category_map.get(category, self.default)


@dataclass
class AdaptivePipelineConfig:
    """
    Configuration for the adaptive PDF parsing pipeline.

    Controls parser order, thresholds, and behavior settings.
    """
    # Parser escalation order (tried in sequence until confidence is met)
    pipeline_order: List[ParserType] = field(default_factory=lambda: [
        ParserType.PYMUPDF,
        ParserType.MARKER,
        ParserType.DOCLING,
        ParserType.VLM,
    ])

    # Escalation thresholds
    thresholds: EscalationThresholds = field(default_factory=EscalationThresholds)

    # Category-specific thresholds (overrides default thresholds)
    category_thresholds: CategoryThresholds = field(default_factory=CategoryThresholds)

    # Behavior settings
    enable_per_page_decisions: bool = True
    """When True, evaluate confidence per-page and escalate only bad pages."""

    enable_hybrid_extraction: bool = True
    """When True, combine fast parser output for good pages with VLM for bad pages."""

    max_vlm_pages: Optional[int] = None
    """Maximum number of pages to send to VLM (cost control)."""

    stop_on_success: bool = True
    """When True, stop escalation when confidence threshold is met."""

    cache_parser_results: bool = True
    """When True, cache intermediate parser results for debugging."""

    # VLM settings
    vlm_batch_size: int = 4
    """Number of pages to batch for VLM analysis."""

    def get_thresholds(
        self, category: Optional[DocumentCategory] = None
    ) -> EscalationThresholds:
        """
        Get effective thresholds for a document category.

        Uses category-specific thresholds if available, otherwise default.
        """
        if category:
            return self.category_thresholds.get_for_category(category)
        return self.thresholds

    def get_parser_limit(self) -> Optional[ParserType]:
        """
        Get the maximum parser type in the pipeline.

        Returns the last parser in the pipeline order.
        """
        return self.pipeline_order[-1] if self.pipeline_order else None

    def limit_to_parser(self, max_parser: ParserType) -> "AdaptivePipelineConfig":
        """
        Create a new config limited to parsers up to and including max_parser.

        Useful for testing or cost control.
        """
        try:
            limit_idx = self.pipeline_order.index(max_parser) + 1
            new_order = self.pipeline_order[:limit_idx]
        except ValueError:
            new_order = self.pipeline_order

        return AdaptivePipelineConfig(
            pipeline_order=new_order,
            thresholds=self.thresholds,
            category_thresholds=self.category_thresholds,
            enable_per_page_decisions=self.enable_per_page_decisions,
            enable_hybrid_extraction=self.enable_hybrid_extraction,
            max_vlm_pages=self.max_vlm_pages,
            stop_on_success=self.stop_on_success,
            cache_parser_results=self.cache_parser_results,
            vlm_batch_size=self.vlm_batch_size,
        )


# Pre-configured pipeline profiles
FAST_PIPELINE = AdaptivePipelineConfig(
    pipeline_order=[ParserType.PYMUPDF],
    enable_hybrid_extraction=False,
)
"""Fastest pipeline - PyMuPDF only, no escalation."""

BALANCED_PIPELINE = AdaptivePipelineConfig(
    pipeline_order=[ParserType.PYMUPDF, ParserType.MARKER],
    enable_hybrid_extraction=True,
)
"""Balanced pipeline - PyMuPDF with Marker fallback, no VLM."""

QUALITY_PIPELINE = AdaptivePipelineConfig(
    pipeline_order=[ParserType.PYMUPDF, ParserType.MARKER, ParserType.DOCLING],
    enable_hybrid_extraction=True,
)
"""Quality pipeline - All local parsers, no VLM."""

FULL_PIPELINE = AdaptivePipelineConfig(
    pipeline_order=[ParserType.PYMUPDF, ParserType.MARKER, ParserType.DOCLING, ParserType.VLM],
    enable_hybrid_extraction=True,
)
"""Full pipeline - All parsers including VLM (can be expensive)."""
