# Testing Strategy

## Overview

This document outlines the testing strategy for the VLM-based document testing library. The core principle is to validate equivalence between tool-based parsing and VLM-based parsing across a **matrix** of document formats and document categories.

## Test Matrix Approach

Testing is organized along two independent dimensions:

1. **Document Format** (Physical representation)
2. **Document Category** (Semantic purpose)

This creates a test matrix where each cell represents a unique combination that should be tested.

### Why This Matters

The same semantic content (e.g., an academic paper) can appear in different formats (PDF, HTML, LaTeX), and the same format (e.g., HTML) can contain different categories of content (blog post, academic paper, documentation). Our testing framework must validate that:

- **Format-agnostic parsing**: The same category of content yields equivalent structured output regardless of format
- **Category-aware extraction**: Different categories extract appropriate fields (e.g., academic papers extract citations, blog posts extract comments)
- **Cross-format consistency**: Converting between formats preserves semantic structure

## Test Dimensions

### Dimension 1: Document Formats

Physical/technical representation of the document:

| Format | Extension | Rendering Method | Notes |
|--------|-----------|------------------|-------|
| HTML | `.html`, `.htm` | Playwright (browser) | Web pages, rendered HTML |
| PDF | `.pdf` | pdf2image, PyMuPDF | Static documents |
| PNG | `.png` | Direct image | Screenshots, exported plots |
| JPG | `.jpg`, `.jpeg` | Direct image | Photos, compressed images |
| SVG | `.svg` | Browser rendering | Vector graphics, plots |
| Markdown | `.md` | Markdown→HTML→Browser | Technical docs, READMEs |
| LaTeX | `.tex`, `.pdf` | Compiled PDF or HTML | Academic papers |
| DOCX | `.docx` | Conversion to PDF/HTML | Word documents |
| PPTX | `.pptx` | Slide rendering | Presentations |
| Jupyter | `.ipynb` | nbconvert or browser | Notebooks with plots |

### Dimension 2: Document Categories

Semantic/content type of the document:

| Category | Typical Fields | Examples |
|----------|----------------|----------|
| Academic Paper | Authors, abstract, citations, figures, sections | arXiv papers, journal articles |
| Blog Post | Author, publish date, tags, comments | Medium articles, personal blogs |
| News Article | Headline, byline, date, images | NYTimes, BBC articles |
| Technical Documentation | Code blocks, API references, navigation | ReadTheDocs, API docs |
| Book Chapter | Chapter number, page numbers, footnotes | O'Reilly books, textbooks |
| Presentation | Slides, speaker notes, transitions | Conference slides, lectures |
| Report | Executive summary, tables, appendices | Business reports, whitepapers |
| Tutorial | Step-by-step instructions, screenshots | How-to guides, walkthroughs |
| Plot/Visualization | Axes, legend, data series, title | Matplotlib plots, charts |
| Infographic | Visual elements, statistics, flow | Data visualizations |
| Webpage (General) | Navigation, content, links | Generic websites |

## Test Matrix

Each cell represents a test case:

