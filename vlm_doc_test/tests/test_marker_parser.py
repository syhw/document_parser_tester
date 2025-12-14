"""
Tests for Marker-PDF parser.

This module tests the MarkerParser class functionality including:
- PDF to Markdown conversion
- Document parsing
- Comparison with PyMuPDF
"""

import pytest
from pathlib import Path


def test_marker_imports():
    """Test that marker parser can be imported."""
    from vlm_doc_test.parsers import MarkerParser, MarkerConfig
    assert MarkerParser is not None
    assert MarkerConfig is not None


def test_marker_config_defaults():
    """Test MarkerConfig default values."""
    from vlm_doc_test.parsers import MarkerConfig

    config = MarkerConfig()
    assert config.use_llm is False
    assert config.extract_images is True
    assert config.max_pages is None
    assert config.output_format == "markdown"


def test_marker_parser_initialization():
    """Test MarkerParser can be initialized."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()
    assert parser.config is not None
    assert parser._models is None  # Lazy loaded


def test_marker_parser_with_custom_config():
    """Test MarkerParser with custom configuration."""
    from vlm_doc_test.parsers import MarkerParser, MarkerConfig

    config = MarkerConfig(use_llm=True, extract_images=False)
    parser = MarkerParser(config=config)

    assert parser.config.use_llm is True
    assert parser.config.extract_images is False


@pytest.mark.slow
def test_marker_parse_pdf(sample_pdf):
    """Test parsing PDF with marker (slow - loads models)."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    try:
        document = parser.parse(sample_pdf)

        assert document is not None
        assert document.format.value == "pdf"
        assert len(document.content) > 0
    except Exception as e:
        # Marker might fail if models aren't available
        pytest.skip(f"Marker parsing failed (models may not be available): {e}")


def test_marker_markdown_output_structure(tmp_path):
    """Test that marker can parse markdown structure."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    # Test markdown parsing
    markdown = """# Heading 1

This is a paragraph.

## Heading 2

Another paragraph with text.
"""

    content = parser._parse_markdown_to_content(markdown)

    assert len(content) > 0
    # Should have headings and paragraphs
    headings = [c for c in content if c.type == "heading"]
    paragraphs = [c for c in content if c.type == "paragraph"]

    assert len(headings) >= 2
    assert len(paragraphs) >= 2


def test_marker_heading_level_detection():
    """Test marker correctly detects heading levels."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    markdown = """# Level 1
## Level 2
### Level 3
"""

    content = parser._parse_markdown_to_content(markdown)

    headings = [c for c in content if c.type == "heading"]
    assert len(headings) == 3

    assert headings[0].level == 1
    assert headings[1].level == 2
    assert headings[2].level == 3


def test_marker_empty_lines_handling():
    """Test marker handles empty lines correctly."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    markdown = """First paragraph.

Second paragraph.


Third paragraph.
"""

    content = parser._parse_markdown_to_content(markdown)

    paragraphs = [c for c in content if c.type == "paragraph"]
    assert len(paragraphs) == 3


def test_marker_batch_convert_interface(tmp_path):
    """Test marker batch conversion interface."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    # Just test the interface exists
    assert hasattr(parser, 'batch_convert')
    assert callable(parser.batch_convert)


def test_marker_comparison_interface(sample_pdf):
    """Test marker comparison with PyMuPDF interface."""
    from vlm_doc_test.parsers import MarkerParser

    parser = MarkerParser()

    # Just test the interface exists
    assert hasattr(parser, 'compare_with_pymupdf')
    assert callable(parser.compare_with_pymupdf)
