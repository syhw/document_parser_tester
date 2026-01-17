#!/usr/bin/env python3
"""
PDF Parsing Comparison Webapp

A Flask-based web application that visualizes and compares VLM-based vs Tool-based
document parsing with interactive bounding box overlays.

Features:
- Side-by-side comparison of extraction results
- Bounding box visualization: Red (VLM) vs Green (Tool/PyMuPDF)
- Multi-page PDF navigation with keyboard shortcuts
- Click-to-highlight: click boxes to highlight corresponding sidebar elements
- Set operations comparison (intersection, union, difference)

Usage:
    python webapp/app.py
    # Then open http://localhost:5000 in your browser

API Endpoints:
    GET  /                  - Main web interface
    GET  /api/list_pdfs     - List available PDF files
    POST /api/parse         - Parse PDF and return comparison results
        Body: {"pdf_path": str, "page": int, "category": str}
"""

import sys
import json
import base64
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS

import fitz  # PyMuPDF

from vlm_doc_test.parsers import PDFParser
from vlm_doc_test.schemas.base import DocumentCategory, DocumentFormat
from vlm_doc_test.schemas.schema_simple import SimpleDocument

app = Flask(__name__)
CORS(app)

# Store parsed results in memory (for demo purposes)
PARSED_RESULTS = {}

# Load VLM cache if available
VLM_CACHE = {}
VLM_CACHE_PATH = Path(__file__).parent / "vlm_cache.json"
if VLM_CACHE_PATH.exists():
    with open(VLM_CACHE_PATH) as f:
        VLM_CACHE = json.load(f)


def render_pdf_page_to_base64(pdf_path: str, page_num: int = 0, dpi: int = 150) -> Tuple[str, int, int]:
    """Render a PDF page to a base64-encoded PNG image.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        dpi: Resolution for rendering (default 150)

    Returns:
        Tuple of (data_uri, width, height) where data_uri is a base64 PNG
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)

    # Save to bytes
    img_bytes = pix.tobytes("png")
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')

    width, height = pix.width, pix.height
    doc.close()

    return f"data:image/png;base64,{img_b64}", width, height


def extract_tool_bboxes(pdf_path: str, page_num: int = 0, dpi: int = 150) -> List[Dict[str, Any]]:
    """Extract bounding boxes using PyMuPDF (tool-based).

    Coordinates are converted from PDF points (72 DPI) to pixels at the specified DPI.
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]

    # Scale factor: convert PDF points (72 DPI) to render pixels
    scale = dpi / 72.0

    elements = []

    # Extract text blocks with bounding boxes
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

    for i, block in enumerate(blocks):
        if block["type"] == 0:  # Text block
            bbox = block["bbox"]  # (x0, y0, x1, y1) in PDF points

            # Get text content
            text_content = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text_content += span.get("text", "") + " "

            text_content = text_content.strip()
            if not text_content:
                continue

            # Determine element type based on font size
            font_sizes = []
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_sizes.append(span.get("size", 12))

            avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12

            if avg_font_size > 14:
                elem_type = "heading"
            else:
                elem_type = "paragraph"

            elements.append({
                "id": f"tool_{i}",
                "type": elem_type,
                "content": text_content[:200] + ("..." if len(text_content) > 200 else ""),
                "bbox": {
                    "x": bbox[0] * scale,
                    "y": bbox[1] * scale,
                    "width": (bbox[2] - bbox[0]) * scale,
                    "height": (bbox[3] - bbox[1]) * scale
                },
                "font_size": round(avg_font_size, 1)
            })

        elif block["type"] == 1:  # Image block
            bbox = block["bbox"]
            elements.append({
                "id": f"tool_img_{i}",
                "type": "figure",
                "content": f"Image ({int(bbox[2]-bbox[0])}x{int(bbox[3]-bbox[1])})",
                "bbox": {
                    "x": bbox[0] * scale,
                    "y": bbox[1] * scale,
                    "width": (bbox[2] - bbox[0]) * scale,
                    "height": (bbox[3] - bbox[1]) * scale
                }
            })

    # Extract tables
    tables = page.find_tables()
    for i, table in enumerate(tables):
        bbox = table.bbox
        elements.append({
            "id": f"tool_table_{i}",
            "type": "table",
            "content": f"Table ({table.row_count} rows × {table.col_count} cols)",
            "bbox": {
                "x": bbox[0] * scale,
                "y": bbox[1] * scale,
                "width": (bbox[2] - bbox[0]) * scale,
                "height": (bbox[3] - bbox[1]) * scale
            },
            "rows": table.row_count,
            "cols": table.col_count
        })

    doc.close()
    return elements


