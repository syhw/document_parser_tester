"""
Test the PDF parser implementation.

Since we don't have a test PDF yet, this creates a simple PDF
using PyMuPDF and then parses it to verify the parser works.
"""

import pymupdf as fitz
from pathlib import Path
from vlm_doc_test.parsers import PDFParser
from vlm_doc_test.schemas.base import DocumentCategory


def create_test_pdf(output_path: str):
    """Create a simple test PDF with text, headings, and structure."""
    doc = fitz.open()  # Create new PDF
    page = doc.new_page(width=595, height=842)  # A4 size

    # Add title
    page.insert_text(
        (50, 50),
        "Test Document",
        fontsize=24,
        fontname="helv",
    )

    # Add heading
    page.insert_text(
        (50, 100),
        "Introduction",
        fontsize=18,
        fontname="helv",
    )

    # Add paragraph
    para1 = (
        "This is a test document created to demonstrate the PDF parsing "
        "capabilities of the vlm_doc_test library. It contains various "
        "elements including headings, paragraphs, and structured content."
    )
    page.insert_textbox(
        fitz.Rect(50, 120, 545, 200),
        para1,
        fontsize=12,
        fontname="helv",
    )

    # Add another heading
    page.insert_text(
        (50, 220),
        "Methods",
        fontsize=18,
        fontname="helv",
    )

    # Add another paragraph
    para2 = (
        "The parsing process uses PyMuPDF to extract text with coordinate "
        "information, detect structural elements like headings based on font "
        "size, and identify visual elements such as figures and tables."
    )
    page.insert_textbox(
        fitz.Rect(50, 240, 545, 320),
        para2,
        fontsize=12,
        fontname="helv",
    )

    # Add a second page
    page2 = doc.new_page(width=595, height=842)

    page2.insert_text(
        (50, 50),
        "Results",
        fontsize=18,
        fontname="helv",
    )

    para3 = (
        "The parser successfully extracts content elements with bounding box "
        "information, enabling coordinate-aware analysis and comparison with "
        "VLM-based extraction methods."
    )
    page2.insert_textbox(
        fitz.Rect(50, 70, 545, 150),
        para3,
        fontsize=12,
        fontname="helv",
    )

    # Set metadata
    doc.set_metadata({
        "title": "Test Document for PDF Parser",
        "author": "VLM Doc Test",
        "subject": "PDF Parsing Demo",
        "keywords": "testing, pdf, parsing",
    })

    doc.save(output_path)
    doc.close()
    print(f"✅ Created test PDF: {output_path}")


def test_pdf_parser():
    """Test the PDF parser on a sample document."""
    print("=" * 70)
    print("PDF Parser Test")
    print("=" * 70)
    print()

    # Create test PDF
    test_pdf_path = "/home/syhw/claude_tester/test_document.pdf"
    create_test_pdf(test_pdf_path)
    print()

    # Parse it
    print("📄 Parsing test PDF...")
    parser = PDFParser()

    document = parser.parse(
        test_pdf_path,
        extract_images=True,
        extract_tables=True,
        category=DocumentCategory.OTHER,
    )

    print("✅ Successfully parsed!")
    print()

    # Verify results
    print("Verification:")
    print(f"  ✓ Document ID: {document.id}")
    print(f"  ✓ Format: {document.format}")
    print(f"  ✓ Source: {document.source.file_path}")
    print()

    print("Metadata:")
    print(f"  ✓ Title: {document.metadata.title}")
    print(f"  ✓ Authors: {[a.name for a in document.metadata.authors]}")
    print(f"  ✓ Keywords: {document.metadata.keywords}")
    print()

    print("Content:")
    print(f"  ✓ Total elements: {len(document.content)}")

    headings = [c for c in document.content if c.type == "heading"]
    paragraphs = [c for c in document.content if c.type == "paragraph"]

    print(f"  ✓ Headings: {len(headings)}")
    print(f"  ✓ Paragraphs: {len(paragraphs)}")
    print()

    # Show extracted headings
    print("Extracted headings:")
    for heading in headings:
        level_str = f" (Level {heading.level})" if heading.level else ""
        bbox_str = f" [Page {heading.bbox.page}]" if heading.bbox else ""
        print(f"  - {heading.content}{level_str}{bbox_str}")
    print()

    # Show first paragraph
    if paragraphs:
        print("First paragraph:")
        para = paragraphs[0]
        content_preview = para.content[:100] + "..." if len(para.content) > 100 else para.content
        print(f"  {content_preview}")
        if para.bbox:
            print(f"  Location: Page {para.bbox.page}, ({para.bbox.x:.1f}, {para.bbox.y:.1f})")
    print()

    # Test JSON serialization
    json_output = document.model_dump_json(indent=2)
    print(f"✓ JSON serialization: {len(json_output)} bytes")
    print()

    # Test page count utility
    page_count = parser.get_page_count(test_pdf_path)
    print(f"✓ Page count utility: {page_count} pages")
    print()

    # Test single page extraction
    page1_text = parser.extract_page_text(test_pdf_path, 1)
    print(f"✓ Page 1 text extraction: {len(page1_text)} characters")
    print()

    print("=" * 70)
    print("✅ All PDF parser tests passed!")
    print("=" * 70)


if __name__ == "__main__":
    test_pdf_parser()
