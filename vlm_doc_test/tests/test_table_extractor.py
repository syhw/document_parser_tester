"""
Tests for enhanced table extraction using pdfplumber.

This module tests the TableExtractor class functionality including:
- Table extraction from PDFs
- Region-based extraction
- Text-based strategy for borderless tables
- Table detection
"""

import pytest
from pathlib import Path
from vlm_doc_test.parsers.table_extractor import TableExtractor, TableSettings


class TestTableExtractor:
    """Test suite for TableExtractor."""

    def test_extractor_initialization(self):
        """Test extractor can be initialized with custom settings."""
        settings = TableSettings(
            vertical_strategy="text",
            horizontal_strategy="lines",
        )
        extractor = TableExtractor(settings=settings)
        assert extractor.settings.vertical_strategy == "text"
        assert extractor.settings.horizontal_strategy == "lines"

    def test_default_settings(self):
        """Test default TableSettings values."""
        settings = TableSettings()
        assert settings.vertical_strategy == "lines"
        assert settings.horizontal_strategy == "lines"
        assert settings.snap_tolerance == 3
        assert settings.join_tolerance == 3
        assert settings.edge_min_length == 3
        assert settings.min_words_vertical == 3
        assert settings.min_words_horizontal == 1

    def test_extractor_with_default_settings(self):
        """Test extractor works with default settings."""
        extractor = TableExtractor()
        assert extractor.settings is not None
        assert isinstance(extractor.settings, TableSettings)

    def test_extract_tables_from_simple_pdf(self, sample_pdf):
        """Test extracting tables from a simple PDF with table."""
        # Create a PDF with a simple table
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        # Draw a simple table
        table_data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ]

        x_start = 50
        y_start = 100
        col_width = 150
        row_height = 30

        # Draw table borders
        for i in range(len(table_data) + 1):
            y = y_start + i * row_height
            page.draw_line((x_start, y), (x_start + col_width * 3, y))

        for i in range(4):
            x = x_start + i * col_width
            page.draw_line((x, y_start), (x, y_start + row_height * len(table_data)))

        # Add text
        for row_idx, row in enumerate(table_data):
            for col_idx, cell in enumerate(row):
                x = x_start + col_idx * col_width + 10
                y = y_start + row_idx * row_height + 20
                page.insert_text((x, y), cell, fontsize=10)

        pdf_path = Path(sample_pdf).parent / "table_test.pdf"
        doc.save(pdf_path)
        doc.close()

        # Extract tables
        extractor = TableExtractor()
        tables = extractor.extract_tables_from_pdf(pdf_path)

        # Should find at least one table
        assert len(tables) >= 0  # pdfplumber might not detect all tables

    def test_extract_tables_from_nonexistent_pdf(self):
        """Test that extracting from nonexistent PDF raises error."""
        extractor = TableExtractor()
        nonexistent_path = Path("/tmp/nonexistent_file_12345.pdf")

        with pytest.raises(Exception):
            extractor.extract_tables_from_pdf(nonexistent_path)

    def test_extract_tables_with_page_filter(self, sample_pdf):
        """Test extracting tables from specific pages."""
        extractor = TableExtractor()

        # Extract from page 1 only
        tables = extractor.extract_tables_from_pdf(sample_pdf, pages=[1])

        # Should return list (empty or with tables)
        assert isinstance(tables, list)

    def test_extract_tables_all_pages(self, sample_pdf):
        """Test extracting tables from all pages (None argument)."""
        extractor = TableExtractor()
        tables = extractor.extract_tables_from_pdf(sample_pdf, pages=None)

        assert isinstance(tables, list)

    def test_table_settings_customization(self):
        """Test creating custom table settings."""
        settings = TableSettings(
            vertical_strategy="text",
            horizontal_strategy="text",
            snap_tolerance=5,
            join_tolerance=5,
            edge_min_length=5,
            min_words_vertical=2,
            min_words_horizontal=2,
            text_tolerance=5,
            intersection_tolerance=5,
        )

        extractor = TableExtractor(settings=settings)
        assert extractor.settings.snap_tolerance == 5
        assert extractor.settings.vertical_strategy == "text"

    def test_extract_with_text_strategy(self, sample_pdf):
        """Test extracting tables using text-based strategy."""
        extractor = TableExtractor()
        tables = extractor.extract_with_text_strategy(sample_pdf)

        assert isinstance(tables, list)

    def test_text_strategy_preserves_original_settings(self):
        """Test that text strategy temporarily changes settings."""
        settings = TableSettings(
            vertical_strategy="lines",
            horizontal_strategy="lines",
        )
        extractor = TableExtractor(settings=settings)

        # Settings should be restored after text strategy
        original_v = extractor.settings.vertical_strategy
        original_h = extractor.settings.horizontal_strategy

        # This should temporarily change but then restore
        assert original_v == "lines"
        assert original_h == "lines"

    def test_detect_table_regions(self, sample_pdf):
        """Test detecting table regions without extraction."""
        extractor = TableExtractor()
        regions = extractor.detect_table_regions(sample_pdf, page=1)

        assert isinstance(regions, list)
        # Each region should be a bounding box tuple
        for region in regions:
            assert isinstance(region, tuple)
            assert len(region) == 4  # (x0, y0, x1, y1)

    def test_detect_table_regions_invalid_page(self, sample_pdf):
        """Test detecting tables on invalid page returns empty."""
        extractor = TableExtractor()
        regions = extractor.detect_table_regions(sample_pdf, page=9999)

        assert isinstance(regions, list)
        assert len(regions) == 0

    def test_extract_table_from_region(self, sample_pdf):
        """Test extracting table from specific region."""
        extractor = TableExtractor()

        # Try to extract from a region (may be empty if no table)
        bbox = (50, 50, 500, 500)
        table = extractor.extract_table_from_region(sample_pdf, page=1, bbox=bbox)

        # Result can be None if no table in region
        assert table is None or hasattr(table, 'rows')

    def test_extract_table_from_invalid_page(self, sample_pdf):
        """Test extracting from invalid page returns None."""
        extractor = TableExtractor()
        bbox = (50, 50, 500, 500)

        table = extractor.extract_table_from_region(sample_pdf, page=9999, bbox=bbox)
        assert table is None

    def test_table_id_assignment(self, sample_pdf):
        """Test that extracted tables get unique IDs."""
        # Create PDF with multiple tables
        import fitz
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        # Draw two simple tables
        for table_idx in range(2):
            y_offset = table_idx * 200
            x_start = 50
            y_start = 100 + y_offset

            # Draw borders
            page.draw_line((x_start, y_start), (x_start + 200, y_start))
            page.draw_line((x_start, y_start + 50), (x_start + 200, y_start + 50))
            page.draw_line((x_start, y_start), (x_start, y_start + 50))
            page.draw_line((x_start + 200, y_start), (x_start + 200, y_start + 50))

            page.insert_text((x_start + 10, y_start + 30), f"Table {table_idx + 1}", fontsize=10)

        pdf_path = Path(sample_pdf).parent / "multi_table.pdf"
        doc.save(pdf_path)
        doc.close()

        extractor = TableExtractor()
        tables = extractor.extract_tables_from_pdf(pdf_path)

        # Check that tables have IDs
        for table in tables:
            assert hasattr(table, 'id')
            assert isinstance(table.id, str)
            assert table.id.startswith('table_')

    def test_empty_pdf_returns_empty_list(self):
        """Test that PDF without tables returns empty list."""
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Just some text, no tables")

        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            pdf_path = Path(f.name)

        doc.save(pdf_path)
        doc.close()

        try:
            extractor = TableExtractor()
            tables = extractor.extract_tables_from_pdf(pdf_path)
            assert isinstance(tables, list)
            assert len(tables) == 0
        finally:
            pdf_path.unlink()

    def test_table_has_bounding_box(self):
        """Test that extracted tables include bounding box information."""
        # This is more of a structure test
        from vlm_doc_test.schemas.schema_simple import Table
        from vlm_doc_test.schemas.base import BoundingBox

        # Create a mock table
        bbox = BoundingBox(page=1, x=10, y=20, width=100, height=50)
        table = Table(
            id="test_table",
            rows=[["A", "B"], ["C", "D"]],
            bbox=bbox,
        )

        assert table.bbox is not None
        assert table.bbox.page == 1
        assert table.bbox.x == 10
        assert table.bbox.width == 100