def extract_vlm_bboxes(pdf_path: str, page_num: int = 0, page_width: int = 0, page_height: int = 0) -> List[Dict[str, Any]]:
    """
    Extract VLM bounding boxes from cache or generate mock.
    Uses real GLM-4.6V results when available in cache.
    """
    # Check cache first
    cache_key = pdf_path
    page_key = f"page_{page_num}"

    if cache_key in VLM_CACHE and page_key in VLM_CACHE[cache_key]:
        cached = VLM_CACHE[cache_key][page_key]
        elements = []

        for elem in cached.get("elements", []):
            # Convert percentage bboxes to pixel coordinates
            bp = elem.get("bbox_percent", {})
            bbox = {
                "x": bp.get("x", 0) * page_width / 100,
                "y": bp.get("y", 0) * page_height / 100,
                "width": bp.get("width", 10) * page_width / 100,
                "height": bp.get("height", 5) * page_height / 100
            }

            elements.append({
                "id": elem.get("id", f"vlm_{len(elements)}"),
                "type": elem.get("type", "paragraph"),
                "content": elem.get("content", "")[:200],
                "bbox": bbox
            })

        return elements

    # Fallback to mock if no cache
    tool_elements = extract_tool_bboxes(pdf_path, page_num)

    vlm_elements = []
    for elem in tool_elements:
        vlm_elem = elem.copy()
        vlm_elem["id"] = elem["id"].replace("tool_", "vlm_")
        vlm_elem["bbox"] = elem["bbox"].copy()

        # VLM might have slightly different bounding boxes
        vlm_elem["bbox"]["x"] += 2
        vlm_elem["bbox"]["y"] += 1
        vlm_elem["bbox"]["width"] -= 4
        vlm_elem["bbox"]["height"] -= 2

        if elem["type"] == "paragraph" and len(elem["content"]) < 50:
            vlm_elem["type"] = "caption"

        vlm_elements.append(vlm_elem)

    return vlm_elements


def parse_with_tool(pdf_path: str, category: str = "academic_paper") -> Dict[str, Any]:
    """Parse PDF with tool-based parser."""
    parser = PDFParser()
    cat = getattr(DocumentCategory, category.upper(), DocumentCategory.ACADEMIC_PAPER)
    doc = parser.parse(pdf_path, category=cat)

    return {
        "title": doc.metadata.title,
        "authors": [a.name for a in doc.metadata.authors] if doc.metadata.authors else [],
        "content_count": len(doc.content),
        "figures_count": len(doc.figures),
        "tables_count": len(doc.tables),
        "content": [
            {"id": c.id, "type": c.type, "content": c.content[:200], "level": c.level}
            for c in doc.content[:20]  # Limit for display
        ],
        "keywords": doc.metadata.keywords or []
    }


def parse_with_vlm(pdf_path: str, page_num: int = 0, category: str = "academic_paper") -> Dict[str, Any]:
    """
    Parse with VLM using cached results or mock.
    Uses real GLM-4.6V results when available in cache.
    """
    cache_key = pdf_path
    page_key = f"page_{page_num}"

    if cache_key in VLM_CACHE and page_key in VLM_CACHE[cache_key]:
        cached = VLM_CACHE[cache_key][page_key]
        elements = cached.get("elements", [])

        return {
            "title": cached.get("title", "Unknown"),
            "authors": cached.get("authors", []),
            "content_count": len(elements),
            "figures_count": len([e for e in elements if e.get("type") == "figure"]),
            "tables_count": len([e for e in elements if e.get("type") == "table"]),
            "content": [
                {"id": e.get("id"), "type": e.get("type"), "content": e.get("content", "")[:200], "level": 1}
                for e in elements[:20]
            ],
            "keywords": cached.get("keywords", []),
            "abstract": cached.get("abstract", ""),
            "sections": cached.get("sections", []),
            "source": "live_vlm_cache"
        }

    # Fallback to mock
    tool_result = parse_with_tool(pdf_path, category)
    return {
        "title": tool_result["title"],
        "authors": tool_result["authors"][:5] if len(tool_result["authors"]) > 5 else tool_result["authors"],
        "content_count": tool_result["content_count"] - 10,
        "figures_count": tool_result["figures_count"],
        "tables_count": max(0, tool_result["tables_count"] - 2),
        "content": tool_result["content"][:15],
        "keywords": tool_result["keywords"][:5] if tool_result["keywords"] else ["AI", "machine learning"],
        "abstract": "This paper presents novel approaches to document understanding...",
        "source": "mock"
    }


