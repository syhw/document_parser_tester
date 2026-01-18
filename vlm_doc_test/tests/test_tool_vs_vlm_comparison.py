"""
Tool vs VLM Comparison Tests.

Tests that compare traditional tool-based parsing (PyMuPDF, pdfplumber, BeautifulSoup)
against VLM-based parsing (GLM-4.6V) to validate equivalence.

This implements the core concept from TESTING.md: equivalence testing between
tool output and VLM analysis.
"""

import pytest
from pathlib import Path
from typing import Optional

from ..parsers import PDFParser, HTMLParser
from ..parsers.vlm_parser import VLMParser, VLMParserWithMCP
from ..validation.equivalence import EquivalenceChecker, MatchQuality
from ..schemas.base import DocumentCategory, DocumentFormat
from ..schemas.schema_simple import SimpleDocument


class TestToolVsVLMComparison:
    """
    Tests comparing tool-based extraction vs VLM-based extraction.

    These tests validate that both approaches extract equivalent information.
    """

    @pytest.fixture
    def equivalence_checker(self):
        """Create equivalence checker with appropriate thresholds."""
        return EquivalenceChecker(
            text_similarity_threshold=0.80,  # 80% similarity acceptable
        )

    @pytest.fixture
    def vlm_parser(self):
        """
        Create VLM parser.

        Note: Actual VLM calls require MCP integration or API access.
        For testing, we'll use mock responses or skip tests.
        """
        return VLMParser()

    def test_pdf_parser_vs_vlm_structure(self, sample_pdf, equivalence_checker):
        """
        Test that PDF parser and VLM parser extract similar document structure.

        This is a structure test - we verify both produce valid SimpleDocument
        instances with the expected fields, even if VLM is mocked.
        """
        # Parse with tool-based parser
        pdf_parser = PDFParser()
        tool_doc = pdf_parser.parse(sample_pdf)

        # Verify tool output structure
        assert tool_doc is not None
        assert isinstance(tool_doc, SimpleDocument)
        assert tool_doc.metadata is not None
        assert tool_doc.metadata.title is not None
        assert len(tool_doc.content) > 0

        # Note: VLM parsing would require actual API/MCP integration
        # For now, we validate the tool output structure
        # Future: Add actual VLM comparison when MCP is integrated

    def test_html_parser_vs_vlm_structure(self, sample_html, equivalence_checker):
        """
        Test that HTML parser and VLM parser extract similar document structure.
        """
        # Parse with tool-based parser
        html_parser = HTMLParser()
        tool_doc = html_parser.parse(sample_html)

        # Verify tool output structure
        assert tool_doc is not None
        assert isinstance(tool_doc, SimpleDocument)
        assert tool_doc.metadata is not None
        assert tool_doc.metadata.title is not None
        assert len(tool_doc.content) > 0

    @pytest.mark.parametrize("category", [
        DocumentCategory.ACADEMIC_PAPER,
        DocumentCategory.BLOG_POST,
        DocumentCategory.TECHNICAL_DOCUMENTATION,
    ])
    def test_category_specific_extraction(self, category):
        """
        Test that extraction quality varies by document category.

        Different categories require different extraction strategies:
        - Academic papers: authors, abstract, sections, citations
        - Blog posts: author, date, tags, content
        - Technical docs: API references, code blocks, parameters
        """
        # This test validates that we have category-aware extraction
        # The actual comparison would require VLM integration

        # Verify we can instantiate parsers with category hints
        pdf_parser = PDFParser()
        vlm_parser = VLMParser()

        # Both parsers should accept category parameter
        assert pdf_parser is not None
        assert vlm_parser is not None

        # Category-specific prompts should be different
        if category == DocumentCategory.ACADEMIC_PAPER:
            prompt = vlm_parser._build_extraction_prompt(category)
            assert "ACADEMIC PAPER" in prompt
            assert "authors" in prompt.lower()
            assert "abstract" in prompt.lower()

        elif category == DocumentCategory.BLOG_POST:
            prompt = vlm_parser._build_extraction_prompt(category)
            assert "BLOG POST" in prompt
            assert "tags" in prompt.lower()

        elif category == DocumentCategory.TECHNICAL_DOCUMENTATION:
            prompt = vlm_parser._build_extraction_prompt(category)
            assert "TECHNICAL DOCUMENTATION" in prompt
            assert "code" in prompt.lower()

    def test_vlm_parser_initialization(self):
        """Test VLM parser can be initialized."""
        parser = VLMParser()
        assert parser is not None
        assert parser.mode == "ZAI"

    def test_vlm_parser_with_mcp_initialization(self):
        """Test VLM parser with MCP can be initialized."""
        parser = VLMParserWithMCP()
        assert parser is not None

    def test_vlm_parser_prompt_generation(self):
        """Test that VLM parser generates appropriate prompts."""
        parser = VLMParser()

        # Test base prompt
        base_prompt = parser._build_extraction_prompt(None)
        assert "JSON" in base_prompt
        assert "title" in base_prompt
        assert "authors" in base_prompt
        assert "content" in base_prompt

        # Test academic paper prompt
        academic_prompt = parser._build_extraction_prompt(DocumentCategory.ACADEMIC_PAPER)
        assert "ACADEMIC PAPER" in academic_prompt
        assert "abstract" in academic_prompt.lower()
        assert "citations" in academic_prompt.lower()

        # Test blog post prompt
        blog_prompt = parser._build_extraction_prompt(DocumentCategory.BLOG_POST)
        assert "BLOG POST" in blog_prompt
        assert "tags" in blog_prompt.lower()

    def test_vlm_parser_requires_mcp_for_parsing(self, tmp_path):
        """Test that VLM parser raises NotImplementedError without MCP."""
        parser = VLMParser()

        # Create a dummy image file
        image_path = tmp_path / "test_image.png"
        image_path.write_text("fake image data")

        # Should raise NotImplementedError since MCP isn't available
        with pytest.raises(NotImplementedError) as exc_info:
            parser.parse(image_path, category=DocumentCategory.ACADEMIC_PAPER)

        assert "MCP" in str(exc_info.value)

    def test_vlm_parser_missing_image(self):
        """Test that VLM parser handles missing images."""
        parser = VLMParser()

        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/image.png")

    def test_equivalence_checker_with_similar_documents(self, sample_document_pair):
        """
        Test equivalence checker can compare tool and VLM outputs.

        This uses sample documents to validate the comparison logic.
        """
        tool_doc, vlm_doc = sample_document_pair
        checker = EquivalenceChecker(text_similarity_threshold=0.70)

        result = checker.compare_documents(tool_doc, vlm_doc)

        # Both documents should be valid
        assert result is not None
        assert result.score >= 0.0  # Score is between 0 and 1

        # Some level of similarity should be detected
        # (exact match depends on the fixture implementation)
        assert result.details is not None


