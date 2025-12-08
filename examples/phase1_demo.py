"""
Phase 1 Complete Demo

Demonstrates all Phase 1 features:
1. HTML parsing with BeautifulSoup
2. PDF parsing with PyMuPDF
3. Equivalence checking with DeepDiff and TheFuzz
4. Visual regression testing with SSIM
5. Enhanced reporting framework
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vlm_doc_test.parsers import HTMLParser, PDFParser
from vlm_doc_test.validation import (
    EquivalenceChecker,
    VisualRegressionTester,
    ValidationReporter,
    ReportFormat,
)
from vlm_doc_test.schemas.base import DocumentCategory
from PIL import Image
import numpy as np


def create_sample_html(path: Path):
    """Create a sample HTML file for testing."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="author" content="Demo Author">
    <title>Phase 1 Demo Document</title>
</head>
<body>
    <main>
        <article>
            <h1>Introduction to VLM Document Testing</h1>

            <h2>Overview</h2>
            <p>This document demonstrates the Phase 1 capabilities of the VLM-based
            document testing library. It includes HTML parsing, validation, and
            visual regression testing.</p>

            <h2>Key Features</h2>
            <p>The library can extract structured content from various document formats
            including HTML, PDF, and images. It uses advanced comparison techniques
            for validation.</p>

            <table>
                <caption>Test Results</caption>
                <tr>
                    <th>Component</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>HTML Parser</td>
                    <td>✅ Passing</td>
                </tr>
                <tr>
                    <td>PDF Parser</td>
                    <td>✅ Passing</td>
                </tr>
            </table>

            <p>Learn more at <a href="https://github.com/example/vlm-doc-test">our repository</a>.</p>
        </article>
    </main>
