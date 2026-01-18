"""
Tests for PDF Parsing Comparison Webapp.

Tests the Flask application and its API endpoints for comparing
VLM-based vs Tool-based document parsing with bounding box visualization.
"""

import pytest
import json
import base64
import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import patch

try:
    from flask import Flask
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from ..schemas.base import DocumentCategory

# Add webapp to path for testing
WEBAPP_PATH = str(Path(__file__).parent.parent.parent / "webapp")


@pytest.fixture
def sample_pdf_with_content(tmp_path):
    """
    Create a sample PDF with various content types for webapp testing.
    
    Includes headings, paragraphs, tables, and images.
    """
    import pymupdf as fitz
    
    pdf_path = tmp_path / "test_content.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Title
    page.insert_text((50, 50), "Test Document Title", fontsize=24, fontname="helv")
    
    # Heading
    page.insert_text((50, 100), "Section 1", fontsize=18, fontname="helv")
    
    # Paragraph
    page.insert_textbox(
        fitz.Rect(50, 130, 545, 180),
        "This is a test paragraph with some text content for parsing.",
        fontsize=12,
        fontname="helv",
    )
    
    # Another heading
    page.insert_text((50, 200), "Section 2", fontsize=18, fontname="helv")
    
    # More content
    page.insert_textbox(
        fitz.Rect(50, 230, 545, 280),
        "Additional paragraph with different content for testing extraction.",
        fontsize=12,
        fontname="helv",
    )
    
    # Add metadata
    doc.set_metadata({
        "title": "Test Document Title",
        "author": "Test Author",
        "keywords": "test, webapp, parsing",
    })
    
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


@pytest.fixture
def sample_multi_page_pdf(tmp_path):
    """Create a multi-page PDF for testing navigation."""
    import pymupdf as fitz
    
    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()
    
    for i in range(3):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), f"Page {i + 1}", fontsize=24, fontname="helv")
        page.insert_text((50, 100), f"Content for page {i + 1}", fontsize=12, fontname="helv")
    
    doc.save(str(pdf_path))
    doc.close()
    
    return pdf_path


