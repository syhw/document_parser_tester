# Tools & Schema Proposal - Thinking Document

## Purpose

This document captures the raw thinking, trade-offs, concerns, and reasoning behind tool selection and schema updates. Unlike TOOLS_PROPOSAL.md which presents final recommendations, this document explores the decision-making process.

## Initial Observations

After reading both ChatGPT and Gemini reports, several patterns emerge:

1. **The tool landscape is vast but fragmented** - There are 30+ tools mentioned, each solving a piece of the puzzle. No single tool does everything.

2. **There's a fundamental tension**: Traditional CV/ML tools (PyMuPDF, pdfplumber) are deterministic and fast but brittle. VLMs (GLM-4.5V, DePlot) are flexible and smart but probabilistic and expensive.

3. **The academic community has already solved parts of this** - GROBID for papers, PDFFigures2 for figure extraction. We should leverage domain-specific tools rather than building everything from scratch with VLMs.

4. **Validation is underspecified in our current design** - We have schema for extraction but not for verification. The Gemini report's emphasis on DeepDiff, SSIM, and visual regression is crucial.

## Deep Analysis: Tool Categories

### Category 1: PDF Text Extraction

**The Landscape:**
- **PyMuPDF (fitz)**: C-based, extremely fast, coordinate-aware
- **pdfplumber**: Python, slower, superior table detection
- **pdfminer.six**: Low-level, maximum control, slowest
- **pypdfium2**: Google's PDFium, fastest for bulk text, no structure
- **Marker**: VLM-based, PDF→Markdown, ~1GB model

**My Thinking:**

The ChatGPT report positions PyMuPDF as the "performance engine" while Gemini emphasizes pdfplumber's "precision." This isn't contradictory - they excel at different tasks.

**Decision Framework:**
- **Speed-critical bulk processing** → PyMuPDF
- **Table extraction** → pdfplumber
- **Academic papers with complex layouts** → Marker or GROBID
- **Maximum control over parameters** → pdfminer.six (expose LAParams)

**Concern**: PyMuPDF's coordinate system (top-left origin, points not pixels) requires transformation when correlating with VLM bounding boxes. The Gemini report notes this explicitly - we need careful matrix transformations.

**Schema Impact**: We should track which tool was used and store both coordinate systems:
```python
class BoundingBox(BaseModel):
    # ... existing fields ...
    coordinate_system: Literal["pdf_points", "image_pixels"] = "pdf_points"
    dpi: int = 72  # For conversion
    transformation_matrix: Optional[List[float]] = None  # fitz.Matrix values
```

**Open Question**: Should we normalize all bounding boxes to a single coordinate system in our schema, or preserve the original and provide conversion utilities?

### Category 2: Layout Analysis

**The Landscape:**
- **Surya**: Deep learning, reading order, layout segmentation, multilingual
- **Unstructured**: High-level partitioning, "element" abstraction
- **LayoutParser**: Research-grade, PubLayNet models
- **HuriDocs PDF Layout Analysis**: Docker service, specialized

**My Thinking:**

The Gemini report's emphasis on Surya is compelling. It solves a problem we haven't fully addressed: **reading order in multi-column documents**. Our current ContentElement schema has a `sequence` field but no guidance on how to determine it.

Surya provides:
1. Line-level detection (preserves poetry/list structure)
2. Reading order prediction (column-aware)
3. Layout classification (Header, Footer, Image, Table, Text)

This is **routing logic** for our pipeline. We don't just extract elements - we need to know which elements are figures (route to DePlot), which are tables (route to pdfplumber), which are text (route to text extraction).

**Schema Impact**: We need layout metadata at the document level:

```python
class LayoutAnalysis(BaseModel):
    """Layout analysis metadata from Surya or similar."""
    reading_order: List[str]  # Ordered list of element IDs
    columns_detected: int
    layout_type: Literal["single_column", "multi_column", "mixed"]
    regions: List[LayoutRegion]


class LayoutRegion(BaseModel):
    """A detected layout region."""
    id: str
    type: Literal["Header", "Footer", "Image", "Table", "Text", "Sidebar"]
    bbox: BoundingBox
    reading_order_index: int
    column: Optional[int] = None
```

**Integration Challenge**: Surya requires GPU for reasonable speed. The Gemini report notes it's PyTorch-based with "heavy dependencies". For a library, we need to make Surya optional and provide a fallback (maybe pdfplumber's simpler layout detection).

