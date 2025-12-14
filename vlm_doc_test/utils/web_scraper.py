"""
Web scraping utilities combining rendering and parsing.

This module integrates Playwright rendering with HTML parsing
for comprehensive web scraping workflows.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from ..renderers import WebRenderer
from ..renderers.web_renderer import RenderOptions
from ..parsers import HTMLParser
from ..schemas.schema_simple import SimpleDocument
from ..schemas.base import DocumentCategory


@dataclass
class ScrapeResult:
    """Result of a web scraping operation."""
    document: SimpleDocument
    screenshot_path: Optional[Path] = None
    html_content: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class WebScraper:
    """
    Comprehensive web scraper.

    Combines Playwright rendering with HTML parsing to:
    1. Render web pages (including JavaScript-heavy sites)
    2. Capture screenshots
    3. Extract structured content
    4. Generate SimpleDocument
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
    ):
        """
        Initialize web scraper.

        Args:
            headless: Run browser in headless mode
            browser_type: Browser to use ("chromium", "firefox", "webkit")
        """
        self.headless = headless
        self.browser_type = browser_type
        self.renderer = WebRenderer(
            browser_type=browser_type,
            headless=headless,
        )
        self.parser = HTMLParser()

    def __enter__(self):
        """Context manager entry."""
        self.renderer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.renderer.stop()

    def scrape_url(
        self,
        url: str,
        screenshot_path: Optional[Path] = None,
        category: Optional[DocumentCategory] = None,
        render_options: Optional[RenderOptions] = None,
        capture_html: bool = True,
    ) -> ScrapeResult:
        """
        Scrape a URL with rendering and parsing.

        Args:
            url: URL to scrape
            screenshot_path: Optional path to save screenshot
            category: Document category
            render_options: Rendering options
            capture_html: Whether to capture rendered HTML

        Returns:
            ScrapeResult with document and optional screenshot
        """
        try:
            # Get rendered HTML
            html_content = None
            if capture_html:
                html_content = self.renderer.get_page_html(url, render_options)

            # Take screenshot if path provided
            if screenshot_path:
                self.renderer.render_url(url, screenshot_path, render_options)

            # Parse HTML
            if html_content:
                document = self.parser.parse(html_content, url=url, category=category)
            else:
                # If we didn't capture HTML, we need to get it
                html_content = self.renderer.get_page_html(url, render_options)
                document = self.parser.parse(html_content, url=url, category=category)

            return ScrapeResult(
                document=document,
                screenshot_path=screenshot_path,
                html_content=html_content,
                success=True,
            )

        except Exception as e:
            # Create minimal document on error
            from ..schemas.schema_simple import DocumentSource, DocumentMetadata
            from ..schemas.base import DocumentFormat

            error_doc = SimpleDocument(
                id="error",
                format=DocumentFormat.HTML,
                source=DocumentSource(url=url, accessed_at=datetime.now()),
                metadata=DocumentMetadata(),
            )

            return ScrapeResult(
                document=error_doc,
                screenshot_path=None,
                html_content=None,
                success=False,
                error=str(e),
            )

    def scrape_with_wait(
        self,
        url: str,
        wait_for_selector: str,
        screenshot_path: Optional[Path] = None,
        category: Optional[DocumentCategory] = None,
        timeout: int = 30000,
    ) -> ScrapeResult:
        """
        Scrape URL, waiting for a specific element.

        Useful for dynamic content that loads after initial page load.

        Args:
            url: URL to scrape
            wait_for_selector: CSS selector to wait for
            screenshot_path: Optional path to save screenshot
            category: Document category
            timeout: Timeout in milliseconds

        Returns:
            ScrapeResult
        """
        render_options = RenderOptions(
            wait_for_selector=wait_for_selector,
            timeout=timeout,
        )

        return self.scrape_url(
            url=url,
            screenshot_path=screenshot_path,
            category=category,
            render_options=render_options,
        )

    def scrape_spa(
        self,
        url: str,
        wait_time: float = 2.0,
        screenshot_path: Optional[Path] = None,
        category: Optional[DocumentCategory] = None,
    ) -> ScrapeResult:
        """
        Scrape Single Page Application (SPA).

        Waits for JavaScript to render content.

        Args:
            url: URL to scrape
            wait_time: Time to wait after load (seconds)
            screenshot_path: Optional path to save screenshot
            category: Document category

        Returns:
            ScrapeResult
        """
        render_options = RenderOptions(
            wait_time=wait_time,
            wait_until="networkidle",
        )

        return self.scrape_url(
            url=url,
            screenshot_path=screenshot_path,
            category=category,
            render_options=render_options,
        )

    def compare_renderings(
        self,
        url: str,
        output_dir: Path,
        viewports: list[tuple[int, int]] = None,
    ) -> list[ScrapeResult]:
        """
        Scrape URL at different viewport sizes.

        Useful for responsive design testing.

        Args:
            url: URL to scrape
            output_dir: Directory for screenshots
            viewports: List of (width, height) tuples

        Returns:
            List of ScrapeResults
        """
        if viewports is None:
            viewports = [
                (1920, 1080),  # Desktop
                (768, 1024),   # Tablet
                (375, 667),    # Mobile
            ]

        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for width, height in viewports:
            render_options = RenderOptions(
                viewport_width=width,
                viewport_height=height,
            )

            screenshot_path = output_dir / f"viewport_{width}x{height}.png"

            result = self.scrape_url(
                url=url,
                screenshot_path=screenshot_path,
                render_options=render_options,
            )

            results.append(result)

        return results
