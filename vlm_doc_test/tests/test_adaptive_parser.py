"""
Tests for the adaptive PDF parser.

Tests confidence calculation, escalation logic, and adaptive parsing behavior.
"""

import pytest
from pathlib import Path
from datetime import datetime
import pymupdf as fitz

from ..schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Table,
    Figure,
    Author,
)
from ..schemas.base import DocumentFormat, DocumentCategory, BoundingBox
from ..schemas.confidence import (
    ConfidenceLevel,
    TextQualityMetrics,
    LayoutMetrics,
    PageConfidence,
    ExtractionConfidence,
)
from ..parsers.confidence_calculator import ConfidenceCalculator, calculate_confidence
from ..parsers.adaptive_config import (
    AdaptivePipelineConfig,
    ParserType,
    EscalationThresholds,
    CategoryThresholds,
    FAST_PIPELINE,
    BALANCED_PIPELINE,
    QUALITY_PIPELINE,
    FULL_PIPELINE,
)
from ..parsers.adaptive_parser import (
    AdaptivePDFParser,
    AdaptiveResult,
    ParserAttempt,
    parse_pdf_adaptive,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def simple_pdf(tmp_path):
    """Create a simple, well-formed PDF for testing."""
    pdf_path = tmp_path / "simple.pdf"

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Add title
    page.insert_text((50, 50), "Test Document Title", fontsize=24, fontname="helv")

    # Add heading
    page.insert_text((50, 100), "Section 1: Introduction", fontsize=16, fontname="helv")

    # Add paragraph
    page.insert_textbox(
        fitz.Rect(50, 130, 545, 200),
        "This is a well-formed test document with clear structure. "
        "It contains multiple paragraphs of text that should be easy to extract.",
        fontsize=12,
        fontname="helv",
    )

    # Add another paragraph
    page.insert_textbox(
        fitz.Rect(50, 220, 545, 290),
        "The parser should be able to extract this content with high confidence "
        "because it uses standard fonts and simple layout.",
        fontsize=12,
        fontname="helv",
    )

    doc.set_metadata({
        "title": "Test Document Title",
        "author": "Test Author",
    })

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


@pytest.fixture
def multi_page_pdf(tmp_path):
    """Create a multi-page PDF for testing per-page confidence."""
    pdf_path = tmp_path / "multipage.pdf"

    doc = fitz.open()

    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), f"Page {i + 1}", fontsize=20, fontname="helv")
        page.insert_textbox(
            fitz.Rect(50, 80, 545, 150),
            f"This is content on page {i + 1}. It contains regular text.",
            fontsize=12,
            fontname="helv",
        )

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


@pytest.fixture
def well_formed_document():
    """Create a well-formed SimpleDocument for testing confidence calculation."""
    return SimpleDocument(
        id="test-well-formed",
        format=DocumentFormat.PDF,
        category=DocumentCategory.TECHNICAL_DOCUMENTATION,
        source=DocumentSource(
            file_path="/test/path.pdf",
            accessed_at=datetime.now(),
        ),
        metadata=DocumentMetadata(
            title="Well-Formed Document",
            authors=[Author(name="Test Author")],
            keywords=["test", "document"],
        ),
        content=[
            ContentElement(
                id="h1",
                type="heading",
                content="Introduction",
                level=1,
                bbox=BoundingBox(page=1, x=50, y=50, width=500, height=30),
            ),
            ContentElement(
                id="p1",
                type="paragraph",
                content="This is a well-formed paragraph with clear, readable text that should "
                        "be easy to parse and extract. It contains multiple sentences.",
                bbox=BoundingBox(page=1, x=50, y=90, width=500, height=60),
            ),
            ContentElement(
                id="p2",
                type="paragraph",
                content="Another paragraph with good quality content that demonstrates "
                        "proper document structure and formatting.",
                bbox=BoundingBox(page=1, x=50, y=160, width=500, height=60),
            ),
        ],
        tables=[
            Table(
                id="t1",
                caption="Sample Data",
                rows=[
                    ["Header 1", "Header 2", "Header 3"],
                    ["Value A", "Value B", "Value C"],
                    ["Value D", "Value E", "Value F"],
                ],
            ),
        ],
    )


