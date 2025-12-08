"""
Pytest configuration and fixtures for vlm_doc_test.

This module provides shared fixtures for testing document parsing,
validation, and comparison functionality.
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
    Figure,
    Table,
    Author,
)
from ..schemas.base import DocumentFormat, DocumentCategory, BoundingBox


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_pdf(tmp_path):
    """
    Create a sample PDF for testing.

    Returns path to the PDF file.
    """
    pdf_path = tmp_path / "sample.pdf"

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Add title
    page.insert_text((50, 50), "Sample Document", fontsize=24, fontname="helv")

    # Add heading
    page.insert_text((50, 100), "Introduction", fontsize=18, fontname="helv")

    # Add paragraph
    page.insert_textbox(
        fitz.Rect(50, 120, 545, 180),
        "This is a sample document for testing the PDF parser.",
        fontsize=12,
        fontname="helv",
    )

    # Set metadata
    doc.set_metadata({
        "title": "Sample Document",
        "author": "Test Author",
        "keywords": "sample, test, pdf",
    })

    doc.save(str(pdf_path))
    doc.close()

    return pdf_path


@pytest.fixture
def sample_html(tmp_path):
    """
    Create a sample HTML file for testing.

    Returns path to the HTML file.
    """
    html_path = tmp_path / "sample.html"

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="author" content="Test Author">
    <meta name="keywords" content="sample, test, html">
    <title>Sample Web Page</title>
</head>
<body>
    <main>
        <article>
            <h1>Sample Web Page</h1>

            <h2>Introduction</h2>
            <p>This is a sample web page for testing the HTML parser. It contains various HTML elements.</p>

            <h2>Features</h2>
            <p>The parser can extract headings, paragraphs, links, images, and tables.</p>

            <figure>
                <img src="test.jpg" alt="Test Image">
                <figcaption>Figure 1: A test image</figcaption>
            </figure>

            <table>
                <caption>Sample Data</caption>
                <tr>
                    <th>Name</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Item 1</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>Item 2</td>
                    <td>200</td>
                </tr>
            </table>

            <p>For more information, visit <a href="https://example.com">our website</a>.</p>
        </article>
    </main>
</body>
</html>"""

    html_path.write_text(html_content, encoding='utf-8')
    return html_path


@pytest.fixture
def sample_document():
    """
    Create a sample SimpleDocument for testing.

    Returns a SimpleDocument instance.
    """
    return SimpleDocument(
        id="test-doc-001",
        format=DocumentFormat.PDF,
        category=DocumentCategory.ACADEMIC_PAPER,
        source=DocumentSource(
            url="https://example.com/paper.pdf",
            accessed_at=datetime.now(),
        ),
        metadata=DocumentMetadata(
            title="Test Document",
            authors=[
                Author(name="Alice Smith", affiliation="University A"),
                Author(name="Bob Jones", affiliation="University B"),
            ],
            keywords=["testing", "document", "analysis"],
        ),
        content=[
            ContentElement(
                id="c1",
                type="heading",
                content="Introduction",
                level=1,
                bbox=BoundingBox(page=1, x=50, y=50, width=500, height=30),
            ),
            ContentElement(
                id="c2",
                type="paragraph",
                content="This is a test paragraph.",
                bbox=BoundingBox(page=1, x=50, y=90, width=500, height=40),
            ),
        ],
        figures=[
            Figure(
                id="fig1",
                caption="Test figure",
                label="Figure 1",
                bbox=BoundingBox(page=1, x=50, y=150, width=400, height=300),
            ),
        ],
        tables=[
            Table(
                id="tab1",
                caption="Test table",
                label="Table 1",
                rows=[
                    ["Header 1", "Header 2"],
                    ["Value 1", "Value 2"],
                ],
            ),
        ],
    )


@pytest.fixture
def sample_document_pair():
    """
    Create a pair of similar documents for comparison testing.

    Returns tuple of (tool_document, vlm_document).
    """
    base_source = DocumentSource(
        url="https://example.com/doc.pdf",
        accessed_at=datetime.now(),
    )

    tool_doc = SimpleDocument(
        id="doc-001",
        format=DocumentFormat.PDF,
        category=DocumentCategory.BLOG_POST,
        source=base_source,
        metadata=DocumentMetadata(
            title="Test Blog Post",
            authors=[Author(name="John Doe")],
            keywords=["blog", "test"],
        ),
        content=[
            ContentElement(
                id="t1",
                type="heading",
                content="Main Title",
                level=1,
            ),
            ContentElement(
                id="t2",
                type="paragraph",
                content="This is the first paragraph of the blog post.",
            ),
        ],
    )

    # VLM document with slight variations
    vlm_doc = SimpleDocument(
        id="doc-001",
        format=DocumentFormat.PDF,
        category=DocumentCategory.BLOG_POST,
        source=base_source,
        metadata=DocumentMetadata(
            title="Test Blog Post",  # Same title
            authors=[Author(name="John Doe")],  # Same author
            keywords=["blog"],  # Fewer keywords
        ),
        content=[
            ContentElement(
                id="v1",
                type="heading",
                content="Main Title",
                level=1,
            ),
            ContentElement(
                id="v2",
                type="paragraph",
                content="This is the first paragraph of the blog.",  # Slightly different
            ),
        ],
    )

    return tool_doc, vlm_doc
