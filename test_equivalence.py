"""
Test the equivalence checking system.

This demonstrates comparing tool-based extraction with simulated VLM output.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from vlm_doc_test.schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Author,
)
from vlm_doc_test.schemas.base import DocumentFormat, DocumentCategory, BoundingBox
from vlm_doc_test.validation import EquivalenceChecker


def create_tool_document() -> SimpleDocument:
    """Create a simulated tool-based extraction."""
    return SimpleDocument(
        id="test-doc",
        format=DocumentFormat.PDF,
        category=DocumentCategory.ACADEMIC_PAPER,
        source=DocumentSource(
            file_path="/path/to/paper.pdf",
            accessed_at=datetime.now(),
        ),
        metadata=DocumentMetadata(
            title="Machine Learning for Document Analysis",
            authors=[
                Author(name="Alice Smith", affiliation="University A"),
                Author(name="Bob Jones", affiliation="University B"),
            ],
            keywords=["machine learning", "document analysis", "NLP"],
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
                content="Document analysis is a critical task in natural language processing.",
                bbox=BoundingBox(page=1, x=50, y=90, width=500, height=60),
            ),
            ContentElement(
                id="c3",
                type="heading",
                content="Methods",
                level=1,
                bbox=BoundingBox(page=1, x=50, y=160, width=500, height=30),
            ),
            ContentElement(
                id="c4",
                type="paragraph",
                content="We propose a novel approach using vision-language models for document understanding.",
                bbox=BoundingBox(page=1, x=50, y=200, width=500, height=60),
            ),
        ],
    )


def create_vlm_document_exact() -> SimpleDocument:
    """Create a VLM extraction that matches exactly."""
    return create_tool_document()


def create_vlm_document_similar() -> SimpleDocument:
    """Create a VLM extraction with minor differences."""
    doc = create_tool_document()

    # Slightly different title (minor typo)
    doc.metadata.title = "Machine Learning for Document Analys"

    # Slightly different text (paraphrase)
    doc.content[1].content = "Document analysis is an essential task in NLP."

    # Missing one author
    doc.metadata.authors = doc.metadata.authors[:1]

    return doc


def create_vlm_document_different() -> SimpleDocument:
    """Create a VLM extraction with significant differences."""
    return SimpleDocument(
        id="test-doc",
        format=DocumentFormat.PDF,
        category=DocumentCategory.ACADEMIC_PAPER,
        source=DocumentSource(
            file_path="/path/to/paper.pdf",
            accessed_at=datetime.now(),
        ),
        metadata=DocumentMetadata(
            title="Deep Learning Applications",
            authors=[
                Author(name="Charlie Brown"),
            ],
            keywords=["deep learning", "AI"],
        ),
        content=[
            ContentElement(
                id="c1",
                type="heading",
                content="Abstract",
                level=1,
            ),
            ContentElement(
                id="c2",
                type="paragraph",
                content="This paper presents a different approach entirely.",
            ),
        ],
    )


def test_equivalence_checking():
    """Test the equivalence checker with different scenarios."""
    print("=" * 70)
    print("Equivalence Checking Test")
    print("=" * 70)
    print()

    checker = EquivalenceChecker(
        text_similarity_threshold=0.85,
        bbox_iou_threshold=0.7,
    )

    tool_doc = create_tool_document()

    print("Tool-based extraction:")
    print(f"  Title: {tool_doc.metadata.title}")
    print(f"  Authors: {len(tool_doc.metadata.authors)}")
    print(f"  Content elements: {len(tool_doc.content)}")
    print()

    # Test 1: Exact match
    print("Test 1: Exact Match")
    print("-" * 70)
    vlm_doc_exact = create_vlm_document_exact()
    result = checker.compare_documents(tool_doc, vlm_doc_exact)
    print(f"  Match Quality: {result.match_quality}")
    print(f"  Overall Score: {result.score:.2%}")
    print(f"  Details: {result.details}")
    print()

    # Test 2: Similar match
    print("Test 2: Similar Match (minor differences)")
    print("-" * 70)
    vlm_doc_similar = create_vlm_document_similar()
    result = checker.compare_documents(tool_doc, vlm_doc_similar)
    print(f"  Match Quality: {result.match_quality}")
    print(f"  Overall Score: {result.score:.2%}")
    print(f"  Metadata: {result.details.get('metadata', {})}")
    print(f"  Content: {result.details.get('content', {})}")
    if result.differences:
        print(f"  Differences: {result.differences}")
    if result.warnings:
        print(f"  Warnings:")
        for warning in result.warnings:
            print(f"    - {warning}")
    print()

    # Test 3: Different document
    print("Test 3: Significant Differences")
    print("-" * 70)
    vlm_doc_diff = create_vlm_document_different()
    result = checker.compare_documents(tool_doc, vlm_doc_diff)
    print(f"  Match Quality: {result.match_quality}")
    print(f"  Overall Score: {result.score:.2%}")
    print(f"  Metadata Score: {result.details.get('metadata', {})}")
    print(f"  Content Score: {result.details.get('content', {})}")
    if result.differences:
        print(f"  Differences found in: {list(result.differences.keys())}")
    print()

    # Test 4: Text similarity demo
    print("Test 4: Text Similarity Examples")
    print("-" * 70)

    texts = [
        ("Document analysis is critical.", "Document analysis is essential."),
        ("Machine learning for NLP", "ML for natural language processing"),
        ("Vision language models", "VLM systems"),
        ("Completely different text", "Another unrelated sentence"),
    ]

    from thefuzz import fuzz

    for text1, text2 in texts:
        ratio = fuzz.ratio(text1, text2)
        token_sort = fuzz.token_sort_ratio(text1, text2)
        print(f"  '{text1}'")
        print(f"  '{text2}'")
        print(f"    Ratio: {ratio}%, Token Sort: {token_sort}%")
        print()

    print("=" * 70)
    print("✅ Equivalence checking tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_equivalence_checking()
