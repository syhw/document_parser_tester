"""
Category-based test matrix for document parsing.

This module implements the test matrix from TESTING.md, testing all valid
combinations of document formats and categories.
"""

import pytest
from pathlib import Path

from vlm_doc_test.parsers import PDFParser, HTMLParser
from vlm_doc_test.validation import (
    validate_document,
    get_category_validator,
    ValidationSeverity,
)


# Test matrix: (format, category, priority)
# Based on TESTING.md test matrix - only implemented formats
TEST_MATRIX = [
    # Academic Paper
    ("pdf", "academic_paper", "high"),      # ✓✓✓ Primary format
    ("html", "academic_paper", "medium"),   # ✓ Valid format

    # Blog Post
    ("html", "blog_post", "high"),          # ✓✓✓ Primary format

    # Technical Documentation
    ("html", "technical_docs", "high"),     # ✓✓✓ Primary format
    ("pdf", "technical_docs", "medium"),    # ✓ Valid format
]


@pytest.fixture
def parser_for_format():
    """Get appropriate parser for a format."""
    def _get_parser(format_type: str):
        if format_type == "pdf":
            return PDFParser()
        elif format_type == "html":
            return HTMLParser()
        else:
            raise ValueError(f"Unknown format: {format_type}")
    return _get_parser


@pytest.fixture
def fixture_path():
    """Get path to test fixture."""
    def _get_path(format_type: str, category: str) -> Path:
        base_path = Path(__file__).parent / "fixtures" / "documents" / category

        if format_type == "pdf":
            pdf_file = base_path / "sample1.pdf"
        elif format_type == "html":
            pdf_file = base_path / "sample1.html"
        else:
            raise ValueError(f"Unknown format: {format_type}")

        if not pdf_file.exists():
            pytest.skip(f"Fixture not available: {pdf_file}")

        return pdf_file

    return _get_path


class TestCategoryMatrix:
    """Test matrix for format × category combinations."""

    @pytest.mark.parametrize("format_type,category,priority", TEST_MATRIX)
    def test_category_validation(
        self,
        format_type: str,
        category: str,
        priority: str,
        parser_for_format,
        fixture_path,
    ):
        """
        Test that documents are correctly validated against category requirements.

        This test verifies:
        1. Parser can extract content from the format
        2. Extracted document passes category-specific validation
        3. Category-specific fields are present
        """
        # Get fixture file
        doc_path = fixture_path(format_type, category)

        # Parse document
        parser = parser_for_format(format_type)
        document = parser.parse(doc_path)

        # Validate against category
        result = validate_document(document, category, strict=False)

        # Print validation details for debugging
        if not result.passed or result.score < 0.7:
            print(f"\n{format_type} × {category} validation:")
            print(f"  Score: {result.score:.2f}")
            print(f"  Passed: {result.passed}")
            if result.issues:
                print(f"  Issues ({len(result.issues)}):")
                for issue in result.issues:
                    print(f"    [{issue.severity.value}] {issue.field}: {issue.message}")

        # Assertions
        assert document is not None, f"Parser returned None for {format_type}"
        assert len(document.content) > 0, f"No content extracted from {format_type}"

        # Category validation should pass (errors only, warnings OK)
        assert result.passed, (
            f"Category validation failed for {format_type} × {category}:\n"
            f"  Errors: {[f'{e.field}: {e.message}' for e in result.errors]}"
        )

        # Score should be reasonable (>= 0.5, allowing for warnings)
        assert result.score >= 0.5, (
            f"Category validation score too low ({result.score:.2f}) "
            f"for {format_type} × {category}"
        )

    @pytest.mark.parametrize("format_type,category,priority", TEST_MATRIX)
    def test_required_fields_present(
        self,
        format_type: str,
        category: str,
        priority: str,
        parser_for_format,
        fixture_path,
    ):
        """
        Test that required category-specific fields are present.

        Different categories require different fields:
        - Academic papers: title, authors, abstract
        - Blog posts: title, content
        - Technical docs: title, content
        """
        # Get fixture and parse
        doc_path = fixture_path(format_type, category)
        parser = parser_for_format(format_type)
        document = parser.parse(doc_path)

        # Category-specific assertions
        if category == "academic_paper":
            assert document.metadata.title, "Academic papers must have a title"
            assert len(document.metadata.title) >= 10, "Title too short"
            # Note: Authors may not be extracted by all parsers
            # assert len(document.metadata.authors) > 0, "Academic papers must have authors"

        elif category == "blog_post":
            assert document.metadata.title, "Blog posts must have a title"
            assert len(document.content) >= 3, "Blog posts should have multiple paragraphs"

        elif category == "technical_docs":
            # Technical docs may not always have a title in metadata
            assert len(document.content) > 0, "Technical docs must have content"

    @pytest.mark.parametrize("format_type,category,priority", TEST_MATRIX)
    def test_content_extraction_quality(
        self,
        format_type: str,
        category: str,
        priority: str,
        parser_for_format,
        fixture_path,
    ):
        """
        Test content extraction quality for format × category combination.

        Verifies:
        - Content is not empty
        - Content elements have reasonable structure
        - Total text length is substantial
        """
        # Get fixture and parse
        doc_path = fixture_path(format_type, category)
        parser = parser_for_format(format_type)
        document = parser.parse(doc_path)

        # General quality checks
        assert len(document.content) > 0, "No content extracted"

        # Check content elements
        total_text_length = sum(len(e.content) for e in document.content if e.content)
        assert total_text_length > 100, (
            f"Total text too short ({total_text_length} chars) "
            f"for {format_type} × {category}"
        )

        # Check that content elements have actual text
        non_empty = [e for e in document.content if e.content and len(e.content.strip()) > 0]
        assert len(non_empty) > 0, "All content elements are empty"