**Dependency Strategy**:
```python
# requirements-base.txt (CPU-only)
pdfplumber>=0.10.0
pymupdf>=1.23.0

# requirements-gpu.txt (with Surya)
-r requirements-base.txt
surya-ocr>=0.3.0
torch>=2.0.0
```

### Category 3: Chart Analysis - The Critical Gap

**The Landscape:**
- **DePlot**: Plot→table, Pix2Struct-based, requires separate LLM for reasoning
- **Matcha**: Mathematical derendering, pre-trained on chart tasks
- **ChartOCR** (Microsoft): Hybrid deep learning + rules
- **WebPlotDigitizer**: Manual GUI tool (reference for algorithms)
- **Pix2Struct (ChartQA)**: VQA for charts

**My Thinking:**

This is where our current design has the **biggest gap**. We have a `Plot` schema with axes, legend, data_series - but no clear extraction strategy.

The Gemini report makes a crucial architectural point about DePlot:
> "The pipeline is: 1. Extraction: Use DePlot to convert chart to text table. 2. Inference: Feed table to LLM."

This is **two-stage reasoning** which is actually better for validation than end-to-end VQA:
1. DePlot extracts data → we can validate this data table
2. LLM reasons over table → we can validate the reasoning logic

**But there's a deeper question**: What exactly are we testing?

**Scenario A**: User has a plotting library (matplotlib) → generates PNG → we validate the PNG matches expected data
- **Tool path**: matplotlib source → expected data
- **VLM path**: PNG → DePlot → extracted data
- **Validation**: Compare expected data vs. extracted data

**Scenario B**: User has a PDF with plots → extracts plot metadata → we validate extraction
- **Tool path**: PDF → pdffigures2 or custom CV → plot metadata
- **VLM path**: PDF page → GLM-4.5V with grounding → plot metadata + bbox
- **Validation**: Compare metadata (title, caption) and bbox accuracy

These are **different use cases** requiring different tools!

**Schema Impact**: We need to distinguish between plot validation modes:

```python
class PlotValidation(BaseModel):
    """Validation metadata for plots."""
    validation_mode: Literal[
        "data_accuracy",      # Validate extracted data points
        "metadata_extraction", # Validate title, caption, labels
        "visual_rendering",    # Validate visual appearance
        "complete"            # All of the above
    ]

    # Data validation (from DePlot/Matcha)
    extracted_data_table: Optional[DataTable] = None
    data_extraction_method: Optional[Literal["deplot", "matcha", "manual"]] = None

    # Metadata validation (from VLM)
    extracted_metadata: Optional[PlotMetadata] = None

    # Visual validation (from pytest-image-snapshot)
    visual_baseline_path: Optional[str] = None
    ssim_score: Optional[float] = None


class PlotMetadata(BaseModel):
    """Metadata extracted from plot image."""
    title: Optional[str] = None
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    legend_items: List[str] = Field(default_factory=list)
    caption: Optional[str] = None
```

**Cost Consideration**: DePlot is open-source but requires GPU. Running it on every test could be slow. Alternative: cache DePlot results or only run on CI, not locally.

**Open Question**: Should we integrate DePlot directly or provide an interface where users can plug in their own chart→data extraction?

### Category 4: Academic Paper Parsing - The Specialist

**The Landscape:**
- **GROBID**: The gold standard, ML-based, TEI XML output
- **Science Parse** (deprecated)
- **PDFFigures 2.0**: Allen AI, figure/caption extraction
- **Marker**: General-purpose PDF→Markdown

**My Thinking:**

GROBID is **essential** for the `academic_paper` category. It's been trained on millions of scholarly papers and understands:
- Author affiliations (linking authors to institutions)
- Section hierarchy (Introduction → Methods → Results → Discussion)
- Citations (in-text markers → bibliography entries)
- Figure/table captions with numbering

The ChatGPT report notes GROBID outputs "structured XML/TEI" - this is both good and bad:
- **Good**: Standardized format (JATS-compatible)
- **Bad**: We need to parse XML and map to our Pydantic schema

**Integration Strategy**:

GROBID runs as a Java service (Docker or local). The Python client sends PDFs and receives XML.

