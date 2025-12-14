# Phase 3 Testing Guide

This guide shows you all the ways to test Phase 3 features of the VLM Document Testing Library.

## Quick Start

### 1. Run the Quick Test Script (Recommended for First-Time Users)

```bash
# Show available options
~/micromamba/envs/doc_understanding_render_checker/bin/python test_phase3_quick.py

# Run quick tests (PyMuPDF only, no model downloads, ~5 seconds)
~/micromamba/envs/doc_understanding_render_checker/bin/python test_phase3_quick.py --quick

# Run full tests (downloads models on first run, ~60 seconds)
~/micromamba/envs/doc_understanding_render_checker/bin/python test_phase3_quick.py --full

# Run pytest suite
~/micromamba/envs/doc_understanding_render_checker/bin/python test_phase3_quick.py --pytest
```

### 2. Run Pytest Directly

```bash
# Activate environment
eval "$(~/micromamba/bin/micromamba shell hook --shell bash)"
micromamba activate doc_understanding_render_checker

# Run all Phase 3 tests
pytest vlm_doc_test/tests/test_pipeline_comparison.py -v
pytest vlm_doc_test/tests/test_marker_parser.py -v
pytest vlm_doc_test/tests/test_docling_parser.py -v

# Run all tests
pytest vlm_doc_test/tests/ -v

# Run specific test
pytest vlm_doc_test/tests/test_pipeline_comparison.py::test_compare_all_single_pipeline -v
```

### 3. Run the Phase 3 Demo

```bash
# Full Phase 3 demonstration
~/micromamba/envs/doc_understanding_render_checker/bin/python examples/phase3_demo.py
```

## Test Output Examples

### Quick Test Output (from test_phase3_quick.py --quick)

```
======================================================================
TEST 1: Verifying Phase 3 Imports
======================================================================
✓ PDFParser imported
✓ MarkerParser imported
✓ DoclingParser imported
✓ PDFPipelineComparison imported
✓ PipelineMetrics imported
✓ ComparisonResult imported

✅ All imports successful!

======================================================================
TEST 2: Quick PDF Comparison (PyMuPDF only)
======================================================================

1. Creating test PDF: /home/syhw/claude_tester/test_output/test_quick.pdf
   ✓ PDF created

2. Running pipeline comparison (PyMuPDF only)...

   Results:
   • PDF Size: 0.0 MB
   • Pages: 1
   • Fastest: pymupdf

   PYMUPDF:
     - Success: True
     - Time: 0.005s
     - Content elements: 2
     - Text length: 49 chars

3. Generating reports...
   ✓ Text report: test_output/quick_report.txt
   ✓ Markdown report: test_output/quick_report.md
   ✓ JSON report: test_output/quick_report.json

✅ Quick comparison successful!
```

### Pytest Output

```bash
$ pytest vlm_doc_test/tests/test_pipeline_comparison.py -v

test_pipeline_comparison_import PASSED
test_pipeline_metrics_dataclass PASSED
test_comparison_framework_initialization PASSED
test_get_parser_pymupdf PASSED
test_get_parser_marker PASSED
test_get_parser_docling PASSED
test_get_parser_invalid PASSED
test_run_pipeline_invalid PASSED
test_run_pipeline_pymupdf PASSED
test_compare_all_single_pipeline PASSED
test_compare_all_multiple_pipelines PASSED
test_comparison_result_structure PASSED
test_generate_text_report PASSED
test_generate_markdown_report PASSED
test_generate_json_report PASSED
test_generate_report_invalid_format PASSED
test_batch_compare_interface PASSED
test_comparison_to_dict PASSED
test_pipeline_metrics_uses_flags PASSED

====== 19 passed in 75.42s ======
```

## Testing Individual Components

### Test PyMuPDF Parser (Fast)

```python
from pathlib import Path
from vlm_doc_test.parsers import PDFParser

parser = PDFParser()
document = parser.parse(Path("test.pdf"))

print(f"Content elements: {len(document.content)}")
print(f"Tables: {len(document.tables)}")
print(f"Links: {len(document.links)}")
```

### Test Marker Parser (Requires Model Download)

```python
from pathlib import Path
from vlm_doc_test.parsers import MarkerParser

# Note: First run downloads ~1GB of models
parser = MarkerParser()
document = parser.parse(Path("test.pdf"))

print(f"Content elements: {len(document.content)}")
print(f"Tables: {len(document.tables)}")

# Export to markdown
markdown = parser.parse_to_markdown(Path("test.pdf"))
print(markdown)
```

### Test Docling Parser (Requires VLM Model Download)

```python
from pathlib import Path
from vlm_doc_test.parsers import DoclingParser

# Note: First run downloads ~258MB Granite Vision model
parser = DoclingParser()
document = parser.parse(Path("test.pdf"))

print(f"Content elements: {len(document.content)}")
print(f"Tables: {len(document.tables)}")
print(f"Figures: {len(document.figures)}")

# Export to markdown
markdown = parser.parse_to_markdown(Path("test.pdf"))
print(markdown)
```

### Test Pipeline Comparison

