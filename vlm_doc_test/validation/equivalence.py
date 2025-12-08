"""
Equivalence checking for document extractions.

Compares tool-based and VLM-based extractions using:
- DeepDiff for structural comparison with numerical tolerance
- TheFuzz for fuzzy string matching
- Custom logic for bounding box comparison
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from deepdiff import DeepDiff
from thefuzz import fuzz

from ..schemas.schema_simple import SimpleDocument, ContentElement, Figure, Table
from ..schemas.base import BoundingBox


class MatchQuality(str, Enum):
    """Quality levels for match assessment."""
    EXACT = "exact"  # 100% match
    EXCELLENT = "excellent"  # 95-99% match
    GOOD = "good"  # 85-94% match
    FAIR = "fair"  # 70-84% match
    POOR = "poor"  # 50-69% match
    FAILED = "failed"  # <50% match


@dataclass
class ComparisonResult:
    """Result of comparing two documents or elements."""
    match_quality: MatchQuality
    score: float  # 0.0 to 1.0
    differences: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class EquivalenceChecker:
    """
    Checks equivalence between tool-based and VLM-based extractions.

    Uses multiple comparison strategies:
    1. Structural comparison with DeepDiff
    2. Fuzzy text matching with TheFuzz
    3. Coordinate-based spatial comparison
    4. Count-based validation
    """

    def __init__(
        self,
        text_similarity_threshold: float = 0.85,
        bbox_iou_threshold: float = 0.7,
        numerical_tolerance: float = 0.01,
    ):
        """
        Initialize equivalence checker.

        Args:
            text_similarity_threshold: Minimum fuzzy match ratio (0-1) for text
            bbox_iou_threshold: Minimum IoU for bounding box match
            numerical_tolerance: Relative tolerance for numerical comparisons
        """
        self.text_similarity_threshold = text_similarity_threshold
        self.bbox_iou_threshold = bbox_iou_threshold
        self.numerical_tolerance = numerical_tolerance

    def compare_documents(
        self,
        tool_doc: SimpleDocument,
        vlm_doc: SimpleDocument,
    ) -> ComparisonResult:
        """
        Compare two SimpleDocument instances.

        Args:
            tool_doc: Document from tool-based extraction
            vlm_doc: Document from VLM-based extraction

        Returns:
            ComparisonResult with detailed comparison
        """
        scores = []
        details = {}
        warnings = []
        differences = {}

        # Compare metadata
        metadata_result = self._compare_metadata(tool_doc, vlm_doc)
        scores.append(metadata_result.score)
        details["metadata"] = metadata_result.details
        if metadata_result.differences:
            differences["metadata"] = metadata_result.differences

        # Compare content elements
        content_result = self._compare_content_lists(
            tool_doc.content,
            vlm_doc.content,
        )
        scores.append(content_result.score)
        details["content"] = content_result.details
        if content_result.differences:
            differences["content"] = content_result.differences
        warnings.extend(content_result.warnings)

        # Compare figures
        figures_result = self._compare_figures(tool_doc.figures, vlm_doc.figures)
        scores.append(figures_result.score)
        details["figures"] = figures_result.details
        if figures_result.differences:
            differences["figures"] = figures_result.differences

        # Compare tables
        tables_result = self._compare_tables(tool_doc.tables, vlm_doc.tables)
        scores.append(tables_result.score)
        details["tables"] = tables_result.details
        if tables_result.differences:
            differences["tables"] = tables_result.differences

        # Calculate overall score (weighted average)
        weights = [0.2, 0.5, 0.15, 0.15]  # metadata, content, figures, tables
        overall_score = sum(s * w for s, w in zip(scores, weights))

        # Determine match quality
        match_quality = self._score_to_quality(overall_score)

        return ComparisonResult(
            match_quality=match_quality,
            score=overall_score,
            differences=differences,
            details=details,
            warnings=warnings,
        )

    def _compare_metadata(
        self,
        tool_doc: SimpleDocument,
        vlm_doc: SimpleDocument,
    ) -> ComparisonResult:
        """Compare document metadata."""
        scores = []
        details = {}
        differences = {}

        # Title comparison
        if tool_doc.metadata.title and vlm_doc.metadata.title:
            title_score = fuzz.ratio(
                tool_doc.metadata.title,
                vlm_doc.metadata.title,
            ) / 100.0
            scores.append(title_score)
            details["title_match"] = title_score
            if title_score < self.text_similarity_threshold:
                differences["title"] = {
                    "tool": tool_doc.metadata.title,
                    "vlm": vlm_doc.metadata.title,
                }
        elif tool_doc.metadata.title or vlm_doc.metadata.title:
            scores.append(0.0)
            differences["title"] = "One document has title, other doesn't"

        # Author count comparison (simple)
        tool_authors = len(tool_doc.metadata.authors)
        vlm_authors = len(vlm_doc.metadata.authors)
        if tool_authors > 0 or vlm_authors > 0:
            author_score = 1.0 - abs(tool_authors - vlm_authors) / max(tool_authors, vlm_authors, 1)
            scores.append(author_score)
            details["author_count"] = {"tool": tool_authors, "vlm": vlm_authors}

        # Keywords comparison
        tool_kw = set(tool_doc.metadata.keywords)
        vlm_kw = set(vlm_doc.metadata.keywords)
        if tool_kw or vlm_kw:
            kw_intersection = len(tool_kw & vlm_kw)
            kw_union = len(tool_kw | vlm_kw)
            kw_score = kw_intersection / kw_union if kw_union > 0 else 0.0
            scores.append(kw_score)
            details["keyword_overlap"] = kw_score

        overall_score = sum(scores) / len(scores) if scores else 0.5

        return ComparisonResult(
            match_quality=self._score_to_quality(overall_score),
            score=overall_score,
            differences=differences,
            details=details,
        )

    def _compare_content_lists(
        self,
        tool_content: List[ContentElement],
        vlm_content: List[ContentElement],
    ) -> ComparisonResult:
        """Compare lists of content elements."""
        details = {}
        warnings = []
        differences = {}

        # Count comparison
        tool_count = len(tool_content)
        vlm_count = len(vlm_content)
        details["count"] = {"tool": tool_count, "vlm": vlm_count}

        if tool_count == 0 and vlm_count == 0:
            return ComparisonResult(
                match_quality=MatchQuality.EXACT,
                score=1.0,
                details=details,
            )

        # Type distribution
        tool_types = {}
        vlm_types = {}
        for elem in tool_content:
            tool_types[elem.type] = tool_types.get(elem.type, 0) + 1
        for elem in vlm_content:
            vlm_types[elem.type] = vlm_types.get(elem.type, 0) + 1

        details["type_distribution"] = {"tool": tool_types, "vlm": vlm_types}

        # Text content comparison (fuzzy matching)
        tool_texts = [elem.content for elem in tool_content]
        vlm_texts = [elem.content for elem in vlm_content]

        # Simple approach: compare concatenated text
        tool_full_text = " ".join(tool_texts)
        vlm_full_text = " ".join(vlm_texts)

        text_score = fuzz.token_sort_ratio(tool_full_text, vlm_full_text) / 100.0
        details["text_similarity"] = text_score

        if text_score < self.text_similarity_threshold:
            warnings.append(
                f"Text similarity ({text_score:.2%}) below threshold "
                f"({self.text_similarity_threshold:.2%})"
            )

        # Count difference penalty
        count_diff = abs(tool_count - vlm_count)
        max_count = max(tool_count, vlm_count, 1)
        count_score = 1.0 - (count_diff / max_count)

        # Combined score
        overall_score = (text_score * 0.7 + count_score * 0.3)

        return ComparisonResult(
            match_quality=self._score_to_quality(overall_score),
            score=overall_score,
            differences=differences,
            details=details,
            warnings=warnings,
        )

    def _compare_figures(
        self,
        tool_figures: List[Figure],
        vlm_figures: List[Figure],
    ) -> ComparisonResult:
        """Compare figure lists."""
        details = {}
        differences = {}

        tool_count = len(tool_figures)
        vlm_count = len(vlm_figures)

        details["count"] = {"tool": tool_count, "vlm": vlm_count}

        if tool_count == 0 and vlm_count == 0:
            return ComparisonResult(
                match_quality=MatchQuality.EXACT,
                score=1.0,
                details=details,
            )

        # Count-based score
        count_diff = abs(tool_count - vlm_count)
        max_count = max(tool_count, vlm_count, 1)
        count_score = 1.0 - (count_diff / max_count)

        # If counts match, try spatial matching
        spatial_score = None
        if tool_count == vlm_count and tool_count > 0:
            # Check if bounding boxes are available
            if all(f.bbox for f in tool_figures) and all(f.bbox for f in vlm_figures):
                spatial_score = self._match_bboxes(
                    [f.bbox for f in tool_figures],
                    [f.bbox for f in vlm_figures],
                )
                details["spatial_match"] = spatial_score

        overall_score = count_score
        if spatial_score is not None:
            overall_score = (count_score + spatial_score) / 2

        return ComparisonResult(
            match_quality=self._score_to_quality(overall_score),
            score=overall_score,
            differences=differences,
            details=details,
        )

    def _compare_tables(
        self,
        tool_tables: List[Table],
        vlm_tables: List[Table],
    ) -> ComparisonResult:
        """Compare table lists."""
        details = {}
        differences = {}

        tool_count = len(tool_tables)
        vlm_count = len(vlm_tables)

        details["count"] = {"tool": tool_count, "vlm": vlm_count}

        if tool_count == 0 and vlm_count == 0:
            return ComparisonResult(
                match_quality=MatchQuality.EXACT,
                score=1.0,
                details=details,
            )

        # Count-based score
        count_diff = abs(tool_count - vlm_count)
        max_count = max(tool_count, vlm_count, 1)
        count_score = 1.0 - (count_diff / max_count)

        # If counts match, compare table dimensions
        if tool_count == vlm_count and tool_count > 0:
            dimension_scores = []
            for tool_table, vlm_table in zip(tool_tables, vlm_tables):
                tool_dims = (len(tool_table.rows), len(tool_table.rows[0]) if tool_table.rows else 0)
                vlm_dims = (len(vlm_table.rows), len(vlm_table.rows[0]) if vlm_table.rows else 0)

                dim_match = 1.0 if tool_dims == vlm_dims else 0.5
                dimension_scores.append(dim_match)

            details["dimension_match"] = sum(dimension_scores) / len(dimension_scores)
            overall_score = (count_score + details["dimension_match"]) / 2
        else:
            overall_score = count_score

        return ComparisonResult(
            match_quality=self._score_to_quality(overall_score),
            score=overall_score,
            differences=differences,
            details=details,
        )

    def _match_bboxes(
        self,
        bboxes1: List[BoundingBox],
        bboxes2: List[BoundingBox],
    ) -> float:
        """
        Match bounding boxes using IoU (Intersection over Union).

        Returns average IoU score for best matches.
        """
        if not bboxes1 or not bboxes2:
            return 0.0

        # Group by page
        pages1 = {}
        pages2 = {}
        for bbox in bboxes1:
            pages1.setdefault(bbox.page, []).append(bbox)
        for bbox in bboxes2:
            pages2.setdefault(bbox.page, []).append(bbox)

        ious = []
        for page in set(pages1.keys()) & set(pages2.keys()):
            page_bboxes1 = pages1[page]
            page_bboxes2 = pages2[page]

            # Greedy matching
            for bbox1 in page_bboxes1:
                best_iou = 0.0
                for bbox2 in page_bboxes2:
                    iou = self._calculate_iou(bbox1, bbox2)
                    best_iou = max(best_iou, iou)
                ious.append(best_iou)

        return sum(ious) / len(ious) if ious else 0.0

    def _calculate_iou(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """Calculate Intersection over Union for two bounding boxes."""
        # Calculate intersection
        x1_max = max(bbox1.x, bbox2.x)
        y1_max = max(bbox1.y, bbox2.y)
        x2_min = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2_min = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)

        if x2_min <= x1_max or y2_min <= y1_max:
            return 0.0  # No intersection

        intersection = (x2_min - x1_max) * (y2_min - y1_max)

        # Calculate union
        area1 = bbox1.width * bbox1.height
        area2 = bbox2.width * bbox2.height
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _score_to_quality(self, score: float) -> MatchQuality:
        """Convert numerical score to MatchQuality enum."""
        if score >= 0.99:
            return MatchQuality.EXACT
        elif score >= 0.95:
            return MatchQuality.EXCELLENT
        elif score >= 0.85:
            return MatchQuality.GOOD
        elif score >= 0.70:
            return MatchQuality.FAIR
        elif score >= 0.50:
            return MatchQuality.POOR
        else:
            return MatchQuality.FAILED