```python
from grobid_client import GrobidClient

# Parse with GROBID
grobid = GrobidClient(config_path="config.json")
tei_xml = grobid.process_pdf(
    "paper.pdf",
    service="processFulltextDocument"
)

# Convert TEI to our schema
paper_doc = parse_tei_to_document(tei_xml)
assert paper_doc.category == DocumentCategory.ACADEMIC_PAPER
```

**Schema Impact**: We need GROBID-specific metadata:

```python
class GROBIDMetadata(BaseModel):
    """GROBID-specific extraction metadata."""
    tei_xml_path: Optional[str] = None  # Store raw TEI for debugging
    extraction_date: datetime

    # Quality indicators (GROBID provides confidence scores)
    header_confidence: Optional[float] = None
    citation_confidence: Optional[float] = None
    reference_confidence: Optional[float] = None

    # Processing metadata
    processing_time_ms: float
    grobid_version: str
```

**Concern**: GROBID requires running a separate service. For ease of use, we should provide:
1. Docker Compose file to spin up GROBID
2. Option to use GROBID Cloud API (if available)
3. Fallback to Marker for users who can't run GROBID

### Category 5: Structured Output Enforcement - The Missing Piece

**The Landscape:**
- **Instructor**: Pydantic validation for LLM outputs, retry logic
- **vLLM Guided Generation**: Constrained decoding for local models
- **Pydantic**: Schema definition and validation

**My Thinking:**

This is the **most important discovery** from the research. We already use Pydantic for our schema, but we haven't integrated it with VLM extraction.

The Gemini report explains Instructor's "validation loop":
> "When the LLM generates a response, Instructor attempts to parse it into the Pydantic model. If validation fails, Instructor captures the validation error and automatically re-prompts the LLM with the error message."

This is **exactly** what we need for reliable VLM extraction!

**Current Problem**:
```python
# Without Instructor (unreliable)
vlm_response = vlm_client.chat("Extract the title from this image")
# Response might be: "The title appears to be 'Machine Learning'"
# We have to parse this string manually - error-prone!
```

**With Instructor**:
```python
# With Instructor (reliable)
import instructor
from openai import OpenAI

client = instructor.from_openai(OpenAI())

doc_metadata = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Extract document metadata"},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]
    }],
    response_model=DocumentMetadata  # Our Pydantic class!
)

# doc_metadata is now a validated DocumentMetadata instance
assert isinstance(doc_metadata, DocumentMetadata)
```

**Schema Impact**: Actually, **no schema changes needed**! Instructor uses our existing Pydantic models. But we should ensure our models have good docstrings and field descriptions:

```python
class DocumentMetadata(BaseModel):
    """Document metadata extracted from visual analysis."""

    title: Optional[str] = Field(
        None,
        description="The main title of the document, typically at the top in large font"
    )

    authors: List[Author] = Field(
        default_factory=list,
        description="List of document authors, usually found below the title"
    )

    # ... etc.
```

These descriptions become part of the VLM prompt, improving extraction accuracy!

**Integration Question**: GLM-4.5V uses a different API format than OpenAI. Does Instructor support it?

Checking Instructor docs... It supports OpenAI-compatible APIs. The README mentions GLM-4V is "compatible with OpenAI's chat completion format" so we should be good!

### Category 6: Validation Tools - The Quality Assurance Layer

**The Landscape:**
- **DeepDiff**: Fuzzy object comparison, numerical tolerance
- **TheFuzz**: Fuzzy string matching (Levenshtein)
- **pytest-image-snapshot**: Visual regression testing
- **SSIM** (via scikit-image): Structural similarity
- **pdf-diff**: PDF text layer comparison

**My Thinking:**

The Gemini report's validation section is eye-opening. It distinguishes three types of validity:
1. **Visual Validity**: Does the rendering match?
2. **Data Validity**: Is the extracted data accurate?
3. **Semantic Validity**: Does the analysis make sense?

Our current `EquivalenceChecker` concept is too vague. We need specific validation strategies for each type.

#### Visual Validity: The Masking Problem

The Gemini report highlights a critical issue with visual regression:
> "PDFs often contain dynamic elements like timestamps that change on every generation. These will cause visual regression tests to fail."

**Solution**: Masking. Use layout analysis to identify dynamic regions, then mask them before comparison.

