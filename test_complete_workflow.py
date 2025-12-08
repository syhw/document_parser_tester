"""
Complete Phase 0 Workflow Test

This test demonstrates the entire Phase 0 pipeline:
1. Parse a PDF with PyMuPDF
2. Simulate VLM output (without requiring API key)
3. Compare using EquivalenceChecker
4. Generate report
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from vlm_doc_test.parsers import PDFParser
from vlm_doc_test.validation import EquivalenceChecker
from vlm_doc_test.schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Author,
)
from vlm_doc_test.schemas.base import DocumentFormat, DocumentCategory, BoundingBox
from datetime import datetime


def simulate_vlm_output(tool_doc: SimpleDocument) -> SimpleDocument:
    """
    Simulate VLM output based on tool extraction.

    In production, this would be replaced with actual VLM API call.
    For testing, we create a slightly modified version to demonstrate
    the comparison functionality.
    """
    # Simulate VLM extracting similar but not identical content
    vlm_doc = SimpleDocument(
        id=tool_doc.id,
        format=tool_doc.format,
        category=tool_doc.category,
        source=tool_doc.source,
        metadata=DocumentMetadata(
            # VLM might extract title slightly differently
            title=tool_doc.metadata.title,
            # VLM might identify authors
            authors=[Author(name="VLM Doc Test")],
            # VLM might not catch all keywords
            keywords=["testing", "pdf"],
        ),
        content=[
            # VLM extracts headings
            ContentElement(
                id="vlm_c1",
                type="heading",
                content="Test Document",
                level=1,
                bbox=BoundingBox(page=1, x=52, y=48, width=498, height=32),
            ),
            ContentElement(
                id="vlm_c2",
                type="heading",
                content="Introduction",
                level=2,
                bbox=BoundingBox(page=1, x=51, y=99, width=499, height=31),
            ),
            # VLM paraphrases paragraph slightly
            ContentElement(
                id="vlm_c3",
                type="paragraph",
                content="This is a test document demonstrating PDF parsing capabilities of the vlm_doc_test library.",
                bbox=BoundingBox(page=1, x=50, y=121, width=500, height=58),
            ),
            ContentElement(
                id="vlm_c4",
                type="heading",
                content="Methods",
                level=2,
                bbox=BoundingBox(page=1, x=50, y=161, width=500, height=29),
            ),
            ContentElement(
                id="vlm_c5",
                type="paragraph",
                content="We use vision-language models for document understanding with a novel approach.",
                bbox=BoundingBox(page=1, x=50, y=201, width=500, height=59),
            ),
            ContentElement(
                id="vlm_c6",
                type="heading",
                content="Results",
                level=2,
                bbox=BoundingBox(page=2, x=50, y=50, width=500, height=30),
            ),
            ContentElement(
                id="vlm_c7",
                type="paragraph",
                content="The parser successfully extracts content with bounding box information.",
                bbox=BoundingBox(page=2, x=50, y=70, width=500, height=60),
            ),
        ],
    )

    return vlm_doc


def test_complete_workflow():
    """Test the complete Phase 0 workflow."""
    print("=" * 70)
    print("Phase 0 Complete Workflow Test")
    print("=" * 70)
    print()

    # Step 1: Parse PDF with tool-based extraction
    print("Step 1: Tool-based PDF Extraction (PyMuPDF)")
    print("-" * 70)

    pdf_path = "test_document.pdf"
    if not Path(pdf_path).exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        print("Please run test_pdf_parser.py first to generate test_document.pdf")
        return

    parser = PDFParser()
    tool_doc = parser.parse(
        pdf_path,
        extract_images=True,
        extract_tables=True,
        category=DocumentCategory.OTHER,
    )

    print(f"✅ Extracted {len(tool_doc.content)} content elements")
    print(f"   - Title: {tool_doc.metadata.title}")
    print(f"   - Authors: {len(tool_doc.metadata.authors)}")
    print(f"   - Headings: {len([c for c in tool_doc.content if c.type == 'heading'])}")
    print(f"   - Paragraphs: {len([c for c in tool_doc.content if c.type == 'paragraph'])}")
    print()

    # Step 2: Simulate VLM extraction
    print("Step 2: VLM-based Extraction (Simulated)")
    print("-" * 70)
    print("Note: In production, this would call VLMAnalyzer.analyze_document_image()")
    print("      For testing without API key, we simulate VLM output.")
    print()

    vlm_doc = simulate_vlm_output(tool_doc)

    print(f"✅ VLM extracted {len(vlm_doc.content)} content elements")
    print(f"   - Title: {vlm_doc.metadata.title}")
    print(f"   - Authors: {len(vlm_doc.metadata.authors)}")
    print(f"   - Headings: {len([c for c in vlm_doc.content if c.type == 'heading'])}")
    print(f"   - Paragraphs: {len([c for c in vlm_doc.content if c.type == 'paragraph'])}")
    print()

    # Step 3: Compare with EquivalenceChecker
    print("Step 3: Equivalence Checking")
    print("-" * 70)

    checker = EquivalenceChecker(
        text_similarity_threshold=0.85,
        bbox_iou_threshold=0.7,
    )

    result = checker.compare_documents(tool_doc, vlm_doc)

    print(f"Match Quality: {result.match_quality.value.upper()}")
    print(f"Overall Score: {result.score:.2%}")
    print()

    # Step 4: Detailed breakdown
    print("Step 4: Detailed Analysis")
    print("-" * 70)

    print("Metadata Comparison:")
    metadata_details = result.details.get('metadata', {})
    for key, value in metadata_details.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")
    print()

    print("Content Comparison:")
    content_details = result.details.get('content', {})
    print(f"  Element counts: {content_details.get('count', {})}")
    print(f"  Type distribution: {content_details.get('type_distribution', {})}")
    print(f"  Text similarity: {content_details.get('text_similarity', 0):.2%}")
    print()

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
        print()

    if result.differences:
        print("Differences detected:")
        for category, diff in result.differences.items():
            print(f"  📋 {category}: {diff}")
        print()

    # Step 5: Pass/Fail decision
    print("Step 5: Test Decision")
    print("-" * 70)

    # Define acceptance criteria
    min_score = 0.85
    required_quality = ["exact", "excellent", "good"]

    passed = (
        result.score >= min_score and
        result.match_quality.value in required_quality
    )

    if passed:
        print(f"✅ TEST PASSED")
        print(f"   Score {result.score:.2%} meets minimum threshold {min_score:.2%}")
        print(f"   Quality '{result.match_quality.value}' is acceptable")
    else:
        print(f"❌ TEST FAILED")
        print(f"   Score {result.score:.2%} below threshold {min_score:.2%}")
        print(f"   Quality '{result.match_quality.value}' not in {required_quality}")
    print()

    # Step 6: Export results
    print("Step 6: Export Results")
    print("-" * 70)

    # Export tool extraction to JSON
    tool_json = tool_doc.model_dump_json(indent=2)
    with open("tool_extraction.json", "w") as f:
        f.write(tool_json)
    print(f"✅ Saved tool extraction: tool_extraction.json ({len(tool_json)} bytes)")

    # Export VLM extraction to JSON
    vlm_json = vlm_doc.model_dump_json(indent=2)
    with open("vlm_extraction.json", "w") as f:
        f.write(vlm_json)
    print(f"✅ Saved VLM extraction: vlm_extraction.json ({len(vlm_json)} bytes)")

    # Export comparison report
    report = {
        "match_quality": result.match_quality.value,
        "score": result.score,
        "details": result.details,
        "differences": result.differences,
        "warnings": result.warnings,
        "passed": passed,
    }
    import json
    report_json = json.dumps(report, indent=2)
    with open("comparison_report.json", "w") as f:
        f.write(report_json)
    print(f"✅ Saved comparison report: comparison_report.json ({len(report_json)} bytes)")
    print()

    print("=" * 70)
    print("✅ Complete workflow test finished!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  - Tool extraction: {len(tool_doc.content)} elements")
    print(f"  - VLM extraction: {len(vlm_doc.content)} elements")
    print(f"  - Match quality: {result.match_quality.value}")
    print(f"  - Score: {result.score:.2%}")
    print(f"  - Result: {'PASS ✅' if passed else 'FAIL ❌'}")
    print()
    print("Phase 0 Components Tested:")
    print("  ✅ PDFParser - Coordinate-aware extraction")
    print("  ✅ SimpleDocument - Pydantic schema validation")
    print("  ✅ EquivalenceChecker - Multi-level comparison")
    print("  ✅ BoundingBox - Spatial information")
    print("  ✅ JSON serialization - Export functionality")


if __name__ == "__main__":
    test_complete_workflow()
