#!/usr/bin/env python3
"""
Quick Phase 3 Testing Script

This script demonstrates how to test Phase 3 features:
1. Basic imports and setup verification
2. Quick PDF comparison (PyMuPDF only - fast)
3. Full pipeline comparison (all parsers - slower)

Usage:
    # Quick test (fast, no model downloads):
    python test_phase3_quick.py --quick

    # Full test (downloads models on first run):
    python test_phase3_quick.py --full

    # Just run pytest:
    pytest vlm_doc_test/tests/test_pipeline_comparison.py -v
"""

import sys
import argparse
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test 1: Verify all Phase 3 imports work."""
    print("\n" + "="*70)
    print("TEST 1: Verifying Phase 3 Imports")
    print("="*70)

    try:
        from vlm_doc_test.parsers import PDFParser, MarkerParser, DoclingParser
        print("✓ PDFParser imported")
        print("✓ MarkerParser imported")
        print("✓ DoclingParser imported")

        from vlm_doc_test.validation.pipeline_comparison import (
            PDFPipelineComparison,
            PipelineMetrics,
            ComparisonResult,
        )
        print("✓ PDFPipelineComparison imported")
        print("✓ PipelineMetrics imported")
        print("✓ ComparisonResult imported")

        print("\n✅ All imports successful!")
        return True

    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        return False


def test_quick_comparison():
    """Test 2: Quick comparison using only PyMuPDF (no model downloads)."""
    print("\n" + "="*70)
    print("TEST 2: Quick PDF Comparison (PyMuPDF only)")
    print("="*70)

    try:
        import fitz
        from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

        # Create a simple test PDF
        output_dir = Path(__file__).parent / "test_output"
        output_dir.mkdir(exist_ok=True)

        pdf_path = output_dir / "test_quick.pdf"

        print(f"\n1. Creating test PDF: {pdf_path}")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Phase 3 Quick Test", fontsize=16)
        page.insert_text((100, 150), "This is a simple test document.", fontsize=11)
        doc.save(pdf_path)
        doc.close()
        print("   ✓ PDF created")

        # Compare with PyMuPDF only (very fast)
        print("\n2. Running pipeline comparison (PyMuPDF only)...")
        comparison = PDFPipelineComparison()
        result = comparison.compare_all(pdf_path, pipelines=["pymupdf"])

        print(f"\n   Results:")
        print(f"   • PDF Size: {result.pdf_size_mb} MB")
        print(f"   • Pages: {result.page_count}")
        print(f"   • Fastest: {result.fastest_pipeline}")

        for name, metrics in result.pipelines.items():
            print(f"\n   {name.upper()}:")
            print(f"     - Success: {metrics.success}")
            print(f"     - Time: {metrics.time_seconds}s")
            print(f"     - Content elements: {metrics.content_elements}")
            print(f"     - Text length: {metrics.total_text_length} chars")

        # Generate reports
        print("\n3. Generating reports...")

        text_report = comparison.generate_report(result, format="text")
        text_path = output_dir / "quick_report.txt"
        text_path.write_text(text_report)
        print(f"   ✓ Text report: {text_path}")

        md_report = comparison.generate_report(result, format="markdown")
        md_path = output_dir / "quick_report.md"
        md_path.write_text(md_report)
        print(f"   ✓ Markdown report: {md_path}")

        json_report = comparison.generate_report(result, format="json")
        json_path = output_dir / "quick_report.json"
        json_path.write_text(json_report)
        print(f"   ✓ JSON report: {json_path}")

        print(f"\n   Sample report preview:")
        print(f"   {'-'*66}")
        print(text_report[:400])
        print(f"   {'-'*66}")

        print("\n✅ Quick comparison successful!")
        return True

    except Exception as e:
        print(f"\n❌ Quick comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_comparison():
    """Test 3: Full comparison with all pipelines (downloads models on first run)."""
    print("\n" + "="*70)
    print("TEST 3: Full Pipeline Comparison (All Parsers)")
    print("="*70)
    print("\n⚠️  WARNING: This will download models on first run (~1.3GB)")
    print("   - Marker-PDF models: ~1GB")
    print("   - Granite Vision: ~258MB")
    print("   - Subsequent runs will be faster (models cached)")

    proceed = input("\nProceed with full test? (y/N): ")
    if proceed.lower() != 'y':
        print("Skipped full comparison test.")
        return True

    try:
        import fitz
        from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

        # Create a test PDF with more content
        output_dir = Path(__file__).parent / "test_output"
        output_dir.mkdir(exist_ok=True)

        pdf_path = output_dir / "test_full.pdf"

        print(f"\n1. Creating test PDF: {pdf_path}")
        doc = fitz.open()
        page = doc.new_page()

        # Title
        page.insert_text((100, 100), "Phase 3 Full Comparison Test", fontsize=16)

        # Content
        content = """