|  | HTML | PDF | PNG | JPG | SVG | Markdown | LaTeX | DOCX | PPTX | Jupyter |
|--|------|-----|-----|-----|-----|----------|-------|------|------|---------|
| **Academic Paper** | ✓ | ✓✓✓ | ✗ | ✗ | ✓ | ✓ | ✓✓✓ | ✓ | ✓ | ✓ |
| **Blog Post** | ✓✓✓ | ✓ | ✗ | ✗ | ✓ | ✓✓ | ✗ | ✓ | ✗ | ✗ |
| **News Article** | ✓✓✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| **Technical Docs** | ✓✓✓ | ✓ | ✗ | ✗ | ✓ | ✓✓✓ | ✓ | ✓ | ✗ | ✓ |
| **Book Chapter** | ✓ | ✓✓✓ | ✗ | ✗ | ✓ | ✓ | ✓✓ | ✓ | ✗ | ✗ |
| **Presentation** | ✓ | ✓✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓✓✓ | ✓ |
| **Report** | ✓ | ✓✓✓ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓✓ | ✓ | ✗ |
| **Tutorial** | ✓✓✓ | ✓ | ✓ | ✓ | ✓ | ✓✓ | ✗ | ✓ | ✗ | ✓✓ |
| **Plot/Viz** | ✓ | ✓ | ✓✓ | ✓✓ | ✓✓✓ | ✗ | ✓ | ✗ | ✓ | ✓✓✓ |
| **Infographic** | ✓ | ✓ | ✓✓✓ | ✓✓✓ | ✓✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| **Webpage (General)** | ✓✓✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Legend:**
- ✓✓✓ = Primary/most common format (high priority testing)
- ✓✓ = Common format (medium priority)
- ✓ = Less common but valid (low priority)
- ✗ = Rare/invalid combination (skip)

## Test Case Structure

Each test case follows this structure:

```python
@pytest.mark.parametrize("format,category", [
    ("html", "academic_paper"),
    ("pdf", "academic_paper"),
    ("html", "blog_post"),
    # ... all valid combinations
])
def test_document_parsing_equivalence(format: str, category: str):
    """
    Test that tool-based and VLM-based parsing produce equivalent
    structured outputs for a given format/category combination.
    """
    # 1. Load test document
    test_doc = load_test_document(format, category)

    # 2. Parse with tool-based parser
    tool_output = parse_with_tool(test_doc, format, category)

    # 3. Render document
    screenshot = render_document(test_doc, format)

    # 4. Parse with VLM
    vlm_output = parse_with_vlm(screenshot, category)

    # 5. Check equivalence
    result = check_equivalence(tool_output, vlm_output, config)

    assert result.passed, f"Equivalence check failed: {result.failures}"
```

## Test Document Repository

Organize test documents by format and category:

```
tests/
  fixtures/
    documents/
      academic_paper/
        sample1.pdf
        sample1.html
        sample1.tex
        sample2.pdf
        sample2.html
      blog_post/
        sample1.html
        sample1.md
        sample2.html
      tutorial/
        sample1.html
        sample1.md
        sample1.ipynb
      plot_visualization/
        sample1.png
        sample1.svg
        sample1.ipynb
        sample1.pdf
      # ... other categories
```

## Category-Specific Testing Requirements

Different categories require different validation criteria:

### Academic Paper Tests

Focus on:
- ✅ Title, authors, affiliations extraction
- ✅ Abstract identification
- ✅ Section hierarchy (Introduction, Methods, Results, etc.)
- ✅ Figure and table extraction with captions
- ✅ Citation markers and bibliography
- ✅ Equation detection
- ✅ Footnotes and endnotes

Example assertion:
```python
assert tool_output.metadata.authors == vlm_output.metadata.authors
assert len(tool_output.citations) > 0
assert tool_output.figures[0].caption == vlm_output.figures[0].caption
```

### Blog Post Tests

Focus on:
- ✅ Title and author
- ✅ Publication date
- ✅ Tags/categories
- ✅ Main content vs. sidebar
- ✅ Images with alt text
- ✅ Internal/external links
- ✅ Comment sections (if present)

### Technical Documentation Tests

Focus on:
- ✅ Navigation structure
- ✅ Code blocks with syntax highlighting
- ✅ API signatures and parameters
- ✅ Warning/note callouts
- ✅ Cross-references between pages
- ✅ Version information

### Plot/Visualization Tests

Focus on:
- ✅ Plot type identification
- ✅ Axis labels and ranges
- ✅ Legend items
- ✅ Data series identification
- ✅ Title and caption
- ✅ Grid lines, tick marks
- ✅ Color scheme

Example assertion:
```python
assert tool_output.plot_type == vlm_output.plot_type
assert tool_output.axes[0].label == vlm_output.axes[0].label
assert len(tool_output.legend.items) == len(vlm_output.legend.items)
```

