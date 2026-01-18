"""
Docling integration with Granite Vision for local VLM-based PDF parsing.

This module provides document conversion using Docling's VLM pipeline,
which uses IBM's Granite Vision model for local document understanding.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from ..schemas.schema_simple import SimpleDocument, DocumentSource, DocumentMetadata, ContentElement, Table, Figure
from ..schemas.base import DocumentFormat, DocumentCategory, BoundingBox
from ..utils.markdown_utils import parse_markdown_to_content


@dataclass
class DoclingConfig:
    """Configuration for Docling VLM pipeline."""
    use_vlm: bool = True  # Use VLM pipeline
    vlm_model: str = "ibm-granite/granite-docling-258M"  # Default local VLM
    batch_size: int = 1
    extract_tables: bool = True
    extract_figures: bool = True
    ocr_enabled: bool = True


class DoclingParser:
    """
    Document parser using Docling with Granite Vision VLM.

    Docling provides:
    - Local VLM-based document understanding
    - Automatic image description with Granite Vision
    - Table and figure extraction
    - Multi-format support (PDF, DOCX, PPTX, HTML)
    - Fast processing with GPU acceleration

    Uses IBM's Granite-Docling-258M model for on-device analysis.
    """

    def __init__(self, config: Optional[DoclingConfig] = None):
        """
        Initialize Docling parser.

        Args:
            config: Docling configuration options
        """
        self.config = config or DoclingConfig()
        self._converter = None  # Lazy load converter

    def _get_converter(self):
        """Lazy load document converter."""
        if self._converter is None:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat

            if self.config.use_vlm:
                # Use VLM pipeline
                from docling.pipeline.vlm_pipeline import VlmPipeline

                self._converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(
                            pipeline_cls=VlmPipeline,
                        ),
                    }
                )
            else:
                # Standard pipeline without VLM
                self._converter = DocumentConverter()

        return self._converter

    def parse(
        self,
        file_path: Path,
        category: Optional[DocumentCategory] = None,
    ) -> SimpleDocument:
        """
        Parse document using Docling.

        Args:
            file_path: Path to document file
            category: Document category

        Returns:
            SimpleDocument with extracted content
        """
        converter = self._get_converter()

        # Convert document
        result = converter.convert(str(file_path))
        docling_doc = result.document

        # Create SimpleDocument
        doc_id = file_path.stem
        source = DocumentSource(
            file_path=str(file_path),
            accessed_at=datetime.now(),
        )

        # Extract metadata
        metadata = self._extract_metadata(docling_doc)

        # Extract content elements
        content = self._extract_content(docling_doc)

        # Extract tables
        tables = self._extract_tables(docling_doc)

        # Extract figures
        figures = self._extract_figures(docling_doc)

        document = SimpleDocument(
            id=doc_id,
            format=self._get_format(file_path),
            source=source,
            category=category,
            metadata=metadata,
            content=content,
            tables=tables,
            figures=figures,
        )

        return document

    def parse_to_markdown(
        self,
        file_path: Path,
        output_path: Optional[Path] = None,
    ) -> str:
        """
        Parse document to markdown using Docling.

        Args:
            file_path: Path to document file
            output_path: Optional path to save markdown

        Returns:
            Markdown text
        """
        converter = self._get_converter()
        result = converter.convert(str(file_path))
        markdown = result.document.export_to_markdown()

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(markdown, encoding='utf-8')

        return markdown

    def parse_to_dict(
        self,
        file_path: Path,
    ) -> Dict[str, Any]:
        """
        Parse document to dictionary structure.

        Args:
            file_path: Path to document file

        Returns:
            Dict with document content
        """
        converter = self._get_converter()
        result = converter.convert(str(file_path))
        return result.document.model_dump()

    def _get_format(self, file_path: Path) -> DocumentFormat:
        """Determine document format from file extension."""
        suffix = file_path.suffix.lower()
        format_map = {
            '.pdf': DocumentFormat.PDF,
            '.html': DocumentFormat.HTML,
            '.htm': DocumentFormat.HTML,
            '.docx': DocumentFormat.DOCX,
            '.pptx': DocumentFormat.PPTX,
            '.md': DocumentFormat.MARKDOWN,
        }
        return format_map.get(suffix, DocumentFormat.OTHER)

    def _extract_metadata(self, docling_doc) -> DocumentMetadata:
        """Extract metadata from Docling document."""
        metadata = DocumentMetadata()

        # Try to extract title
        try:
            if hasattr(docling_doc, 'title'):
                metadata.title = docling_doc.title
        except (AttributeError, TypeError, ValueError):
            # Document may not have accessible title attribute
            pass

        return metadata

    def _extract_content(self, docling_doc) -> List[ContentElement]:
        """Extract content elements from Docling document."""
        # Docling provides structured content via markdown export
        try:
            text_content = docling_doc.export_to_markdown()
            # Use shared markdown parser (merge_paragraphs=False for line-by-line)
            return parse_markdown_to_content(
                text_content,
                id_prefix="elem",
                merge_paragraphs=False,
            )
        except Exception:
            # Fallback to simple text extraction
            try:
                text = str(docling_doc)
                return [ContentElement(
                    id="elem_1",
                    type="paragraph",
                    content=text,
                )]
            except (TypeError, ValueError, AttributeError):
                # Could not convert document to string
                return []

    def _extract_tables(self, docling_doc) -> List[Table]:
        """Extract tables from Docling document."""
        tables = []

        # Docling has table detection
        # This is a simplified extraction
        try:
            if hasattr(docling_doc, 'tables'):
                for idx, table_obj in enumerate(docling_doc.tables, 1):
                    # Try to extract table data
                    try:
                        table = Table(
                            id=f"table_{idx}",
                            rows=[],  # Would need proper conversion
                        )
                        tables.append(table)
                    except (TypeError, ValueError, AttributeError):
                        # Skip malformed table objects
                        continue
        except (AttributeError, TypeError):
            # Document may not have tables attribute or it's not iterable
            pass

        return tables

    def _extract_figures(self, docling_doc) -> List[Figure]:
        """Extract figures from Docling document."""
        figures = []

        # Docling with VLM can describe figures
        try:
            if hasattr(docling_doc, 'pictures'):
                for idx, pic_obj in enumerate(docling_doc.pictures, 1):
                    # VLM provides automatic descriptions
                    caption = None
                    if hasattr(pic_obj, 'description'):
                        caption = pic_obj.description

                    figure = Figure(
                        id=f"figure_{idx}",
                        caption=caption,
                    )
                    figures.append(figure)
        except (AttributeError, TypeError):
            # Document may not have pictures attribute or it's not iterable
            pass

        return figures

    def batch_convert(
        self,
        file_paths: List[Path],
        output_dir: Path,
        format: str = "markdown",
    ) -> List[Path]:
        """
        Batch convert multiple documents.

        Args:
            file_paths: List of document paths
            output_dir: Output directory
            format: Output format ("markdown", "json")

        Returns:
            List of output file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_paths = []

        for file_path in file_paths:
            output_name = file_path.stem + (".md" if format == "markdown" else ".json")
            output_path = output_dir / output_name

            if format == "markdown":
                self.parse_to_markdown(file_path, output_path)
            elif format == "json":
                import json
                data = self.parse_to_dict(file_path)
                output_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

            output_paths.append(output_path)

        return output_paths

    def compare_with_marker(
        self,
        pdf_path: Path,
    ) -> Dict[str, Any]:
        """
        Compare Docling output with Marker-PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Comparison results
        """
        from .marker_parser import MarkerParser
        import time

        # Time Docling extraction
        start = time.time()
        docling_doc = self.parse(pdf_path)
        docling_time = time.time() - start

        # Time Marker extraction
        start = time.time()
        marker_parser = MarkerParser()
        marker_doc = marker_parser.parse(pdf_path)
        marker_time = time.time() - start

        # Compare results
        comparison = {
            "pdf": str(pdf_path),
            "docling_vlm": {
                "content_elements": len(docling_doc.content),
                "tables": len(docling_doc.tables),
                "figures": len(docling_doc.figures),
                "time_seconds": round(docling_time, 2),
                "uses_local_vlm": self.config.use_vlm,
            },
            "marker": {
                "content_elements": len(marker_doc.content),
                "tables": len(marker_doc.tables),
                "figures": len(marker_doc.figures),
                "time_seconds": round(marker_time, 2),
            },
            "speed_ratio": round(marker_time / docling_time if docling_time > 0 else 0, 2),
        }

        return comparison