**Implementation**:
```python
def test_pdf_visual_regression():
    # Render PDF
    rendered = render_pdf("report.pdf")

    # Detect dynamic regions using Surya
    layout = surya.detect_layout(rendered)
    dynamic_regions = [
        elem.bbox for elem in layout.elements
        if is_dynamic(elem)  # Footer, timestamp, unique ID
    ]

    # Load baseline
    baseline = load_image("baseline.png")

    # Mask both images
    masked_rendered = apply_masks(rendered, dynamic_regions)
    masked_baseline = apply_masks(baseline, dynamic_regions)

    # Compare with SSIM
    ssim_score = structural_similarity(masked_rendered, masked_baseline)
    assert ssim_score > 0.98
```

**Schema Impact**: Track masked regions in validation metadata:

```python
class VisualValidation(BaseModel):
    """Visual validation results."""
    baseline_path: str
    test_image_path: str

    # Masking
    masked_regions: List[BoundingBox] = Field(default_factory=list)
    mask_strategy: Literal["manual", "automatic", "none"] = "none"

    # Metrics
    ssim_score: float = Field(ge=0.0, le=1.0)
    pixel_diff_count: int
    pixel_diff_percentage: float

    # Result
    passed: bool
    threshold: float
```

#### Data Validity: The Floating Point Problem

The Gemini report emphasizes numerical tolerance:
> "DeepDiff supports parameters like significant_digits and math_epsilon. This allows the tool to treat 10.00001 and 10.00002 as equal."

This is crucial for plot validation! When DePlot extracts data points from a rasterized plot, interpolation introduces variance.

**Example**:
```python
# Expected data (from matplotlib source)
expected = {"year": 2020, "revenue": 15.5}

# Extracted data (from DePlot on rendered plot)
extracted = {"year": 2020, "revenue": 15.50001}  # Slight interpolation error

# Strict comparison fails
assert expected == extracted  # ❌ False

# Fuzzy comparison with tolerance passes
diff = DeepDiff(
    expected,
    extracted,
    significant_digits=2,
    math_epsilon=0.01
)
assert not diff  # ✅ True
```

**Schema Impact**: Validation config needs tolerance settings:

```python
class EquivalenceConfig(BaseModel):
    """Configuration for equivalence checking."""

    # Text similarity
    text_fuzzy_threshold: float = Field(0.85, ge=0.0, le=1.0)
    text_matching_algorithm: Literal["token_set_ratio", "levenshtein", "exact"] = "token_set_ratio"

    # Numerical tolerance
    numerical_precision: int = Field(5, ge=1, le=15)  # Significant digits
    numerical_epsilon: float = 1e-5

    # Structural comparison
    ignore_order: bool = True
    ignore_string_case: bool = False

    # Element count tolerance
    element_count_tolerance: float = 0.05  # 5% difference allowed
```

#### Semantic Validity: Visual Grounding

The Gemini report introduces a fascinating validation technique:
> "If the analysis tool determines 'Sales peaked in Q3,' the validation module can ask GLM-4V to 'Locate the highest bar' and verify the bounding box aligns with Q3."

This is **visual grounding** used for **validation**! We extract a semantic claim, then verify it spatially.

**Example Workflow**:
1. DePlot: "The maximum value is 42.5 in category 'Q3'"
2. Validation: Ask GLM-4V with grounding: "Locate the highest bar"
3. GLM-4V returns: `{"label": "Q3", "bbox": [100, 150, 120, 300]}`
4. Verify: The bbox's x-position should align with Q3 on the x-axis

**Schema Impact**: Need to track grounding validation:

```python
class GroundingValidation(BaseModel):
    """Validation using visual grounding."""
    claim: str  # "The highest value is in Q3"
    grounding_query: str  # "Locate the highest bar"

    # VLM response
    grounded_element: GroundedElement

    # Verification
    geometric_verification: bool  # Did bbox align with expected position?
    label_match: bool  # Did label match expected?
    confidence: float


class GroundedElement(BaseModel):
    """An element located via visual grounding."""
    label: str
    bbox: BoundingBox
    confidence: Optional[float] = None
```

## Tool Integration Architecture

After analyzing all tools, here's my thinking on the overall architecture:

### Pipeline Stages

