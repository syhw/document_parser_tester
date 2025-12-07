# Tools & Schema Updates Proposal

Based on comprehensive research from ChatGPT and Gemini library recommendations, this document proposes updates to our README.md dependencies and schema definitions.

## Executive Summary

The research identified several critical gaps in our current tooling plan:

1. **No chart-to-data extraction**: We need DePlot/Matcha for plot understanding
2. **No structured output enforcement**: Instructor + Pydantic integration missing
3. **Limited validation tools**: Need DeepDiff, TheFuzz, pytest-image-snapshot
4. **No academic paper specialized tools**: GROBID is essential for academic_paper category
5. **No reading order detection**: Surya provides this critical capability

## Proposed Tool Additions

### Tier 1: Critical (Must Have)

| Tool | Category | Why Critical | Use Case |
|------|----------|--------------|----------|
| **Instructor** | Structured Output | Forces VLM outputs into valid Pydantic schemas with retry logic | Ensures all VLM extraction matches our schema exactly |
| **DePlot** | Chart Analysis | Converts plot images to data tables | Core capability for plot_visualization category testing |
| **DeepDiff** | Validation | Fuzzy comparison with numerical tolerance | Equivalence checking between tool/VLM outputs |
| **Surya** | Layout Analysis | Reading order + layout segmentation with deep learning | Handles complex multi-column layouts |
| **GROBID** | Academic Papers | ML-based extraction of paper structure (title, abstract, citations) | Essential for academic_paper category |

### Tier 2: Highly Recommended

| Tool | Category | Why Recommended | Use Case |
|------|----------|-----------------|----------|
| **Marker** | PDF Conversion | High-fidelity PDF→Markdown with preserved layout | Alternative representation for testing |
| **pytest-image-snapshot** | Visual Testing | Baseline image comparison with masking | Visual regression testing |
| **TheFuzz** | Validation | Fuzzy string matching (Levenshtein distance) | Text similarity in equivalence checks |
| **Unstructured** | Preprocessing | Semantic element partitioning | Initial document preprocessing |
| **Matcha** | Chart Analysis | Mathematical derendering for scientific plots | Advanced plot analysis |

### Tier 3: Nice to Have

| Tool | Category | Why Useful | Use Case |
|------|----------|------------|----------|
| **SmolDocling** | Document Parsing | 256M param VLM with bounding boxes | Lightweight alternative to GLM-4.5V |
| **img2table** | Table Detection | Detects tables in rasterized images | Fallback for scanned documents |
| **PandasAI** | Data Analysis | Natural language interface for data queries | Interactive data exploration |
| **RapidFuzz** | Validation | Faster fuzzy matching | Performance optimization |

## Updated README.md Dependencies Section

```markdown
### Core Dependencies

**Schema & Validation:**
- `pydantic>=2.0` - Schema definition and validation
- `instructor` - Structured LLM output enforcement
- `deepdiff` - Fuzzy object comparison with tolerance
- `thefuzz[speedup]` - Fuzzy string matching

**PDF Processing:**
- `pymupdf` (fitz) - High-performance PDF rendering
- `pdfplumber` - Precision table extraction
- `surya-ocr` - Deep learning layout analysis
- `marker-pdf` - PDF to Markdown conversion
- `unstructured[pdf]` - Document partitioning

**Academic Paper Parsing:**
- `grobid-client-python` - GROBID client for scholarly PDFs

**Chart/Plot Analysis:**
- `deplot` - Plot-to-table transformation
- `matcha` - Mathematical chart derendering
- `img2table` - Table detection in images

**Rendering:**
- `playwright` - Web page rendering
- `pdf2image` - PDF to image conversion
- `pillow` - Image processing

**Testing & Validation:**
- `pytest` - Test framework
- `pytest-image-snapshot` - Visual regression testing
- `pytest-benchmark` - Performance benchmarking

**VLM & AI:**
- `requests` - API calls (GLM-4.5V, etc.)
- `smoldocling` (optional) - Lightweight document VLM

**Utilities:**
- `python-dotenv` - Environment configuration
- `pyyaml` - YAML config files
- `opencv-python` - Image analysis (optional)
```

## Schema Updates

### 1. Enhanced ExtractionMetadata

Add more detailed tool tracking:

```python
class ToolInfo(BaseModel):
    """Enhanced tool information."""
    name: str
    version: Optional[str] = None
    extraction_method: Literal[
        "text_extraction",      # PyMuPDF, pdfplumber
        "ocr",                   # Surya, Tesseract
        "layout_analysis",       # Surya, Unstructured
        "chart_derendering",     # DePlot, Matcha
        "markdown_conversion",   # Marker
        "academic_extraction"    # GROBID
    ]

    # Configuration used
    config: Dict[str, Any] = Field(default_factory=dict)

    # Performance metrics
    duration_ms: Optional[float] = None
    confidence: Optional[float] = None
```

