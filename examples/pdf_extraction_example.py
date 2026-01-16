#!/usr/bin/env python3
"""
Example: Using the PDF Extraction Tool Programmatically

This example shows how to use test_mcp_zai_GLM.py functions
directly from Python code for batch processing, custom workflows,
or integration with other tools.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_mcp_zai_GLM import (
    render_pdf_to_image,
    encode_image_to_base64,
    build_extraction_prompt,
    call_mcp_tool,
    parse_vlm_response,
)
from vlm_doc_test.schemas.base import DocumentCategory


def extract_pdf_page(
    pdf_path: Path,
    page: int = 0,
    category: DocumentCategory = None,
    dpi: int = 150,
    output_dir: Path = None
) -> dict:
    """
    Extract structured content from a PDF page.

    Args:
        pdf_path: Path to PDF file
        page: Page number (0-indexed)
        category: Document category for optimized extraction
        dpi: DPI for rendering (default: 150)
        output_dir: Directory to save results (default: same as PDF)

    Returns:
        Dictionary with extraction results
    """
    print(f"\n{'='*70}")
    print(f"  Extracting: {pdf_path.name} (page {page+1})")
    print(f"{'='*70}\n")

    # Set output directory
    if output_dir is None:
        output_dir = pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Render PDF to image
    print(f"📄 Rendering page {page+1} at {dpi} DPI...")
    image_path = render_pdf_to_image(pdf_path, page=page, dpi=dpi)
    print(f"✅ Rendered: {image_path}")

    # 2. Encode to base64
    print("\n🔧 Encoding to base64...")
    image_uri = encode_image_to_base64(image_path)
    print(f"✅ Encoded: {len(image_uri):,} characters")

    # 3. Build extraction prompt
    print(f"\n📝 Building extraction prompt...")
    if category:
        print(f"   Category: {category.value}")
    prompt = build_extraction_prompt(category)
    print(f"✅ Prompt: {len(prompt)} characters")

    # 4. Call GLM-4.6V via MCP
    print(f"\n🤖 Calling GLM-4.6V via MCP...")
    response_json = call_mcp_tool(image_uri, prompt)

    # 5. Parse response into SimpleDocument
    print(f"\n📋 Parsing response...")
    document = parse_vlm_response(response_json, pdf_path, category)

    # 6. Save results
    output_path = output_dir / f"{pdf_path.stem}_page{page}_extracted.json"
    print(f"\n💾 Saving to: {output_path}")

    with open(output_path, 'w') as f:
        json.dump(document.model_dump(mode='json'), f, indent=2, default=str)

    # 7. Clean up temporary image
    image_path.unlink()
    print(f"🗑️  Removed temporary: {image_path.name}")

    # Display results
    print(f"\n{'='*70}")
    print(f"  EXTRACTION RESULTS")
    print(f"{'='*70}\n")
    print(f"📊 Title: {document.metadata.title}")
    print(f"👥 Authors: {len(document.metadata.authors)}")
    print(f"📝 Content: {len(document.content)} elements")
    print(f"📊 Tables: {len(document.tables)}")
    print(f"🖼️  Figures: {len(document.figures)}")
    print(f"🔗 Links: {len(document.links)}")

    return {
        'document': document,
        'output_path': output_path,
        'pdf_path': pdf_path,
        'page': page,
    }


def batch_extract_pdf(
    pdf_path: Path,
    pages: list[int] = None,
    category: DocumentCategory = None,
    dpi: int = 150,
    output_dir: Path = None
) -> list[dict]:
    """
    Extract content from multiple pages of a PDF.

    Args:
        pdf_path: Path to PDF file
        pages: List of page numbers to extract (default: all pages)
        category: Document category for optimized extraction
        dpi: DPI for rendering (default: 150)
        output_dir: Directory to save results

    Returns:
        List of extraction results for each page
    """
    import fitz  # PyMuPDF

    # Get page count
    pdf_doc = fitz.open(pdf_path)
    page_count = pdf_doc.page_count
    pdf_doc.close()

    # Default to all pages if not specified
    if pages is None:
        pages = list(range(page_count))

    print(f"\n{'='*70}")
    print(f"  BATCH EXTRACTION")
    print(f"{'='*70}")
    print(f"📄 PDF: {pdf_path.name}")
    print(f"📑 Pages: {len(pages)} pages")
    print(f"📂 Category: {category.value if category else 'auto-detect'}")
    print(f"{'='*70}\n")

    results = []
    for i, page in enumerate(pages, 1):
        print(f"\n[{i}/{len(pages)}] Processing page {page+1}...")
        try:
            result = extract_pdf_page(
                pdf_path=pdf_path,
                page=page,
                category=category,
                dpi=dpi,
                output_dir=output_dir
            )
            results.append(result)
            print(f"✅ Page {page+1} complete")
        except Exception as e:
            print(f"❌ Page {page+1} failed: {e}")
            continue

    # Summary
    print(f"\n{'='*70}")
    print(f"  BATCH SUMMARY")
    print(f"{'='*70}")
    print(f"✅ Processed: {len(results)}/{len(pages)} pages")
    print(f"📁 Output: {output_dir or pdf_path.parent}")
    print(f"{'='*70}\n")

    return results


def compare_categories(
    pdf_path: Path,
    page: int = 0,
    categories: list[DocumentCategory] = None,
    dpi: int = 150
) -> dict:
    """
    Extract the same page with different category prompts for comparison.

    Args:
        pdf_path: Path to PDF file
        page: Page number (0-indexed)
        categories: List of categories to try
        dpi: DPI for rendering

    Returns:
        Dictionary mapping category to extraction results
    """
    if categories is None:
        categories = [
            DocumentCategory.ACADEMIC_PAPER,
            DocumentCategory.TECHNICAL_DOCUMENTATION,
            DocumentCategory.REPORT,
        ]

    print(f"\n{'='*70}")
    print(f"  CATEGORY COMPARISON")
    print(f"{'='*70}")
    print(f"📄 PDF: {pdf_path.name} (page {page+1})")
    print(f"🔍 Testing {len(categories)} categories")
    print(f"{'='*70}\n")

    results = {}
    for category in categories:
        print(f"\n📂 Trying category: {category.value}")
        try:
            result = extract_pdf_page(
                pdf_path=pdf_path,
                page=page,
                category=category,
                dpi=dpi,
                output_dir=pdf_path.parent / "category_comparison"
            )
            results[category.value] = result
            print(f"✅ {category.value} complete")
        except Exception as e:
            print(f"❌ {category.value} failed: {e}")
            continue

    # Compare results
    print(f"\n{'='*70}")
    print(f"  COMPARISON RESULTS")
    print(f"{'='*70}\n")

    for cat_name, result in results.items():
        doc = result['document']
        print(f"📂 {cat_name}:")
        print(f"   Title: {doc.metadata.title}")
        print(f"   Content: {len(doc.content)} elements")
        print(f"   Tables: {len(doc.tables)}")
        print(f"   Figures: {len(doc.figures)}")
        print()

    return results


# Example usage
if __name__ == "__main__":
    # Example 1: Extract single page
    print("\n" + "="*70)
    print("  EXAMPLE 1: Single Page Extraction")
    print("="*70)

    pdf_file = Path("../vlm_doc_test/tests/fixtures/documents/academic_paper/sample1.pdf")

    if pdf_file.exists():
        result = extract_pdf_page(
            pdf_path=pdf_file,
            page=0,
            category=DocumentCategory.ACADEMIC_PAPER,
            dpi=150
        )
        print(f"\n✅ Extracted to: {result['output_path']}")
    else:
        print(f"\n⚠️  Sample PDF not found: {pdf_file}")


    # Example 2: Batch extraction
    print("\n\n" + "="*70)
    print("  EXAMPLE 2: Batch Extraction (First 3 Pages)")
    print("="*70)

    if pdf_file.exists():
        results = batch_extract_pdf(
            pdf_path=pdf_file,
            pages=[0, 1, 2],  # First 3 pages
            category=DocumentCategory.ACADEMIC_PAPER,
            dpi=150,
            output_dir=Path("examples/output/batch_extraction")
        )
        print(f"\n✅ Batch complete: {len(results)} pages")


    # Example 3: Category comparison
    print("\n\n" + "="*70)
    print("  EXAMPLE 3: Category Comparison")
    print("="*70)

    if pdf_file.exists():
        results = compare_categories(
            pdf_path=pdf_file,
            page=0,
            categories=[
                DocumentCategory.ACADEMIC_PAPER,
                DocumentCategory.TECHNICAL_DOCUMENTATION,
            ],
            dpi=150
        )
        print(f"\n✅ Compared {len(results)} categories")


    print("\n\n" + "="*70)
    print("  ALL EXAMPLES COMPLETE!")
    print("="*70)
    print("\n💡 To use with real GLM-4.6V:")
    print("   claude -p examples/pdf_extraction_example.py")
    print("\n")