```
1. INGESTION
   ├─ PDF → [PyMuPDF] → Raw text + images
   ├─ PDF → [Marker] → Markdown (alternative)
   └─ PDF → [GROBID] → TEI XML (academic only)

2. LAYOUT ANALYSIS
   ├─ Page image → [Surya] → Layout regions + reading order
   └─ Fallback → [pdfplumber] → Simple bounding boxes

3. ROUTING (based on layout analysis)
   ├─ Text regions → Text extraction
   ├─ Table regions → [pdfplumber] table extraction
   ├─ Image regions → Chart analysis
   └─ Header/Footer → Metadata extraction

4. CHART ANALYSIS (for plot_visualization category)
   ├─ Chart image → [DePlot] → Data table
   ├─ Data table → [Instructor + LLM] → Structured Plot schema
   └─ Optional: [GLM-4.5V grounding] → Verify visual elements

5. STRUCTURED EXTRACTION (VLM-based)
   ├─ Page/region image → [GLM-4.5V]
   ├─ → [Instructor] → Enforce Pydantic schema
   └─ → Validated Document/ContentElement

6. VALIDATION
   ├─ Visual: [pytest-image-snapshot + SSIM] → Visual regression
   ├─ Data: [DeepDiff] → Fuzzy comparison
   ├─ Text: [TheFuzz] → String similarity
   └─ Grounding: [GLM-4.5V] → Spatial verification
```

### Dependency Graph

```python
# Core (always required)
pydantic
requests
pillow

# PDF Processing (choose based on use case)
pymupdf  # Fast extraction
pdfplumber  # Table extraction
marker-pdf  # Markdown conversion (optional)

# Layout Analysis (GPU-dependent)
surya-ocr  # Requires GPU, optional with fallback

# Academic Papers (optional, requires Docker)
grobid-client-python  # Requires GROBID service

# Chart Analysis (optional, GPU-dependent)
# DePlot installation via transformers
transformers[torch]
accelerate

# Structured Output (required for VLM extraction)
instructor

# Validation (required for equivalence checking)
deepdiff
thefuzz[speedup]
pytest-image-snapshot
scikit-image  # For SSIM

# Testing
pytest
pytest-benchmark
```

**Observation**: We have a lot of optional dependencies. We should organize them clearly:

```
requirements-core.txt       # Minimal: Pydantic, basic PDF, validation
requirements-gpu.txt        # Adds: Surya, DePlot
requirements-academic.txt   # Adds: GROBID client
requirements-full.txt       # Everything
```

## Critical Trade-offs

### Trade-off 1: Speed vs. Accuracy

**Fast but Brittle**:
- PyMuPDF for text
- pdfplumber heuristics for tables
- OpenCV for chart analysis

**Slow but Robust**:
- Surya for layout
- DePlot for charts
- GLM-4.5V for everything

**My Recommendation**: **Hybrid approach with tiered fallbacks**
1. Try fast methods first
2. If confidence is low, use slower but more accurate methods
3. Let users configure speed/accuracy trade-off

```python
class ExtractionConfig(BaseModel):
    mode: Literal["fast", "balanced", "accurate"] = "balanced"

    # Fast mode: PyMuPDF only, no VLM
    # Balanced: Layout analysis + selective VLM
    # Accurate: Full VLM pipeline
```

### Trade-off 2: Open Source vs. API-based

**Open Source** (DePlot, Surya):
- ✅ No API costs
- ✅ Run locally, privacy
- ❌ Requires GPU
- ❌ Setup complexity
- ❌ Model downloads (~1-5GB)

**API-based** (GLM-4.5V, GPT-4V):
- ✅ No GPU needed
- ✅ Easy setup
- ✅ Always latest models
- ❌ API costs ($)
- ❌ Rate limits
- ❌ Privacy concerns

**My Recommendation**: **Support both, let users choose**

```python
class VLMConfig(BaseModel):
    provider: Literal["glm-4.5v", "gpt-4v", "deplot-local"]

    # API-based
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None

    # Local model
    model_path: Optional[str] = None
    device: Literal["cuda", "cpu", "mps"] = "cuda"
```

### Trade-off 3: GROBID Deployment Complexity

**Options**:
1. **User runs GROBID Docker**: Full control, best accuracy, complex setup
2. **Use GROBID Cloud API**: Easy, costs money, may have limits
3. **Fallback to Marker**: Easier, less accurate for academic papers