@pytest.fixture
def poor_quality_document():
    """Create a poor quality SimpleDocument for testing low confidence detection."""
    return SimpleDocument(
        id="test-poor-quality",
        format=DocumentFormat.PDF,
        source=DocumentSource(
            file_path="/test/poor.pdf",
            accessed_at=datetime.now(),
        ),
        metadata=DocumentMetadata(),  # Missing title
        content=[
            ContentElement(
                id="c1",
                type="paragraph",
                content="",  # Empty content
                bbox=BoundingBox(page=1, x=50, y=50, width=100, height=20),
            ),
            ContentElement(
                id="c2",
                type="paragraph",
                content="x y z ! @ # $ % ^",  # Broken text/OCR artifacts
                bbox=BoundingBox(page=1, x=50, y=80, width=100, height=20),
            ),
            ContentElement(
                id="c3",
                type="paragraph",
                content="\ufffd\ufffd\ufffd test \ufffd\ufffd",  # Encoding issues
                bbox=BoundingBox(page=1, x=50, y=110, width=100, height=20),
            ),
        ],
        tables=[
            Table(
                id="t1",
                rows=[
                    ["", "", ""],
                    ["", "x", ""],
                    ["", "", ""],
                ],
            ),
        ],
    )


# =============================================================================
# Tests for ConfidenceLevel
# =============================================================================

