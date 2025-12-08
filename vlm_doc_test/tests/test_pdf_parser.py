"""
Tests for PDF parser.
"""

import pytest
from ..parsers import PDFParser
from ..schemas.base import DocumentFormat, DocumentCategory


def test_pdf_parser_basic(sample_pdf):
    """Test basic PDF parsing functionality."""
    parser = PDFParser()
    doc = parser.parse(str(sample_pdf))

    assert doc.id == "sample"
    assert doc.format == DocumentFormat.PDF
    assert doc.metadata.title == "Sample Document"
    assert len(doc.metadata.authors) == 1
    assert doc.metadata.authors[0].name == "Test Author"


def test_pdf_parser_content_extraction(sample_pdf):
    """Test content element extraction."""
    parser = PDFParser()
    doc = parser.parse(str(sample_pdf))

    assert len(doc.content) > 0

    # Check for headings
    headings = [c for c in doc.content if c.type == "heading"]
    assert len(headings) > 0

    # Check for paragraphs
    paragraphs = [c for c in doc.content if c.type == "paragraph"]
    assert len(paragraphs) > 0


def test_pdf_parser_bounding_boxes(sample_pdf):
    """Test bounding box extraction."""
    parser = PDFParser()
    doc = parser.parse(str(sample_pdf))

    # All content elements should have bounding boxes
    for element in doc.content:
        assert element.bbox is not None
        assert element.bbox.page >= 1
        assert element.bbox.x >= 0
        assert element.bbox.y >= 0
        assert element.bbox.width > 0
        assert element.bbox.height > 0


def test_pdf_parser_page_count(sample_pdf):
    """Test page count utility."""
    parser = PDFParser()
    count = parser.get_page_count(str(sample_pdf))

    assert count >= 1


def test_pdf_parser_single_page(sample_pdf):
    """Test single page text extraction."""
    parser = PDFParser()
    text = parser.extract_page_text(str(sample_pdf), 1)

    assert len(text) > 0
    assert "Sample Document" in text


def test_pdf_parser_category(sample_pdf):
    """Test category assignment."""
    parser = PDFParser()
    doc = parser.parse(
        str(sample_pdf),
        category=DocumentCategory.ACADEMIC_PAPER,
    )

    assert doc.category == DocumentCategory.ACADEMIC_PAPER


def test_pdf_parser_json_serialization(sample_pdf):
    """Test JSON serialization."""
    parser = PDFParser()
    doc = parser.parse(str(sample_pdf))

    json_output = doc.model_dump_json()
    assert len(json_output) > 0
    assert "Sample Document" in json_output
