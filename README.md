# VLM-Based Document Testing Library

## Overview

A testing framework that validates the output of programs that download, scrape, and render web pages, PDFs, plots, and other visual documents. The validation principle is based on **equivalence testing** between:

1. **Program Output**: Structured data extracted by your program (title, text, plots, figures, links, references)
2. **VLM Analysis**: What a Vision Language Model (VLM) like GLM-4.6V perceives when analyzing the actual rendered document

By comparing these two perspectives, we can detect discrepancies in extraction logic, rendering issues, and structural parsing problems.

## Core Concept

```
┌─────────────────┐
│  Source Doc     │
│ (Web/PDF/Plot)  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌──────────┐
│Program│  │ Renderer │
│Parser │  │(Playwright│
└───┬───┘  │  /PDF)   │
    │      └────┬─────┘
    │           │
    ▼           ▼
┌────────┐  ┌─────────┐
│Struct. │  │Screenshot│
│Output  │  │  Image   │
└───┬────┘  └────┬────┘
    │            │
    │            ▼
    │       ┌─────────┐
    │       │GLM-4.6V │
    │       │ VLM API │
    │       └────┬────┘
    │            │
    │            ▼
    │       ┌─────────┐
    │       │  VLM    │
    │       │ Output  │
    └───┬───┴────┬────┘
        │        │
        ▼        ▼
    ┌──────────────┐
    │  Equivalence │
    │    Checker   │
    └──────────────┘
```

## Problem Statement

When building tools that extract structured information from documents, we face several testing challenges:

1. **Rendering Fidelity**: Does the rendered output match what was extracted?
2. **Structure Preservation**: Are relationships between elements (e.g., figure captions, references) correctly identified?
3. **Content Completeness**: Did we miss important elements (plots, tables, footnotes)?
4. **Cross-Format Consistency**: Do different rendering approaches (HTML vs PDF vs image) maintain semantic equivalence?

Traditional unit tests can't easily validate these visual and structural aspects. This library solves that by using VLMs as an "oracle" that can perceive the document as a human would.

## Key Features

### 1. Multi-Format Support
- **Web Pages**: Playwright-rendered screenshots
- **PDFs**: Page-by-page rendering and analysis
- **Plots/Figures**: Matplotlib, Plotly, or other visualization outputs
- **Documents**: Academic papers, reports, presentations

### 2. Structured Field Validation
The library validates common document structures:
- **Metadata**: Title, authors, date, URLs
- **Content**: Text blocks, paragraphs, sections
- **Visual Elements**: Plots, figures, images, tables
- **Relationships**: Figure captions, citations, cross-references, links
- **Layout**: Multi-column text, sidebars, headers/footers

### 3. VLM-Powered Analysis
Uses GLM-4.6V (or compatible VLMs) to:
- Extract structure from rendered documents
- Identify visual elements and their relationships
- Parse text content with spatial awareness
- Validate coordinates and bounding boxes (via grounding features)

### 4. Equivalence Checking
Compares program output against VLM analysis using:
- **Exact matching**: For metadata and identifiers
- **Fuzzy matching**: For text content (accounting for OCR variations)
- **Structural matching**: For hierarchical relationships
- **Semantic matching**: For content equivalence despite formatting differences
- **Visual grounding**: For element positions and bounding boxes

## Testing Pipeline Architecture

Our testing pipeline orchestrates multiple specialized tools, each excelling at specific tasks. The architecture follows a **staged approach** with **routing logic** based on document type and layout analysis.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCUMENT INGESTION                          │
│  PDF/HTML/Image → [PyMuPDF/Playwright] → Raw content + images  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LAYOUT ANALYSIS                             │
│  Page image → [Surya] → Reading order + Region classification  │
│  └─ Fallback: [pdfplumber] for simple bbox detection           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │   ROUTING LOGIC         │
                │   (by region type)      │
                └┬────────┬──────┬───────┘
                 │        │      │
       ┌─────────▼─┐   ┌─▼───┐ ┌▼────────┐
       │   Text    │   │Table│ │ Image   │
       │  Regions  │   │ Reg.│ │ Regions │
       └─────┬─────┘   └──┬──┘ └────┬────┘
             │            │         │
             ▼            ▼         ▼
        ┌────────┐  ┌──────────┐ ┌────────────┐
        │PyMuPDF │  │pdfplumber│ │   DePlot   │
        │extract │  │  table   │ │ chart→data │
        └────┬───┘  │ extract  │ └─────┬──────┘
             │      └─────┬────┘       │
             │            │            │
             └────────────┴────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │  STRUCTURED EXTRACTION │
            │  [Instructor + VLM]    │
            │  → Pydantic validation │
            └────────────┬───────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │      VALIDATION        │
            │  ┌──────────────────┐  │
            │  │ Visual: SSIM +   │  │
            │  │ pytest-snapshot  │  │
            │  ├──────────────────┤  │
            │  │ Data: DeepDiff + │  │
            │  │ numerical tol.   │  │
            │  ├──────────────────┤  │
            │  │ Text: TheFuzz    │  │
            │  │ fuzzy matching   │  │
            │  ├──────────────────┤  │
            │  │ Grounding: VLM   │  │
            │  │ spatial verify   │  │
            │  └──────────────────┘  │
            └────────────────────────┘