**My Recommendation**: Make GROBID optional but recommended for academic papers.

```python
# In our test framework
@pytest.mark.academic_paper
@pytest.mark.requires_grobid
def test_paper_extraction():
    if not grobid_available():
        pytest.skip("GROBID not available, install docker-compose")
    # ... test logic
```

Provide clear docs:
```markdown
## Academic Paper Testing

For best results with academic papers, install GROBID:

bash
docker-compose -f docker/grobid.yml up -d


Alternatively, use Marker (less accurate but no setup):

bash
pip install marker-pdf

```

## Schema Refinements Based on Tools

### 1. Extraction Provenance

We need to track **how** each piece of data was extracted:

```python
class ExtractionProvenance(BaseModel):
    """Detailed provenance for each extracted element."""
    element_id: str
    extraction_method: Literal[
        "text_extraction",      # PyMuPDF, pdfplumber
        "ocr",                   # Surya, Tesseract
        "layout_analysis",       # Surya segmentation
        "chart_derendering",     # DePlot, Matcha
        "vlm_analysis",          # GLM-4.5V, GPT-4V
        "academic_parser",       # GROBID
        "markdown_conversion"    # Marker
    ]

    tool_name: str
    tool_version: Optional[str] = None

    # Confidence/quality
    confidence: Optional[float] = None

    # For debugging
    raw_output: Optional[str] = None  # Store original tool output
    processing_time_ms: float
```

Add to Document:
```python
class Document(BaseModel):
    # ... existing fields ...

    extraction_provenance: Dict[str, ExtractionProvenance] = Field(default_factory=dict)
    # Maps element_id → provenance
```

### 2. Multi-Modal Representations

Documents can have multiple representations (original PDF, markdown, structured data):

```python
class DocumentRepresentations(BaseModel):
    """Multiple representations of the same document."""

    # Original
    original_format: DocumentFormat
    original_path: str

    # Derived representations
    markdown: Optional[str] = None  # From Marker
    tei_xml: Optional[str] = None   # From GROBID
    plain_text: Optional[str] = None # From PyMuPDF

    # Intermediate artifacts
    layout_analysis: Optional[LayoutAnalysis] = None  # From Surya
    extracted_images: List[str] = Field(default_factory=list)  # Paths to extracted images
```

### 3. Validation Results

Validation should be first-class in the schema:

```python
class ValidationResult(BaseModel):
    """Complete validation result."""

    # Overall
    passed: bool
    timestamp: datetime

    # Component results
    visual_validation: Optional[VisualValidation] = None
    data_validation: Optional[DataValidation] = None
    grounding_validation: List[GroundingValidation] = Field(default_factory=list)

    # Summary
    failures: List[ValidationFailure] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ValidationFailure(BaseModel):
    """A specific validation failure."""
    category: Literal["visual", "data", "grounding", "schema"]
    element_id: Optional[str] = None
    expected: Any
    actual: Any
    message: str
```

Add to Document:
```python
class Document(BaseModel):
    # ... existing fields ...

    validation: Optional[ValidationResult] = None
```

## Open Questions & Concerns

### Question 1: GPU Requirements

Many tools (Surya, DePlot) require GPU. How do we handle users without GPUs?

**Options**:
1. Make GPU tools optional, provide CPU fallbacks
2. Provide cloud/API alternatives
3. Document GPU requirements clearly

**Leaning toward**: Option 1 + 3. Make it work on CPU (slow) but recommend GPU.

### Question 2: GROBID Service Management

GROBID requires a Java service. Who manages this?

**Options**:
1. User responsibility (provide docker-compose)
2. We manage it (subprocess launching)
3. Use cloud GROBID API (if available)

**Leaning toward**: Option 1 for libraries, Option 2 for CLI tools.

### Question 3: Cost Management for API-based VLMs

GLM-4.5V costs $0.60/$1.80 per M tokens. For large test suites, this adds up.

**Mitigation strategies**:
1. **Caching**: Cache VLM responses keyed by image hash
2. **Sampling**: Only test random subset of documents
3. **Local alternatives**: Prefer DePlot/SmolDocling when possible
4. **Cost limits**: Config option to set max API spend

