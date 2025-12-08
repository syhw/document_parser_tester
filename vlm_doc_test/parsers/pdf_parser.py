"""
PDF parser using PyMuPDF (fitz) for coordinate-aware text extraction.

This parser provides fast, deterministic extraction of text, structure,
and visual elements from PDF documents with bounding box information.
"""

import pymupdf as fitz
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Figure,
    Table,
    Author,
)
from ..schemas.base import DocumentFormat, DocumentCategory, BoundingBox


class PDFParser:
    """
    PDF parser using PyMuPDF for text and structure extraction.

    Features:
    - Coordinate-aware text extraction with bounding boxes
    - Page-by-page processing
    - Figure/image detection
    - Basic metadata extraction
    - Table detection (simple approach)
    """

    def __init__(self):
        """Initialize the PDF parser."""
        self.doc = None
        self.file_path = None

    def parse(
        self,
        pdf_path: str,
        extract_images: bool = True,
        extract_tables: bool = True,
        category: Optional[DocumentCategory] = None,
    ) -> SimpleDocument:
        """
        Parse a PDF file into a SimpleDocument.

        Args:
            pdf_path: Path to the PDF file
            extract_images: Whether to extract figure information
            extract_tables: Whether to detect and extract tables
            category: Optional document category (academic_paper, etc.)

        Returns:
            SimpleDocument with extracted content
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.file_path = str(pdf_path.absolute())
        self.doc = fitz.open(self.file_path)

        # Generate document ID from filename
        doc_id = pdf_path.stem

        # Extract metadata
        metadata = self._extract_metadata()

        # Extract content elements (text blocks with structure)
        content = self._extract_content()

        # Extract figures
        figures = []
        if extract_images:
            figures = self._extract_figures()

        # Extract tables (basic detection for now)
        tables = []
        if extract_tables:
            tables = self._detect_tables()

        # Create document
        document = SimpleDocument(
            id=doc_id,
            format=DocumentFormat.PDF,
            category=category,
            source=DocumentSource(
                file_path=self.file_path,
                accessed_at=datetime.now(),
            ),
            metadata=metadata,
            content=content,
            figures=figures,
            tables=tables,
        )

        self.doc.close()
        self.doc = None

        return document

    def _extract_metadata(self) -> DocumentMetadata:
        """Extract metadata from PDF."""
        meta = self.doc.metadata

        # Parse authors if present
        authors = []
        if meta.get("author"):
            # Simple parsing - split by comma or semicolon
            author_names = meta["author"].replace(";", ",").split(",")
            authors = [Author(name=name.strip()) for name in author_names if name.strip()]

        # Parse date if present
        date = None
        if meta.get("creationDate"):
            try:
                # PyMuPDF date format: D:YYYYMMDDHHmmSSOHH'mm
                date_str = meta["creationDate"]
                if date_str.startswith("D:"):
                    date_str = date_str[2:16]  # YYYYMMDDHHmmSS
                    date = datetime.strptime(date_str, "%Y%m%d%H%M%S")
            except (ValueError, IndexError):
                pass

        # Extract keywords
        keywords = []
        if meta.get("keywords"):
            keywords = [k.strip() for k in meta["keywords"].split(",") if k.strip()]

        return DocumentMetadata(
            title=meta.get("title"),
            authors=authors,
            date=date,
            keywords=keywords,
        )

    def _extract_content(self) -> List[ContentElement]:
        """
        Extract content elements with structure detection.

        Uses PyMuPDF's text block detection to identify paragraphs
        and attempts to identify headings based on font size.
        """
        content = []

        for page_num, page in enumerate(self.doc, start=1):
            # Get text blocks with position information
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

            # Calculate average font size for this page (for heading detection)
            font_sizes = []
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            font_sizes.append(span.get("size", 12))

            avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12

            # Process each text block
            for block_idx, block in enumerate(blocks.get("blocks", [])):
                if block.get("type") != 0:  # Skip non-text blocks
                    continue

                bbox_coords = block.get("bbox", [0, 0, 0, 0])
                bbox = BoundingBox(
                    page=page_num,
                    x=bbox_coords[0],
                    y=bbox_coords[1],
                    width=bbox_coords[2] - bbox_coords[0],
                    height=bbox_coords[3] - bbox_coords[1],
                )

                # Extract text from all lines in block
                text_parts = []
                max_font_size = 0

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text_parts.append(span.get("text", ""))
                        max_font_size = max(max_font_size, span.get("size", 12))

                text = " ".join(text_parts).strip()
                if not text:
                    continue

                # Detect if this is likely a heading (larger font size)
                is_heading = max_font_size > avg_font_size * 1.2
                element_type = "heading" if is_heading else "paragraph"

                # Simple heading level detection (larger = higher level)
                level = None
                if is_heading:
                    size_ratio = max_font_size / avg_font_size
                    if size_ratio > 1.8:
                        level = 1
                    elif size_ratio > 1.4:
                        level = 2
                    else:
                        level = 3

                content.append(ContentElement(
                    id=f"p{page_num}_b{block_idx}",
                    type=element_type,
                    content=text,
                    bbox=bbox,
                    level=level,
                ))

        return content

    def _extract_figures(self) -> List[Figure]:
        """
        Extract figures (images) from the PDF.

        Returns basic figure information with bounding boxes.
        """
        figures = []

        for page_num, page in enumerate(self.doc, start=1):
            # Get image list for this page
            image_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]

                # Get image bounding box
                # Note: This gets the first occurrence of the image on the page
                rects = page.get_image_rects(xref)
                if rects:
                    rect = rects[0]
                    bbox = BoundingBox(
                        page=page_num,
                        x=rect.x0,
                        y=rect.y0,
                        width=rect.width,
                        height=rect.height,
                    )

                    figures.append(Figure(
                        id=f"fig_p{page_num}_i{img_idx}",
                        bbox=bbox,
                        # Caption and label detection would require more analysis
                    ))

        return figures

    def _detect_tables(self) -> List[Table]:
        """
        Basic table detection using PyMuPDF.

        This is a simple heuristic-based approach. For production,
        consider using pdfplumber or dedicated table extraction tools.
        """
        tables = []

        for page_num, page in enumerate(self.doc, start=1):
            # Look for tables using find_tables() if available
            try:
                # PyMuPDF 1.23+ has find_tables()
                page_tables = page.find_tables()

                for tab_idx, table in enumerate(page_tables):
                    bbox_coords = table.bbox
                    bbox = BoundingBox(
                        page=page_num,
                        x=bbox_coords[0],
                        y=bbox_coords[1],
                        width=bbox_coords[2] - bbox_coords[0],
                        height=bbox_coords[3] - bbox_coords[1],
                    )

                    # Extract table data
                    rows = []
                    try:
                        table_data = table.extract()
                        rows = [[str(cell) if cell else "" for cell in row] for row in table_data]
                    except Exception:
                        pass

                    tables.append(Table(
                        id=f"tab_p{page_num}_t{tab_idx}",
                        bbox=bbox,
                        rows=rows,
                    ))
            except AttributeError:
                # Older PyMuPDF version without find_tables()
                # Could implement basic table detection heuristics here
                pass

        return tables

    def get_page_count(self, pdf_path: str) -> int:
        """Get the number of pages in a PDF without full parsing."""
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count

    def extract_page_text(self, pdf_path: str, page_num: int) -> str:
        """Extract plain text from a specific page (1-indexed)."""
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            raise ValueError(f"Page {page_num} out of range (1-{len(doc)})")

        page = doc[page_num - 1]
        text = page.get_text()
        doc.close()
        return text
