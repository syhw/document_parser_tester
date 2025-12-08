# Quick Start Guide - Phase 0

## Installation

```bash
# Activate environment
micromamba activate doc_understanding_render_checker

# Install Phase 0 dependencies (already installed)
pip install -r requirements-core.txt
```

## Running Tests

### All Tests at Once
```bash
# Run all Phase 0 tests
python test_setup.py
python test_pdf_parser.py
python test_equivalence.py
python test_complete_workflow.py
```

### Individual Components

**Test 1: Basic Setup**
```bash
python test_setup.py
```
Verifies: imports, schemas, JSON serialization

**Test 2: PDF Parser**
```bash
python test_pdf_parser.py
```
Verifies: PDF parsing, metadata extraction, bounding boxes

**Test 3: Equivalence Checker**
```bash
python test_equivalence.py
```
Verifies: comparison logic, fuzzy matching, quality scoring

**Test 4: Complete Workflow**
```bash
python test_complete_workflow.py
```
Verifies: end-to-end pipeline with JSON export

## Usage Examples

### 1. Parse a PDF

```python
from vlm_doc_test.parsers import PDFParser
from vlm_doc_test.schemas.base import DocumentCategory

# Create parser
parser = PDFParser()

# Parse PDF
document = parser.parse(
    "your_document.pdf",
    extract_images=True,
    extract_tables=True,
    category=DocumentCategory.ACADEMIC_PAPER,
)

# Access results
print(f"Title: {document.metadata.title}")
print(f"Elements: {len(document.content)}")
print(f"Figures: {len(document.figures)}")

# Export to JSON
json_output = document.model_dump_json(indent=2)
```

### 2. Compare Extractions

```python
from vlm_doc_test.validation import EquivalenceChecker

# Create checker
checker = EquivalenceChecker(
    text_similarity_threshold=0.85,
    bbox_iou_threshold=0.7,
)

# Compare two documents
result = checker.compare_documents(tool_doc, vlm_doc)

# Check results
print(f"Quality: {result.match_quality}")
print(f"Score: {result.score:.2%}")

if result.warnings:
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

### 3. VLM Analysis (requires API key)

```python
from vlm_doc_test.vlm_analyzer import VLMAnalyzer

# Set up API key in .env file first
# Copy .env.example to .env and add your key

# Create analyzer
analyzer = VLMAnalyzer()

# Analyze document image
vlm_document = analyzer.analyze_document_image(
    "document_screenshot.png",
    document_id="doc-001",
    extract_bboxes=True,
)

# Access results
print(f"Extracted {len(vlm_document.content)} elements")
```

## Demo Script

Run the complete demo:
```bash
python examples/pdf_extraction_demo.py test_document.pdf
```

## File Locations

- **Package**: `vlm_doc_test/`
- **Tests**: `test_*.py`
- **Examples**: `examples/`
- **Config**: `.env.example` (copy to `.env`)
- **Requirements**: `requirements-*.txt`

## Test Results

All Phase 0 tests passing ✅

See `test_summary.txt` for detailed results.

## Next Steps

Phase 0 complete! Ready for Phase 1:
- DePlot chart analysis
- pytest-image-snapshot visual regression
- HTML parser with BeautifulSoup
- Enhanced validation framework

## Troubleshooting

**Import errors?**
```bash
# Make sure you're in the right directory
cd /home/syhw/claude_tester

# Verify environment
micromamba activate doc_understanding_render_checker
python -c "import vlm_doc_test; print('OK')"
```

**VLM analyzer not working?**
- Copy `.env.example` to `.env`
- Add your `GLM_API_KEY` or `OPENAI_API_KEY`
- VLM tests are optional for Phase 0

## Documentation

- `README.md` - Full project documentation
- `SCHEMA.md` - Complete schema reference
- `SCHEMA_SIMPLE.md` - Simplified schema docs
- `PHASE_0_COMPLETE.md` - Implementation details
- `test_summary.txt` - Test results summary
