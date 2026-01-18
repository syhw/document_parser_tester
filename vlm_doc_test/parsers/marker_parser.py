"""
Marker-PDF integration for high-fidelity PDF to Markdown conversion.

This module provides a wrapper around marker-pdf for converting PDFs to
structured Markdown with preserved formatting, tables, equations, and links.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..schemas.schema_simple import SimpleDocument, DocumentSource, DocumentMetadata, ContentElement
from ..schemas.base import DocumentFormat, DocumentCategory
from ..utils.markdown_utils import parse_markdown_to_content


@dataclass
class MarkerConfig:
    """Configuration for marker-pdf conversion."""
    use_llm: bool = False  # Use LLM for enhanced accuracy
    extract_images: bool = True
    max_pages: Optional[int] = None
    languages: Optional[List[str]] = None  # e.g., ["en", "fr"]
    disable_ocr: bool = False
    paginate_output: bool = False
    output_format: str = "markdown"  # "markdown", "json", "html"


class MarkerParser:
    """
    High-fidelity PDF parser using marker-pdf.

    Marker converts PDFs to markdown with:
    - Accurate table extraction
    - Equation and math formatting
    - Code block detection
    - Link preservation
    - Multi-language support

    Benchmarks favorably vs Llamaparse and Mathpix.
    """

    def __init__(self, config: Optional[MarkerConfig] = None):
        """
        Initialize marker parser.

        Args:
            config: Marker configuration options
        """
        self.config = config or MarkerConfig()
        self._models = None  # Lazy load models

    def _load_models(self):
        """Lazy load marker models (can be slow on first run)."""
        if self._models is None:
            from marker.models import create_model_dict
            self._models = create_model_dict()
        return self._models

    def parse(
        self,
        pdf_path: Path,
        category: Optional[DocumentCategory] = None,
    ) -> SimpleDocument:
        """
        Parse PDF to SimpleDocument using marker-pdf.

        Args:
            pdf_path: Path to PDF file
            category: Document category

        Returns:
            SimpleDocument with markdown-formatted content
        """
        from marker.converters.pdf import PdfConverter
        from marker.output import text_from_rendered

        # Load models
        models = self._load_models()

        # Create converter
        converter = PdfConverter(
            artifact_dict=models,
        )

        # Convert PDF
        rendered = converter(str(pdf_path))

        # Extract text content
        markdown_text = text_from_rendered(rendered)

        # Create document
        doc_id = pdf_path.stem
        source = DocumentSource(
            file_path=str(pdf_path),
            accessed_at=datetime.now(),
        )

        # Parse markdown into content elements
        content = self._parse_markdown_to_content(markdown_text)

        document = SimpleDocument(
            id=doc_id,
            format=DocumentFormat.PDF,
            source=source,
            category=category,
            metadata=DocumentMetadata(),
            content=content,
        )

        return document

    def parse_to_markdown(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
    ) -> str:
        """
        Parse PDF directly to markdown string.

        Args:
            pdf_path: Path to PDF file
            output_path: Optional path to save markdown

        Returns:
            Markdown text
        """
        from marker.converters.pdf import PdfConverter
        from marker.output import text_from_rendered

        models = self._load_models()
        converter = PdfConverter(artifact_dict=models)
        rendered = converter(str(pdf_path))
        markdown_text = text_from_rendered(rendered)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown_text, encoding='utf-8')

        return markdown_text

    def parse_to_json(
        self,
        pdf_path: Path,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Parse PDF to JSON structure.

        Args:
            pdf_path: Path to PDF file
            output_path: Optional path to save JSON

        Returns:
            Dict with structured content
        """
        from marker.converters.pdf import PdfConverter
        import json

        models = self._load_models()
        converter = PdfConverter(artifact_dict=models)
        rendered = converter(str(pdf_path))

        # Convert to dict
        result = {
            "pdf_path": str(pdf_path),
            "pages": len(rendered.pages),
            "metadata": rendered.metadata if hasattr(rendered, 'metadata') else {},
            "content": str(rendered),
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(result, indent=2), encoding='utf-8')

        return result

    def _parse_markdown_to_content(self, markdown: str) -> List[ContentElement]:
        """
        Parse markdown text into content elements.

        Args:
            markdown: Markdown text

        Returns:
            List of content elements
        """
        return parse_markdown_to_content(markdown, id_prefix="elem", merge_paragraphs=True)

    def batch_convert(
        self,
        pdf_paths: List[Path],
        output_dir: Path,
        format: str = "markdown",
    ) -> List[Path]:
        """
        Batch convert multiple PDFs.

        Args:
            pdf_paths: List of PDF paths
            output_dir: Output directory
            format: Output format ("markdown", "json")

        Returns:
            List of output file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = []

        for pdf_path in pdf_paths:
            output_name = pdf_path.stem + (".md" if format == "markdown" else ".json")
            output_path = output_dir / output_name

            if format == "markdown":
                self.parse_to_markdown(pdf_path, output_path)
            elif format == "json":
                self.parse_to_json(pdf_path, output_path)

            output_paths.append(output_path)

        return output_paths

    def compare_with_pymupdf(
        self,
        pdf_path: Path,
    ) -> Dict[str, Any]:
        """
        Compare marker output with PyMuPDF extraction.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Comparison results
        """
        from ..parsers import PDFParser
        import time

        # Time marker extraction
        start = time.time()
        marker_doc = self.parse(pdf_path)
        marker_time = time.time() - start

        # Time PyMuPDF extraction
        start = time.time()
        pymupdf_parser = PDFParser()
        pymupdf_doc = pymupdf_parser.parse(pdf_path)
        pymupdf_time = time.time() - start

        # Compare results
        comparison = {
            "pdf": str(pdf_path),
            "marker": {
                "content_elements": len(marker_doc.content),
                "time_seconds": round(marker_time, 2),
                "total_text_length": sum(len(e.content) for e in marker_doc.content),
            },
            "pymupdf": {
                "content_elements": len(pymupdf_doc.content),
                "time_seconds": round(pymupdf_time, 2),
                "total_text_length": sum(len(e.content) for e in pymupdf_doc.content),
            },
            "speed_ratio": round(pymupdf_time / marker_time if marker_time > 0 else 0, 2),
        }

        return comparison
