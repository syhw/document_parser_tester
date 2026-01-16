# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VLM-Based Document Testing Library** - A testing framework that validates document parsing by comparing tool-based extraction with Vision Language Model (VLM) analysis. The core principle is **equivalence testing**: comparing structured data extracted by your program against what a VLM perceives when analyzing the rendered document.

The library is in **Phase 3 Complete** status with 135+ pytest tests covering PDF, HTML, web rendering, and multi-parser validation.

## Development Environment

This project uses **micromamba** with Python 3.11:

```bash
# Activate environment
micromamba activate doc_understanding_render_checker

# Verify environment
python --version  # Should be 3.11.x
```

### API Configuration

VLM analysis requires API credentials. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
# Edit .env and add your GLM_API_KEY
```

The system supports:
- **GLM-4.6V** (Zhipu AI) - Primary VLM provider
- **OpenAI-compatible APIs** - Alternative via OPENAI_API_KEY

Configuration is loaded via `vlm_doc_test/config.py` using python-dotenv.

## Common Development Commands

### Running Tests

```bash
# Run all tests (135+ tests)
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/ -v

# Run specific test modules
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/test_pdf_parser.py -v
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/test_equivalence.py -v
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/test_visual_regression.py -v

# Run with shorter traceback
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/ -v --tb=short

# Run category matrix tests
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/test_category_matrix.py -v

# Run pipeline comparison tests
~/micromamba/envs/doc_understanding_render_checker/bin/pytest vlm_doc_test/tests/test_pipeline_comparison.py -v
```

### Installing Dependencies

The project uses **layered requirements** for different use cases:

```bash
# Core dependencies (CPU-only, no GPU tools)
pip install -r requirements-core.txt

# With GPU support (Surya, DePlot)
pip install -r requirements-gpu.txt

# Academic paper support (requires Docker for GROBID)
pip install -r requirements-academic.txt

# Full installation
pip install -r requirements-full.txt

# Default (links to core)
pip install -r requirements.txt
```

### Installing Playwright (for web rendering)

```bash
~/micromamba/envs/doc_understanding_render_checker/bin/playwright install chromium
```

### Running Demos

```bash
# Phase 1: PDF and HTML parsing with validation
python examples/phase1_demo.py

# Phase 2: Web rendering and table extraction
python examples/phase2_demo.py

# Phase 3: Multi-parser comparison (Marker, Docling)
python examples/phase3_demo.py
```

### Quick Validation

```bash
# Quick setup test
python test_setup.py

# Quick Phase 3 test
python test_phase3_quick.py
```

## Architecture

### Core Pipeline: Extraction → Validation → Comparison

```
Document (PDF/HTML/Image)
    ↓
[Parser Layer] → Structured Output (Pydantic models)
    ↓
[VLM Analysis] → VLM Output (Instructor-validated)
    ↓
[Equivalence Checker] → Test Results (DeepDiff, TheFuzz, SSIM)
```

### Package Structure

```
vlm_doc_test/
├── schemas/           # Pydantic data models
│   ├── base.py       # BoundingBox, enums (DocumentFormat, DocumentCategory)
│   └── schema_simple.py  # SimpleDocument (main schema)
│
├── parsers/          # Document format parsers
│   ├── pdf_parser.py      # PyMuPDF-based PDF extraction
│   ├── html_parser.py     # BeautifulSoup HTML parser
│   ├── table_extractor.py # pdfplumber table extraction
│   ├── marker_parser.py   # Marker: PDF→Markdown (~1GB model)
│   ├── docling_parser.py  # Docling: hybrid PDF parser
│   └── vlm_parser.py      # VLM-based extraction
│
├── renderers/        # Document rendering
│   └── web_renderer.py    # Playwright browser rendering
│
├── validation/       # Equivalence checking
│   ├── equivalence.py          # DeepDiff + TheFuzz comparison
│   ├── visual_regression.py   # SSIM image comparison
│   ├── pipeline_comparison.py # Multi-parser comparison
│   ├── category_validators.py # Category-specific validation
│   └── reporter.py            # Report generation (TEXT/JSON/Markdown)
│
├── utils/            # Utilities
│   └── web_scraper.py         # URL fetching + rendering
│
├── tests/            # Pytest test suite (135+ tests)
│   ├── conftest.py            # Shared fixtures
│   ├── test_pdf_parser.py
│   ├── test_html_parser.py
│   ├── test_equivalence.py
│   ├── test_visual_regression.py
│   ├── test_category_matrix.py      # Format × Category testing
│   ├── test_pipeline_comparison.py  # Multi-parser validation
│   └── ...
│
├── config.py         # API configuration (VLMConfig)
└── vlm_analyzer.py   # VLM client with Instructor integration
```

### Key Components

#### 1. Schema Layer (`schemas/`)

All document data uses **Pydantic v2** models for validation:

- `DocumentFormat`: PDF, HTML, PNG, JPG, SVG, Markdown, etc.
- `DocumentCategory`: ACADEMIC_PAPER, BLOG_POST, NEWS_ARTICLE, etc.
- `SimpleDocument`: Main document model with metadata, content, figures, tables
- `BoundingBox`: Spatial coordinates for elements (page, x, y, width, height)

Schema design separates **format** (physical representation) from **category** (semantic purpose).

#### 2. Parser Layer (`parsers/`)

**Critical architectural decision**: The library supports multiple parsers, enabling **pipeline comparison**:

- **PDFParser** (PyMuPDF/fitz): Fast C-based PDF extraction with coordinate awareness
- **HTMLParser** (BeautifulSoup + lxml): HTML structure extraction
- **TableExtractor** (pdfplumber): Precision table detection using line-based algorithms
- **MarkerParser**: High-fidelity PDF→Markdown (requires ~1GB model download)
- **DoclingParser**: Hybrid approach combining layout analysis with text extraction
- **VLMParser**: Direct VLM-based extraction (baseline for comparison)

**Parser selection logic**:
- Academic papers → Try GROBID (if Docker available), else Marker or Docling
- Tables → pdfplumber for line-based tables
- Web pages → Playwright rendering + BeautifulSoup parsing
- Charts/plots → DePlot (Phase 3, GPU-dependent)

#### 3. VLM Integration (`vlm_analyzer.py`)

**Critical tool**: `instructor` library forces VLM outputs into valid Pydantic schemas with automatic retry logic.

```python
from instructor import from_openai
from openai import OpenAI