### 2. Reading Order Support

Add to Document or ContentElement:

```python
class ContentElement(BaseModel):
    # ... existing fields ...

    # Reading order (from Surya)
    reading_order: Optional[int] = None
    reading_group: Optional[str] = None  # "column1", "column2", etc.
```

### 3. Enhanced Plot Schema

Add data table from DePlot:

```python
class Plot(Figure):
    # ... existing fields ...

    # DePlot/Matcha output
    data_table: Optional[DataTable] = None
    data_table_format: Optional[Literal["markdown", "csv", "json"]] = None

    # Source code (if extractable)
    source_code: Optional[str] = None
    source_language: Optional[Literal["python", "r", "matlab"]] = None


class DataTable(BaseModel):
    """Structured data extracted from plot."""
    headers: List[str]
    rows: List[List[Union[str, float, int]]]

    # Metadata
    extraction_method: Literal["deplot", "matcha", "manual"]
    confidence: Optional[float] = None
```

### 4. Alternative Representations

Add to Document:

```python
class Document(BaseModel):
    # ... existing fields ...

    # Alternative representations
    markdown_representation: Optional[str] = None  # From Marker
    semantic_elements: List[SemanticElement] = Field(default_factory=list)  # From Unstructured


class SemanticElement(BaseModel):
    """Semantic element from Unstructured."""
    type: Literal["Title", "NarrativeText", "Table", "Image", "List", "Footer"]
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### 5. GROBID Academic Paper Extension

Enhance AcademicPaperExtension:

```python
class GROBIDExtraction(BaseModel):
    """GROBID-specific extraction data."""
    # TEI XML output
    tei_xml: Optional[str] = None

    # Extracted entities
    affiliations_resolved: List[Affiliation] = Field(default_factory=list)
    references_parsed: List[Reference] = Field(default_factory=list)

    # Quality metrics
    header_confidence: Optional[float] = None
    reference_confidence: Optional[float] = None
```

### 6. Visual Regression Testing Metadata

Add to RenderingInfo:

```python
class RenderingInfo(BaseModel):
    # ... existing fields ...

    # Visual regression testing
    baseline_image: Optional[str] = None  # Path to baseline
    baseline_hash: Optional[str] = None
    visual_diff_metrics: Optional[VisualDiffMetrics] = None


class VisualDiffMetrics(BaseModel):
    """Metrics from visual comparison."""
    ssim_score: Optional[float] = Field(None, ge=0.0, le=1.0)  # Structural similarity
    pixel_diff_count: Optional[int] = None
    pixel_diff_percentage: Optional[float] = None
    masked_regions: List[BoundingBox] = Field(default_factory=list)
```

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. Set up micromamba environment with Tier 1 dependencies
2. Integrate Instructor + Pydantic for structured outputs
3. Implement basic DeepDiff-based equivalence checking
4. Add PyMuPDF + pdfplumber for PDF extraction

### Phase 2: Core Capabilities (Week 3-4)
5. Integrate DePlot for chart analysis
6. Add Surya for layout analysis
7. Implement GROBID for academic papers
8. Set up pytest-image-snapshot for visual testing

### Phase 3: Enhancement (Week 5-6)
9. Add Marker for Markdown conversion
10. Integrate Matcha for advanced chart analysis
11. Add fuzzy matching (TheFuzz)
12. Performance optimization

## Validation Strategy Updates

Based on the research, update our equivalence checking:

### Text Equivalence
```python
from thefuzz import fuzz
from deepdiff import DeepDiff

def check_text_equivalence(tool_text: str, vlm_text: str, threshold: float = 0.85) -> bool:
    """Check text equivalence with fuzzy matching."""
    # Token set ratio handles word order differences
    similarity = fuzz.token_set_ratio(tool_text, vlm_text) / 100.0
    return similarity >= threshold
```

### Data Equivalence
```python
def check_data_equivalence(
    tool_data: Dict[str, Any],
    vlm_data: Dict[str, Any],
    numerical_tolerance: float = 1e-5
) -> DeepDiff:
    """Check data equivalence with numerical tolerance."""
    return DeepDiff(
        tool_data,
        vlm_data,
        significant_digits=5,
        math_epsilon=numerical_tolerance,
        ignore_order=True  # For lists where order doesn't matter
    )
```

### Visual Equivalence
```python
from skimage.metrics import structural_similarity as ssim
import numpy as np

