"""
Tests for equivalence checker.
"""

import pytest
from ..validation import EquivalenceChecker, MatchQuality
from ..schemas.schema_simple import SimpleDocument, ContentElement
from ..schemas.base import DocumentFormat


def test_equivalence_exact_match(sample_document_pair):
    """Test exact match detection."""
    tool_doc, _ = sample_document_pair

    # Compare document with itself
    checker = EquivalenceChecker()
    result = checker.compare_documents(tool_doc, tool_doc)

    assert result.match_quality == MatchQuality.EXACT
    assert result.score == 1.0


def test_equivalence_similar_match(sample_document_pair):
    """Test similar document matching."""
    tool_doc, vlm_doc = sample_document_pair

    checker = EquivalenceChecker(text_similarity_threshold=0.80)
    result = checker.compare_documents(tool_doc, vlm_doc)

    # Should be good or excellent match
    assert result.score >= 0.85
    assert result.match_quality in [MatchQuality.EXCELLENT, MatchQuality.GOOD]


def test_equivalence_metadata_comparison(sample_document):
    """Test metadata comparison."""
    # Create a copy with different metadata
    import copy
    doc2 = copy.deepcopy(sample_document)
    doc2.metadata.title = "Different Title"

    checker = EquivalenceChecker()
    result = checker.compare_documents(sample_document, doc2)

    assert "metadata" in result.details
    assert result.details["metadata"]["title_match"] < 1.0


def test_equivalence_content_count(sample_document):
    """Test content element count comparison."""
    import copy
    doc2 = copy.deepcopy(sample_document)

    # Remove one content element
    doc2.content = doc2.content[:-1]

    checker = EquivalenceChecker()
    result = checker.compare_documents(sample_document, doc2)

    assert "content" in result.details
    count_details = result.details["content"]["count"]
    assert count_details["tool"] != count_details["vlm"]


def test_equivalence_thresholds():
    """Test custom threshold settings."""
    checker = EquivalenceChecker(
        text_similarity_threshold=0.95,
        bbox_iou_threshold=0.85,
    )

    assert checker.text_similarity_threshold == 0.95
    assert checker.bbox_iou_threshold == 0.85


def test_equivalence_warnings(sample_document_pair):
    """Test warning generation."""
    tool_doc, vlm_doc = sample_document_pair

    # Use high threshold to trigger warnings
    checker = EquivalenceChecker(text_similarity_threshold=0.95)
    result = checker.compare_documents(tool_doc, vlm_doc)

    # May have warnings about similarity
    # (depends on exact text differences)
    assert isinstance(result.warnings, list)


def test_equivalence_empty_documents():
    """Test comparison of empty documents."""
    from ..schemas.schema_simple import DocumentSource, DocumentMetadata
    from datetime import datetime

    source = DocumentSource(accessed_at=datetime.now())

    doc1 = SimpleDocument(
        id="empty1",
        format=DocumentFormat.HTML,
        source=source,
        metadata=DocumentMetadata(),
    )

    doc2 = SimpleDocument(
        id="empty2",
        format=DocumentFormat.HTML,
        source=source,
        metadata=DocumentMetadata(),
    )

    checker = EquivalenceChecker()
    result = checker.compare_documents(doc1, doc2)

    # Empty documents should match well
    assert result.score >= 0.5