# VLM client with automatic Pydantic validation
client = from_openai(OpenAI(api_key=config.glm_api_key))
result = client.chat.completions.create(
    model="glm-4v-plus",
    messages=[...],
    response_model=SimpleDocument  # Automatically validated!
)
```

Without `instructor`, VLM outputs are unreliable strings. With it, they're validated objects.

#### 4. Validation Layer (`validation/`)

**Three validation strategies**:

1. **Equivalence Checking** (`equivalence.py`):
   - **DeepDiff**: Fuzzy object comparison with numerical tolerance
   - **TheFuzz**: String similarity using Levenshtein distance
   - Handles float precision issues (e.g., 15.50001 vs 15.5)

2. **Visual Regression** (`visual_regression.py`):
   - **SSIM** (Structural Similarity): Perceptual image comparison (threshold 0.98)
   - **pytest-image-snapshot**: Baseline comparison with masking support
   - Tolerates anti-aliasing, slight shifts, compression artifacts

3. **Pipeline Comparison** (`pipeline_comparison.py`):
   - Compares outputs from different parsers (Marker vs Docling vs PyMuPDF)
   - Identifies consensus and outliers
   - Validates parser agreement on ground truth

#### 5. Test Matrix Approach (`tests/`)

Testing is organized along **two independent dimensions**:

**Format × Category Matrix**:
```
           │ PDF │ HTML │ PNG │ SVG │ ...
───────────┼─────┼──────┼─────┼─────┼────
Academic   │ ✓✓✓ │  ✓   │  ✗  │  ✓  │
Blog Post  │  ✓  │ ✓✓✓  │  ✗  │  ✓  │
News       │  ✓  │ ✓✓✓  │  ✗  │  ✓  │
Tech Docs  │  ✓  │ ✓✓✓  │  ✗  │  ✓  │
Plots      │  ✓  │  ✓   │ ✓✓  │ ✓✓✓ │
```

See `TESTING.md` for the full matrix and priority levels.

**Test fixtures** (`conftest.py`):
- `sample_pdf`: Generates test PDF with PyMuPDF
- `sample_html`: Creates test HTML file
- `sample_document`: Returns SimpleDocument instance
- `sample_document_pair`: Returns (tool_output, vlm_output) for comparison

### Critical Dependencies

**Phase 0 (Core)**:
- `pydantic>=2.0` - Schema validation
- `instructor` - **CRITICAL**: VLM output validation with retry
- `pymupdf` (fitz) - High-performance PDF rendering
- `pdfplumber` - Table extraction
- `deepdiff` - Fuzzy object comparison
- `thefuzz[speedup]` - String similarity
- `pillow` - Image processing
- `python-dotenv` - Environment config

**Phase 1 (Testing)**:
- `pytest` - Test framework
- `pytest-image-snapshot` - Visual regression
- `scikit-image` - SSIM comparison
- `beautifulsoup4` + `lxml` - HTML parsing

**Phase 2 (Web)**:
- `playwright` - Browser rendering
- `requests` - HTTP client

**Phase 3 (Advanced)**:
- `marker-pdf` - PDF→Markdown conversion
- `docling` - Hybrid PDF parser
- `surya-ocr` - Layout analysis (GPU-optional)
- `transformers` + `accelerate` - For DePlot chart analysis

**Phase 4 (Specialized)**:
- GROBID (Docker service) - Academic paper extraction
- DePlot model - Chart→data table conversion

## Common Development Patterns

### Writing a New Parser

1. Create parser in `vlm_doc_test/parsers/your_parser.py`
2. Import and register in `parsers/__init__.py`
3. Implement method returning `SimpleDocument`
4. Write tests in `vlm_doc_test/tests/test_your_parser.py`
5. Add fixtures to `conftest.py` if needed

### Writing a New Category Validator

1. Add category to `schemas/base.py:DocumentCategory` if not present
2. Implement validator in `validation/category_validators.py`
3. Add test cases to `tests/test_category_matrix.py`
4. Document expected fields in validation logic

### Adding a New Format

1. Add format to `schemas/base.py:DocumentFormat`
2. Implement renderer if needed (see `renderers/web_renderer.py`)
3. Add parser for that format
4. Update test matrix in `TESTING.md`

### Running VLM Analysis

**Important**: VLM calls cost money and have rate limits. Always:
- Use caching for repeated requests
- Split complex documents into multiple focused requests (max ~10 fields per request)
- Set `temperature=0.1` for deterministic outputs
- Handle retry logic (already built into `instructor`)

Example:
```python
from vlm_doc_test.vlm_analyzer import VLMAnalyzer
from vlm_doc_test.config import get_config

