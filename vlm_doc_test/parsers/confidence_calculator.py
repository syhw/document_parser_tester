"""
Confidence calculator for PDF extraction quality assessment.

Computes confidence scores based on heuristics to determine whether
a fast parser's output is reliable or if escalation to VLM is needed.
"""

import re
import statistics
from typing import List, Optional, Tuple
from collections import Counter

from ..schemas.schema_simple import SimpleDocument, ContentElement, Table, Figure
from ..schemas.confidence import (
    ExtractionConfidence,
    PageConfidence,
    TextQualityMetrics,
    LayoutMetrics,
    TableConfidenceMetrics,
    FigureConfidenceMetrics,
    ConfidenceLevel,
)


class ConfidenceCalculator:
    """
    Calculate extraction confidence from parsed document output.

    Uses heuristics to detect:
    - Encoding issues (garbled text, replacement characters)
    - OCR artifacts (broken words, isolated punctuation)
    - Layout complexity (multi-column, overlapping elements)
    - Table extraction quality
    - Missing content
    """

    # Unicode replacement character and common encoding issues
    REPLACEMENT_CHARS = {'\ufffd', '\x00', '\ufffe', '\uffff'}

    # Common OCR artifact patterns
    OCR_ARTIFACT_PATTERNS = [
        r'\b[^\w\s]{2,}\b',  # Multiple punctuation in isolation
        r'\b[a-zA-Z]\b(?!\.)(?!\:)',  # Single letters (except abbreviations)
        r'\d{1,2}[a-zA-Z]{1}\d',  # Digit-letter-digit patterns
    ]

    def __init__(
        self,
        min_text_confidence: float = 0.65,
        min_table_confidence: float = 0.60,
        min_page_confidence: float = 0.65,
    ):
        """
        Initialize confidence calculator.

        Args:
            min_text_confidence: Threshold below which text is flagged
            min_table_confidence: Threshold below which tables are flagged
            min_page_confidence: Threshold below which pages are flagged for VLM
        """
        self.min_text_confidence = min_text_confidence
        self.min_table_confidence = min_table_confidence
        self.min_page_confidence = min_page_confidence

    def calculate(self, document: SimpleDocument) -> ExtractionConfidence:
        """
        Calculate extraction confidence for a document.

        Args:
            document: Parsed SimpleDocument

        Returns:
            ExtractionConfidence with overall and per-page scores
        """
        # Group content by page
        pages_content = self._group_content_by_page(document)

        # Calculate per-page confidence
        page_confidences = []
        for page_num, content in pages_content.items():
            page_tables = [t for t in document.tables if t.bbox and t.bbox.page == page_num]
            page_figures = [f for f in document.figures if f.bbox and f.bbox.page == page_num]

            page_conf = self._calculate_page_confidence(
                page_num=page_num,
                content_elements=content,
                tables=page_tables,
                figures=page_figures,
            )
            page_confidences.append(page_conf)

        # Handle documents with no page information
        if not page_confidences:
            all_content = document.content
            page_conf = self._calculate_page_confidence(
                page_num=1,
                content_elements=all_content,
                tables=document.tables,
                figures=document.figures,
            )
            page_confidences.append(page_conf)

        # Aggregate scores
        total_pages = len(page_confidences)
        pages_needing_vlm = sum(1 for pc in page_confidences if pc.needs_vlm)

        # Calculate overall scores
        content_score = self._calculate_content_score(document)
        structure_score = self._calculate_structure_score(document)
        table_score = self._calculate_tables_score(document.tables) if document.tables else None
        figure_score = self._calculate_figures_score(document.figures) if document.figures else None

        # Combine into overall score
        scores = [content_score, structure_score]
        weights = [0.5, 0.3]

        if table_score is not None:
            scores.append(table_score)
            weights.append(0.1)

        if figure_score is not None:
            scores.append(figure_score)
            weights.append(0.1)

        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        overall_score = sum(s * w for s, w in zip(scores, weights))

        # Collect all issues
        all_issues = []
        for pc in page_confidences:
            all_issues.extend(pc.issues)

        return ExtractionConfidence(
            overall_score=overall_score,
            content_score=content_score,
            structure_score=structure_score,
            table_score=table_score,
            figure_score=figure_score,
            page_confidences=page_confidences,
            total_pages=total_pages,
            pages_needing_vlm=pages_needing_vlm,
            issues=list(set(all_issues)),  # Deduplicate
        )

    def _group_content_by_page(
        self, document: SimpleDocument
    ) -> dict[int, List[ContentElement]]:
        """Group content elements by page number."""
        pages = {}
        for elem in document.content:
            page_num = elem.bbox.page if elem.bbox else 1
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(elem)
        return pages

    def _calculate_page_confidence(
        self,
        page_num: int,
        content_elements: List[ContentElement],
        tables: List[Table],
        figures: List[Figure],
    ) -> PageConfidence:
        """Calculate confidence for a single page."""
        issues = []

        # Calculate text quality
        text_metrics = self._calculate_text_metrics(content_elements)
        text_score = self._text_metrics_to_score(text_metrics)

        if text_score < self.min_text_confidence:
            issues.append(f"Page {page_num}: Low text quality ({text_score:.2f})")

        # Calculate layout metrics
        layout_metrics = self._calculate_layout_metrics(content_elements)
        layout_score = self._layout_metrics_to_score(layout_metrics)

        if layout_metrics.has_multi_column:
            issues.append(f"Page {page_num}: Multi-column layout detected")
        if layout_metrics.has_overlapping_blocks:
            issues.append(f"Page {page_num}: Overlapping blocks detected")

        # Calculate table score if tables present
        table_score = None
        if tables:
            table_score = self._calculate_tables_score(tables)
            if table_score < self.min_table_confidence:
                issues.append(f"Page {page_num}: Low table confidence ({table_score:.2f})")

        # Calculate figure score if figures present
        figure_score = None
        if figures:
            figure_score = self._calculate_figures_score(figures)

        # Calculate overall page score
        scores = [text_score, layout_score]
        if table_score is not None:
            scores.append(table_score)
        if figure_score is not None:
            scores.append(figure_score)

        overall_score = sum(scores) / len(scores)

        # Determine if page needs VLM
        needs_vlm = overall_score < self.min_page_confidence

        return PageConfidence(
            page_number=page_num,
            text_score=text_score,
            layout_score=layout_score,
            table_score=table_score,
            figure_score=figure_score,
            overall_score=overall_score,
            text_metrics=text_metrics,
            layout_metrics=layout_metrics,
            needs_vlm=needs_vlm,
            issues=issues,
        )

    def _calculate_text_metrics(
        self, content_elements: List[ContentElement]
    ) -> TextQualityMetrics:
        """Calculate text quality metrics from content elements."""
        if not content_elements:
            return TextQualityMetrics(empty_block_ratio=1.0)

        all_text = " ".join(elem.content for elem in content_elements)

        if not all_text.strip():
            return TextQualityMetrics(empty_block_ratio=1.0)

        total_chars = len(all_text)

        # Count character types
        alphanumeric = sum(1 for c in all_text if c.isalnum())
        whitespace = sum(1 for c in all_text if c.isspace())
        replacement = sum(1 for c in all_text if c in self.REPLACEMENT_CHARS)

        alphanumeric_ratio = alphanumeric / total_chars if total_chars > 0 else 0
        whitespace_ratio = whitespace / total_chars if total_chars > 0 else 0
        replacement_ratio = replacement / total_chars if total_chars > 0 else 0

        # Word-level analysis
        words = all_text.split()
        if words:
            avg_word_length = sum(len(w) for w in words) / len(words)
            # Count broken words (single char, isolated punctuation)
            broken = sum(1 for w in words if len(w) == 1 and not w.isalnum())
            broken_word_ratio = broken / len(words)
        else:
            avg_word_length = 0
            broken_word_ratio = 1.0

        # Count empty blocks
        empty_blocks = sum(1 for elem in content_elements if not elem.content.strip())
        empty_block_ratio = empty_blocks / len(content_elements)

        return TextQualityMetrics(
            alphanumeric_ratio=alphanumeric_ratio,
            replacement_char_ratio=replacement_ratio,
            whitespace_ratio=whitespace_ratio,
            avg_word_length=avg_word_length,
            broken_word_ratio=broken_word_ratio,
            empty_block_ratio=empty_block_ratio,
        )

    def _text_metrics_to_score(self, metrics: TextQualityMetrics) -> float:
        """Convert text metrics to confidence score (0-1)."""
        score = 1.0

        # Penalize low alphanumeric ratio (should be > 0.5 for normal text)
        if metrics.alphanumeric_ratio < 0.3:
            score -= 0.4
        elif metrics.alphanumeric_ratio < 0.5:
            score -= 0.2

        # Penalize replacement characters (encoding issues)
        if metrics.replacement_char_ratio > 0.05:
            score -= 0.5
        elif metrics.replacement_char_ratio > 0.01:
            score -= 0.2

        # Penalize very short average word length (OCR artifacts)
        if metrics.avg_word_length < 2:
            score -= 0.3
        elif metrics.avg_word_length < 3:
            score -= 0.1

        # Penalize high broken word ratio
        if metrics.broken_word_ratio > 0.3:
            score -= 0.3
        elif metrics.broken_word_ratio > 0.1:
            score -= 0.1

        # Penalize high empty block ratio
        if metrics.empty_block_ratio > 0.5:
            score -= 0.3
        elif metrics.empty_block_ratio > 0.2:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _calculate_layout_metrics(
        self, content_elements: List[ContentElement]
    ) -> LayoutMetrics:
        """Calculate layout complexity metrics."""
        if not content_elements:
            return LayoutMetrics()

        # Get x positions of elements with bounding boxes
        x_positions = []
        for elem in content_elements:
            if elem.bbox:
                x_positions.append(elem.bbox.x)

        # Calculate x-position variance
        x_variance = 0.0
        if len(x_positions) > 1:
            x_variance = statistics.variance(x_positions)

        # Detect multi-column layout (high x-position variance)
        # Normalize variance by page width (assume 600 points)
        normalized_variance = x_variance / (600 ** 2)
        has_multi_column = normalized_variance > 0.02

        # Count headings
        heading_count = sum(1 for elem in content_elements if elem.type == "heading")

        # Check for overlapping blocks (simplified)
        has_overlapping = self._check_overlapping_blocks(content_elements)

        return LayoutMetrics(
            x_position_variance=x_variance,
            heading_count=heading_count,
            has_multi_column=has_multi_column,
            has_overlapping_blocks=has_overlapping,
        )

    def _check_overlapping_blocks(self, content_elements: List[ContentElement]) -> bool:
        """Check if any content elements have overlapping bounding boxes."""
        elements_with_bbox = [e for e in content_elements if e.bbox]

        for i, elem1 in enumerate(elements_with_bbox):
            for elem2 in elements_with_bbox[i + 1:]:
                if elem1.bbox.page != elem2.bbox.page:
                    continue

                # Check for overlap
                if self._boxes_overlap(elem1.bbox, elem2.bbox):
                    return True

        return False

    def _boxes_overlap(self, box1, box2) -> bool:
        """Check if two bounding boxes overlap."""
        # Box format: x, y, width, height
        x1_min, y1_min = box1.x, box1.y
        x1_max = box1.x + box1.width
        y1_max = box1.y + box1.height

        x2_min, y2_min = box2.x, box2.y
        x2_max = box2.x + box2.width
        y2_max = box2.y + box2.height

        # Check for no overlap
        if x1_max < x2_min or x2_max < x1_min:
            return False
        if y1_max < y2_min or y2_max < y1_min:
            return False

        return True

    def _layout_metrics_to_score(self, metrics: LayoutMetrics) -> float:
        """Convert layout metrics to confidence score."""
        score = 1.0

        # Multi-column layout reduces confidence (harder to extract correctly)
        if metrics.has_multi_column:
            score -= 0.2

        # Overlapping blocks indicate extraction issues
        if metrics.has_overlapping_blocks:
            score -= 0.3

        # Very high image density may mean important content in images
        if metrics.image_density > 0.5:
            score -= 0.2

        return max(0.0, min(1.0, score))

    def _calculate_tables_score(self, tables: List[Table]) -> float:
        """Calculate confidence score for table extraction."""
        if not tables:
            return 1.0

        table_scores = []
        for table in tables:
            score = self._calculate_single_table_score(table)
            table_scores.append(score)

        return sum(table_scores) / len(table_scores)

    def _calculate_single_table_score(self, table: Table) -> float:
        """Calculate confidence for a single table."""
        if not table.rows:
            return 0.3  # Empty table is suspicious

        score = 1.0

        # Check row consistency (all rows same column count)
        col_counts = [len(row) for row in table.rows]
        if col_counts:
            most_common_cols = Counter(col_counts).most_common(1)[0][0]
            consistent_rows = sum(1 for c in col_counts if c == most_common_cols)
            row_consistency = consistent_rows / len(col_counts)

            if row_consistency < 0.8:
                score -= 0.3

        # Check empty cell ratio
        total_cells = sum(len(row) for row in table.rows)
        empty_cells = sum(
            1 for row in table.rows for cell in row
            if not cell or not str(cell).strip()
        )

        if total_cells > 0:
            empty_ratio = empty_cells / total_cells
            if empty_ratio > 0.5:
                score -= 0.3
            elif empty_ratio > 0.3:
                score -= 0.15

        # Check if table has reasonable dimensions
        if len(table.rows) < 2:
            score -= 0.1  # Very small table

        return max(0.0, min(1.0, score))

    def _calculate_figures_score(self, figures: List[Figure]) -> float:
        """Calculate confidence score for figure extraction."""
        if not figures:
            return 1.0

        figure_scores = []
        for figure in figures:
            score = 1.0

            # Having caption increases confidence
            if not figure.caption:
                score -= 0.1

            # Having label increases confidence
            if not figure.label:
                score -= 0.1

            # Valid bbox increases confidence
            if figure.bbox:
                if figure.bbox.width <= 0 or figure.bbox.height <= 0:
                    score -= 0.3

            figure_scores.append(score)

        return sum(figure_scores) / len(figure_scores) if figure_scores else 1.0

    def _calculate_content_score(self, document: SimpleDocument) -> float:
        """Calculate overall content extraction score."""
        if not document.content:
            return 0.3  # No content is suspicious

        all_text = " ".join(elem.content for elem in document.content)

        if len(all_text.strip()) < 50:
            return 0.4  # Very little content

        # Use text metrics for overall content scoring
        text_metrics = self._calculate_text_metrics(document.content)
        return self._text_metrics_to_score(text_metrics)

    def _calculate_structure_score(self, document: SimpleDocument) -> float:
        """Calculate document structure extraction score."""
        score = 1.0

        # Check for headings (well-structured documents have them)
        headings = [e for e in document.content if e.type == "heading"]
        if not headings:
            score -= 0.1

        # Check for metadata
        if not document.metadata.title:
            score -= 0.1

        # Check for reasonable content length distribution
        if document.content:
            lengths = [len(e.content) for e in document.content]
            if lengths:
                avg_length = sum(lengths) / len(lengths)
                if avg_length < 10:
                    score -= 0.2  # Very short elements suggest fragmentation

        return max(0.0, min(1.0, score))


def calculate_confidence(document: SimpleDocument) -> ExtractionConfidence:
    """
    Convenience function to calculate confidence for a document.

    Args:
        document: Parsed SimpleDocument

    Returns:
        ExtractionConfidence with scores and analysis
    """
    calculator = ConfidenceCalculator()
    return calculator.calculate(document)
