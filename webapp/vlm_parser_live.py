#!/usr/bin/env python3
"""
Live VLM Parser for Webapp

This script is meant to be run via Claude Code to perform actual VLM parsing.
It saves results to a JSON file that the webapp can load.

Usage:
    claude -p webapp/vlm_parser_live.py path/to/document.pdf
"""

import sys
import json
import base64
from pathlib import Path
from datetime import datetime

import fitz  # PyMuPDF


def render_pdf_to_base64(pdf_path: str, page_num: int = 0, dpi: int = 150) -> tuple:
    """Render PDF page to base64."""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)

    # Save temporarily
    temp_path = Path(f"/tmp/vlm_page_{page_num}.png")
    pix.save(str(temp_path))

    width, height = pix.width, pix.height
    doc.close()

    return str(temp_path), width, height


def build_extraction_prompt(category: str = "academic_paper") -> str:
    """Build extraction prompt for VLM."""
    base_prompt = """Analyze this document image and extract structured information as JSON.

Extract ALL visible elements with their approximate positions (as percentages of page dimensions):

{
  "title": "document title",
  "authors": ["author names"],
  "elements": [
    {
      "type": "heading|paragraph|table|figure|caption|list",
      "content": "text content (first 200 chars)",
      "bbox_percent": {
        "x": 0-100,
        "y": 0-100,
        "width": 0-100,
        "height": 0-100
      }
    }
  ],
  "tables": [
    {"id": "Table N", "caption": "caption", "rows": N, "cols": N}
  ],
  "figures": [
    {"id": "Figure N", "caption": "caption"}
  ],
  "abstract": "abstract text if present",
  "keywords": ["keyword1", "keyword2"]
}

Be thorough - extract every visible text block, heading, paragraph, table, and figure.
Return ONLY valid JSON."""

    if category == "academic_paper":
        base_prompt += "\n\nThis is an ACADEMIC PAPER. Focus on: title, authors, abstract, section headings, citations."
    elif category == "blog_post":
        base_prompt += "\n\nThis is a BLOG POST. Focus on: title, author, date, tags, main content."
    elif category == "technical_documentation":
        base_prompt += "\n\nThis is TECHNICAL DOCUMENTATION. Focus on: API names, code blocks, parameters."

    return base_prompt


def parse_vlm_response(response_text: str, page_width: int, page_height: int) -> dict:
    """Parse VLM JSON response and convert bbox percentages to pixels."""
    try:
        # Try to extract JSON from response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        data = json.loads(response_text)

        # Convert percentage bboxes to pixels
        for elem in data.get("elements", []):
            if "bbox_percent" in elem:
                bp = elem["bbox_percent"]
                elem["bbox"] = {
                    "x": bp["x"] * page_width / 100,
                    "y": bp["y"] * page_height / 100,
                    "width": bp["width"] * page_width / 100,
                    "height": bp["height"] * page_height / 100
                }
                del elem["bbox_percent"]

        return data

    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Response was: {response_text[:500]}...")
        return {"error": str(e), "raw_response": response_text}


def main():
    if len(sys.argv) < 2:
        print("Usage: claude -p webapp/vlm_parser_live.py <pdf_path> [page_num] [category]")
        print("\nThis script should be run via Claude Code to use MCP tools.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_num = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    category = sys.argv[3] if len(sys.argv) > 3 else "academic_paper"

    if not Path(pdf_path).exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"=== Live VLM Parser ===")
    print(f"PDF: {pdf_path}")
    print(f"Page: {page_num}")
    print(f"Category: {category}")
    print()

    # Render PDF page
    print("Rendering PDF page...")
    image_path, width, height = render_pdf_to_base64(pdf_path, page_num)
    print(f"Rendered: {image_path} ({width}x{height})")

    # Build prompt
    prompt = build_extraction_prompt(category)
    print(f"Prompt length: {len(prompt)} chars")

    print()
    print("=" * 50)
    print("TO COMPLETE VLM PARSING:")
    print("=" * 50)
    print()
    print("Run this in Claude Code with MCP tools:")
    print()
    print(f"  Image path: {image_path}")
    print(f"  Prompt: {prompt[:100]}...")
    print()
    print("The VLM tool to call is: mcp__zai-mcp-server__analyze_image")
    print()

    # Save config for webapp to use
    output = {
        "pdf_path": str(Path(pdf_path).absolute()),
        "page_num": page_num,
        "category": category,
        "image_path": image_path,
        "page_width": width,
        "page_height": height,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat(),
        "status": "pending_vlm_call"
    }

    output_path = Path("webapp/vlm_pending.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Config saved to: {output_path}")
    print()
    print("After VLM call, save results to: webapp/vlm_results.json")


if __name__ == "__main__":
    main()
