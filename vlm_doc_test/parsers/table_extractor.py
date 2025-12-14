"""
Enhanced table extraction using pdfplumber.

This module provides advanced table extraction capabilities
beyond basic PyMuPDF table detection.
"""

import pdfplumber
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..schemas.schema_simple import Table
from ..schemas.base import BoundingBox


@dataclass
class TableSettings:
    """Settings for table extraction."""
    vertical_strategy: str = "lines"  # "lines", "lines_strict", "text"
    horizontal_strategy: str = "lines"  # "lines", "lines_strict", "text"
    snap_tolerance: int = 3
    join_tolerance: int = 3
    edge_min_length: int = 3
    min_words_vertical: int = 3
    min_words_horizontal: int = 1
    text_tolerance: int = 3
    intersection_tolerance: int = 3


class TableExtractor:
    """
    Enhanced table extractor using pdfplumber.

    Provides more accurate table extraction than basic PyMuPDF,
    especially for tables without explicit borders.
    """

    def __init__(self, settings: Optional[TableSettings] = None):
        """
        Initialize table extractor.

        Args:
            settings: Table extraction settings
        """
        self.settings = settings or TableSettings()

    def extract_tables_from_pdf(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
    ) -> List[Table]:
        """
        Extract tables from a PDF file.

        Args:
            pdf_path: Path to PDF file
            pages: Specific pages to extract from (1-indexed), None for all

        Returns:
            List of extracted tables
        """
        tables = []

        with pdfplumber.open(pdf_path) as pdf:
            # Determine which pages to process
            if pages is None:
                pages_to_process = range(len(pdf.pages))
            else:
                pages_to_process = [p - 1 for p in pages]  # Convert to 0-indexed

            table_counter = 0

            for page_idx in pages_to_process:
                if page_idx >= len(pdf.pages):
                    continue

                page = pdf.pages[page_idx]
                page_tables = self._extract_from_page(page, page_idx + 1)

                for table in page_tables:
                    table_counter += 1
                    table.id = f"table_{table_counter}"
                    tables.append(table)

        return tables

    def _extract_from_page(self, page, page_number: int) -> List[Table]:
        """Extract tables from a single page."""
        tables = []

        # Create table settings dict
        table_settings = {
            "vertical_strategy": self.settings.vertical_strategy,
            "horizontal_strategy": self.settings.horizontal_strategy,
            "snap_tolerance": self.settings.snap_tolerance,
            "join_tolerance": self.settings.join_tolerance,
            "edge_min_length": self.settings.edge_min_length,
            "min_words_vertical": self.settings.min_words_vertical,
            "min_words_horizontal": self.settings.min_words_horizontal,
            "text_tolerance": self.settings.text_tolerance,
            "intersection_tolerance": self.settings.intersection_tolerance,
        }

        # Find tables on page
        page_tables = page.find_tables(table_settings=table_settings)

        for idx, table_obj in enumerate(page_tables):
            # Extract table data
            extracted = table_obj.extract()

            if not extracted:
                continue

            # Convert to list of lists, handling None values
            rows = []
            for row in extracted:
                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                rows.append(cleaned_row)

            # Get bounding box
            bbox = table_obj.bbox
            bounding_box = BoundingBox(
                page=page_number,
                x=bbox[0],
                y=bbox[1],
                width=bbox[2] - bbox[0],
                height=bbox[3] - bbox[1],
            )

            # Create table object
            table = Table(
                id=f"temp_{idx}",  # Will be replaced by caller
                rows=rows,
                bbox=bounding_box,
            )

            tables.append(table)

        return tables

    def extract_table_from_region(
        self,
        pdf_path: Path,
        page: int,
        bbox: tuple,
    ) -> Optional[Table]:
        """
        Extract a table from a specific region.

        Args:
            pdf_path: Path to PDF
            page: Page number (1-indexed)
            bbox: Bounding box (x0, y0, x1, y1)

        Returns:
            Extracted table or None
        """
        with pdfplumber.open(pdf_path) as pdf:
            if page < 1 or page > len(pdf.pages):
                return None

            pdf_page = pdf.pages[page - 1]

            # Crop page to region
            cropped = pdf_page.crop(bbox)

            # Extract table
            table_settings = {
                "vertical_strategy": self.settings.vertical_strategy,
                "horizontal_strategy": self.settings.horizontal_strategy,
            }

            tables = cropped.find_tables(table_settings=table_settings)

            if not tables:
                return None

            # Get first table
            table_obj = tables[0]
            extracted = table_obj.extract()

            if not extracted:
                return None

            # Convert to rows
            rows = []
            for row in extracted:
                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                rows.append(cleaned_row)

            bounding_box = BoundingBox(
                page=page,
                x=bbox[0],
                y=bbox[1],
                width=bbox[2] - bbox[0],
                height=bbox[3] - bbox[1],
            )

            return Table(
                id="extracted_table",
                rows=rows,
                bbox=bounding_box,
            )

    def detect_table_regions(
        self,
        pdf_path: Path,
        page: int,
    ) -> List[tuple]:
        """
        Detect table regions on a page without extracting content.

        Useful for identifying where tables are located.

        Args:
            pdf_path: Path to PDF
            page: Page number (1-indexed)

        Returns:
            List of bounding boxes (x0, y0, x1, y1)
        """
        regions = []

        with pdfplumber.open(pdf_path) as pdf:
            if page < 1 or page > len(pdf.pages):
                return regions

            pdf_page = pdf.pages[page - 1]

            table_settings = {
                "vertical_strategy": self.settings.vertical_strategy,
                "horizontal_strategy": self.settings.horizontal_strategy,
            }

            tables = pdf_page.find_tables(table_settings=table_settings)

            for table_obj in tables:
                regions.append(table_obj.bbox)

        return regions

    def extract_with_text_strategy(
        self,
        pdf_path: Path,
        pages: Optional[List[int]] = None,
    ) -> List[Table]:
        """
        Extract tables using text-based strategy.

        Useful for tables without borders.

        Args:
            pdf_path: Path to PDF
            pages: Specific pages (1-indexed), None for all

        Returns:
            List of extracted tables
        """
        # Temporarily change settings
        old_vertical = self.settings.vertical_strategy
        old_horizontal = self.settings.horizontal_strategy

        self.settings.vertical_strategy = "text"
        self.settings.horizontal_strategy = "text"

        try:
            return self.extract_tables_from_pdf(pdf_path, pages)
        finally:
            # Restore settings
            self.settings.vertical_strategy = old_vertical
            self.settings.horizontal_strategy = old_horizontal