## Format-Specific Testing Requirements

Different formats require different parsing strategies:

### HTML Testing

Tool stack:
- BeautifulSoup for DOM parsing
- Playwright for rendering
- CSS selector extraction

Challenges:
- Dynamic content (JavaScript)
- Responsive layouts
- Hidden elements
- Iframe content

### PDF Testing

Tool stack:
- pdfplumber or PyMuPDF for text extraction
- pdf2image for rendering
- Coordinate-based extraction

Challenges:
- Multi-column layouts
- Rotated text
- Embedded fonts
- Image-based PDFs (requiring OCR)

### Jupyter Notebook Testing

Tool stack:
- nbformat for reading
- nbconvert for rendering
- Execution state handling

Challenges:
- Cell execution order
- Output cells (text, images, plots)
- Markdown vs. code cells
- Interactive widgets

### Image Formats (PNG, JPG) Testing

Tool stack:
- PIL/Pillow for loading
- Direct VLM analysis (no separate rendering)
- Optional OCR preprocessing

Challenges:
- Text extraction quality
- Low resolution
- Compression artifacts
- No structural information

## Equivalence Checking Strategy

Define category-specific equivalence thresholds:

```python
EQUIVALENCE_CONFIG = {
    "academic_paper": {
        "metadata": {
            "title": {"method": "exact", "required": True},
            "authors": {"method": "fuzzy", "threshold": 0.90, "required": True},
            "abstract": {"method": "semantic", "threshold": 0.85, "required": True},
        },
        "citations": {
            "count_tolerance": 0.05,  # Allow 5% difference
            "match_method": "fuzzy",
            "threshold": 0.80,
        },
        "figures": {
            "count_match": "exact",
            "caption_similarity": 0.85,
            "require_bbox": True,
        },
    },
    "blog_post": {
        "metadata": {
            "title": {"method": "exact", "required": True},
            "author": {"method": "fuzzy", "threshold": 0.90},
            "date": {"method": "exact"},
        },
        "content": {
            "text_similarity": 0.90,
            "preserve_paragraphs": True,
        },
        "links": {
            "url_match": "exact",
            "text_similarity": 0.75,
        },
    },
    "plot_visualization": {
        "plot_type": {"method": "exact", "required": True},
        "axes": {
            "count_match": "exact",
            "label_similarity": 0.85,
        },
        "legend": {
            "item_count": "exact",
            "label_similarity": 0.80,
        },
    },
    # ... other categories
}
```

## Cross-Format Consistency Tests

Test that the same content in different formats produces equivalent outputs:

```python
def test_cross_format_consistency():
    """
    Test that an academic paper in PDF and HTML formats
    produces equivalent structured outputs.
    """
    # Same paper, different formats
    paper_pdf = load_document("fixtures/paper1.pdf")
    paper_html = load_document("fixtures/paper1.html")

    # Parse both
    pdf_output = parse_document(paper_pdf)
    html_output = parse_document(paper_html)

    # Should have same metadata
    assert pdf_output.metadata.title == html_output.metadata.title
    assert pdf_output.metadata.authors == html_output.metadata.authors

    # Should have same structure
    assert len(pdf_output.content) == len(html_output.content)

    # Figures should match (allowing for minor bbox differences)
    assert len(pdf_output.figures) == len(html_output.figures)
```

## Performance Benchmarks

Track performance metrics across formats:

```python
@pytest.mark.benchmark
def test_parsing_performance(format: str, category: str):
    """Benchmark parsing performance."""
    doc = load_test_document(format, category)

    # Tool-based parsing
    with Timer() as tool_timer:
        tool_output = parse_with_tool(doc, format, category)

    # VLM-based parsing
    with Timer() as vlm_timer:
        screenshot = render_document(doc, format)
        vlm_output = parse_with_vlm(screenshot, category)

    # Record metrics
    metrics = {
        "format": format,
        "category": category,
        "tool_time_ms": tool_timer.duration_ms,
        "vlm_time_ms": vlm_timer.duration_ms,
        "vlm_tokens": vlm_output.extraction.vlm.total_tokens,
        "vlm_cost_usd": vlm_output.extraction.vlm.cost_usd,
    }

    log_benchmark(metrics)
```

