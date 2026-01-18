"""
Document parsers for different formats.

This module provides parsers for extracting structured data from various
document formats (PDF, HTML, images, etc.) and converting them to our schemas.
"""

from .pdf_parser import PDFParser
from .html_parser import HTMLParser
from .table_extractor import TableExtractor, TableSettings
from .marker_parser import MarkerParser, MarkerConfig
from .docling_parser import DoclingParser, DoclingConfig
from .vlm_parser import VLMParser, VLMParserWithMCP, create_vlm_parser

# Adaptive parsing (Phase 4)
from .adaptive_config import (
    AdaptivePipelineConfig,
    ParserType,
    EscalationThresholds,
    CategoryThresholds,
    FAST_PIPELINE,
    BALANCED_PIPELINE,
    QUALITY_PIPELINE,
    FULL_PIPELINE,
)
from .adaptive_parser import (
    AdaptivePDFParser,
    AdaptiveResult,
    ParserAttempt,
    parse_pdf_adaptive,
)
from .confidence_calculator import ConfidenceCalculator, calculate_confidence

__all__ = [
    # Existing parsers
    "PDFParser",
    "HTMLParser",
    "TableExtractor",
    "TableSettings",
    "MarkerParser",
    "MarkerConfig",
    "DoclingParser",
    "DoclingConfig",
    "VLMParser",
    "VLMParserWithMCP",
    "create_vlm_parser",
    # Adaptive parsing (Phase 4)
    "AdaptivePDFParser",
    "AdaptiveResult",
    "ParserAttempt",
    "AdaptivePipelineConfig",
    "ParserType",
    "EscalationThresholds",
    "CategoryThresholds",
    "FAST_PIPELINE",
    "BALANCED_PIPELINE",
    "QUALITY_PIPELINE",
    "FULL_PIPELINE",
    "ConfidenceCalculator",
    "calculate_confidence",
    "parse_pdf_adaptive",
]