def check_visual_equivalence(
    baseline_image: np.ndarray,
    test_image: np.ndarray,
    threshold: float = 0.98,
    masked_regions: List[BoundingBox] = None
) -> tuple[bool, float]:
    """Check visual equivalence with SSIM."""
    # Apply masks if provided
    if masked_regions:
        for bbox in masked_regions:
            baseline_image = apply_mask(baseline_image, bbox)
            test_image = apply_mask(test_image, bbox)

    # Calculate SSIM
    score = ssim(baseline_image, test_image, multichannel=True)
    return score >= threshold, score
```

## Tool-Specific Testing Examples

### Example 1: Academic Paper with GROBID

```python
from grobid_client import GrobidClient

def test_academic_paper_grobid():
    """Test academic paper extraction using GROBID."""
    # Tool extraction
    grobid = GrobidClient(config_path="./grobid_config.json")
    tool_output = grobid.process_pdf(
        "fixtures/paper.pdf",
        service="processFulltextDocument"
    )

    # Parse GROBID TEI XML
    paper_data = parse_grobid_tei(tool_output)

    # VLM extraction
    vlm_output = parse_with_vlm(render_pdf("fixtures/paper.pdf"))

    # Equivalence check
    assert check_text_equivalence(
        paper_data.metadata.title,
        vlm_output.metadata.title,
        threshold=0.95
    )
    assert len(paper_data.citations) == len(vlm_output.citations)
```

### Example 2: Chart Analysis with DePlot

```python
from transformers import Pix2StructForConditionalGeneration, Pix2StructProcessor
import instructor
from openai import OpenAI

def test_chart_derendering():
    """Test chart data extraction using DePlot + Instructor."""
    # DePlot: Image → Table Text
    model = Pix2StructForConditionalGeneration.from_pretrained("google/deplot")
    processor = Pix2StructProcessor.from_pretrained("google/deplot")

    chart_image = load_image("fixtures/bar_chart.png")
    inputs = processor(images=chart_image, return_tensors="pt")
    outputs = model.generate(**inputs)
    table_text = processor.decode(outputs[0], skip_special_tokens=True)

    # Instructor: Enforce Pydantic schema
    client = instructor.from_openai(OpenAI())
    structured_data = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": f"Convert this table to structured data:\n{table_text}"
        }],
        response_model=Plot  # Our Pydantic model
    )

    # Validate against expected
    assert structured_data.plot_type == PlotType.BAR
    assert len(structured_data.data_table.rows) == 5
```

### Example 3: Visual Regression with Masking

```python
def test_pdf_rendering_regression():
    """Test PDF rendering with visual regression (mask dynamic content)."""
    # Render PDF
    rendered = render_pdf_page("report.pdf", page=1)

    # Extract dynamic regions (dates, IDs) using Surya
    layout = surya.detect_layout(rendered)
    dynamic_regions = [
        elem.bbox for elem in layout.elements
        if elem.type in ["Footer", "Header"] or "date" in elem.text.lower()
    ]

    # Visual comparison with masking
    passed, ssim_score = check_visual_equivalence(
        baseline_image=load_baseline("report_baseline.png"),
        test_image=rendered,
        threshold=0.98,
        masked_regions=dynamic_regions
    )

    assert passed, f"Visual regression failed: SSIM={ssim_score}"
```

## Cost-Benefit Analysis

### DePlot vs. GLM-4.5V for Chart Analysis

| Aspect | DePlot (Open) | GLM-4.5V (API) |
|--------|---------------|----------------|
| **Cost** | Free (GPU compute) | $0.60/$1.80 per M tokens |
| **Accuracy** | ~85% on ChartQA | ~90%+ (with grounding) |
| **Speed** | ~2s per chart (GPU) | ~3s per chart (API) |
| **Output** | Text table only | Text + bounding boxes |
| **Best For** | Batch processing | Interactive validation |

**Recommendation**: Use DePlot as primary, GLM-4.5V for validation and grounding.

## Next Steps

1. **Review & Approve**: Review this proposal and approve tool additions
2. **Create requirements.txt**: Generate dependency file with pinned versions
3. **Update Schema Files**: Add proposed fields to SCHEMA.md and SCHEMA_SIMPLE.md
4. **Integration Plan**: Create integration guide for each tool
5. **Testing Strategy**: Update TESTING.md with tool-specific test cases

## Questions for Discussion

1. Should we use GROBID as a standalone service (Docker) or via grobid-client-python?
2. Do we want to support both DePlot and Matcha, or just DePlot initially?
3. Should SmolDocling be included as an alternative to GLM-4.5V for cost savings?
4. What's the priority on visual regression testing vs. data validation?

## References

- ChatGPT Libraries Report: `chatgpt_libraries_and_tools.md`
- Gemini Technical Report: `gemini_libraries_and_tools.md`
- Current README: `README.md`
- Current Schema: `SCHEMA.md`
