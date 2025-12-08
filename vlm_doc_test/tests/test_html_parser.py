"""
Tests for HTML parser.
"""

import pytest
from ..parsers import HTMLParser
from ..schemas.base import DocumentFormat


def test_html_parser_basic(sample_html):
    """Test basic HTML parsing functionality."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert doc.format == DocumentFormat.HTML
    assert doc.metadata.title == "Sample Web Page"
    assert len(doc.metadata.authors) == 1
    assert doc.metadata.authors[0].name == "Test Author"


def test_html_parser_content_extraction(sample_html):
    """Test content element extraction."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert len(doc.content) > 0

    # Check for headings
    headings = [c for c in doc.content if c.type == "heading"]
    assert len(headings) >= 3  # h1 + 2 h2s

    # Check heading levels
    h1_headings = [c for c in headings if c.level == 1]
    assert len(h1_headings) >= 1

    # Check for paragraphs
    paragraphs = [c for c in doc.content if c.type == "paragraph"]
    assert len(paragraphs) >= 2


def test_html_parser_figures(sample_html):
    """Test figure extraction."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert len(doc.figures) >= 1

    # Check figure with caption
    fig = doc.figures[0]
    assert fig.caption is not None
    assert "test" in fig.caption.lower() or "figure" in fig.caption.lower()


def test_html_parser_tables(sample_html):
    """Test table extraction."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert len(doc.tables) >= 1

    # Check table structure
    table = doc.tables[0]
    assert table.caption == "Sample Data"
    assert len(table.rows) == 3  # Header + 2 data rows

    # Check table content
    assert table.rows[0] == ["Name", "Value"]  # Header row
    assert table.rows[1][0] == "Item 1"


def test_html_parser_links(sample_html):
    """Test link extraction."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert len(doc.links) >= 1

    # Check link properties
    link = doc.links[0]
    assert link.url == "https://example.com"
    assert "website" in link.text.lower()


def test_html_parser_keywords(sample_html):
    """Test keyword extraction."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    assert len(doc.metadata.keywords) > 0
    assert "sample" in doc.metadata.keywords or "test" in doc.metadata.keywords


def test_html_parser_string_input():
    """Test parsing HTML from string."""
    html_string = """
    <html>
    <head><title>Test</title></head>
    <body>
        <h1>Hello</h1>
        <p>World</p>
    </body>
    </html>
    """

    parser = HTMLParser()
    doc = parser.parse(html_string, url="https://example.com/test")

    assert doc.metadata.title == "Test"
    assert doc.source.url == "https://example.com/test"
    assert len(doc.content) == 2  # 1 heading + 1 paragraph


def test_html_parser_parse_url():
    """Test parse_url convenience method."""
    html_string = "<html><body><h1>Test</h1></body></html>"

    parser = HTMLParser()
    doc = parser.parse_url(
        url="https://example.com",
        html_content=html_string,
    )

    assert doc.source.url == "https://example.com"
    assert len(doc.content) > 0


def test_html_parser_json_serialization(sample_html):
    """Test JSON serialization."""
    parser = HTMLParser()
    doc = parser.parse(str(sample_html))

    json_output = doc.model_dump_json()
    assert len(json_output) > 0
    assert "Sample Web Page" in json_output