config = get_config()
if not config.has_glm_credentials():
    print("Set GLM_API_KEY in .env file")
    exit(1)

analyzer = VLMAnalyzer(config)
result = analyzer.analyze_document(
    image_path="path/to/screenshot.png",
    prompt="Extract document metadata: title, authors, date"
)
```

### Debugging Parser Issues

1. **Check coordinates**: PDF uses points (72 DPI), images use pixels
   - PyMuPDF bboxes: `(x0, y0, x1, y1)` in points
   - Our schema: `BoundingBox(page, x, y, width, height)`

2. **Verify table extraction**: pdfplumber provides visual debugging
   ```python
   import pdfplumber
   with pdfplumber.open("doc.pdf") as pdf:
       page = pdf.pages[0]
       im = page.to_image()
       im.debug_tablefinder()  # Visual overlay
       im.save("debug_tables.png")
   ```

3. **Test equivalence thresholds**: DeepDiff settings in validation config
   ```python
   diff = DeepDiff(
       tool_output, vlm_output,
       significant_digits=5,    # Ignore tiny float differences
       math_epsilon=1e-5,
       ignore_order=True
   )
   ```

## Phase Status & Roadmap

**Completed** ✅:
- Phase 0: Core schemas, PDF parser, equivalence checker
- Phase 1: HTML parser, pytest framework, visual regression (SSIM)
- Phase 2: Playwright web rendering, pdfplumber tables, web scraping
- Phase 3: Marker parser, Docling parser, pipeline comparison, category validation

**Next Steps** (Phase 3+ Optional):
- DePlot integration for chart analysis (GPU)
- GROBID integration for academic papers (Docker)
- Surya OCR for advanced layout analysis
- Performance optimization (caching, batching)
- CI/CD integration examples

## Important Notes

### Coordinate Systems

**Three different coordinate systems** in use:
1. **PDF points** (PyMuPDF): 72 DPI, origin top-left
2. **Pixel coordinates** (Playwright screenshots): Varies by viewport
3. **VLM grounding coordinates**: Model-specific, often normalized

Always document which system you're using when working with bboxes.

### Test Data Location

Test fixtures are in `vlm_doc_test/tests/fixtures/`. When adding test documents:
- Use synthetic generated documents when possible (see `conftest.py`)
- For real documents, ensure licensing allows redistribution
- Keep file sizes small (<1MB) for fast test execution

### VLM Best Practices

From research and testing:
- **Avoid extracting >20 fields** in one request → split into multiple focused requests
- **Use grounding features** for spatial validation when available
- **Expect 80-90% accuracy** out-of-the-box, fine-tuning needed for production (99%+)
- **Non-determinism**: Run multiple times for confidence on edge cases

### File Organization

- **Documentation**: `*.md` files in project root (README, TESTING, SCHEMA, etc.)
- **Examples**: `examples/` for demonstration scripts
- **Test outputs**: `test_output/` and `examples/output/` (gitignored)
- **Package code**: `vlm_doc_test/` only

## Documentation Files

- `README.md` - Project overview, architecture, installation
- `TESTING.md` - Test matrix, testing strategy
- `SCHEMA.md` - Full Pydantic schema documentation
- `SCHEMA_SIMPLE.md` - Simplified schema for quick prototyping
- `TOOLS_PROPOSAL.md` - Tool selection rationale (summary)
- `TOOLS_PROPOSAL_THINKING.md` - Deep analysis of 30+ tools and trade-offs
- `TESTING_GUIDE.md` - How to write tests for this project
- `PHASE_*_COMPLETE.md` - Milestone completion reports

## Git Workflow

This is an active development repository. When making commits:
- Follow conventional commit format (feat:, fix:, docs:, test:, refactor:)
- Run full test suite before committing (`pytest vlm_doc_test/tests/ -v`)
- Update relevant `*.md` documentation when adding features
- Do not commit `.env` (contains API keys) - use `.env.example`
