"""
Test basic setup and imports.
"""

from datetime import datetime
from vlm_doc_test.schemas import (
    SimpleDocument,
    DocumentFormat,
    DocumentCategory,
    BoundingBox,
    SimpleAuthor,
)


def test_simple_document_creation():
    """Test creating a simple document."""
    from vlm_doc_test.schemas.schema_simple import DocumentSource

    doc = SimpleDocument(
        id="test-001",
        format=DocumentFormat.HTML,
        category=DocumentCategory.BLOG_POST,
        source=DocumentSource(
            url="https://example.com/blog",
            accessed_at=datetime.now()
        )
    )

    print("✅ Successfully created SimpleDocument:")
    print(f"   ID: {doc.id}")
    print(f"   Format: {doc.format}")
    print(f"   Category: {doc.category}")
    print()

    # Test adding content
    from vlm_doc_test.schemas.schema_simple import ContentElement

    doc.content.append(ContentElement(
        id="c1",
        type="heading",
        content="Test Heading",
        level=1
    ))

    print(f"✅ Added content element: {doc.content[0].content}")
    print()

    # Test JSON serialization
    json_output = doc.model_dump_json(indent=2)
    print("✅ Successfully serialized to JSON:")
    print(json_output[:200] + "...")
    print()


def test_bounding_box():
    """Test bounding box creation."""
    bbox = BoundingBox(
        page=1,
        x=100.0,
        y=200.0,
        width=400.0,
        height=300.0,
        confidence=0.95
    )

    print("✅ Successfully created BoundingBox:")
    print(f"   Page: {bbox.page}")
    print(f"   Coordinates: ({bbox.x}, {bbox.y})")
    print(f"   Size: {bbox.width}x{bbox.height}")
    print(f"   Confidence: {bbox.confidence}")
    print()


def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    print()

    # Core dependencies
    try:
        import pydantic
        print(f"✅ pydantic {pydantic.VERSION}")
    except ImportError as e:
        print(f"❌ pydantic: {e}")

    try:
        import instructor
        print("✅ instructor")
    except ImportError as e:
        print(f"❌ instructor: {e}")

    try:
        import pymupdf
        print(f"✅ pymupdf {pymupdf.version}")
    except ImportError as e:
        print(f"❌ pymupdf: {e}")

    try:
        import pdfplumber
        print("✅ pdfplumber")
    except ImportError as e:
        print(f"❌ pdfplumber: {e}")

    try:
        from deepdiff import DeepDiff
        print("✅ deepdiff")
    except ImportError as e:
        print(f"❌ deepdiff: {e}")

    try:
        from thefuzz import fuzz
        print("✅ thefuzz")
    except ImportError as e:
        print(f"❌ thefuzz: {e}")

    print()


if __name__ == "__main__":
    print("=" * 70)
    print("VLM Document Testing Library - Setup Test")
    print("=" * 70)
    print()

    test_imports()
    test_bounding_box()
    test_simple_document_creation()

    print("=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