</body>
</html>"""

    path.write_text(html_content, encoding='utf-8')
    return path


def create_sample_images(dir_path: Path):
    """Create sample images for visual regression testing."""
    # Create baseline image
    baseline = Image.new('RGB', (400, 300), color='white')
    pixels = baseline.load()

    # Draw blue rectangle
    for x in range(100, 300):
        for y in range(100, 200):
            pixels[x, y] = (0, 100, 255)

    # Add text-like pattern
    for x in range(50, 350):
        if x % 10 == 0:
            for y in range(50, 60):
                pixels[x, y] = (0, 0, 0)

    baseline_path = dir_path / "baseline.png"
    baseline.save(baseline_path)

    # Create slightly modified version
    modified = baseline.copy()
    modified_pixels = modified.load()

    # Add small change
    for x in range(320, 340):
        for y in range(240, 260):
            modified_pixels[x, y] = (255, 200, 0)

    modified_path = dir_path / "current.png"
    modified.save(modified_path)

    return baseline_path, modified_path


def demo_html_parsing(html_path: Path):
    """Demonstrate HTML parsing."""
    print("=" * 70)
    print("1. HTML Parsing Demo")
    print("=" * 70)
    print()

    parser = HTMLParser()
    doc = parser.parse(str(html_path), category=DocumentCategory.WEBPAGE_GENERAL)

    print(f"✅ Parsed HTML document")
    print(f"   Title: {doc.metadata.title}")
    print(f"   Author: {doc.metadata.authors[0].name if doc.metadata.authors else 'N/A'}")
    print(f"   Content elements: {len(doc.content)}")

    headings = [c for c in doc.content if c.type == "heading"]
    paragraphs = [c for c in doc.content if c.type == "paragraph"]

    print(f"   - Headings: {len(headings)}")
    print(f"   - Paragraphs: {len(paragraphs)}")
    print(f"   - Tables: {len(doc.tables)}")
    print(f"   - Links: {len(doc.links)}")
    print()

    print("First few headings:")
    for h in headings[:3]:
        print(f"  H{h.level}: {h.content}")
    print()

    return doc


def demo_equivalence_checking(doc1, doc2):
    """Demonstrate equivalence checking."""
    print("=" * 70)
    print("2. Equivalence Checking Demo")
    print("=" * 70)
    print()

    checker = EquivalenceChecker(
        text_similarity_threshold=0.85,
        bbox_iou_threshold=0.7,
    )

    result = checker.compare_documents(doc1, doc2)

    print(f"Match Quality: {result.match_quality.value.upper()}")
    print(f"Overall Score: {result.score:.2%}")
    print()

    print("Detailed Breakdown:")
    print(f"  Metadata Score: {result.details.get('metadata', {})}")
    print(f"  Content Similarity: {result.details.get('content', {}).get('text_similarity', 0):.2%}")
    print()

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
        print()

    return result


def demo_visual_regression(baseline_path, current_path, output_dir):
    """Demonstrate visual regression testing."""
    print("=" * 70)
    print("3. Visual Regression Testing Demo")
    print("=" * 70)
    print()

    tester = VisualRegressionTester(
        ssim_threshold=0.95,
        pixel_diff_threshold=1.0,
    )

    result = tester.compare_images(
        baseline_path,
        current_path,
        create_diff=True,
    )

    print(f"Visual Comparison Results:")
    print(f"  SSIM Score: {result.similarity_score:.4f}")
    print(f"  Pixel Diff: {result.diff_percentage:.2f}%")
    print(f"  Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print()

    # Save diff image
    if result.diff_image is not None:
        diff_path = output_dir / "visual_diff.png"
        tester.save_diff_image(result.diff_image, diff_path)
        print(f"✅ Saved diff image: {diff_path}")
        print()

    return result


def demo_enhanced_reporting(comp_result, visual_result, output_dir):
    """Demonstrate enhanced reporting."""
    print("=" * 70)
    print("4. Enhanced Reporting Demo")
    print("=" * 70)
    print()

    reporter = ValidationReporter()
    report = reporter.start_report("Phase 1 Demo Test")

    # Add results
    report.add_comparison(comp_result)
    report.add_visual_comparison(visual_result)

    # Finalize
    report = reporter.finalize_report(report)

    print(f"Report Summary:")
    print(f"  Test: {report.test_name}")
    print(f"  Overall Result: {'✅ PASSED' if report.passed else '❌ FAILED'}")
    print(f"  Comparisons: {report.summary['total_comparisons']}")
    print(f"  Visual Tests: {report.summary['total_visual_comparisons']}")
    print()

    # Generate reports in multiple formats
    formats_to_generate = [
        (ReportFormat.TEXT, "report.txt"),
        (ReportFormat.JSON, "report.json"),
        (ReportFormat.MARKDOWN, "report.md"),
    ]

    for format_type, filename in formats_to_generate:
        output_path = output_dir / filename
        reporter.save_report(report, output_path, format=format_type)
        print(f"✅ Generated {format_type.value} report: {output_path}")

    print()

    # Print text report
    print("Text Report Preview:")
    print("-" * 70)
    text_report = reporter.generate_text_report(report)
    print(text_report)


def main():
    """Run the complete Phase 1 demo."""
    print("\n" + "=" * 70)
    print("PHASE 1 COMPLETE DEMONSTRATION")
    print("=" * 70)
    print("\n")

    # Create output directory
    output_dir = Path("phase1_demo_output")
    output_dir.mkdir(exist_ok=True)

    # Create test files
    html_path = output_dir / "demo.html"
    create_sample_html(html_path)

    # Create images for visual testing
    baseline_path, current_path = create_sample_images(output_dir)

    # Demo 1: HTML Parsing
    html_doc = demo_html_parsing(html_path)

    # Demo 2: Equivalence Checking
    # Compare document with itself for exact match
    comparison_result = demo_equivalence_checking(html_doc, html_doc)

    # Demo 3: Visual Regression
    visual_result = demo_visual_regression(baseline_path, current_path, output_dir)

    # Demo 4: Enhanced Reporting
    demo_enhanced_reporting(comparison_result, visual_result, output_dir)

    print("\n" + "=" * 70)
    print("✅ Phase 1 Demo Complete!")
    print("=" * 70)
    print()
    print("Output files saved to: phase1_demo_output/")
    print("  - demo.html - Sample HTML document")
    print("  - baseline.png - Baseline image")
    print("  - current.png - Current image")
    print("  - visual_diff.png - Difference visualization")
    print("  - report.txt - Text format report")
    print("  - report.json - JSON format report")
    print("  - report.md - Markdown format report")
    print()


if __name__ == "__main__":
    main()