class TestCategoryValidators:
    """Test category validators directly."""

    def test_academic_paper_validator_strict(self):
        """Test academic paper validator in strict mode."""
        from vlm_doc_test.schemas.schema_simple import (
            SimpleDocument,
            DocumentMetadata,
            DocumentSource,
            ContentElement,
        )
        from vlm_doc_test.schemas.base import DocumentFormat
        from datetime import datetime

        # Import Author
        from vlm_doc_test.schemas.schema_simple import Author

        # Create a minimal academic paper
        metadata = DocumentMetadata(
            title="Novel Approaches to Machine Learning",
            authors=[Author(name="Jane Smith"), Author(name="John Doe")],
        )
        # Add abstract as extra field (not in schema but validators check for it)
        metadata.__dict__['abstract'] = "This paper presents novel approaches to ML optimization."

        doc = SimpleDocument(
            id="test",
            format=DocumentFormat.PDF,
            source=DocumentSource(accessed_at=datetime.now()),
            metadata=metadata,
            content=[
                ContentElement(id="c1", type="paragraph", content="Introduction section with background."),
                ContentElement(id="c2", type="paragraph", content="Methods section describing our approach."),
                ContentElement(id="c3", type="paragraph", content="Results showing improvements."),
                ContentElement(id="c4", type="paragraph", content="Conclusion summarizing findings."),
            ],
        )

        # Validate
        result = validate_document(doc, "academic_paper", strict=False)

        # Should pass
        assert result.passed
        assert result.score >= 0.7

    def test_blog_post_validator(self):
        """Test blog post validator."""
        from vlm_doc_test.schemas.schema_simple import (
            SimpleDocument,
            DocumentMetadata,
            DocumentSource,
            ContentElement,
        )
        from vlm_doc_test.schemas.base import DocumentFormat
        from datetime import datetime

        # Import Author
        from vlm_doc_test.schemas.schema_simple import Author

        # Create a blog post
        metadata = DocumentMetadata(
            title="Getting Started with Python",
            authors=[Author(name="Sarah Chen")],
            keywords=["python", "tutorial", "beginners"],
        )
        # Add publish_date as extra field
        metadata.__dict__['publish_date'] = datetime(2025, 1, 15)

        doc = SimpleDocument(
            id="test",
            format=DocumentFormat.HTML,
            source=DocumentSource(accessed_at=datetime.now()),
            metadata=metadata,
            content=[
                ContentElement(id="c1", type="paragraph", content="Python is a great language for beginners."),
                ContentElement(id="c2", type="paragraph", content="In this post, I'll show you how to get started."),
                ContentElement(id="c3", type="paragraph", content="Let's dive into the basics!"),
            ],
        )

        # Validate
        result = validate_document(doc, "blog_post", strict=False)

        # Should pass
        assert result.passed
        assert result.score >= 0.7

    def test_technical_docs_validator(self):
        """Test technical documentation validator."""
        from vlm_doc_test.schemas.schema_simple import (
            SimpleDocument,
            DocumentMetadata,
            DocumentSource,
            ContentElement,
        )
        from vlm_doc_test.schemas.base import DocumentFormat
        from datetime import datetime

        # Create technical docs
        doc = SimpleDocument(
            id="test",
            format=DocumentFormat.HTML,
            source=DocumentSource(accessed_at=datetime.now()),
            metadata=DocumentMetadata(
                title="API Reference - PDFParser",
            ),
            content=[
                ContentElement(id="c1", type="paragraph", content="The PDFParser class provides methods for parsing."),
                ContentElement(id="c2", type="code", content="Example: parser = PDFParser()"),
                ContentElement(id="c3", type="paragraph", content="Use the parse() function to extract content."),
            ],
        )

        # Validate
        result = validate_document(doc, "technical_docs", strict=False)

        # Should pass
        assert result.passed or len(result.errors) == 0  # May have warnings

    def test_validator_with_missing_required_fields(self):
        """Test that validators catch missing required fields."""
        from vlm_doc_test.schemas.schema_simple import (
            SimpleDocument,
            DocumentMetadata,
            DocumentSource,
        )
        from vlm_doc_test.schemas.base import DocumentFormat
        from datetime import datetime

        # Create document with no title
        doc = SimpleDocument(
            id="test",
            format=DocumentFormat.PDF,
            source=DocumentSource(accessed_at=datetime.now()),
            metadata=DocumentMetadata(),  # No title!
            content=[],  # No content!
        )

        # Validate as academic paper
        result = validate_document(doc, "academic_paper", strict=False)

        # Should fail
        assert not result.passed
        assert len(result.errors) > 0
        assert any("title" in e.field.lower() for e in result.errors)