```

### Component Responsibilities

#### 1. **Ingestion Layer**

**Tool: PyMuPDF (fitz)**
- **Role**: Fast PDF rendering and coordinate-aware text extraction
- **Output**: Text blocks with bounding boxes (PDF points, 72 DPI)
- **When to use**: All PDF processing, especially when speed matters
- **Note**: Coordinate system requires transformation for VLM correlation

**Tool: Playwright**
- **Role**: Web page rendering to screenshots
- **Output**: PNG/JPEG screenshots, DOM structure
- **When to use**: HTML/web page testing

**Trade-off**: PyMuPDF is deterministic but heuristic-based. May merge text incorrectly in complex layouts.

#### 2. **Layout Analysis & Routing**

**Tool: Surya** (GPU-dependent, optional)
- **Role**: Deep learning-based layout understanding
- **Output**:
  - Reading order for multi-column documents
  - Region classification (Header, Footer, Image, Table, Text)
  - Line-level detection preserving structure
- **When to use**: Complex layouts (academic papers, magazines)
- **Fallback**: pdfplumber's simpler bbox detection

**Why this matters**: Surya provides **routing logic**. It tells us which regions are charts (→ DePlot), tables (→ pdfplumber), or text (→ PyMuPDF).

#### 3. **Specialized Extraction**

**Tool: pdfplumber**
- **Role**: Precision table extraction
- **How it works**: Detects vertical/horizontal lines, infers grid structure, extracts cells
- **Output**: Structured table data with cell coordinates
- **When to use**: PDFs with line-delimited tables
- **Debugging**: Provides visual overlay feature to verify detected tables

**Tool: DePlot** (GPU-dependent)
- **Role**: Chart analysis via plot-to-table translation
- **How it works**:
  1. Takes plot image as input
  2. Outputs linearized text table (CSV/Markdown)
  3. Separate LLM reasons over table (two-stage approach)
- **Output**: Data table that can be validated
- **When to use**: `plot_visualization` category testing
- **Alternative**: Matcha for mathematical/scientific plots

**Why two-stage?**: Separating extraction (DePlot) from reasoning (LLM) enables validation of the extracted data before analysis.

#### 4. **Structured Output Enforcement**

**Tool: Instructor** (Critical)
- **Role**: Bridges VLMs and Pydantic schemas
- **How it works**:
  1. Sends image + prompt to VLM (GLM-4.6V, GPT-4V)
  2. Receives text response
  3. Attempts to parse into Pydantic model
  4. If validation fails → re-prompts VLM with error message
  5. Repeats until valid or max retries
- **Why critical**: Without this, VLM outputs are unreliable strings. With this, they're validated objects.
- **Output**: Validated `Document`, `ContentElement`, `Figure`, etc.

**Example**:
```python
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())

# VLM extraction with automatic validation
doc_metadata = client.chat.completions.create(
    model="gpt-4-vision",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract document metadata"},
            {"type": "image_url", "image_url": {"url": screenshot_url}}
        ]
    }],
    response_model=DocumentMetadata  # Our Pydantic class!
)

# doc_metadata is now a validated DocumentMetadata instance
assert isinstance(doc_metadata, DocumentMetadata)
```

#### 5. **Validation Layer**

**Tool: DeepDiff**
- **Role**: Fuzzy comparison of complex objects
- **Use case**: Compare tool output vs. VLM output with tolerance
- **Key feature**: `significant_digits` and `math_epsilon` for numerical tolerance
- **Why needed**: DePlot extracts 15.50001 from interpolation, expected is 15.5 → should match!

**Example**:
```python
from deepdiff import DeepDiff

