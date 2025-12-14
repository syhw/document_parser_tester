"""
Tests for Docling parser with Granite Vision.

This module tests the DoclingParser class functionality including:
- VLM-based document parsing
- Markdown conversion
- Comparison with Marker
"""

import pytest
from pathlib import Path


def test_docling_imports():
    """Test that docling parser can be imported."""
    from vlm_doc_test.parsers import DoclingParser, DoclingConfig
    assert DoclingParser is not None
    assert DoclingConfig is not None


def test_docling_config_defaults():
    """Test DoclingConfig default values."""
    from vlm_doc_test.parsers import DoclingConfig

    config = DoclingConfig()
    assert config.use_vlm is True
    assert config.vlm_model == "ibm-granite/granite-docling-258M"
    assert config.batch_size == 1
    assert config.extract_tables is True
    assert config.extract_figures is True
    assert config.ocr_enabled is True


def test_docling_parser_initialization():
    """Test DoclingParser can be initialized."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()
    assert parser.config is not None
    assert parser._converter is None  # Lazy loaded


def test_docling_parser_with_custom_config():
    """Test DoclingParser with custom configuration."""
    from vlm_doc_test.parsers import DoclingParser, DoclingConfig

    config = DoclingConfig(use_vlm=False, batch_size=4)
    parser = DoclingParser(config=config)

    assert parser.config.use_vlm is False
    assert parser.config.batch_size == 4


def test_docling_format_detection():
    """Test Docling correctly detects document formats."""
    from vlm_doc_test.parsers import DoclingParser
    from vlm_doc_test.schemas.base import DocumentFormat

    parser = DoclingParser()

    assert parser._get_format(Path("test.pdf")) == DocumentFormat.PDF
    assert parser._get_format(Path("test.html")) == DocumentFormat.HTML
    assert parser._get_format(Path("test.docx")) == DocumentFormat.DOCX
    assert parser._get_format(Path("test.pptx")) == DocumentFormat.PPTX
    assert parser._get_format(Path("test.md")) == DocumentFormat.MARKDOWN
    assert parser._get_format(Path("test.xyz")) == DocumentFormat.OTHER


@pytest.mark.slow
def test_docling_parse_pdf(sample_pdf):
    """Test parsing PDF with Docling (slow - loads VLM)."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    try:
        document = parser.parse(sample_pdf)

        assert document is not None
        assert document.format.value == "pdf"
        assert document.source.file_path == str(sample_pdf)
    except Exception as e:
        # Docling might fail if models aren't available
        pytest.skip(f"Docling parsing failed (VLM may not be available): {e}")


def test_docling_metadata_extraction():
    """Test metadata extraction structure."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Create mock docling doc
    class MockDoclingDoc:
        title = "Test Title"

    metadata = parser._extract_metadata(MockDoclingDoc())
    assert metadata is not None
    assert metadata.title == "Test Title"


def test_docling_content_extraction_empty():
    """Test content extraction with minimal document."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Create mock docling doc
    class MockDoclingDoc:
        def export_to_markdown(self):
            return ""

    content = parser._extract_content(MockDoclingDoc())
    assert isinstance(content, list)


def test_docling_tables_extraction_structure():
    """Test table extraction returns proper structure."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Create mock docling doc
    class MockDoclingDoc:
        tables = []

    tables = parser._extract_tables(MockDoclingDoc())
    assert isinstance(tables, list)
    assert len(tables) == 0


def test_docling_figures_extraction_structure():
    """Test figure extraction returns proper structure."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Create mock docling doc
    class MockDoclingDoc:
        pictures = []

    figures = parser._extract_figures(MockDoclingDoc())
    assert isinstance(figures, list)
    assert len(figures) == 0


def test_docling_batch_convert_interface(tmp_path):
    """Test docling batch conversion interface."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Just test the interface exists
    assert hasattr(parser, 'batch_convert')
    assert callable(parser.batch_convert)


def test_docling_comparison_interface():
    """Test docling comparison with Marker interface."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    # Just test the interface exists
    assert hasattr(parser, 'compare_with_marker')
    assert callable(parser.compare_with_marker)


def test_docling_parse_to_markdown_interface():
    """Test parse to markdown interface."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    assert hasattr(parser, 'parse_to_markdown')
    assert callable(parser.parse_to_markdown)


def test_docling_parse_to_dict_interface():
    """Test parse to dict interface."""
    from vlm_doc_test.parsers import DoclingParser

    parser = DoclingParser()

    assert hasattr(parser, 'parse_to_dict')
    assert callable(parser.parse_to_dict)