class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum and from_score method."""

    def test_from_score_high(self):
        assert ConfidenceLevel.from_score(0.90) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.85) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(1.0) == ConfidenceLevel.HIGH

    def test_from_score_medium(self):
        assert ConfidenceLevel.from_score(0.75) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.70) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.84) == ConfidenceLevel.MEDIUM

    def test_from_score_low(self):
        assert ConfidenceLevel.from_score(0.60) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.50) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.69) == ConfidenceLevel.LOW

    def test_from_score_very_low(self):
        assert ConfidenceLevel.from_score(0.40) == ConfidenceLevel.VERY_LOW
        assert ConfidenceLevel.from_score(0.0) == ConfidenceLevel.VERY_LOW
        assert ConfidenceLevel.from_score(0.49) == ConfidenceLevel.VERY_LOW


# =============================================================================
# Tests for ConfidenceCalculator
# =============================================================================

class TestConfidenceCalculator:
    """Tests for the confidence calculator."""

    def test_calculate_well_formed_document(self, well_formed_document):
        """Well-formed documents should have high confidence."""
        calculator = ConfidenceCalculator()
        confidence = calculator.calculate(well_formed_document)

        assert confidence.overall_score >= 0.7
        assert confidence.content_score >= 0.7
        assert confidence.level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
        assert len(confidence.page_confidences) > 0

    def test_calculate_poor_quality_document(self, poor_quality_document):
        """Poor quality documents should have low confidence."""
        calculator = ConfidenceCalculator()
        confidence = calculator.calculate(poor_quality_document)

        assert confidence.overall_score < 0.7
        assert confidence.level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]

    def test_calculate_empty_document(self):
        """Empty documents should have very low confidence."""
        empty_doc = SimpleDocument(
            id="empty",
            format=DocumentFormat.PDF,
            source=DocumentSource(
                file_path="/test/empty.pdf",
                accessed_at=datetime.now(),
            ),
            metadata=DocumentMetadata(),
            content=[],
        )

        calculator = ConfidenceCalculator()
        confidence = calculator.calculate(empty_doc)

        assert confidence.overall_score < 0.5
        assert confidence.content_score < 0.5

    def test_text_metrics_good_text(self):
        """Good text should produce high text quality score."""
        calculator = ConfidenceCalculator()

        good_content = [
            ContentElement(
                id="p1",
                type="paragraph",
                content="This is a well-written paragraph with proper words and sentences.",
            ),
        ]

        metrics = calculator._calculate_text_metrics(good_content)
        score = calculator._text_metrics_to_score(metrics)

        assert metrics.alphanumeric_ratio > 0.5
        assert metrics.replacement_char_ratio == 0
        assert metrics.avg_word_length > 3
        assert score >= 0.8

    def test_text_metrics_encoding_issues(self):
        """Text with encoding issues should have lower score."""
        calculator = ConfidenceCalculator()

        bad_content = [
            ContentElement(
                id="p1",
                type="paragraph",
                content="Test \ufffd\ufffd\ufffd more \ufffd text",
            ),
        ]

        metrics = calculator._calculate_text_metrics(bad_content)
        score = calculator._text_metrics_to_score(metrics)

        assert metrics.replacement_char_ratio > 0
        assert score < 0.8

    def test_table_confidence_good_table(self):
        """Good tables should have high confidence."""
        calculator = ConfidenceCalculator()

        good_tables = [
            Table(
                id="t1",
                rows=[
                    ["A", "B", "C"],
                    ["1", "2", "3"],
                    ["4", "5", "6"],
                ],
            ),
        ]

        score = calculator._calculate_tables_score(good_tables)
        assert score >= 0.7

    def test_table_confidence_empty_cells(self):
        """Tables with many empty cells should have lower confidence."""
        calculator = ConfidenceCalculator()

        sparse_tables = [
            Table(
                id="t1",
                rows=[
                    ["", "", ""],
                    ["x", "", ""],
                    ["", "", "y"],
                ],
            ),
        ]

        score = calculator._calculate_tables_score(sparse_tables)
        assert score < 0.9

    def test_page_confidence_tracking(self, well_formed_document):
        """Should correctly track per-page confidence."""
        calculator = ConfidenceCalculator()
        confidence = calculator.calculate(well_formed_document)

        assert confidence.total_pages >= 1
        assert len(confidence.page_confidences) >= 1
        assert all(pc.page_number >= 1 for pc in confidence.page_confidences)


# =============================================================================
# Tests for EscalationThresholds
# =============================================================================

class TestEscalationThresholds:
    """Tests for escalation threshold logic."""

    def test_should_escalate_below_overall(self):
        """Should escalate when overall score is below threshold."""
        thresholds = EscalationThresholds(min_overall_confidence=0.70)
        assert thresholds.should_escalate(overall_score=0.65) is True
        assert thresholds.should_escalate(overall_score=0.75) is False

    def test_should_escalate_below_content(self):
        """Should escalate when content score is below threshold."""
        thresholds = EscalationThresholds(min_content_confidence=0.75)
        assert thresholds.should_escalate(overall_score=0.80, content_score=0.70) is True
        assert thresholds.should_escalate(overall_score=0.80, content_score=0.80) is False

    def test_should_escalate_below_table(self):
        """Should escalate when table score is below threshold."""
        thresholds = EscalationThresholds(min_table_confidence=0.65)
        assert thresholds.should_escalate(overall_score=0.80, table_score=0.60) is True
        assert thresholds.should_escalate(overall_score=0.80, table_score=0.70) is False

    def test_should_not_escalate_none_scores(self):
        """Should not escalate based on None scores."""
        thresholds = EscalationThresholds()
        # None scores should not trigger escalation
        assert thresholds.should_escalate(
            overall_score=0.80,
            content_score=None,
            table_score=None,
        ) is False


# =============================================================================
# Tests for CategoryThresholds
# =============================================================================

class TestCategoryThresholds:
    """Tests for category-specific threshold selection."""

    def test_get_academic_paper_thresholds(self):
        """Academic papers should have stricter thresholds."""
        category_thresholds = CategoryThresholds()
        thresholds = category_thresholds.get_for_category(DocumentCategory.ACADEMIC_PAPER)

        assert thresholds.min_table_confidence >= 0.70
        assert thresholds.min_content_confidence >= 0.75

    def test_get_plot_thresholds(self):
        """Plots should have very high figure thresholds."""
        category_thresholds = CategoryThresholds()
        thresholds = category_thresholds.get_for_category(DocumentCategory.PLOT_VISUALIZATION)

        assert thresholds.min_figure_confidence >= 0.85

    def test_get_blog_thresholds(self):
        """Blog posts should have more lenient thresholds."""
        category_thresholds = CategoryThresholds()
        thresholds = category_thresholds.get_for_category(DocumentCategory.BLOG_POST)

        assert thresholds.min_overall_confidence <= 0.70

    def test_get_default_for_unknown(self):
        """Unknown categories should use default thresholds."""
        category_thresholds = CategoryThresholds()
        thresholds = category_thresholds.get_for_category(DocumentCategory.OTHER)

        assert thresholds == category_thresholds.default


# =============================================================================
# Tests for AdaptivePipelineConfig
# =============================================================================

class TestAdaptivePipelineConfig:
    """Tests for pipeline configuration."""

    def test_default_pipeline_order(self):
        """Default pipeline should include all parsers in correct order."""
        config = FULL_PIPELINE
        assert ParserType.PYMUPDF in config.pipeline_order
        assert ParserType.VLM in config.pipeline_order
        # PyMuPDF should come before VLM
        pymupdf_idx = config.pipeline_order.index(ParserType.PYMUPDF)
        vlm_idx = config.pipeline_order.index(ParserType.VLM)
        assert pymupdf_idx < vlm_idx

    def test_fast_pipeline(self):
        """Fast pipeline should only include PyMuPDF."""
        config = FAST_PIPELINE
        assert config.pipeline_order == [ParserType.PYMUPDF]
        assert config.enable_hybrid_extraction is False

    def test_balanced_pipeline(self):
        """Balanced pipeline should include PyMuPDF and Marker."""
        config = BALANCED_PIPELINE
        assert ParserType.PYMUPDF in config.pipeline_order
        assert ParserType.MARKER in config.pipeline_order
        assert ParserType.VLM not in config.pipeline_order

    def test_limit_to_parser(self):
        """Should correctly limit pipeline to specified parser."""
        config = FULL_PIPELINE.limit_to_parser(ParserType.MARKER)

        assert ParserType.PYMUPDF in config.pipeline_order
        assert ParserType.MARKER in config.pipeline_order
        assert ParserType.DOCLING not in config.pipeline_order
        assert ParserType.VLM not in config.pipeline_order

    def test_get_thresholds_with_category(self):
        """Should return category-specific thresholds."""
        config = AdaptivePipelineConfig()

        academic_thresholds = config.get_thresholds(DocumentCategory.ACADEMIC_PAPER)
        default_thresholds = config.get_thresholds(None)

        # Academic should be stricter
        assert academic_thresholds.min_content_confidence >= default_thresholds.min_content_confidence


# =============================================================================
# Tests for AdaptivePDFParser
# =============================================================================

class TestAdaptivePDFParser:
    """Tests for the main adaptive parser."""

    def test_parse_simple_pdf(self, simple_pdf):
        """Should parse a simple PDF successfully with PyMuPDF only."""
        parser = AdaptivePDFParser(config=FAST_PIPELINE)
        result = parser.parse(simple_pdf)

        assert result is not None
        assert result.document is not None
        assert result.confidence is not None
        assert result.final_parser == ParserType.PYMUPDF
        assert len(result.attempts) >= 1

    def test_parse_with_category(self, simple_pdf):
        """Should apply category-specific thresholds."""
        parser = AdaptivePDFParser(config=FAST_PIPELINE)
        result = parser.parse(simple_pdf, category=DocumentCategory.BLOG_POST)

        assert result is not None
        assert result.document.category == DocumentCategory.BLOG_POST

    def test_parse_nonexistent_file(self, tmp_path):
        """Should raise error for non-existent file."""
        parser = AdaptivePDFParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "nonexistent.pdf")

    def test_parser_attempt_summary(self, simple_pdf):
        """ParserAttempt summary should contain expected fields."""
        parser = AdaptivePDFParser(config=FAST_PIPELINE)
        result = parser.parse(simple_pdf)

        assert len(result.attempts) >= 1
        summary = result.attempts[0].summary()

        assert "parser" in summary
        assert "success" in summary
        assert "duration_seconds" in summary
        assert summary["success"] is True

    def test_result_summary(self, simple_pdf):
        """AdaptiveResult summary should contain expected fields."""
        parser = AdaptivePDFParser(config=FAST_PIPELINE)
        result = parser.parse(simple_pdf)

        summary = result.summary()

        assert "final_parser" in summary
        assert "confidence" in summary
        assert "total_duration_seconds" in summary
        assert "attempts" in summary

    def test_get_parser_info(self):
        """Should return parser configuration info."""
        parser = AdaptivePDFParser(config=BALANCED_PIPELINE)
        info = parser.get_parser_info()

        assert "pipeline_order" in info
        assert "thresholds" in info
        assert "hybrid_enabled" in info

    def test_max_escalation_level(self, simple_pdf):
        """Should respect max_escalation_level parameter."""
        # Use FULL_PIPELINE but limit to PYMUPDF
        parser = AdaptivePDFParser(config=FULL_PIPELINE)
        result = parser.parse(simple_pdf, max_escalation_level=ParserType.PYMUPDF)

        # Should only try PyMuPDF
        assert all(a.parser_type == ParserType.PYMUPDF for a in result.attempts)


# =============================================================================
# Tests for convenience function
# =============================================================================

class TestParseAdaptiveFunction:
    """Tests for the parse_pdf_adaptive convenience function."""

    def test_basic_usage(self, simple_pdf):
        """Should work with basic usage."""
        result = parse_pdf_adaptive(simple_pdf)

        assert result is not None
        assert result.document is not None
        assert result.confidence is not None

    def test_with_category(self, simple_pdf):
        """Should work with category parameter."""
        result = parse_pdf_adaptive(
            simple_pdf,
            category=DocumentCategory.TECHNICAL_DOCUMENTATION
        )

        assert result is not None
        assert result.document.category == DocumentCategory.TECHNICAL_DOCUMENTATION

    def test_with_custom_config(self, simple_pdf):
        """Should work with custom config."""
        result = parse_pdf_adaptive(
            simple_pdf,
            config=FAST_PIPELINE
        )

        assert result is not None
        assert result.final_parser == ParserType.PYMUPDF


# =============================================================================
# Tests for ExtractionConfidence
# =============================================================================

class TestExtractionConfidence:
    """Tests for ExtractionConfidence model."""

    def test_vlm_page_ratio_calculation(self):
        """Should correctly calculate VLM page ratio."""
        confidence = ExtractionConfidence(
            total_pages=10,
            pages_needing_vlm=3,
            page_confidences=[],
        )

        assert confidence.vlm_page_ratio == 0.3

    def test_vlm_page_ratio_empty(self):
        """Should handle zero pages."""
        confidence = ExtractionConfidence(
            total_pages=0,
            pages_needing_vlm=0,
            page_confidences=[],
        )

        assert confidence.vlm_page_ratio == 0.0

    def test_needs_full_vlm_threshold(self):
        """Should correctly detect when full VLM is needed."""
        low_ratio = ExtractionConfidence(
            total_pages=10,
            pages_needing_vlm=2,  # 20%
            page_confidences=[],
        )
        assert low_ratio.needs_full_vlm is False

        high_ratio = ExtractionConfidence(
            total_pages=10,
            pages_needing_vlm=4,  # 40%
            page_confidences=[],
        )
        assert high_ratio.needs_full_vlm is True

    def test_get_vlm_pages(self):
        """Should return correct list of pages needing VLM."""
        page_confidences = [
            PageConfidence(page_number=1, overall_score=0.9, needs_vlm=False),
            PageConfidence(page_number=2, overall_score=0.5, needs_vlm=True),
            PageConfidence(page_number=3, overall_score=0.8, needs_vlm=False),
            PageConfidence(page_number=4, overall_score=0.4, needs_vlm=True),
        ]

        confidence = ExtractionConfidence(
            total_pages=4,
            pages_needing_vlm=2,
            page_confidences=page_confidences,
        )

        vlm_pages = confidence.get_vlm_pages()
        assert vlm_pages == [2, 4]

    def test_summary_method(self):
        """Summary should contain all expected fields."""
        confidence = ExtractionConfidence(
            overall_score=0.75,
            total_pages=5,
            pages_needing_vlm=1,
            issues=["Test issue"],
            page_confidences=[],
        )

        summary = confidence.summary()

        assert "overall_score" in summary
        assert "level" in summary
        assert "total_pages" in summary
        assert "pages_needing_vlm" in summary
        assert "needs_full_vlm" in summary
        assert "issues" in summary