diff = DeepDiff(
    tool_output,
    vlm_output,
    significant_digits=5,      # Ignore tiny float differences
    math_epsilon=1e-5,
    ignore_order=True          # List order doesn't matter
)

assert not diff  # No significant differences
```

**Tool: TheFuzz**
- **Role**: Fuzzy string matching
- **Use case**: Compare extracted text with OCR variations
- **Key feature**: `token_set_ratio` handles word order differences
- **Example**: "Quarterly Report 2023" matches "2023 Report Quarterly" at 100%

**Tool: pytest-image-snapshot**
- **Role**: Visual regression testing
- **How it works**:
  1. First run: saves screenshot as baseline
  2. Subsequent runs: compares to baseline
  3. Uses pixelmatch algorithm (ignores anti-aliasing)
- **Key feature**: **Masking** - can ignore dynamic regions (timestamps, IDs)

**Masking workflow**:
```python
# Use Surya to detect dynamic regions
layout = surya.detect_layout(screenshot)
dynamic_regions = [elem.bbox for elem in layout.elements
                   if elem.type in ["Footer", "Header"]]

# Mask before comparison
compare_with_masking(baseline, screenshot, masked_regions=dynamic_regions)
```

**Tool: SSIM (scikit-image)**
- **Role**: Perceptual image comparison
- **Why better than pixel diff**: Compares structure, not exact pixels
- **Use case**: Charts may be slightly shifted/compressed → SSIM tolerates this
- **Threshold**: 0.98 typically means "visually identical"

#### 6. **Specialized: Academic Papers**

**Tool: GROBID** (requires Docker service)
- **Role**: ML-based scholarly PDF parsing
- **Trained on**: Millions of academic papers
- **Output**: TEI XML with:
  - Author-affiliation linking
  - Section hierarchy (Intro → Methods → Results → Discussion)
  - In-text citations → bibliography mapping
  - Figure/table caption detection with numbering
- **When to use**: `academic_paper` category
- **Setup**: Docker Compose file provided
- **Fallback**: Marker for users who can't run Docker

**Integration**:
```python
from grobid_client import GrobidClient

grobid = GrobidClient(config_path="config.json")
tei_xml = grobid.process_pdf("paper.pdf", service="processFulltextDocument")

# Parse TEI XML → our Pydantic schema
paper = parse_tei_to_document(tei_xml)
assert paper.category == DocumentCategory.ACADEMIC_PAPER
```

### Tool Selection Decision Tree

```
Is it a PDF?
├─ Yes → Is it an academic paper?
│   ├─ Yes → GROBID (if available) or Marker
│   └─ No → PyMuPDF + pdfplumber
│
└─ No → Is it HTML?
    ├─ Yes → Playwright + BeautifulSoup
    └─ No → Is it a plot image?
        ├─ Yes → DePlot → Instructor → VLM
        └─ No → Direct VLM analysis

After extraction, always:
1. Layout analysis (Surya if GPU, else pdfplumber)
2. Structured extraction (Instructor + VLM)
3. Validation (DeepDiff + TheFuzz + pytest-snapshot)
```

## Technical Architecture

### Components

#### 2. **Program Output Schema**
Defines structured output format:
```python
@dataclass
class DocumentStructure:
    title: Optional[str]
    text_blocks: List[TextBlock]
    figures: List[Figure]
    links: List[Link]
    references: List[Reference]
    relationships: List[Relationship]
```

#### 3. **VLM Client**
Interfaces with GLM-4.6V or other VLMs:
```python
class VLMClient:
    def analyze_document(
        screenshot: Screenshot,
        prompt_template: str
    ) -> VLMAnalysis
```

Key considerations:
- **API**: GLM-4.6V via `https://api.z.ai/api/paas/v4/chat/completions`
- **Authentication**: Bearer token
- **Pricing**: $0.60/M input tokens, $1.80/M output tokens
- **Capabilities**: Document interpretation, grounding (coordinates), 16K max output
- **Strategy**: Split extraction into multiple requests for complex documents (avoid extracting too many fields at once)

#### 4. **Equivalence Checker**
Compares structured outputs:
```python
class EquivalenceChecker:
    def check_equivalence(
        program_output: DocumentStructure,
        vlm_output: VLMAnalysis,
        config: CheckConfig
    ) -> TestResult
```

