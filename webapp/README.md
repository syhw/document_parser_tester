# PDF Parsing Comparison Webapp

A Flask-based web application that visualizes and compares VLM-based vs Tool-based document parsing with interactive bounding box overlays.

## Features

- **Side-by-side comparison**: View VLM and Tool extraction results simultaneously
- **Bounding box visualization**:
  - Red boxes: VLM-based parsing (GLM-4.6V)
  - Green boxes: Tool-based parsing (PyMuPDF)
- **Multi-page navigation**: Browse through all pages of a PDF
- **Interactive selection**: Click boxes to highlight corresponding sidebar elements
- **Keyboard shortcuts**: Arrow keys for page navigation
- **Set operations**: Compare results using intersection, union, and difference

## Quick Start

```bash
# From the project root directory
python webapp/app.py

# Or with explicit Python path
~/micromamba/envs/doc_understanding_render_checker/bin/python webapp/app.py
```

Then open http://localhost:5000 in your browser.

## Usage

1. **Select a PDF**: Use the dropdown or enter a path manually
2. **Parse**: Click "Parse PDF" to load and analyze
3. **Navigate pages**: Use prev/next buttons or arrow keys
4. **Toggle overlays**: Click VLM/Tool buttons to show/hide boxes
5. **Inspect elements**:
   - Hover over boxes to highlight
   - Click boxes to select and scroll to sidebar item
   - Click sidebar items to scroll PDF to that location

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` / `↑` | Previous page |
| `→` / `↓` | Next page |
| `Home` | First page |
| `End` | Last page |
| `Enter` (in page input) | Jump to page |

## API Endpoints

### `GET /`
Serves the main web interface.

### `GET /api/list_pdfs`
Lists available PDF files in the project directory.

**Response:**
```json
{
  "pdfs": [
    {"path": "/path/to/file.pdf", "name": "file.pdf", "size": 12345}
  ]
}
```

### `POST /api/parse`
Parses a PDF page and returns comparison results.

**Request body:**
```json
{
  "pdf_path": "/path/to/file.pdf",
  "page": 0,
  "category": "academic_paper"
}
```

**Response:**
```json
{
  "pdf_info": {"filename": "file.pdf", "page_count": 10, "current_page": 0},
  "image": {"data": "data:image/png;base64,...", "width": 1275, "height": 1650},
  "tool": {"bboxes": [...], "result": {...}},
  "vlm": {"bboxes": [...], "result": {...}},
  "comparison": {"intersection": {...}, "union": {...}, ...}
}
```

## Architecture

```
webapp/
├── app.py              # Flask application with API endpoints
├── templates/
│   └── index.html      # Single-page app with embedded CSS/JS
├── vlm_cache.json      # Optional: cached VLM results
└── README.md           # This file
```

## Coordinate System

The webapp handles coordinate conversion between different systems:

- **PDF points**: Native PyMuPDF coordinates (72 DPI)
- **Image pixels**: Rendered image coordinates (150 DPI)
- **Display pixels**: Screen coordinates (scaled to fit viewport)

Bounding boxes are converted from PDF points to image pixels on the backend, then scaled to display pixels on the frontend based on the rendered image size.

## VLM Cache

If you have cached VLM extraction results, place them in `webapp/vlm_cache.json`:

```json
{
  "/path/to/file.pdf": {
    "page_0": {
      "title": "Document Title",
      "elements": [
        {
          "id": "vlm_0",
          "type": "heading",
          "content": "Introduction",
          "bbox_percent": {"x": 10, "y": 5, "width": 80, "height": 3}
        }
      ]
    }
  }
}
```

Without cached results, VLM boxes are mocked based on tool extraction with slight offsets.

## Dependencies

- Flask
- flask-cors
- PyMuPDF (fitz)
- vlm_doc_test (parent package)
