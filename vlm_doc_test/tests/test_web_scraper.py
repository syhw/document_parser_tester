"""
Tests for web scraper combining rendering and parsing.

This module tests the WebScraper class functionality including:
- URL scraping with rendering
- SPA and dynamic content handling
- Screenshot capture
- Error handling
"""

import pytest
from pathlib import Path
from vlm_doc_test.utils.web_scraper import WebScraper, ScrapeResult
from vlm_doc_test.renderers.web_renderer import RenderOptions


class TestWebScraper:
    """Test suite for WebScraper."""

    def test_scraper_initialization(self):
        """Test scraper can be initialized."""
        scraper = WebScraper(headless=True, browser_type="chromium")
        assert scraper.headless is True
        assert scraper.browser_type == "chromium"
        assert scraper.renderer is not None
        assert scraper.parser is not None

    def test_scraper_context_manager(self):
        """Test scraper works as context manager."""
        with WebScraper() as scraper:
            assert scraper.renderer.browser is not None

    def test_scrape_result_dataclass(self):
        """Test ScrapeResult structure."""
        from vlm_doc_test.schemas.schema_simple import SimpleDocument, DocumentSource, DocumentMetadata
        from vlm_doc_test.schemas.base import DocumentFormat
        from datetime import datetime

        doc = SimpleDocument(
            id="test",
            format=DocumentFormat.HTML,
            source=DocumentSource(url="http://example.com", accessed_at=datetime.now()),
            metadata=DocumentMetadata(),
        )

        result = ScrapeResult(
            document=doc,
            screenshot_path=Path("/tmp/test.png"),
            html_content="<html></html>",
            success=True,
            error=None,
        )

        assert result.success is True
        assert result.document.id == "test"
        assert result.screenshot_path == Path("/tmp/test.png")

    def test_scrape_simple_html_content(self, tmp_path):
        """Test scraping HTML content from a temporary file."""
        # Create a simple HTML file
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Test Heading</h1>
            <p>Test paragraph with content.</p>
        </body>
        </html>
        """

        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        screenshot_path = tmp_path / "screenshot.png"

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                screenshot_path=screenshot_path,
                capture_html=True,
            )

            assert result.success is True
            assert result.document is not None
            assert result.html_content is not None
            assert screenshot_path.exists()

    def test_scrape_without_screenshot(self, tmp_path):
        """Test scraping without taking screenshot."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                screenshot_path=None,
                capture_html=True,
            )

            assert result.success is True
            assert result.screenshot_path is None
            assert result.html_content is not None

    def test_scrape_without_html_capture(self, tmp_path):
        """Test scraping without capturing HTML (still gets it for parsing)."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                screenshot_path=None,
                capture_html=False,
            )

            assert result.success is True
            # Even with capture_html=False, we still get HTML for parsing
            assert result.html_content is not None

    def test_scrape_with_wait_selector(self, tmp_path):
        """Test scraping with wait for selector."""
        html_content = """
        <html>
        <body>
            <h1 id="title">Loading...</h1>
            <script>
                setTimeout(function() {
                    var elem = document.createElement('p');
                    elem.id = 'loaded';
                    elem.textContent = 'Content loaded';
                    document.body.appendChild(elem);
                }, 100);
            </script>
        </body>
        </html>
        """

        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_with_wait(
                url=f"file://{html_file}",
                wait_for_selector="#loaded",
                timeout=5000,
            )

            assert result.success is True
            assert result.document is not None

    def test_scrape_spa_with_wait_time(self, tmp_path):
        """Test scraping Single Page Application with wait time."""
        html_content = """
        <html>
        <body>
            <h1>SPA Content</h1>
            <div id="app">Loading...</div>
            <script>
                setTimeout(function() {
                    document.getElementById('app').textContent = 'App loaded';
                }, 50);
            </script>
        </body>
        </html>
        """

        html_file = tmp_path / "spa.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_spa(
                url=f"file://{html_file}",
                wait_time=0.2,
            )

            assert result.success is True
            assert result.document is not None

    def test_scrape_with_render_options(self, tmp_path):
        """Test scraping with custom render options."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        options = RenderOptions(
            viewport_width=800,
            viewport_height=600,
            wait_until="load",
        )

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                render_options=options,
            )

            assert result.success is True

    def test_scrape_with_category(self, tmp_path):
        """Test scraping with document category."""
        from vlm_doc_test.schemas.base import DocumentCategory

        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                category=DocumentCategory.NEWS_ARTICLE,
            )

            assert result.success is True
            assert result.document.category == DocumentCategory.NEWS_ARTICLE

    def test_compare_renderings_multiple_viewports(self, tmp_path):
        """Test comparing renderings at multiple viewport sizes."""
        html_content = "<html><body><h1>Responsive Test</h1></body></html>"

        html_file = tmp_path / "resp.html"
        html_file.write_text(html_content)

        output_dir = tmp_path / "viewports"

        viewports = [
            (1920, 1080),  # Desktop
            (768, 1024),   # Tablet
            (375, 667),    # Mobile
        ]

        with WebScraper() as scraper:
            results = scraper.compare_renderings(
                url=f"file://{html_file}",
                output_dir=output_dir,
                viewports=viewports,
            )

            assert len(results) == 3
            for result in results:
                assert result.success is True
                assert result.screenshot_path is not None
                assert result.screenshot_path.exists()

    def test_compare_renderings_default_viewports(self, tmp_path):
        """Test comparing renderings with default viewport sizes."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        output_dir = tmp_path / "default_viewports"

        with WebScraper() as scraper:
            results = scraper.compare_renderings(
                url=f"file://{html_file}",
                output_dir=output_dir,
            )

            # Default is 3 viewports
            assert len(results) == 3

    def test_scrape_error_handling_invalid_url(self):
        """Test error handling for invalid URL."""
        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url="http://thisisnotavalidurlatallatall12345.com",
            )

            assert result.success is False
            assert result.error is not None
            assert result.document is not None  # Error document created

    def test_scrape_html_with_tables(self, tmp_path):
        """Test scraping HTML with tables."""
        html_content = """
        <html>
        <body>
            <h1>Document with Table</h1>
            <table>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Data 1</td><td>Data 2</td></tr>
                <tr><td>Data 3</td><td>Data 4</td></tr>
            </table>
        </body>
        </html>
        """

        html_file = tmp_path / "table.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(f"file://{html_file}")

            assert result.success is True
            assert len(result.document.tables) > 0

    def test_scrape_html_with_links(self, tmp_path):
        """Test scraping HTML with links."""
        html_content = """
        <html>
        <body>
            <h1>Document with Links</h1>
            <a href="https://example.com">Example Link</a>
            <a href="/relative/path">Relative Link</a>
        </body>
        </html>
        """

        html_file = tmp_path / "links.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(f"file://{html_file}")

            assert result.success is True
            assert len(result.document.links) > 0

    def test_scrape_html_with_images(self, tmp_path):
        """Test scraping HTML with images."""
        html_content = """
        <html>
        <body>
            <h1>Document with Images</h1>
            <img src="https://example.com/image.jpg" alt="Test Image">
        </body>
        </html>
        """

        html_file = tmp_path / "images.html"
        html_file.write_text(html_content)

        with WebScraper() as scraper:
            result = scraper.scrape_url(f"file://{html_file}")

            assert result.success is True
            assert len(result.document.figures) > 0

    def test_scrape_creates_output_directories(self, tmp_path):
        """Test that scraping creates output directories for screenshots."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        screenshot_path = tmp_path / "nested" / "dir" / "screenshot.png"

        with WebScraper() as scraper:
            result = scraper.scrape_url(
                url=f"file://{html_file}",
                screenshot_path=screenshot_path,
            )

            assert result.success is True
            assert screenshot_path.exists()
            assert screenshot_path.parent.exists()

    def test_scrape_metadata_includes_url(self, tmp_path):
        """Test that scraped document includes source URL."""
        html_content = "<html><body><h1>Test</h1></body></html>"
        html_file = tmp_path / "test.html"
        html_file.write_text(html_content)

        url = f"file://{html_file}"

        with WebScraper() as scraper:
            result = scraper.scrape_url(url)

            assert result.success is True
            assert result.document.source.url == url
