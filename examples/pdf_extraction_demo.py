"""
PDF Extraction Demo

Demonstrates how to use the PDFParser to extract structured content
from a PDF document and convert it to our SimpleDocument schema.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from vlm_doc_test.parsers import PDFParser
from vlm_doc_test.schemas.base import DocumentCategory


def demo_pdf_extraction(pdf_path: str):
    """
    Demonstrate PDF extraction with PyMuPDF parser.

    Args:
        pdf_path: Path to a PDF file to parse
    """
    print("=" * 70)
    print("PDF Extraction Demo - PyMuPDF Parser")
    print("=" * 70)
    print()

    # Create parser
    parser = PDFParser()

    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"❌ File not found: {pdf_path}")
        print()
        print("Please provide a valid PDF file path.")
        print("Example usage:")
        print(f"  python {Path(__file__).name} /path/to/document.pdf")
        return

    print(f"📄 Parsing: {pdf_path}")
    print()

    # Parse the PDF
    try:
        document = parser.parse(
            pdf_path,
            extract_images=True,
            extract_tables=True,
            category=DocumentCategory.OTHER,  # Could be detected or specified
        )
    except Exception as e:
        print(f"❌ Error parsing PDF: {e}")
        return

    # Display results
    print("✅ Successfully parsed PDF!")
    print()

    print(f"Document ID: {document.id}")
    print(f"Format: {document.format}")
    print(f"Category: {document.category}")
    print()

    # Metadata
    print("📋 Metadata:")
    if document.metadata.title:
        print(f"  Title: {document.metadata.title}")
    if document.metadata.authors:
        print(f"  Authors: {', '.join(a.name for a in document.metadata.authors)}")
    if document.metadata.date:
        print(f"  Date: {document.metadata.date}")
    if document.metadata.keywords:
        print(f"  Keywords: {', '.join(document.metadata.keywords)}")
    print()

    # Content statistics
    print("📝 Content:")
    print(f"  Total elements: {len(document.content)}")

    headings = [c for c in document.content if c.type == "heading"]
    paragraphs = [c for c in document.content if c.type == "paragraph"]

    print(f"  Headings: {len(headings)}")
    print(f"  Paragraphs: {len(paragraphs)}")
    print()

    # Show first few headings
    if headings:
        print("  First few headings:")
        for heading in headings[:5]:
            level_str = f" (Level {heading.level})" if heading.level else ""
            content_preview = heading.content[:60] + "..." if len(heading.content) > 60 else heading.content
            print(f"    - {content_preview}{level_str}")
        print()

    # Figures
    print(f"🖼️  Figures: {len(document.figures)}")
    if document.figures:
        print(f"  Detected {len(document.figures)} image(s)")
        for fig in document.figures[:3]:
            if fig.bbox:
                print(f"    - {fig.id}: Page {fig.bbox.page}, "
                      f"Position ({fig.bbox.x:.1f}, {fig.bbox.y:.1f}), "
                      f"Size {fig.bbox.width:.1f}x{fig.bbox.height:.1f}")
    print()

    # Tables
    print(f"📊 Tables: {len(document.tables)}")
    if document.tables:
        print(f"  Detected {len(document.tables)} table(s)")
        for table in document.tables[:3]:
            row_count = len(table.rows)
            col_count = len(table.rows[0]) if table.rows else 0
            print(f"    - {table.id}: {row_count} rows × {col_count} columns")
            if table.bbox:
                print(f"      Page {table.bbox.page}, "
                      f"Position ({table.bbox.x:.1f}, {table.bbox.y:.1f})")
    print()

    # JSON export demo
    print("💾 JSON Export:")
    json_output = document.model_dump_json(indent=2)
    print(f"  Total size: {len(json_output)} bytes")
    print()
    print("  Preview (first 500 chars):")
    print("  " + "-" * 66)
    for line in json_output[:500].split("\n"):
        print(f"  {line}")
    if len(json_output) > 500:
        print("  ...")
    print("  " + "-" * 66)
    print()

    print("=" * 70)
    print("✅ Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Default: look for any PDF in current directory
        pdf_files = list(Path.cwd().glob("*.pdf"))
        if pdf_files:
            pdf_path = str(pdf_files[0])
            print(f"No PDF specified, using: {pdf_path}")
            print()
        else:
            print("Usage: python pdf_extraction_demo.py <path_to_pdf>")
            print()
            print("No PDF file found in current directory.")
            print("Please provide a PDF file path as an argument.")
            sys.exit(1)

    demo_pdf_extraction(pdf_path)
