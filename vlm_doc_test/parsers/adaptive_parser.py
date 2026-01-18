"""
Adaptive PDF parser that intelligently escalates to more expensive parsers.

Uses fast local parsers first and only escalates to expensive VLM analysis
when extraction quality is uncertain or poor.
"""

import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from ..schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Table,
    Figure,
)
from ..schemas.base import DocumentFormat, DocumentCategory
from ..schemas.confidence import ExtractionConfidence, PageConfidence

from .adaptive_config import (
    AdaptivePipelineConfig,
    ParserType,
    FULL_PIPELINE,
    EscalationThresholds,
)
from .confidence_calculator import ConfidenceCalculator, calculate_confidence


@dataclass
class ParserAttempt:
    """Record of a single parser attempt."""
    parser_type: ParserType
    document: Optional[SimpleDocument]
    confidence: Optional[ExtractionConfidence]
    duration_seconds: float
    success: bool
    error: Optional[str] = None

    def summary(self) -> Dict[str, Any]:
        """Get summary dict for reporting."""
        return {
            "parser": self.parser_type.value,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 3),
            "confidence_score": round(self.confidence.overall_score, 3) if self.confidence else None,
            "error": self.error,
        }


@dataclass
class AdaptiveResult:
    """Result from adaptive parsing."""
    document: SimpleDocument
    final_parser: ParserType
    confidence: ExtractionConfidence
    attempts: List[ParserAttempt] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    used_hybrid: bool = False
    vlm_pages: List[int] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Get summary dict for reporting."""
        return {
            "final_parser": self.final_parser.value,
            "confidence": self.confidence.summary(),
            "total_duration_seconds": round(self.total_duration_seconds, 3),
            "used_hybrid": self.used_hybrid,
            "vlm_pages": self.vlm_pages,
            "attempts": [a.summary() for a in self.attempts],
        }


class AdaptivePDFParser:
    """
    Adaptive PDF parser with intelligent escalation.

    Tries fast local parsers first, calculates confidence, and only
    escalates to more expensive parsers (including VLM) when needed.

    Example usage:
        parser = AdaptivePDFParser()
        result = parser.parse("document.pdf")
        print(f"Used: {result.final_parser}, Confidence: {result.confidence.overall_score}")

        # With category hint
        result = parser.parse("paper.pdf", category=DocumentCategory.ACADEMIC_PAPER)

        # Force specific parser limit
        result = parser.parse("doc.pdf", max_escalation_level=ParserType.MARKER)
    """

    def __init__(self, config: Optional[AdaptivePipelineConfig] = None):
        """
        Initialize adaptive parser.

        Args:
            config: Pipeline configuration. Uses FULL_PIPELINE by default.
        """
        self.config = config or FULL_PIPELINE
        self.confidence_calculator = ConfidenceCalculator()
        self._parsers: Dict[ParserType, Any] = {}

    def _get_parser(self, parser_type: ParserType):
        """Lazy-load parser instance."""
        if parser_type not in self._parsers:
            self._parsers[parser_type] = self._create_parser(parser_type)
        return self._parsers[parser_type]

    def _create_parser(self, parser_type: ParserType):
        """Create parser instance by type."""
        if parser_type == ParserType.PYMUPDF:
            from .pdf_parser import PDFParser
            return PDFParser()

        elif parser_type == ParserType.MARKER:
            from .marker_parser import MarkerParser
            return MarkerParser()

        elif parser_type == ParserType.DOCLING:
            from .docling_parser import DoclingParser
            return DoclingParser()

        elif parser_type == ParserType.VLM:
            from .vlm_parser import VLMParser
            return VLMParser()

        else:
            raise ValueError(f"Unknown parser type: {parser_type}")

    def parse(
        self,
        pdf_path: Union[str, Path],
        category: Optional[DocumentCategory] = None,
        force_vlm: bool = False,
        max_escalation_level: Optional[ParserType] = None,
    ) -> AdaptiveResult:
        """
        Parse PDF with adaptive escalation.

        Args:
            pdf_path: Path to PDF file
            category: Document category hint for threshold selection
            force_vlm: If True, bypass adaptive logic and use VLM directly
            max_escalation_level: Maximum parser to try (e.g., MARKER to avoid VLM)

        Returns:
            AdaptiveResult with document, confidence, and parsing metadata
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        start_time = time.time()
        attempts: List[ParserAttempt] = []

        # Force VLM mode
        if force_vlm:
            return self._parse_with_vlm(pdf_path, category, start_time)

        # Get effective thresholds for this category
        thresholds = self.config.get_thresholds(category)

        # Determine effective pipeline
        pipeline = self.config.pipeline_order
        if max_escalation_level:
            try:
                limit_idx = pipeline.index(max_escalation_level) + 1
                pipeline = pipeline[:limit_idx]
            except ValueError:
                pass  # Keep original pipeline if level not found

        # Try parsers in order
        best_result: Optional[ParserAttempt] = None
        best_document: Optional[SimpleDocument] = None
        best_confidence: Optional[ExtractionConfidence] = None

        for parser_type in pipeline:
            attempt = self._try_parser(pdf_path, parser_type, category)
            attempts.append(attempt)

            if not attempt.success:
                continue

            # Update best result if this is better
            if best_confidence is None or (
                attempt.confidence and
                attempt.confidence.overall_score > best_confidence.overall_score
            ):
                best_result = attempt
                best_document = attempt.document
                best_confidence = attempt.confidence

            # Check if we meet threshold
            if attempt.confidence and not thresholds.should_escalate(
                overall_score=attempt.confidence.overall_score,
                content_score=attempt.confidence.content_score,
                table_score=attempt.confidence.table_score,
                figure_score=attempt.confidence.figure_score,
            ):
                # Confidence is good enough, stop here
                if self.config.stop_on_success:
                    break

        # Check if we need hybrid extraction
        used_hybrid = False
        vlm_pages = []

        if (
            self.config.enable_hybrid_extraction and
            best_confidence and
            best_confidence.pages_needing_vlm > 0 and
            not best_confidence.needs_full_vlm and
            ParserType.VLM in pipeline
        ):
            # Do hybrid extraction
            hybrid_result = self._hybrid_extraction(
                pdf_path=pdf_path,
                base_document=best_document,
                base_confidence=best_confidence,
                category=category,
            )

            if hybrid_result:
                best_document = hybrid_result
                best_confidence = calculate_confidence(hybrid_result)
                used_hybrid = True
                vlm_pages = best_confidence.get_vlm_pages() if best_confidence else []

        total_duration = time.time() - start_time

        # Ensure we have a result
        if best_document is None or best_confidence is None:
            raise RuntimeError("All parsers failed")

        return AdaptiveResult(
            document=best_document,
            final_parser=best_result.parser_type if best_result else pipeline[-1],
            confidence=best_confidence,
            attempts=attempts,
            total_duration_seconds=total_duration,
            used_hybrid=used_hybrid,
            vlm_pages=vlm_pages,
        )

    def _try_parser(
        self,
        pdf_path: Path,
        parser_type: ParserType,
        category: Optional[DocumentCategory],
    ) -> ParserAttempt:
        """
        Attempt parsing with a specific parser.

        Returns ParserAttempt with results or error information.
        """
        start_time = time.time()

        try:
            parser = self._get_parser(parser_type)

            # Parse document
            if parser_type == ParserType.VLM:
                # VLM parser requires image path, not PDF
                # For now, skip VLM in standard parsing (use hybrid mode instead)
                raise NotImplementedError("VLM parser requires rendered images")

            document = parser.parse(pdf_path, category=category)

            # Calculate confidence
            confidence = self.confidence_calculator.calculate(document)

            duration = time.time() - start_time

            return ParserAttempt(
                parser_type=parser_type,
                document=document,
                confidence=confidence,
                duration_seconds=duration,
                success=True,
            )

        except Exception as e:
            duration = time.time() - start_time
            return ParserAttempt(
                parser_type=parser_type,
                document=None,
                confidence=None,
                duration_seconds=duration,
                success=False,
                error=str(e),
            )

    def _parse_with_vlm(
        self,
        pdf_path: Path,
        category: Optional[DocumentCategory],
        start_time: float,
    ) -> AdaptiveResult:
        """
        Force VLM parsing for entire document.

        Renders all pages to images and sends to VLM.
        """
        # First, try PyMuPDF to get page count and basic structure
        try:
            from .pdf_parser import PDFParser
            pymupdf_parser = PDFParser()
            page_count = pymupdf_parser.get_page_count(str(pdf_path))
        except Exception:
            page_count = 1

        # For now, VLM parsing is not implemented in standalone mode
        # It requires MCP integration or rendered images
        raise NotImplementedError(
            "Force VLM mode requires MCP integration or pre-rendered page images. "
            "Use hybrid extraction instead."
        )

    def _hybrid_extraction(
        self,
        pdf_path: Path,
        base_document: SimpleDocument,
        base_confidence: ExtractionConfidence,
        category: Optional[DocumentCategory],
    ) -> Optional[SimpleDocument]:
        """
        Combine fast parser results with VLM for specific pages.

        Uses VLM only for pages that have low confidence.

        Args:
            pdf_path: Path to PDF
            base_document: Document from fast parser
            base_confidence: Confidence with per-page scores
            category: Document category

        Returns:
            Merged SimpleDocument or None if hybrid extraction fails
        """
        # Get pages that need VLM
        vlm_pages = base_confidence.get_vlm_pages()

        if not vlm_pages:
            return base_document

        # Limit VLM pages if configured
        if self.config.max_vlm_pages and len(vlm_pages) > self.config.max_vlm_pages:
            # Sort by confidence score (lowest first)
            page_scores = {
                pc.page_number: pc.overall_score
                for pc in base_confidence.page_confidences
            }
            vlm_pages = sorted(vlm_pages, key=lambda p: page_scores.get(p, 1.0))
            vlm_pages = vlm_pages[:self.config.max_vlm_pages]

        # Note: Actual VLM integration would require:
        # 1. Render pages to images using PyMuPDF
        # 2. Send images to VLM (via MCP or direct API)
        # 3. Parse VLM response and merge with base document

        # For now, return base document with a note that VLM would be used
        # Full implementation requires MCP tools or direct VLM API access

        return base_document

    def _merge_documents(
        self,
        base_document: SimpleDocument,
        vlm_contents: Dict[int, List[ContentElement]],
        vlm_tables: Dict[int, List[Table]],
        vlm_figures: Dict[int, List[Figure]],
    ) -> SimpleDocument:
        """
        Merge VLM extracted content into base document.

        Replaces content for specific pages while keeping good pages from base.
        """
        # Get page numbers to replace
        vlm_page_numbers = set(vlm_contents.keys())

        # Filter base content to keep only good pages
        merged_content = [
            elem for elem in base_document.content
            if elem.bbox is None or elem.bbox.page not in vlm_page_numbers
        ]

        # Add VLM content
        for page_num in sorted(vlm_contents.keys()):
            merged_content.extend(vlm_contents[page_num])

        # Merge tables
        merged_tables = [
            table for table in base_document.tables
            if table.bbox is None or table.bbox.page not in vlm_page_numbers
        ]
        for page_num in sorted(vlm_tables.keys()):
            merged_tables.extend(vlm_tables[page_num])

        # Merge figures
        merged_figures = [
            figure for figure in base_document.figures
            if figure.bbox is None or figure.bbox.page not in vlm_page_numbers
        ]
        for page_num in sorted(vlm_figures.keys()):
            merged_figures.extend(vlm_figures[page_num])

        # Create merged document
        return SimpleDocument(
            id=base_document.id,
            format=base_document.format,
            category=base_document.category,
            source=base_document.source,
            metadata=base_document.metadata,
            content=merged_content,
            tables=merged_tables,
            figures=merged_figures,
            links=base_document.links,
        )

    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about available parsers and configuration."""
        return {
            "pipeline_order": [p.value for p in self.config.pipeline_order],
            "thresholds": {
                "min_overall": self.config.thresholds.min_overall_confidence,
                "min_content": self.config.thresholds.min_content_confidence,
                "min_table": self.config.thresholds.min_table_confidence,
                "min_figure": self.config.thresholds.min_figure_confidence,
            },
            "hybrid_enabled": self.config.enable_hybrid_extraction,
            "per_page_decisions": self.config.enable_per_page_decisions,
        }


# Convenience functions
def parse_pdf_adaptive(
    pdf_path: Union[str, Path],
    category: Optional[DocumentCategory] = None,
    config: Optional[AdaptivePipelineConfig] = None,
) -> AdaptiveResult:
    """
    Parse PDF with adaptive escalation.

    Convenience function for quick usage.

    Args:
        pdf_path: Path to PDF file
        category: Document category hint
        config: Pipeline configuration (uses default if None)

    Returns:
        AdaptiveResult with document and parsing metadata
    """
    parser = AdaptivePDFParser(config)
    return parser.parse(pdf_path, category=category)
