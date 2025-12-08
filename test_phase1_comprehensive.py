"""
Comprehensive Phase 1 Integration Tests

This test suite performs in-depth testing of all Phase 1 components
with real-world scenarios and edge cases.
"""

import sys
from pathlib import Path
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent))

from vlm_doc_test.parsers import HTMLParser, PDFParser
from vlm_doc_test.validation import (
    EquivalenceChecker,
    VisualRegressionTester,
    ValidationReporter,
    ReportFormat,
)
from vlm_doc_test.schemas.base import DocumentCategory, DocumentFormat
import pymupdf as fitz
from PIL import Image
import numpy as np


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✅ {test_name}")

    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))
        print(f"  ❌ {test_name}: {error}")

    def print_summary(self):
        total = self.passed + self.failed
        print()
        print("=" * 70)
        print(f"Test Summary: {self.passed}/{total} passed")
        print("=" * 70)
        if self.errors:
            print("\nFailed Tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print()


def test_html_parser_edge_cases(results, temp_dir):
    """Test HTML parser with edge cases."""
    print("\n" + "=" * 70)
    print("1. HTML Parser Edge Cases")
    print("=" * 70)

    parser = HTMLParser()

    # Test 1: Empty HTML
    try:
        empty_html = "<html><body></body></html>"
        doc = parser.parse(empty_html)
        assert len(doc.content) == 0, "Empty HTML should have no content"
        results.add_pass("Empty HTML handling")
    except Exception as e:
        results.add_fail("Empty HTML handling", str(e))

    # Test 2: HTML with nested structures
    try:
        nested_html = """
        <html>
        <body>
            <div>
                <section>
                    <article>
                        <h1>Nested Heading</h1>
                        <p>Nested paragraph</p>
                    </article>
                </section>
            </div>
        </body>
        </html>
        """
        doc = parser.parse(nested_html)
        assert len(doc.content) == 2, "Should extract from nested structures"
        results.add_pass("Nested HTML structures")
    except Exception as e:
        results.add_fail("Nested HTML structures", str(e))

    # Test 3: HTML with special characters
    try:
        special_html = """
        <html>
        <body>
            <h1>Title with &amp; &lt; &gt; &quot;</h1>
            <p>Content with émojis 🎉 and ümlauts</p>
        </body>
        </html>
        """
        doc = parser.parse(special_html)
        assert "&amp;" not in doc.content[0].content, "Should decode HTML entities"
        results.add_pass("Special characters and entities")
    except Exception as e:
        results.add_fail("Special characters and entities", str(e))

    # Test 4: Large HTML document
    try:
        large_html = "<html><body>"
        for i in range(100):
            large_html += f"<h2>Heading {i}</h2><p>Paragraph {i} content</p>"
        large_html += "</body></html>"
        doc = parser.parse(large_html)
        assert len(doc.content) == 200, f"Expected 200 elements, got {len(doc.content)}"
        results.add_pass("Large HTML document (100 headings + 100 paragraphs)")
    except Exception as e:
        results.add_fail("Large HTML document", str(e))

    # Test 5: Malformed HTML
    try:
        malformed = "<html><body><h1>Unclosed heading<p>Missing tags</body>"
        doc = parser.parse(malformed)
        assert len(doc.content) > 0, "Should handle malformed HTML gracefully"
        results.add_pass("Malformed HTML")
    except Exception as e:
        results.add_fail("Malformed HTML", str(e))

    # Test 6: Complex table
    try:
        table_html = """
        <html>
        <body>
            <table>
                <caption>Complex Table</caption>
                <thead>
                    <tr><th colspan="2">Header</th></tr>
                </thead>
                <tbody>
                    <tr><td>A1</td><td>B1</td></tr>
                    <tr><td>A2</td><td>B2</td></tr>
                    <tr><td>A3</td><td>B3</td></tr>
                </tbody>
            </table>
        </body>
        </html>
        """
        doc = parser.parse(table_html)
        assert len(doc.tables) == 1, "Should extract table"
        assert len(doc.tables[0].rows) == 4, f"Expected 4 rows, got {len(doc.tables[0].rows)}"
        results.add_pass("Complex table with thead/tbody")
    except Exception as e:
        results.add_fail("Complex table", str(e))

    # Test 7: Multiple links
    try:
        links_html = """
        <html>
        <body>
            <a href="https://example.com">Link 1</a>
            <a href="https://test.com">Link 2</a>
            <a href="#anchor">Anchor</a>
            <a href="relative.html">Relative</a>
        </body>
        </html>
        """
        doc = parser.parse(links_html)
        # Anchors are skipped, so should have 3 links
        assert len(doc.links) == 3, f"Expected 3 links (excluding anchor), got {len(doc.links)}"
        results.add_pass("Multiple links (excluding anchors)")
    except Exception as e:
        results.add_fail("Multiple links", str(e))


def test_pdf_parser_edge_cases(results, temp_dir):
    """Test PDF parser with edge cases."""
    print("\n" + "=" * 70)
    print("2. PDF Parser Edge Cases")
    print("=" * 70)

    parser = PDFParser()

    # Test 1: Multi-page PDF
    try:
        pdf_path = temp_dir / "multipage.pdf"
        doc = fitz.open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i+1}", fontsize=18)
            page.insert_text((50, 100), f"Content for page {i+1}", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        parsed = parser.parse(str(pdf_path))
        assert len(parsed.content) >= 10, "Should extract from all pages"
        results.add_pass("Multi-page PDF (5 pages)")
    except Exception as e:
        results.add_fail("Multi-page PDF", str(e))

    # Test 2: PDF with no metadata
    try:
        pdf_path = temp_dir / "no_meta.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Content", fontsize=12)
        doc.save(str(pdf_path))
        doc.close()

        parsed = parser.parse(str(pdf_path))
        assert parsed.metadata is not None, "Should handle missing metadata"
        results.add_pass("PDF with no metadata")
    except Exception as e:
        results.add_fail("PDF with no metadata", str(e))

    # Test 3: PDF with images
    try:
        pdf_path = temp_dir / "with_images.pdf"
        doc = fitz.open()
        page = doc.new_page()

        # Create a simple image
        img = Image.new('RGB', (100, 100), color='red')
        img_path = temp_dir / "test_img.png"
        img.save(img_path)

        # Insert image into PDF
        page.insert_image(fitz.Rect(50, 50, 150, 150), filename=str(img_path))
        doc.save(str(pdf_path))
        doc.close()

        parsed = parser.parse(str(pdf_path), extract_images=True)
        assert len(parsed.figures) >= 1, "Should extract images"
        results.add_pass("PDF with embedded images")
    except Exception as e:
        results.add_fail("PDF with embedded images", str(e))

    # Test 4: Large text content
    try:
        pdf_path = temp_dir / "large_text.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=2000)  # Tall page

        y_pos = 50
        for i in range(50):
            page.insert_text((50, y_pos), f"Line {i}: " + "x" * 50, fontsize=10)
            y_pos += 15

        doc.save(str(pdf_path))
        doc.close()

        parsed = parser.parse(str(pdf_path))
        assert len(parsed.content) >= 40, "Should handle large text content"
        results.add_pass("PDF with large text content (50 lines)")
    except Exception as e:
        results.add_fail("PDF with large text", str(e))