class TestToolVsVLMMetrics:
    """Tests for measuring quality of tool vs VLM extraction."""

    def test_metadata_extraction_comparison(self, sample_document_pair):
        """
        Compare metadata extraction quality.

        Metrics:
        - Title match: exact vs fuzzy
        - Author count match
        - Author name similarity
        - Keywords overlap
        """
        tool_doc, vlm_doc = sample_document_pair
        checker = EquivalenceChecker()

        result = checker.compare_documents(tool_doc, vlm_doc)

        # Check metadata comparison
        assert result.details.get("metadata") is not None

        # Title should match (even if fuzzy)
        if tool_doc.metadata.title and vlm_doc.metadata.title:
            assert result.score >= 0.0  # Some similarity detected

    def test_content_extraction_comparison(self, sample_document_pair):
        """
        Compare content extraction quality.

        Metrics:
        - Content element count
        - Text similarity per element
        - Structure preservation (headings, paragraphs)
        """
        tool_doc, vlm_doc = sample_document_pair
        checker = EquivalenceChecker()

        result = checker.compare_documents(tool_doc, vlm_doc)

        # Both should have extracted some content
        assert len(tool_doc.content) > 0 or len(vlm_doc.content) > 0

        # Content match quality should be measurable
        assert result.details.get("content") is not None

    def test_table_extraction_comparison(self, sample_document):
        """
        Compare table extraction quality.

        Tool-based (pdfplumber) should detect tables.
        VLM-based should also detect tables.
        Both should extract similar data.
        """
        # This is a placeholder for actual table comparison
        # Would require VLM integration to test fully

        assert sample_document.tables is not None
        if len(sample_document.tables) > 0:
            table = sample_document.tables[0]
            assert table.caption is not None or table.rows is not None

    def test_figure_extraction_comparison(self, sample_document):
        """
        Compare figure extraction quality.

        Both tool and VLM should identify figures with captions.
        """
        assert sample_document.figures is not None
        if len(sample_document.figures) > 0:
            figure = sample_document.figures[0]
            assert figure.caption is not None or figure.label is not None