Configurable thresholds for:
- Text similarity (Levenshtein, embedding-based)
- Structural similarity (graph matching)
- Element count tolerance
- Position tolerance (for grounded elements)

#### 5. **Test Framework Integration**
Works with pytest or unittest:
```python
@vlm_test(renderer="playwright", model="glm-4.6v")
def test_webpage_extraction(url: str):
    # Your extraction logic
    program_output = extract_webpage(url)

    # Automatic VLM validation
    assert_equivalent(program_output, tolerance=0.95)
```

### Prompt Engineering

The library uses structured prompts for VLM analysis:

```
You are analyzing a document screenshot. Extract the following:

1. Title and metadata
2. All text blocks with their hierarchical structure
3. Figures, plots, and images with descriptions
4. Links and their anchor text
5. References and citations
6. Relationships between elements (e.g., "Figure 1 caption", "Reference [1]")

Output in JSON format: {...}
```

Best practices (from research):
- Split complex documents into multiple VLM requests (max ~10 fields per request)
- Use grounding features for spatial validation
- Provide clear JSON schema in prompts
- Consider multi-page handling for long documents

## Use Cases

### 1. Web Scraper Testing
Validate that your scraper correctly extracts article structure, images, and links by comparing against what the VLM sees in the rendered page.

### 2. PDF Parser Validation
Test PDF extraction libraries by comparing structured output against VLM analysis of rendered PDF pages.

### 3. Plot Generation Testing
Ensure generated plots contain expected elements (axes, legends, data points) by having VLM verify the visual output.

### 4. Document Converter Testing
Validate HTML-to-PDF, Markdown-to-HTML, or other conversions preserve structure and content.

### 5. OCR Quality Assurance
Compare OCR output against VLM analysis for accuracy validation.

## Example Workflow

```python
from vlm_test import VLMTester, DocumentStructure, Figure

# Initialize tester
tester = VLMTester(
    model="glm-4.6v",
    api_key=os.getenv("GLM_API_KEY")
)

# Your program's output
program_output = DocumentStructure(
    title="Machine Learning Paper",
    text_blocks=[...],
    figures=[
        Figure(id="fig1", caption="Loss curve", position=(100, 200))
    ],
    references=[...]
)

# Render the actual document
screenshot = tester.render_webpage("https://example.com/paper.html")

# Run equivalence test
result = tester.test_equivalence(
    program_output=program_output,
    screenshot=screenshot,
    config={
        "text_similarity_threshold": 0.90,
        "require_all_figures": True,
        "position_tolerance_px": 50
    }
)

# Check results
assert result.passed, f"Failures: {result.failures}"
```

## Configuration

### VLM Provider Configuration
```yaml
vlm:
  provider: glm-4.6v
  endpoint: https://api.z.ai/api/paas/v4/chat/completions
  api_key: ${GLM_API_KEY}
  max_retries: 3
  timeout: 30

  # Advanced features
  enable_thinking: false  # GLM-4.6V reasoning mode
  enable_grounding: true  # Object localization
```

### Renderer Configuration
```yaml
renderer:
  playwright:
    headless: true
    viewport: {width: 1920, height: 1080}
    wait_until: networkidle

  pdf:
    dpi: 150
    format: png
```

### Equivalence Thresholds
```yaml
equivalence:
  text_similarity: 0.85
  structure_similarity: 0.90
  require_all_elements: false
  position_tolerance_px: 100

  # Per-element type thresholds
  figures:
    count_match: exact  # or "approximate"
    caption_similarity: 0.80

  links:
    url_match: exact
    text_similarity: 0.75
```

## Research Insights

Based on current VLM literature and best practices:

1. **Model Selection**: GLM-4.6V offers strong document interpretation with grounding capabilities. Alternatives include GPT-4V, Claude 3.5, Gemini 1.5, Qwen 2.5 VL.

2. **Accuracy Expectations**: Out-of-the-box VLMs achieve good but not production-ready accuracy. Fine-tuning can improve performance by 10-30%.

3. **Field Extraction Strategy**: Avoid extracting too many fields (>20) in a single request. Split into multiple focused requests.

4. **Benchmarking**: Standard datasets like DocVQA, OCRBench, SROIE, and CORD can be used for baseline validation.

5. **Human-in-the-Loop**: For production-level accuracy (99%), consider integrating human review for edge cases.

## Limitations & Future Work