@pytest.fixture
def vlm_cache_file(tmp_path):
    """Create a sample VLM cache file."""
    cache_path = tmp_path / "vlm_cache.json"
    cache_content = {
        "test_pdf.pdf": {
            "page_0": {
                "title": "Cached Title",
                "authors": ["Cached Author"],
                "elements": [
                    {
                        "id": "vlm_0",
                        "type": "heading",
                        "content": "Cached Heading",
                        "bbox_percent": {"x": 10, "y": 5, "width": 80, "height": 3}
                    },
                    {
                        "id": "vlm_1",
                        "type": "paragraph",
                        "content": "Cached paragraph content",
                        "bbox_percent": {"x": 10, "y": 10, "width": 80, "height": 5}
                    }
                ],
                "abstract": "Cached abstract text",
                "sections": ["Introduction"],
                "keywords": ["cached", "keyword"]
            }
        }
    }
    
    cache_path.write_text(json.dumps(cache_content, indent=2))
    return cache_path


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
class TestWebappHelpers:
    """Tests for webapp helper functions."""
    
    def test_render_pdf_page_to_base64(self, sample_pdf_with_content):
        """Test PDF page rendering to base64 image."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import render_pdf_page_to_base64
        
        img_data, width, height = render_pdf_page_to_base64(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=150
        )
        
        assert img_data.startswith("data:image/png;base64,")
        assert width > 0
        assert height > 0
        
        # Verify it's valid base64
        b64_part = img_data.split(",")[1]
        decoded = base64.b64decode(b64_part)
        assert len(decoded) > 0
    
    def test_render_pdf_page_different_dpi(self, sample_pdf_with_content):
        """Test rendering with different DPI settings."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import render_pdf_page_to_base64
        
        # 72 DPI (PDF native resolution)
        img_72, w_72, h_72 = render_pdf_page_to_base64(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=72
        )
        
        # 150 DPI (default)
        img_150, w_150, h_150 = render_pdf_page_to_base64(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=150
        )
        
        # 300 DPI (high resolution)
        img_300, w_300, h_300 = render_pdf_page_to_base64(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=300
        )
        
        # Higher DPI should produce larger images
        assert w_72 < w_150 < w_300
        assert h_72 < h_150 < h_300
    
    def test_render_nonexistent_page(self, sample_pdf_with_content):
        """Test rendering a page that doesn't exist."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import render_pdf_page_to_base64
        
        with pytest.raises(Exception):
            render_pdf_page_to_base64(
                str(sample_pdf_with_content),
                page_num=99
            )
    
    def test_extract_tool_bboxes(self, sample_pdf_with_content):
        """Test tool-based bounding box extraction."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import extract_tool_bboxes
        
        elements = extract_tool_bboxes(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=150
        )
        
        assert len(elements) > 0
        
        # Check element structure
        for elem in elements:
            assert "id" in elem
            assert "type" in elem
            assert "content" in elem
            assert "bbox" in elem
            assert "x" in elem["bbox"]
            assert "y" in elem["bbox"]
            assert "width" in elem["bbox"]
            assert "height" in elem["bbox"]
        
        # Check for expected element types
        element_types = {elem["type"] for elem in elements}
        assert "heading" in element_types
        assert "paragraph" in element_types
    
    def test_extract_tool_bboxes_coordinate_scaling(self, sample_pdf_with_content):
        """Test that coordinates are properly scaled from PDF points to pixels."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import extract_tool_bboxes
        
        # Extract at 72 DPI (native PDF resolution)
        elements_72 = extract_tool_bboxes(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=72
        )
        
        # Extract at 150 DPI
        elements_150 = extract_tool_bboxes(
            str(sample_pdf_with_content),
            page_num=0,
            dpi=150
        )
        
        # Coordinates should be scaled proportionally
        assert len(elements_72) == len(elements_150)
        
        scale_factor = 150 / 72
        
        for elem_72, elem_150 in zip(elements_72, elements_150):
            assert abs(elem_150["bbox"]["x"] - elem_72["bbox"]["x"] * scale_factor) < 1
            assert abs(elem_150["bbox"]["y"] - elem_72["bbox"]["y"] * scale_factor) < 1
    
    def test_extract_vlm_bboxes_with_cache(self, sample_pdf_with_content, vlm_cache_file):
        """Test VLM bounding box extraction with cache."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import extract_vlm_bboxes
        from unittest.mock import patch
        
        cache_data = json.loads(vlm_cache_file.read_text())
        
        with patch('app.VLM_CACHE', cache_data):
            elements = extract_vlm_bboxes(
                "test_pdf.pdf",
                page_num=0,
                page_width=1275,
                page_height=1650
            )
        
        assert len(elements) > 0
        
        # Check that cached data is used
        cached_titles = [e["content"] for e in elements if "Cached" in e["content"]]
        assert len(cached_titles) > 0
    
    def test_extract_vlm_bboxes_without_cache(self, sample_pdf_with_content):
        """Test VLM bounding box extraction without cache (fallback to mock)."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import extract_vlm_bboxes
        from unittest.mock import patch
        
        # Mock empty cache
        with patch('app.VLM_CACHE', {}):
            elements = extract_vlm_bboxes(
                str(sample_pdf_with_content),
                page_num=0,
                page_width=1275,
                page_height=1650
            )
        
        # Should fall back to mock data based on tool extraction
        assert len(elements) > 0
        assert all(e["id"].startswith("vlm_") for e in elements)
    
    def test_parse_with_tool(self, sample_pdf_with_content):
        """Test tool-based parsing."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import parse_with_tool
        
        result = parse_with_tool(
            str(sample_pdf_with_content),
            category="academic_paper"
        )
        
        assert "title" in result
        assert "authors" in result
        assert "content_count" in result
        assert "figures_count" in result
        assert "tables_count" in result
        assert "content" in result
        
        assert result["title"] == "Test Document Title"
        assert isinstance(result["authors"], list)
        assert result["content_count"] > 0
    
    def test_parse_with_vlm_with_cache(self, vlm_cache_file):
        """Test VLM parsing with cached results."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import parse_with_vlm
        
        cache_data = json.loads(vlm_cache_file.read_text())
        
        with patch('app.VLM_CACHE', cache_data):
            result = parse_with_vlm(
                "test_pdf.pdf",
                page_num=0,
                category="academic_paper"
            )
        
        assert result["title"] == "Cached Title"
        assert "Cached Author" in result["authors"]
        assert result["source"] == "live_vlm_cache"
        assert "abstract" in result
    
    def test_parse_with_vlm_without_cache(self, sample_pdf_with_content):
        """Test VLM parsing without cache (fallback to mock)."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import parse_with_vlm
        
        with patch('app.VLM_CACHE', {}):
            result = parse_with_vlm(
                str(sample_pdf_with_content),
                page_num=0,
                category="academic_paper"
            )
        
        assert result["source"] == "mock"
        assert "title" in result
        assert "content" in result
    
    def test_compute_comparison(self, sample_pdf_with_content):
        """Test comparison computation between tool and VLM results."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import compute_comparison, parse_with_tool, parse_with_vlm
        
        tool_result = parse_with_tool(str(sample_pdf_with_content))
        
        with patch('app.VLM_CACHE', {}):
            vlm_result = parse_with_vlm(str(sample_pdf_with_content))
        
        comparison = compute_comparison(tool_result, vlm_result)
        
        # Check all set operation keys
        assert "tool_only" in comparison
        assert "vlm_only" in comparison
        assert "intersection" in comparison
        assert "union" in comparison
        assert "symmetric_difference" in comparison
        
        # Check tool_only
        assert "content_types" in comparison["tool_only"]
        assert "keywords" in comparison["tool_only"]
        assert "extra_content_count" in comparison["tool_only"]
        
        # Check intersection
        assert "content_types" in comparison["intersection"]
        assert "keywords" in comparison["intersection"]
        assert "title_match" in comparison["intersection"]
        assert "author_overlap" in comparison["intersection"]


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
class TestWebappAPI:
    """Tests for Flask API endpoints."""
    
    @pytest.fixture
    def client(self, vlm_cache_file):
        """Create Flask test client."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import app
        
        # Mock cache
        import app as app_module
        app_module.VLM_CACHE = json.loads(vlm_cache_file.read_text())
        
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_index_route(self, client):
        """Test index route."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data
    
    def test_list_pdfs(self, client, sample_pdf_with_content):
        """Test listing available PDF files."""
        response = client.get('/api/list_pdfs')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "pdfs" in data
        assert isinstance(data["pdfs"], list)
    
    def test_parse_pdf_valid(self, client, sample_pdf_with_content):
        """Test parsing a valid PDF."""
        response = client.post(
            '/api/parse',
            json={
                "pdf_path": str(sample_pdf_with_content),
                "page": 0,
                "category": "academic_paper"
            },
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "pdf_info" in data
        assert "image" in data
        assert "tool" in data
        assert "vlm" in data
        assert "comparison" in data
        
        # Check pdf_info
        assert "filename" in data["pdf_info"]
        assert "page_count" in data["pdf_info"]
        assert "current_page" in data["pdf_info"]
        
        # Check image
        assert "data" in data["image"]
        assert "width" in data["image"]
        assert "height" in data["image"]
        assert data["image"]["data"].startswith("data:image/png;base64,")
        
        # Check tool results
        assert "bboxes" in data["tool"]
        assert "result" in data["tool"]
        
        # Check VLM results
        assert "bboxes" in data["vlm"]
        assert "result" in data["vlm"]
    
    def test_parse_pdf_different_pages(self, client, sample_multi_page_pdf):
        """Test parsing different pages of a multi-page PDF."""
        # Parse first page
        response1 = client.post(
            '/api/parse',
            json={
                "pdf_path": str(sample_multi_page_pdf),
                "page": 0
            }
        )
        assert response1.status_code == 200
        data1 = json.loads(response1.data)
        assert data1["pdf_info"]["current_page"] == 0
        
        # Parse second page
        response2 = client.post(
            '/api/parse',
            json={
                "pdf_path": str(sample_multi_page_pdf),
                "page": 1
            }
        )
        assert response2.status_code == 200
        data2 = json.loads(response2.data)
        assert data2["pdf_info"]["current_page"] == 1
    
    def test_parse_pdf_nonexistent(self, client):
        """Test parsing a non-existent PDF."""
        response = client.post(
            '/api/parse',
            json={
                "pdf_path": "/nonexistent/path/to/file.pdf",
                "page": 0
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_parse_pdf_missing_path(self, client):
        """Test parsing without providing pdf_path."""
        response = client.post(
            '/api/parse',
            json={"page": 0}
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_parse_pdf_bounding_boxes(self, client, sample_pdf_with_content):
        """Test that bounding boxes are included in response."""
        response = client.post(
            '/api/parse',
            json={
                "pdf_path": str(sample_pdf_with_content),
                "page": 0
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Check tool bounding boxes
        tool_bboxes = data["tool"]["bboxes"]
        assert len(tool_bboxes) > 0
        
        for bbox in tool_bboxes:
            assert "id" in bbox
            assert "type" in bbox
            assert "content" in bbox
            assert "bbox" in bbox
        
        # Check VLM bounding boxes
        vlm_bboxes = data["vlm"]["bboxes"]
        assert len(vlm_bboxes) > 0
    
    def test_parse_pdf_comparison_data(self, client, sample_pdf_with_content):
        """Test that comparison data is correctly computed."""
        response = client.post(
            '/api/parse',
            json={
                "pdf_path": str(sample_pdf_with_content),
                "page": 0
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        comparison = data["comparison"]
        
        # Check all comparison types
        assert "tool_only" in comparison
        assert "vlm_only" in comparison
        assert "intersection" in comparison
        assert "union" in comparison
        assert "symmetric_difference" in comparison
        
        # Check that comparison contains expected fields
        assert "content_types" in comparison["intersection"]
        assert "keywords" in comparison["intersection"]
        assert "title_match" in comparison["intersection"]
    
    def test_parse_pdf_different_categories(self, client, sample_pdf_with_content):
        """Test parsing with different document categories."""
        categories = ["academic_paper", "blog_post", "technical_docs"]
        
        for category in categories:
            response = client.post(
                '/api/parse',
                json={
                    "pdf_path": str(sample_pdf_with_content),
                    "page": 0,
                    "category": category
                }
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "tool" in data
            assert "vlm" in data


@pytest.mark.skipif(not FLASK_AVAILABLE, reason="Flask not installed")
class TestWebappIntegration:
    """Integration tests for the webapp."""
    
    def test_full_workflow(self, sample_pdf_with_content):
        """Test complete workflow from listing to parsing."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import app
        
        app.config['TESTING'] = True
        with app.test_client() as client:
            # Step 1: List PDFs
            list_response = client.get('/api/list_pdfs')
            assert list_response.status_code == 200
            list_data = json.loads(list_response.data)
            
            # Step 2: Parse a specific PDF
            parse_response = client.post(
                '/api/parse',
                json={
                    "pdf_path": str(sample_pdf_with_content),
                    "page": 0,
                    "category": "academic_paper"
                }
            )
            assert parse_response.status_code == 200
            parse_data = json.loads(parse_response.data)
            
            # Step 3: Verify all data is present
            assert parse_data["pdf_info"]["filename"] == sample_pdf_with_content.name
            assert len(parse_data["tool"]["bboxes"]) > 0
            assert len(parse_data["vlm"]["bboxes"]) > 0
    
    def test_bbox_coordinates_consistency(self, sample_pdf_with_content):
        """Test that bounding box coordinates are consistent with image dimensions."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import app
        
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.post(
                '/api/parse',
                json={
                    "pdf_path": str(sample_pdf_with_content),
                    "page": 0
                }
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            img_width = data["image"]["width"]
            img_height = data["image"]["height"]
            
            # Check that all bounding boxes are within image bounds
            for bbox in data["tool"]["bboxes"]:
                assert 0 <= bbox["bbox"]["x"] <= img_width
                assert 0 <= bbox["bbox"]["y"] <= img_height
                assert 0 < bbox["bbox"]["width"] <= img_width
                assert 0 < bbox["bbox"]["height"] <= img_height
                
            for bbox in data["vlm"]["bboxes"]:
                assert 0 <= bbox["bbox"]["x"] <= img_width
                assert 0 <= bbox["bbox"]["y"] <= img_height
                assert 0 < bbox["bbox"]["width"] <= img_width
                assert 0 < bbox["bbox"]["height"] <= img_height
    
    def test_element_type_mapping(self, sample_pdf_with_content):
        """Test that element types are correctly mapped."""
        sys.path.insert(0, WEBAPP_PATH)
        from app import app
        
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.post(
                '/api/parse',
                json={
                    "pdf_path": str(sample_pdf_with_content),
                    "page": 0
                }
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Check for expected element types
            tool_types = {bbox["type"] for bbox in data["tool"]["bboxes"]}
            vlm_types = {bbox["type"] for bbox in data["vlm"]["bboxes"]}
            
            assert "heading" in tool_types
            assert "paragraph" in tool_types