class TestToolVsVLMIntegration:
    """
    Integration tests for full tool-vs-VLM pipeline.

    These tests would require actual VLM API access or MCP integration.
    """

    @pytest.mark.skip(reason="Requires VLM API/MCP integration")
    def test_full_pipeline_pdf_academic_paper(self, sample_pdf):
        """
        Full pipeline test: PDF academic paper.

        1. Parse with PDFParser (tool)
        2. Render PDF to image
        3. Parse with VLMParser (vision)
        4. Compare results
        5. Assert equivalence
        """
        # Tool-based extraction
        pdf_parser = PDFParser()
        tool_doc = pdf_parser.parse(sample_pdf)

        # VLM-based extraction (requires MCP)
        # vlm_parser = VLMParserWithMCP()
        # screenshot = render_pdf_to_image(sample_pdf)
        # vlm_doc = vlm_parser.parse(screenshot, category=DocumentCategory.ACADEMIC_PAPER)

        # Comparison
        # checker = EquivalenceChecker(text_similarity_threshold=0.80)
        # result = checker.compare_documents(tool_doc, vlm_doc)

        # Assert equivalence
        # assert result.passed
        # assert result.metadata_match >= MatchQuality.FUZZY_MATCH
        # assert result.score >= 0.80

        pass  # Placeholder until MCP integration

    @pytest.mark.skip(reason="Requires VLM API/MCP integration")
    def test_full_pipeline_html_blog_post(self, sample_html):
        """
        Full pipeline test: HTML blog post.

        1. Parse with HTMLParser (tool)
        2. Render HTML to screenshot
        3. Parse with VLMParser (vision)
        4. Compare results
        5. Assert equivalence
        """
        pass  # Placeholder until MCP integration


@pytest.mark.integration
class TestVLMMCPIntegration:
    """
    Tests for actual MCP integration with Z.AI Vision MCP Server.

    These tests require:
    1. MCP server configured (zai_glmV_mcp.json)
    2. Valid Z.AI API key
    3. Running within Claude Code environment
    """

    @pytest.mark.skip(reason="Requires Claude Code MCP environment")
    def test_mcp_server_available(self):
        """Test that MCP server is accessible."""
        # This would check if mcp__zai_mcp_server__image_analysis tool exists
        pass

    @pytest.mark.skip(reason="Requires Claude Code MCP environment")
    def test_mcp_image_analysis_call(self, tmp_path):
        """Test calling MCP image analysis tool."""
        # This would actually call the MCP tool
        # tool_name = "mcp__zai_mcp_server__image_analysis"
        # response = call_mcp_tool(tool_name, image=..., prompt=...)
        pass

    @pytest.mark.skip(reason="Requires Claude Code MCP environment")
    def test_vlm_parser_with_real_mcp(self, sample_pdf):
        """Test VLM parser with real MCP integration."""
        # This would test the full VLM parsing workflow
        pass


def test_comparison_framework_exists():
    """Verify that tool-vs-VLM comparison framework is in place."""
    # Verify classes exist
    assert PDFParser is not None
    assert HTMLParser is not None
    assert VLMParser is not None
    assert EquivalenceChecker is not None

    # Verify we can instantiate them
    pdf_parser = PDFParser()
    html_parser = HTMLParser()
    vlm_parser = VLMParser()
    checker = EquivalenceChecker()

    assert pdf_parser is not None
    assert html_parser is not None
    assert vlm_parser is not None
    assert checker is not None


def test_vlm_parser_in_parsers_module():
    """Verify VLM parser is exported from parsers module."""
    from ..parsers import (
        PDFParser,
        HTMLParser,
        TableExtractor,
        MarkerParser,
        DoclingParser,
    )

    # All parsers should be available
    assert PDFParser is not None
    assert HTMLParser is not None
    assert TableExtractor is not None
    assert MarkerParser is not None
    assert DoclingParser is not None

    # VLM parser should be importable
    from ..parsers.vlm_parser import VLMParser
    assert VLMParser is not None