### Current Limitations
- VLM API costs can add up for large test suites
- Rate limits may slow down test execution
- VLM output non-determinism requires multiple runs for confidence
- Cross-browser rendering differences need separate baselines

### Future Enhancements
- [ ] Caching layer for VLM responses
- [ ] Multi-VLM consensus (ensemble approach)
- [ ] Fine-tuning support for domain-specific documents
- [ ] Differential testing (compare changes between versions)
- [ ] Performance benchmarking suite
- [ ] Support for video/animation testing
- [ ] Integration with CI/CD pipelines

## Project Structure

```
.
├── README.md                           # This file
├── SCHEMA.md                           # Full document schema (Pydantic models)
├── SCHEMA_SIMPLE.md                    # Simplified schema for quick prototyping
├── TESTING.md                          # Testing strategy and test matrix
├── TOOLS_PROPOSAL.md                   # Proposed tool additions (summary)
├── TOOLS_PROPOSAL_THINKING.md          # Deep analysis and trade-offs
├── chatgpt_libraries_and_tools.md      # Research: ChatGPT recommendations
├── gemini_libraries_and_tools.md       # Research: Gemini technical analysis
├── .env.example                        # API configuration template
├── requirements-core.txt               # Phase 0 dependencies (CPU-only)
├── requirements-gpu.txt                # Phase 1 dependencies (with GPU support)
├── requirements-academic.txt           # Phase 2 dependencies (academic papers)
├── requirements-full.txt               # All dependencies
├── vlm_doc_test/                       # Main package
│   ├── __init__.py
│   ├── config.py                       # Configuration and API credentials
│   ├── vlm_analyzer.py                 # VLM-based document analyzer
│   ├── schemas/                        # Pydantic schema definitions
│   │   ├── __init__.py
│   │   ├── base.py                     # Base types (BoundingBox, enums)
│   │   └── schema_simple.py            # SimpleDocument schema
│   ├── parsers/                        # Document parsers
│   │   ├── __init__.py
│   │   └── pdf_parser.py               # PyMuPDF-based PDF parser
│   ├── validation/                     # Equivalence checking
│   │   ├── __init__.py
│   │   └── equivalence.py              # DeepDiff + TheFuzz comparison
│   ├── renderers/                      # Document renderers (planned)
│   ├── utils/                          # Utility functions (planned)
│   └── tests/                          # Unit tests (planned)
├── examples/                           # Example usage
│   └── pdf_extraction_demo.py          # PDF parsing demonstration
├── test_setup.py                       # Basic imports and schema test
├── test_pdf_parser.py                  # PDF parser test
├── test_equivalence.py                 # Equivalence checker test
└── test_document.pdf                   # Generated test PDF
```

## Installation & Setup

### Environment Setup

This project uses a micromamba environment with Python 3.11:

```bash
# Activate the environment
micromamba activate doc_understanding_render_checker

# Install dependencies (when available)
pip install -r requirements.txt
```

### Dependencies

Based on comprehensive research (see [TOOLS_PROPOSAL_THINKING.md](./TOOLS_PROPOSAL_THINKING.md)), our dependencies are organized into tiers:

#### Phase 0: Foundation (Required)

**Schema & Structured Output:**
- `pydantic>=2.0` - Schema definition and validation
- `instructor` - **Critical**: Forces VLM outputs into valid Pydantic schemas with automatic retry logic

**Core PDF Processing:**
- `pymupdf` (fitz) - High-performance C-based PDF rendering and coordinate extraction
- `pdfplumber` - Precision table extraction using line detection algorithms

**Validation:**
- `deepdiff` - Fuzzy object comparison with numerical tolerance (essential for float comparisons)
- `thefuzz[speedup]` - Fuzzy string matching using Levenshtein distance

**Basic Tools:**
- `pillow` - Image processing
- `requests` - VLM API calls
- `python-dotenv` - Environment configuration

#### Phase 1: Core Capabilities

**Chart Analysis** (Critical for `plot_visualization` category):
- `transformers[torch]` - For DePlot model
- `accelerate` - GPU optimization for DePlot
- DePlot model: Converts plot images → data tables (two-stage reasoning)

**Visual Regression:**
- `pytest` - Test framework
- `pytest-image-snapshot` - Baseline image comparison with masking support
- `scikit-image` - SSIM (Structural Similarity Index) for perceptual comparison

**Layout Analysis** (Optional, GPU-dependent):
- `surya-ocr` - Deep learning for reading order detection and layout segmentation
- Fallback: Use pdfplumber's simpler bounding box extraction