def test_equivalence_checker_scenarios(results, temp_dir):
    """Test equivalence checker with various scenarios."""
    print("\n" + "=" * 70)
    print("3. Equivalence Checker Scenarios")
    print("=" * 70)

    from vlm_doc_test.schemas.schema_simple import (
        SimpleDocument, DocumentSource, DocumentMetadata,
        ContentElement, Author
    )
    from datetime import datetime

    checker = EquivalenceChecker()

    # Test 1: Different content lengths
    try:
        source = DocumentSource(accessed_at=datetime.now())

        doc1 = SimpleDocument(
            id="d1", format=DocumentFormat.HTML, source=source,
            metadata=DocumentMetadata(title="Test"),
            content=[
                ContentElement(id="c1", type="paragraph", content="Para 1"),
                ContentElement(id="c2", type="paragraph", content="Para 2"),
                ContentElement(id="c3", type="paragraph", content="Para 3"),
            ]
        )

        doc2 = SimpleDocument(
            id="d2", format=DocumentFormat.HTML, source=source,
            metadata=DocumentMetadata(title="Test"),
            content=[
                ContentElement(id="c1", type="paragraph", content="Para 1"),
            ]
        )

        result = checker.compare_documents(doc1, doc2)
        assert result.score < 1.0, "Different lengths should score < 1.0"
        results.add_pass("Different content lengths")
    except Exception as e:
        results.add_fail("Different content lengths", str(e))

    # Test 2: Paraphrased content
    try:
        doc1.content = [
            ContentElement(id="c1", type="paragraph",
                         content="The quick brown fox jumps over the lazy dog")
        ]
        doc2.content = [
            ContentElement(id="c1", type="paragraph",
                         content="A fast brown fox leaps across a sleepy dog")
        ]

        result = checker.compare_documents(doc1, doc2)
        assert 0.3 < result.score < 0.9, "Paraphrased should score in middle range"
        results.add_pass("Paraphrased content detection")
    except Exception as e:
        results.add_fail("Paraphrased content", str(e))

    # Test 3: Case sensitivity
    try:
        doc1.content = [ContentElement(id="c1", type="paragraph", content="HELLO WORLD")]
        doc2.content = [ContentElement(id="c1", type="paragraph", content="hello world")]

        result = checker.compare_documents(doc1, doc2)
        assert result.score > 0.7, "Case differences should still score reasonably high"
        results.add_pass("Case sensitivity handling")
    except Exception as e:
        results.add_fail("Case sensitivity", str(e))


