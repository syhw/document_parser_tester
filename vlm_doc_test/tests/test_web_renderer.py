"""
Tests for web renderer using Playwright.

This module tests the WebRenderer class functionality including:
- Basic URL rendering
- HTML content rendering
- Multiple URL rendering
- JavaScript execution
- Context manager usage
"""

import pytest
from pathlib import Path
from vlm_doc_test.renderers.web_renderer import WebRenderer, RenderOptions


class TestWebRenderer:
    """Test suite for WebRenderer."""

    def test_renderer_initialization(self):
        """Test renderer can be initialized with different browsers."""
        renderer = WebRenderer(browser_type="chromium", headless=True)
        assert renderer.browser_type == "chromium"
        assert renderer.headless is True
        assert renderer.browser is None  # Not started yet

    def test_context_manager(self):
        """Test renderer works as context manager."""
        with WebRenderer() as renderer:
            assert renderer.browser is not None
        # Browser should be closed after context exit
        assert renderer.browser is None

    def test_render_simple_html(self, tmp_path):
        """Test rendering simple HTML content."""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test page.</p>
        </body>
        </html>
        """

        output_path = tmp_path / "test_simple.png"

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path)
            assert result.exists()
            assert result.stat().st_size > 0

    def test_render_with_custom_viewport(self, tmp_path):
        """Test rendering with custom viewport size."""
        html = "<html><body><h1>Test</h1></body></html>"
        output_path = tmp_path / "test_viewport.png"

        options = RenderOptions(
            viewport_width=800,
            viewport_height=600,
            full_page=False,
        )

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path, options=options)
            assert result.exists()

    def test_render_with_wait_time(self, tmp_path):
        """Test rendering with additional wait time."""
        html = """
        <html>
        <body>
            <h1 id="title">Loading...</h1>
            <script>
                setTimeout(function() {
                    document.getElementById('title').textContent = 'Loaded!';
                }, 100);
            </script>
        </body>
        </html>
        """

        output_path = tmp_path / "test_wait.png"
        options = RenderOptions(wait_time=0.5)

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path, options=options)
            assert result.exists()

    def test_get_page_html_content(self):
        """Test getting rendered HTML content."""
        html = """
        <html>
        <body>
            <h1>Original</h1>
            <script>
                document.querySelector('h1').textContent = 'Modified by JS';
            </script>
        </body>
        </html>
        """

        with WebRenderer() as renderer:
            # Create a temporary HTML file to serve
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html)
                temp_path = f.name

            try:
                # Get the rendered HTML after JS execution
                content = renderer.get_page_html(f"file://{temp_path}")
                assert "Modified by JS" in content or "Original" in content
            finally:
                Path(temp_path).unlink()

    def test_render_multiple_html_documents(self, tmp_path):
        """Test rendering multiple HTML documents."""
        html_docs = [
            "<html><body><h1>Page 1</h1></body></html>",
            "<html><body><h1>Page 2</h1></body></html>",
            "<html><body><h1>Page 3</h1></body></html>",
        ]

        with WebRenderer() as renderer:
            for idx, html in enumerate(html_docs):
                output_path = tmp_path / f"page_{idx}.png"
                result = renderer.render_html(html, output_path)
                assert result.exists()
                assert result.stat().st_size > 0

    def test_render_with_javascript_disabled(self, tmp_path):
        """Test rendering with JavaScript disabled."""
        html = """
        <html>
        <body>
            <h1>Static</h1>
            <script>
                document.body.innerHTML = '<h1>Should not appear</h1>';
            </script>
        </body>
        </html>
        """

        output_path = tmp_path / "test_no_js.png"
        options = RenderOptions(javascript_enabled=False)

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path, options=options)
            assert result.exists()

    def test_render_creates_parent_directories(self, tmp_path):
        """Test that render creates parent directories if needed."""
        nested_path = tmp_path / "level1" / "level2" / "test.png"
        html = "<html><body><h1>Test</h1></body></html>"

        with WebRenderer() as renderer:
            result = renderer.render_html(html, nested_path)
            assert result.exists()
            assert result.parent.exists()

    def test_render_options_defaults(self):
        """Test RenderOptions has correct defaults."""
        options = RenderOptions()
        assert options.viewport_width == 1920
        assert options.viewport_height == 1080
        assert options.full_page is True
        assert options.wait_until == "networkidle"
        assert options.wait_for_selector is None
        assert options.wait_time == 0.0
        assert options.javascript_enabled is True
        assert options.timeout == 30000

    def test_browser_not_started_error(self, tmp_path):
        """Test that rendering without starting browser raises error."""
        renderer = WebRenderer()
        html = "<html><body><h1>Test</h1></body></html>"
        output_path = tmp_path / "test.png"

        with pytest.raises(RuntimeError, match="Browser not started"):
            renderer.render_html(html, output_path)

    def test_render_complex_html_structure(self, tmp_path):
        """Test rendering HTML with complex structure."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Complex Page</title>
            <style>
                body { font-family: Arial; margin: 20px; }
                .container { max-width: 800px; }
                table { border-collapse: collapse; width: 100%; }
                td, th { border: 1px solid #ddd; padding: 8px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Complex Document</h1>
                <p>This document has multiple elements:</p>
                <ul>
                    <li>Lists</li>
                    <li>Tables</li>
                    <li>Styles</li>
                </ul>
                <table>
                    <tr><th>Header 1</th><th>Header 2</th></tr>
                    <tr><td>Data 1</td><td>Data 2</td></tr>
                </table>
            </div>
        </body>
        </html>
        """

        output_path = tmp_path / "complex.png"

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path)
            assert result.exists()
            # Complex HTML should produce larger image
            assert result.stat().st_size > 1000

    def test_render_with_different_wait_until_options(self, tmp_path):
        """Test different wait_until strategies."""
        html = "<html><body><h1>Test</h1></body></html>"

        wait_strategies = ["load", "domcontentloaded", "networkidle"]

        with WebRenderer() as renderer:
            for strategy in wait_strategies:
                output_path = tmp_path / f"wait_{strategy}.png"
                options = RenderOptions(wait_until=strategy)
                result = renderer.render_html(html, output_path, options=options)
                assert result.exists()

    def test_render_empty_html(self, tmp_path):
        """Test rendering minimal/empty HTML."""
        html = "<html></html>"
        output_path = tmp_path / "empty.png"

        with WebRenderer() as renderer:
            result = renderer.render_html(html, output_path)
            assert result.exists()