#### Phase 2: Specialized Tools

**Academic Papers** (`academic_paper` category):
- `grobid-client-python` - Client for GROBID service
- GROBID service (Docker): ML-based extraction of paper structure (TEI XML output)
- Fallback: `marker-pdf` for users who can't run GROBID

**Web Rendering:**
- `playwright` - Browser-based web page rendering
- `beautifulsoup4` - HTML parsing

**Alternative Representations:**
- `marker-pdf` - High-fidelity PDF → Markdown conversion (~1GB model)
- `unstructured[pdf]` - Semantic element partitioning

#### Phase 3: Optional Enhancements

**Advanced Chart Analysis:**
- Matcha model - Mathematical derendering for scientific plots

**Performance:**
- `pytest-benchmark` - Performance testing
- `rapidfuzz` - Faster fuzzy matching (C++ backend)

**Lightweight VLM Alternative:**
- SmolDocling - 256M param model for cost-effective document parsing

### Installation Profiles

Choose based on your needs:

```bash
# Minimal (CPU-only, no GPU tools)
pip install -r requirements-core.txt

# With GPU support (Surya, DePlot)
pip install -r requirements-gpu.txt

# Academic papers (requires Docker for GROBID)
pip install -r requirements-academic.txt

# Full installation
pip install -r requirements-full.txt
```

### API Keys

Set your VLM API key:

```bash
export GLM_API_KEY="your-api-key-here"
# Or add to .env file
```

## Quick Start

### 1. Choose Your Schema

Start with the simple schema for prototyping:

```python
from schema_simple import SimpleDocument, DocumentFormat, DocumentSource
from datetime import datetime

# Create a simple document
doc = SimpleDocument(
    id="test-001",
    format=DocumentFormat.HTML,
    source=DocumentSource(
        url="https://example.com",
        accessed_at=datetime.now()
    )
)
```

Or use the full schema for complex documents (see [SCHEMA.md](./SCHEMA.md)).

### 2. Extract PDF Content with GLM-4.6V

Use the PDF extraction tool to get structured content from PDF files:

```bash
# Extract content from a PDF file
claude -p test_mcp_zai_GLM.py document.pdf

# Extract specific page with category
claude -p test_mcp_zai_GLM.py paper.pdf --page 2 --category academic_paper

# High-resolution extraction
claude -p test_mcp_zai_GLM.py scan.pdf --dpi 300
```

**Features**:
- Extracts structured content (title, authors, sections, tables, figures)
- Category-aware prompts for 9 document types (academic_paper, blog_post, etc.)
- Outputs SimpleDocument format (JSON)
- Configurable DPI and page selection
- Works with GLM-4.6V via MCP (Model Context Protocol)

**Output**: JSON file with structured document data matching `SCHEMA_SIMPLE.md`

See [PDF_EXTRACTION_TOOL_COMPLETE.md](./PDF_EXTRACTION_TOOL_COMPLETE.md) for complete documentation.

### 3. Run Tests

See [TESTING.md](./TESTING.md) for the complete testing strategy using the format × category test matrix.

## Current Status

**Project Phase**: Implementation - Phase 2 Complete ✅

### Completed ✅
- **Schema Design**:
  - Full schema (SCHEMA.md) with Pydantic models
  - Simple schema (SCHEMA_SIMPLE.md) as strict subset
  - Format vs. category separation

- **Testing Strategy**:
  - Format × Category test matrix (TESTING.md)
  - Equivalence checking framework
  - Visual regression approach

- **Tool Research**:
  - Comprehensive analysis of 30+ tools
  - Tool selection decision tree
  - Pipeline architecture design
  - Trade-off analysis (TOOLS_PROPOSAL_THINKING.md)

- **Phase 0 Implementation** (Completed ✅):
  - ✅ Created layered requirements files (core, GPU, academic, full)
  - ✅ Set up project structure: `vlm_doc_test/` package
  - ✅ Implemented core Pydantic schemas (base.py, schema_simple.py)
  - ✅ Integrated Instructor for VLM output validation
  - ✅ Implemented PDF parser with PyMuPDF (coordinate-aware extraction)
  - ✅ Created equivalence checker with DeepDiff and TheFuzz
  - ✅ Built VLM analyzer with structured output validation
  - ✅ All tests passing (6 test scripts)