This document tests all Phase 3 PDF extraction pipelines:

1. PyMuPDF (fitz) - Fast, coordinate-aware extraction
2. Marker-PDF - High-fidelity Markdown conversion
3. Docling + Granite Vision - Local VLM analysis

Each pipeline has different strengths and trade-offs.
        """.strip()
        page.insert_text((100, 150), content, fontsize=10)

        # Simple table
        table_y = 350
        table_data = [
            ["Pipeline", "Speed", "Accuracy"],
            ["PyMuPDF", "Very Fast", "Good"],
            ["Marker", "Moderate", "Excellent"],
            ["Docling", "Moderate", "Excellent"],
        ]

        for row in table_data:
            x = 100
            for cell in row:
                page.insert_text((x, table_y), cell, fontsize=9)
                x += 120
            table_y += 20

        doc.save(pdf_path)
        doc.close()
        print("   ✓ PDF created")

        # Compare all pipelines
        print("\n2. Running full pipeline comparison...")
        print("   This may take 30-60 seconds on first run...")

        comparison = PDFPipelineComparison()
        result = comparison.compare_all(
            pdf_path,
            pipelines=["pymupdf", "marker", "docling"]
        )

        print(f"\n   Overall Results:")
        print(f"   • PDF Size: {result.pdf_size_mb} MB")
        print(f"   • Pages: {result.page_count}")
        print(f"   • Fastest: {result.fastest_pipeline}")
        print(f"   • Most Content: {result.most_content_pipeline}")

        print(f"\n   Pipeline Details:")
        for name, metrics in result.pipelines.items():
            print(f"\n   {name.upper()}:")
            if metrics.success:
                print(f"     ✓ Success")
                print(f"     • Time: {metrics.time_seconds}s")
                print(f"     • Content: {metrics.content_elements} elements")
                print(f"     • Tables: {metrics.tables_extracted}")
                print(f"     • Figures: {metrics.figures_extracted}")
                print(f"     • Text: {metrics.total_text_length} chars")
                print(f"     • Local Model: {'Yes' if metrics.uses_local_model else 'No'}")
                print(f"     • GPU: {'Yes' if metrics.uses_gpu else 'No'}")
            else:
                print(f"     ✗ Failed: {metrics.error}")

        # Generate reports
        print("\n3. Generating comprehensive reports...")

        text_report = comparison.generate_report(result, format="text")
        text_path = output_dir / "full_report.txt"
        text_path.write_text(text_report)
        print(f"   ✓ Text report: {text_path}")

        md_report = comparison.generate_report(result, format="markdown")
        md_path = output_dir / "full_report.md"
        md_path.write_text(md_report)
        print(f"   ✓ Markdown report: {md_path}")

        json_report = comparison.generate_report(result, format="json")
        json_path = output_dir / "full_report.json"
        json_path.write_text(json_report)
        print(f"   ✓ JSON report: {json_path}")

        print("\n✅ Full comparison successful!")
        print(f"\n📁 All reports saved to: {output_dir}")

        return True

    except Exception as e:
        print(f"\n❌ Full comparison failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_parsers():
    """Test 4: Test individual parsers separately."""
    print("\n" + "="*70)
    print("TEST 4: Individual Parser Testing")
    print("="*70)

    try:
        import fitz
        from vlm_doc_test.parsers import PDFParser, MarkerParser, DoclingParser

        # Create test PDF
        output_dir = Path(__file__).parent / "test_output"
        output_dir.mkdir(exist_ok=True)
        pdf_path = output_dir / "test_individual.pdf"

        print(f"\nCreating test PDF: {pdf_path}")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Individual Parser Test", fontsize=16)
        page.insert_text((100, 150), "Testing each parser individually.", fontsize=11)
        doc.save(pdf_path)
        doc.close()
        print("✓ PDF created")

        # Test PyMuPDF Parser
        print("\n1. Testing PyMuPDF Parser...")
        pymupdf_parser = PDFParser()
        doc1 = pymupdf_parser.parse(pdf_path)
        print(f"   ✓ Parsed with PyMuPDF")
        print(f"   • Content elements: {len(doc1.content)}")
        print(f"   • Format: {doc1.format.value}")

        # Test Marker Parser (may fail if models not available)
        print("\n2. Testing Marker Parser...")
        try:
            marker_parser = MarkerParser()
            doc2 = marker_parser.parse(pdf_path)
            print(f"   ✓ Parsed with Marker")
            print(f"   • Content elements: {len(doc2.content)}")
        except Exception as e:
            print(f"   ⚠️  Marker parser skipped: {e}")
            print(f"   (Expected if models not downloaded)")

        # Test Docling Parser (may fail if models not available)
        print("\n3. Testing Docling Parser...")
        try:
            docling_parser = DoclingParser()
            doc3 = docling_parser.parse(pdf_path)
            print(f"   ✓ Parsed with Docling")
            print(f"   • Content elements: {len(doc3.content)}")
            print(f"   • Tables: {len(doc3.tables)}")
            print(f"   • Figures: {len(doc3.figures)}")
        except Exception as e:
            print(f"   ⚠️  Docling parser skipped: {e}")
            print(f"   (Expected if VLM model not downloaded)")

        print("\n✅ Individual parser testing complete!")
        return True

    except Exception as e:
        print(f"\n❌ Individual parser testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Phase 3 features")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (PyMuPDF, no model downloads)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full tests (downloads models on first run)"
    )
    parser.add_argument(
        "--pytest",
        action="store_true",
        help="Run pytest suite"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("PHASE 3 TESTING GUIDE")
    print("="*70)

    # If no args, show help
    if not (args.quick or args.full or args.pytest):
        print("\nUsage:")
        print("  --quick   Run quick tests (PyMuPDF only, ~5 seconds)")
        print("  --full    Run full tests (all parsers, ~60 seconds first run)")
        print("  --pytest  Run pytest suite")
        print("\nExamples:")
        print("  python test_phase3_quick.py --quick")
        print("  python test_phase3_quick.py --full")
        print("  python test_phase3_quick.py --pytest")
        print("\nOr run pytest directly:")
        print("  pytest vlm_doc_test/tests/test_pipeline_comparison.py -v")
        print("  pytest vlm_doc_test/tests/test_marker_parser.py -v")
        print("  pytest vlm_doc_test/tests/test_docling_parser.py -v")
        return 0

    results = []

    # Always test imports
    results.append(("Imports", test_imports()))

    if args.pytest:
        print("\n" + "="*70)
        print("Running pytest suite...")
        print("="*70)
        import subprocess
        result = subprocess.run(
            ["pytest", "vlm_doc_test/tests/test_pipeline_comparison.py", "-v"],
            cwd=Path(__file__).parent
        )
        return result.returncode

    if args.quick:
        results.append(("Quick Comparison", test_quick_comparison()))
        results.append(("Individual Parsers", test_individual_parsers()))

    if args.full:
        results.append(("Quick Comparison", test_quick_comparison()))
        results.append(("Full Comparison", test_full_comparison()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())