def compute_comparison(tool_result: Dict, vlm_result: Dict) -> Dict[str, Any]:
    """Compute set operations between tool and VLM results."""

    # For content elements, compare by type
    tool_types = set(c["type"] for c in tool_result.get("content", []))
    vlm_types = set(c["type"] for c in vlm_result.get("content", []))

    # Keywords comparison
    tool_keywords = set(tool_result.get("keywords", []))
    vlm_keywords = set(vlm_result.get("keywords", []))

    return {
        "tool_only": {
            "content_types": list(tool_types - vlm_types),
            "keywords": list(tool_keywords - vlm_keywords),
            "extra_content_count": tool_result["content_count"] - vlm_result["content_count"],
            "extra_tables": tool_result["tables_count"] - vlm_result["tables_count"]
        },
        "vlm_only": {
            "content_types": list(vlm_types - tool_types),
            "keywords": list(vlm_keywords - tool_keywords),
            "has_abstract": "abstract" in vlm_result
        },
        "intersection": {
            "content_types": list(tool_types & vlm_types),
            "keywords": list(tool_keywords & vlm_keywords),
            "title_match": tool_result["title"] == vlm_result["title"],
            "author_overlap": len(set(tool_result["authors"]) & set(vlm_result["authors"]))
        },
        "union": {
            "all_content_types": list(tool_types | vlm_types),
            "all_keywords": list(tool_keywords | vlm_keywords)
        },
        "symmetric_difference": {
            "unique_to_either": list((tool_types | vlm_types) - (tool_types & vlm_types)),
            "unique_keywords": list((tool_keywords | vlm_keywords) - (tool_keywords & vlm_keywords))
        }
    }


@app.route("/")
def index():
    """Serve the main page."""
    return render_template("index.html")


@app.route("/api/parse", methods=["POST"])
def parse_pdf():
    """Parse a PDF file and return comparison results."""
    data = request.json
    pdf_path = data.get("pdf_path")
    page_num = data.get("page", 0)
    category = data.get("category", "academic_paper")
    use_live_vlm = data.get("use_live_vlm", False)

    if not pdf_path or not Path(pdf_path).exists():
        return jsonify({"error": f"PDF not found: {pdf_path}"}), 400

    try:
        # Render PDF page
        img_data, width, height = render_pdf_page_to_base64(pdf_path, page_num)

        # Extract bounding boxes
        tool_bboxes = extract_tool_bboxes(pdf_path, page_num)
        vlm_bboxes = extract_vlm_bboxes(pdf_path, page_num, width, height)

        # Parse documents
        tool_result = parse_with_tool(pdf_path, category)
        vlm_result = parse_with_vlm(pdf_path, page_num, category)

        # Compute comparison
        comparison = compute_comparison(tool_result, vlm_result)

        # Get PDF info
        doc = fitz.open(pdf_path)
        pdf_info = {
            "filename": Path(pdf_path).name,
            "page_count": len(doc),
            "current_page": page_num
        }
        doc.close()

        result = {
            "pdf_info": pdf_info,
            "image": {
                "data": img_data,
                "width": width,
                "height": height
            },
            "tool": {
                "bboxes": tool_bboxes,
                "result": tool_result
            },
            "vlm": {
                "bboxes": vlm_bboxes,
                "result": vlm_result
            },
            "comparison": comparison
        }

        return jsonify(result)

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.route("/api/list_pdfs", methods=["GET"])
def list_pdfs():
    """List available PDF files."""
    base_path = Path(__file__).parent.parent
    pdf_files = list(base_path.rglob("*.pdf"))

    return jsonify({
        "pdfs": [
            {"path": str(p), "name": p.name, "size": p.stat().st_size}
            for p in pdf_files[:20]  # Limit to 20
        ]
    })


if __name__ == "__main__":
    # Ensure templates directory exists
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(exist_ok=True)

    print("Starting PDF Parsing Comparison Webapp...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host="0.0.0.0", port=5000)