def test_visual_regression_scenarios(results, temp_dir):
    """Test visual regression with various image scenarios."""
    print("\n" + "=" * 70)
    print("4. Visual Regression Scenarios")
    print("=" * 70)

    tester = VisualRegressionTester()

    # Test 1: Grayscale images
    try:
        img1 = Image.new('L', (200, 200), color=128)
        img2 = Image.new('L', (200, 200), color=128)

        path1 = temp_dir / "gray1.png"
        path2 = temp_dir / "gray2.png"
        img1.save(path1)
        img2.save(path2)

        result = tester.compare_images(path1, path2)
        assert result.similarity_score == 1.0, "Identical grayscale should score 1.0"
        results.add_pass("Grayscale image comparison")
    except Exception as e:
        results.add_fail("Grayscale comparison", str(e))

    # Test 2: High contrast images
    try:
        img1 = Image.new('RGB', (200, 200), color='white')
        pixels = img1.load()
        for x in range(100, 200):
            for y in range(100, 200):
                pixels[x, y] = (0, 0, 0)

        img2 = Image.new('RGB', (200, 200), color='black')
        pixels2 = img2.load()
        for x in range(0, 100):
            for y in range(0, 100):
                pixels2[x, y] = (255, 255, 255)

        path1 = temp_dir / "contrast1.png"
        path2 = temp_dir / "contrast2.png"
        img1.save(path1)
        img2.save(path2)

        result = tester.compare_images(path1, path2)
        assert result.similarity_score < 0.8, "High contrast differences should score low"
        results.add_pass("High contrast differences")
    except Exception as e:
        results.add_fail("High contrast differences", str(e))

    # Test 3: Gradual changes
    try:
        img1 = Image.new('RGB', (200, 200), color='white')
        img2 = Image.new('RGB', (200, 200), color='white')
        pixels2 = img2.load()

        # Add gradual noise
        np.random.seed(42)
        for x in range(200):
            for y in range(200):
                if np.random.random() < 0.01:  # 1% noise
                    pixels2[x, y] = (200, 200, 200)

        path1 = temp_dir / "grad1.png"
        path2 = temp_dir / "grad2.png"
        img1.save(path1)
        img2.save(path2)

        result = tester.compare_images(path1, path2)
        assert result.similarity_score > 0.95, "Small gradual changes should score high"
        results.add_pass("Gradual pixel changes (1% noise)")
    except Exception as e:
        results.add_fail("Gradual changes", str(e))

    # Test 4: Different aspect ratios
    try:
        img1 = Image.new('RGB', (200, 100), color='blue')
        img2 = Image.new('RGB', (100, 200), color='blue')

        path1 = temp_dir / "aspect1.png"
        path2 = temp_dir / "aspect2.png"
        img1.save(path1)
        img2.save(path2)

        result = tester.compare_images(path1, path2)
        # Should resize and compare
        assert result is not None, "Should handle different aspect ratios"
        results.add_pass("Different aspect ratios")
    except Exception as e:
        results.add_fail("Different aspect ratios", str(e))