- **Phase 1 Implementation** (Completed ✅):
  - ✅ Implemented HTML parser with BeautifulSoup
  - ✅ Set up pytest framework with fixtures
  - ✅ Implemented visual regression testing with SSIM
  - ✅ Created enhanced validation reporting (TEXT/JSON/Markdown)
  - ✅ 32 pytest tests, all passing
  - ✅ Phase 1 demo with multi-format reports

- **Phase 2 Implementation** (Completed ✅):
  - ✅ Playwright integration for web rendering
  - ✅ Enhanced pdfplumber table extraction
  - ✅ Web scraping utilities (rendering + parsing)
  - ✅ Multi-viewport responsive testing
  - ✅ 49 pytest tests, all passing
  - ✅ Phase 2 demo with web rendering examples

- **Phase 3 Implementation** (Completed ✅):
  - ✅ Marker-PDF parser for high-fidelity PDF → Markdown conversion
  - ✅ Docling parser with hybrid layout analysis
  - ✅ VLM parser with GLM-4.6V integration
  - ✅ Pipeline comparison framework for benchmarking extractors
  - ✅ Category validators for format-agnostic validation
  - ✅ Cross-format consistency testing
  - ✅ 124+ pytest tests (93.3% passing)

- **GLM-4.6V MCP Integration** (Completed ✅):
  - ✅ MCP server configuration for Z.AI GLM-4.6V
  - ✅ VLM parser with category-aware prompts
  - ✅ PDF extraction tool (`test_mcp_zai_GLM.py`)
  - ✅ Tool-vs-VLM comparison tests (17/22 passing, 5 pending MCP)
  - ✅ Complete documentation (MCP_GLM46V_GUIDE.md, PDF_EXTRACTION_TOOL_COMPLETE.md)
  - ✅ All integration tests passing

### Next Steps 🚀

#### Phase 4: Advanced Features (Optional)
- [ ] Integrate DePlot for chart analysis (GPU)
- [ ] GROBID integration for academic papers (Docker)
- [ ] Surya OCR for advanced layout analysis
- [ ] Performance optimization (caching, batching)
- [ ] CI/CD integration examples

#### Phase 4: Polish
- [ ] Example test suite for each category
- [ ] Documentation and tutorials
- [ ] Video/animation testing support

### Tool Integration Status

| Tool | Priority | Status | Notes |
|------|----------|--------|-------|
| **Instructor** | P0 | ✅ Implemented | VLM output validation with retry logic |
| **PyMuPDF** | P0 | ✅ Implemented | Coordinate-aware PDF extraction |
| **pdfplumber** | P0 | ✅ Implemented | Enhanced table extraction (Phase 2) |
| **DeepDiff** | P0 | ✅ Implemented | Fuzzy object comparison |
| **TheFuzz** | P0 | ✅ Implemented | String similarity matching |
| **Pydantic** | P0 | ✅ Implemented | Schema validation |
| **BeautifulSoup** | P1 | ✅ Implemented | HTML parsing with lxml |
| **pytest** | P1 | ✅ Implemented | Test framework (81 tests total) |
| **scikit-image** | P1 | ✅ Implemented | SSIM visual regression |
| **pytest-image-snapshot** | P1 | ✅ Installed | Visual regression plugin |
| **Playwright** | P2 | ✅ Implemented | Web rendering (Phase 2) |
| **DePlot** | P3 | 📋 Planned | Chart analysis (GPU) |
| **Surya** | P3 | 📋 Planned | Layout analysis (optional) |
| **GROBID** | P3 | 📋 Planned | Academic papers (Docker) |
| **Marker** | P3 | 📋 Planned | PDF→Markdown fallback |

### Design Decisions 📝

**Key Architectural Choices** (from TOOLS_PROPOSAL_THINKING.md):

1. **Hybrid Speed/Accuracy**: Fast methods first, fall back to VLM if low confidence
2. **Layered Dependencies**: Core (CPU) → GPU → Academic → Full
3. **Optional GPU Tools**: Surya and DePlot work on CPU but recommend GPU
4. **GROBID as Optional**: Docker required, provide Marker fallback
5. **Two-Stage Chart Analysis**: DePlot extraction → LLM reasoning (enables validation)
6. **Instructor Integration**: All VLM outputs validated against Pydantic schemas

## Contributing

This project is in the specification phase. Feedback welcome on:
- Additional document types to support
- Equivalence checking strategies
- VLM prompt engineering approaches
- Performance optimization ideas

## License

TBD
