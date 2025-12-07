# VLM-Based Document Testing Library

## Overview

A testing framework that validates the output of programs that download, scrape, and render web pages, PDFs, plots, and other visual documents. The validation principle is based on **equivalence testing** between:

1. **Program Output**: Structured data extracted by your program (title, text, plots, figures, links, references)
2. **VLM Analysis**: What a Vision Language Model (VLM) like GLM-4.5V perceives when analyzing the actual rendered document

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
    │       │GLM-4.5V │
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
Uses GLM-4.5V (or compatible VLMs) to:
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

## Technical Architecture

### Components

#### 1. **Renderer**
Converts documents to visual representations:
```python
class Renderer:
    def render_webpage(url: str) -> Screenshot
    def render_pdf(path: str, page: int) -> Screenshot
    def render_plot(figure: Figure) -> Screenshot
```

Uses Playwright for web content, pdf2image or similar for PDFs.

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
Interfaces with GLM-4.5V or other VLMs:
```python
class VLMClient:
    def analyze_document(
        screenshot: Screenshot,
        prompt_template: str
    ) -> VLMAnalysis
```

Key considerations:
- **API**: GLM-4.5V via `https://api.z.ai/api/paas/v4/chat/completions`
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
@vlm_test(renderer="playwright", model="glm-4.5v")
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
    model="glm-4.5v",
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
  provider: glm-4.5v
  endpoint: https://api.z.ai/api/paas/v4/chat/completions
  api_key: ${GLM_API_KEY}
  max_retries: 3
  timeout: 30

  # Advanced features
  enable_thinking: false  # GLM-4.5V reasoning mode
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

1. **Model Selection**: GLM-4.5V offers strong document interpretation with grounding capabilities. Alternatives include GPT-4V, Claude 3.5, Gemini 1.5, Qwen 2.5 VL.

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

## Installation (Planned)

```bash
pip install vlm-document-test
```

Dependencies:
- `playwright` for web rendering
- `pdf2image` or `pypdfium2` for PDF rendering
- `requests` for VLM API calls
- `pillow` for image processing
- `pytest` for test framework integration

## Contributing

This project is in the specification phase. Feedback welcome on:
- Additional document types to support
- Equivalence checking strategies
- VLM prompt engineering approaches
- Performance optimization ideas

## License

TBD