def test_reporter_scenarios(results, temp_dir):
    """Test reporter with various scenarios."""
    print("\n" + "=" * 70)
    print("5. Reporter Scenarios")
    print("=" * 70)

    from vlm_doc_test.validation.equivalence import ComparisonResult, MatchQuality
    from vlm_doc_test.validation.visual_regression import VisualComparisonResult

    reporter = ValidationReporter()

    # Test 1: Report with no results
    try:
        report = reporter.start_report("Empty Test")
        report = reporter.finalize_report(report)
        assert report.summary['total_comparisons'] == 0
        results.add_pass("Empty report generation")
    except Exception as e:
        results.add_fail("Empty report", str(e))

    # Test 2: Report with multiple comparisons
    try:
        report = reporter.start_report("Multi Test")

        for i in range(10):
            comp_result = ComparisonResult(
                match_quality=MatchQuality.GOOD,
                score=0.85 + (i * 0.01),
                details={},
            )
            report.add_comparison(comp_result)

        report = reporter.finalize_report(report)
        assert report.summary['total_comparisons'] == 10
        assert 'avg_score' in report.summary
        results.add_pass("Multiple comparisons in report")
    except Exception as e:
        results.add_fail("Multiple comparisons", str(e))

    # Test 3: All report formats
    try:
        report = reporter.start_report("Format Test")
        comp_result = ComparisonResult(
            match_quality=MatchQuality.EXCELLENT,
            score=0.97,
            details={'test': 'data'},
        )
        report.add_comparison(comp_result)
        report = reporter.finalize_report(report)

        # Generate all formats
        text = reporter.generate_text_report(report)
        json_str = reporter.generate_json_report(report)
        markdown = reporter.generate_markdown_report(report)

        assert len(text) > 0 and "Format Test" in text
        assert len(json_str) > 0 and '"test_name"' in json_str
        assert len(markdown) > 0 and "# Validation Report" in markdown

        results.add_pass("All report formats (TEXT/JSON/Markdown)")
    except Exception as e:
        results.add_fail("All report formats", str(e))

    # Test 4: Report file saving
    try:
        for format_type, ext in [
            (ReportFormat.TEXT, ".txt"),
            (ReportFormat.JSON, ".json"),
            (ReportFormat.MARKDOWN, ".md"),
        ]:
            output_path = temp_dir / f"test_report{ext}"
            reporter.save_report(report, output_path, format=format_type)
            assert output_path.exists(), f"Report file should exist: {output_path}"
            assert output_path.stat().st_size > 0, "Report file should not be empty"

        results.add_pass("Report file saving (all formats)")
    except Exception as e:
        results.add_fail("Report file saving", str(e))


def test_integration_workflow(results, temp_dir):
    """Test complete integration workflow."""
    print("\n" + "=" * 70)
    print("6. Integration Workflow Test")
    print("=" * 70)

    try:
        # Step 1: Create HTML document
        html_content = """
        <html>
        <head><title>Integration Test</title></head>
        <body>
            <h1>Test Document</h1>
            <p>This is a test paragraph.</p>
            <table>
                <tr><td>A</td><td>B</td></tr>
            </table>
        </body>
        </html>
        """

        html_parser = HTMLParser()
        doc1 = html_parser.parse(html_content, url="https://test.com")

        # Step 2: Create similar document
        doc2 = html_parser.parse(html_content, url="https://test.com")

        # Step 3: Compare
        checker = EquivalenceChecker()
        comp_result = checker.compare_documents(doc1, doc2)

        # Step 4: Create visual comparison
        img = Image.new('RGB', (300, 200), color='white')
        img_path = temp_dir / "workflow.png"
        img.save(img_path)

        visual_tester = VisualRegressionTester()
        visual_result = visual_tester.compare_images(img_path, img_path)

        # Step 5: Generate report
        reporter = ValidationReporter()
        report = reporter.start_report("Integration Workflow")
        report.add_comparison(comp_result)
        report.add_visual_comparison(visual_result)
        report = reporter.finalize_report(report)

        # Step 6: Save report
        report_path = temp_dir / "integration_report.txt"
        reporter.save_report(report, report_path, ReportFormat.TEXT)

        # Verify everything
        assert comp_result.score == 1.0, "Identical docs should score 1.0"
        assert visual_result.passed, "Identical images should pass"
        assert report.passed, "Report should show passed"
        assert report_path.exists(), "Report file should exist"

        results.add_pass("Complete integration workflow")
    except Exception as e:
        results.add_fail("Complete integration workflow", str(e))


def main():
    """Run all comprehensive tests."""
    print("=" * 70)
    print("PHASE 1 COMPREHENSIVE TESTING")
    print("=" * 70)

    results = TestResults()

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="phase1_test_"))
    print(f"\nUsing temporary directory: {temp_dir}")

    try:
        # Run all test suites
        test_html_parser_edge_cases(results, temp_dir)
        test_pdf_parser_edge_cases(results, temp_dir)
        test_equivalence_checker_scenarios(results, temp_dir)
        test_visual_regression_scenarios(results, temp_dir)
        test_reporter_scenarios(results, temp_dir)
        test_integration_workflow(results, temp_dir)

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\nCleaned up temporary directory")

    # Print results
    results.print_summary()

    return results.failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