```python
class VLMConfig(BaseModel):
    # ... existing fields ...

    # Cost controls
    enable_caching: bool = True
    cache_dir: str = ".vlm_cache"
    max_cost_usd: Optional[float] = None  # Stop if exceeded
    prefer_local_models: bool = True  # Use DePlot before GLM-4.5V
```

### Question 4: Version Compatibility

Tools evolve. DePlot models get updated. GROBID releases new versions. How do we ensure reproducibility?

**Solution**: Pin versions and document them:

```python
class ExtractionMetadata(BaseModel):
    # ... existing fields ...

    environment: ExtractionEnvironment


class ExtractionEnvironment(BaseModel):
    """Environment snapshot for reproducibility."""
    python_version: str
    tool_versions: Dict[str, str]  # {tool_name: version}
    model_versions: Dict[str, str]  # {model_name: checkpoint}

    # For reproducibility
    random_seed: Optional[int] = None
    deterministic: bool = False  # Disable sampling randomness
```

### Question 5: How Much to Abstract?

Should we expose tool-specific details or abstract them away?

**Example**: Should users know they're using DePlot, or just call a generic `extract_chart_data()`?

**Tension**:
- **High abstraction**: Easier to use, but less control
- **Low abstraction**: More control, but steeper learning curve

**Leaning toward**: Layered API
- **High-level**: `doc.extract()` - does everything automatically
- **Mid-level**: `doc.extract_charts(method="deplot")` - some control
- **Low-level**: Direct tool access for power users

## Implementation Priority Re-Evaluation

After this deeper analysis, my priorities shift:

### Phase 0: Foundation (Must Have First)
1. **Instructor** - Without this, VLM extraction is unreliable
2. **PyMuPDF + pdfplumber** - Basic PDF processing
3. **DeepDiff + TheFuzz** - Core validation
4. **Basic schema** - Document, ContentElement, Figure, Table

### Phase 1: Core Capabilities (Week 1-2)
5. **DePlot** - Chart analysis (most unique capability)
6. **pytest-image-snapshot** - Visual regression
7. **Surya** - Layout analysis (can start with CPU, add GPU later)

### Phase 2: Specialized Tools (Week 3-4)
8. **GROBID** - Academic papers (with Docker guide)
9. **Marker** - Alternative PDF processing
10. **GLM-4.5V grounding** - Advanced validation

### Phase 3: Polish (Week 5+)
11. **SmolDocling** - Cost-effective alternative
12. **Matcha** - Advanced math charts
13. **Performance optimization** - Caching, batching

## Final Recommendations

### Immediate Actions:

1. **Create layered requirements files**:
   - `requirements-core.txt`
   - `requirements-gpu.txt`
   - `requirements-academic.txt`

2. **Enhance schema with**:
   - `ExtractionProvenance` for tracking tool usage
   - `ValidationResult` for test results
   - `EquivalenceConfig` for validation settings
   - Enhanced `Plot` with `data_table` field

3. **Start with Instructor integration**:
   - This is the highest-leverage addition
   - Works with existing Pydantic schemas
   - Immediately improves VLM reliability

4. **Document GPU requirements clearly**:
   - Surya and DePlot need GPU for reasonable speed
   - Provide CPU fallbacks
   - Document cloud alternatives

5. **Create GROBID setup guide**:
   - Docker Compose file
   - Alternative: Marker for users who can't run GROBID
   - Make it optional but recommended

### What NOT to do (yet):

1. ❌ Don't integrate every tool mentioned - start with core set
2. ❌ Don't require GPU - make it optional
3. ❌ Don't force GROBID on everyone - optional for academic papers
4. ❌ Don't build custom chart analysis - use DePlot
5. ❌ Don't reinvent validation - use DeepDiff/TheFuzz

## Conclusion

The tool landscape is rich but requires careful curation. The key insight is that **different tools excel at different tasks**:

- **PyMuPDF**: Fast text extraction
- **pdfplumber**: Table extraction
- **Surya**: Layout understanding
- **DePlot**: Chart → data
- **GROBID**: Academic papers
- **Instructor**: Reliable structured output
- **DeepDiff**: Fuzzy validation

Our job is to **orchestrate** these tools into a coherent pipeline, not to replace them with a monolithic VLM approach.

The schema should be **tool-agnostic** but **validation-aware** - we don't care which tool extracted data, but we do care about tracking provenance and validation results.

Next step: Get user feedback on this thinking, then create concrete implementation PRs.