## Test Coverage Goals

Target test coverage by priority:

### Phase 1: Core Formats × Core Categories (MVP)
- ✅ HTML × (Academic Paper, Blog Post, Tutorial)
- ✅ PDF × (Academic Paper, Report)
- ✅ PNG/SVG × Plot/Visualization
- ✅ Jupyter × Tutorial

### Phase 2: Extended Coverage
- ✅ All ✓✓✓ cells from test matrix
- ✅ All ✓✓ cells from test matrix
- ✅ Cross-format consistency tests

### Phase 3: Comprehensive Coverage
- ✅ All ✓ cells from test matrix
- ✅ Edge cases and error handling
- ✅ Performance optimization

## Quality Metrics

Track these metrics across all tests:

1. **Equivalence Score**: Percentage of fields that match between tool and VLM output
2. **Recall**: Percentage of elements found by both parsers (vs. ground truth)
3. **Precision**: Percentage of found elements that are correct
4. **F1 Score**: Harmonic mean of precision and recall
5. **Parse Time**: Time taken for parsing
6. **VLM Cost**: API cost for VLM-based parsing
7. **Confidence**: Average confidence score from VLM output

## Ground Truth Creation

For high-quality testing, create manually annotated ground truth:

```python
# tests/fixtures/ground_truth/academic_paper_sample1.json
{
  "id": "gt-paper-001",
  "format": "pdf",
  "category": "academic_paper",
  "metadata": {
    "title": "Novel Approaches to Deep Learning",
    "authors": [...],
    # ... manually verified metadata
  },
  "figures": [
    {
      "id": "fig1",
      "label": "Figure 1",
      "caption": "Training loss over epochs",
      "bbox": {"page": 3, "x": 72, "y": 200, "width": 450, "height": 300},
      # Manually verified
    }
  ],
  # ... complete manual annotation
}
```

Then test both parsers against ground truth:

```python
def test_against_ground_truth(parser_type: str):
    """Test parser output against manually annotated ground truth."""
    doc = load_test_document("pdf", "academic_paper")
    ground_truth = load_ground_truth("academic_paper_sample1.json")

    if parser_type == "tool":
        output = parse_with_tool(doc)
    else:
        output = parse_with_vlm(render_document(doc))

    # Compare against ground truth
    score = compare_to_ground_truth(output, ground_truth)

    assert score.precision > 0.90
    assert score.recall > 0.85
    assert score.f1 > 0.87
```

## Continuous Integration

Run test matrix in CI/CD:

```yaml
# .github/workflows/test.yml
name: Test Matrix

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        format: [html, pdf, markdown, jupyter]
        category: [academic_paper, blog_post, tutorial, plot_visualization]
        exclude:
          - format: markdown
            category: plot_visualization
          # ... exclude invalid combinations

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/test_equivalence.py::test_${{ matrix.format }}_${{ matrix.category }}
        env:
          GLM_API_KEY: ${{ secrets.GLM_API_KEY }}
```

## Future Testing Enhancements

- [ ] Adversarial testing (corrupted PDFs, malformed HTML)
- [ ] Multi-language document support
- [ ] Dynamic content testing (JavaScript-heavy pages)
- [ ] Large document testing (100+ page PDFs)
- [ ] Real-time rendering tests (animations, videos)
- [ ] Accessibility testing (screen reader compatibility)
- [ ] Cross-VLM comparison (GLM-4.5V vs. GPT-4V vs. Claude 3.5)

## Version History

- **v1.0.0** (2025-12-07): Initial testing strategy
  - Test matrix approach
  - Format/category separation
  - Equivalence checking framework