```python
from pathlib import Path
from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

comparison = PDFPipelineComparison()

# Compare all pipelines
result = comparison.compare_all(
    Path("test.pdf"),
    pipelines=["pymupdf", "marker", "docling"]
)

print(f"Fastest: {result.fastest_pipeline}")
print(f"Most Content: {result.most_content_pipeline}")

# Generate reports
text_report = comparison.generate_report(result, format="text")
print(text_report)

markdown_report = comparison.generate_report(result, format="markdown")
json_report = comparison.generate_report(result, format="json")
```

## Understanding Test Results

### What Each Test Validates

**test_pipeline_comparison.py** (19 tests):
- Import functionality
- Parser initialization
- Pipeline execution
- Metrics collection
- Report generation (TEXT, Markdown, JSON)
- Batch comparison
- Error handling

**test_marker_parser.py** (9 tests):
- Marker-PDF integration
- Markdown conversion
- Table extraction
- Batch conversion
- Comparison with PyMuPDF

**test_docling_parser.py** (13 tests):
- Docling + Granite Vision integration
- VLM-based parsing
- Multi-format support
- Figure extraction with descriptions
- Comparison with Marker

### Performance Expectations

| Test Type | Duration | Downloads |
|-----------|----------|-----------|
| Quick test (PyMuPDF only) | ~5 seconds | None |
| Marker parser tests | ~30 seconds first run | ~1GB models |
| Docling parser tests | ~30 seconds first run | ~258MB VLM |
| Full pipeline comparison | ~60 seconds first run | ~1.3GB total |
| Subsequent runs | ~10 seconds | None (cached) |

## Troubleshooting

### Models Not Downloaded

If you see errors like "VLM model not downloaded" or "Marker models not available":

```bash
# Run the full test to download models
~/micromamba/envs/doc_understanding_render_checker/bin/python test_phase3_quick.py --full
```

This will:
1. Download Marker-PDF models (~1GB)
2. Download Granite Vision model (~258MB)
3. Cache models for future use

### Permission Warnings

If you see warnings about "Could not set the permissions":
- These are harmless warnings from Hugging Face Hub
- They occur on WSL/Windows file systems
- Models download and work correctly despite the warnings

### Marker Parser Errors

If Marker parser fails with "'tuple' object has no attribute 'split'":
- Models may not be fully downloaded
- Try running: `python test_phase3_quick.py --full`
- Or wait for models to fully download in background

### Docling Parser Errors

If Docling fails with "Input/output error":
- VLM model may not be available
- Check GPU availability (CUDA)
- Try running on CPU (slower but works)

### Memory Issues

If you get out-of-memory errors:
- Marker and Docling require ~3-5GB RAM
- GPU recommended but not required
- Close other applications
- Or test with PyMuPDF only

## Test Coverage

### Current Status
- **Total Tests**: 124 (all phases)
- **Phase 3 Tests**: 41
- **Pass Rate**: 100%

### Test Breakdown
- Core schemas (Phase 0): 32 tests
- HTML & visual regression (Phase 1): 32 tests
- Playwright & web scraping (Phase 2): 49 tests
- Multi-pipeline extraction (Phase 3): 41 tests

## Generated Reports

After running tests, check these directories for output:

```bash
# Quick test outputs
test_output/
├── quick_report.txt
├── quick_report.md
├── quick_report.json
├── test_quick.pdf

# Full test outputs
test_output/
├── full_report.txt
├── full_report.md
├── full_report.json
├── test_full.pdf

# Phase 3 demo outputs
examples/output/
├── phase3_marker/
│   ├── sample.pdf
│   └── sample.md
├── phase3_docling/
│   ├── sample.pdf
│   └── sample.md
└── phase3_comparison/
    ├── sample.pdf
    ├── comparison_report.txt
    ├── comparison_report.md
    └── comparison_report.json
```

## Sample Report Format

### Text Report
```
======================================================================
PDF PIPELINE COMPARISON REPORT
======================================================================

PDF: /path/to/document.pdf
Size: 1.23 MB
Pages: 5
Tested: 2025-12-08 21:10:31

----------------------------------------------------------------------
PIPELINE RESULTS
----------------------------------------------------------------------

PYMUPDF:
  ✓ Success
  Time: 0.052s
  Content Elements: 42
  Tables: 3
  Total Text: 5024 chars
  Local Model: No
  GPU: No

MARKER:
  ✓ Success
  Time: 4.183s
  Content Elements: 48
  Tables: 5
  Total Text: 5234 chars
  Local Model: No
  GPU: Yes

DOCLING:
  ✓ Success
  Time: 8.741s
  Content Elements: 45
  Tables: 4
  Figures: 2
  Total Text: 5187 chars
  Local Model: Yes
  GPU: Yes

----------------------------------------------------------------------
SUMMARY
----------------------------------------------------------------------
Fastest Pipeline: pymupdf
Most Content: marker
Best Time: 0.052s
======================================================================
```

## Next Steps

After testing Phase 3:

1. **Review Reports**: Check generated reports in `test_output/`
2. **Try Demo**: Run `examples/phase3_demo.py` for full demonstration
3. **Integrate**: Use parsers in your own code
4. **Benchmark**: Compare pipelines on your own PDFs
5. **Customize**: Adjust configs for your use case

## Support

For issues or questions:
- Check `PHASE_3_COMPLETE.md` for detailed documentation
- Review test files for usage examples
- See `examples/phase3_demo.py` for comprehensive demo
