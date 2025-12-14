"""
Web page renderer using Playwright.

This module provides functionality to render web pages to images
using headless Chromium for visual regression testing and VLM analysis.
"""

from playwright.sync_api import sync_playwright, Browser, Page, ViewportSize
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time


@dataclass
class RenderOptions:
    """Options for web page rendering."""
    viewport_width: int = 1920
    viewport_height: int = 1080
    full_page: bool = True
    wait_until: str = "networkidle"  # "load", "domcontentloaded", "networkidle"
    wait_for_selector: Optional[str] = None
    wait_time: float = 0.0  # Additional wait time in seconds
    javascript_enabled: bool = True
    timeout: int = 30000  # ms
    scale: str = "css"  # "css" or "device"


class WebRenderer:
    """
    Web page renderer using Playwright.

    Features:
    - Headless browser rendering
    - Full page or viewport screenshots
    - Wait for specific selectors or network idle
    - JavaScript execution support
    - Customizable viewport size
    - Cookie and authentication support
    """

    def __init__(
        self,
        browser_type: str = "chromium",
        headless: bool = True,
    ):
        """
        Initialize web renderer.

        Args:
            browser_type: Browser to use ("chromium", "firefox", "webkit")
            headless: Whether to run browser in headless mode
        """
        self.browser_type = browser_type
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def start(self):
        """Start the browser instance."""
        if self.playwright is None:
            self.playwright = sync_playwright().start()

            if self.browser_type == "chromium":
                self.browser = self.playwright.chromium.launch(headless=self.headless)
            elif self.browser_type == "firefox":
                self.browser = self.playwright.firefox.launch(headless=self.headless)
            elif self.browser_type == "webkit":
                self.browser = self.playwright.webkit.launch(headless=self.headless)
            else:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

    def stop(self):
        """Stop the browser instance."""
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    def render_url(
        self,
        url: str,
        output_path: Path,
        options: Optional[RenderOptions] = None,
    ) -> Path:
        """
        Render a URL to an image.

        Args:
            url: URL to render
            output_path: Path to save screenshot
            options: Rendering options

        Returns:
            Path to saved screenshot
        """
        if options is None:
            options = RenderOptions()

        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")

        # Create browser context
        context = self.browser.new_context(
            viewport={
                "width": options.viewport_width,
                "height": options.viewport_height,
            },
            java_script_enabled=options.javascript_enabled,
        )

        try:
            # Create page
            page = context.new_page()

            # Navigate to URL
            page.goto(url, wait_until=options.wait_until, timeout=options.timeout)

            # Wait for specific selector if provided
            if options.wait_for_selector:
                page.wait_for_selector(
                    options.wait_for_selector,
                    timeout=options.timeout,
                )

            # Additional wait time
            if options.wait_time > 0:
                time.sleep(options.wait_time)

            # Take screenshot
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(output_path),
                full_page=options.full_page,
                scale=options.scale,
            )

            return output_path

        finally:
            context.close()

    def render_html(
        self,
        html_content: str,
        output_path: Path,
        base_url: Optional[str] = None,
        options: Optional[RenderOptions] = None,
    ) -> Path:
        """
        Render HTML content to an image.

        Args:
            html_content: HTML content as string
            output_path: Path to save screenshot
            base_url: Base URL for resolving relative links
            options: Rendering options

        Returns:
            Path to saved screenshot
        """
        if options is None:
            options = RenderOptions()

        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")

        context = self.browser.new_context(
            viewport={
                "width": options.viewport_width,
                "height": options.viewport_height,
            },
            java_script_enabled=options.javascript_enabled,
        )

        try:
            page = context.new_page()

            # Set content
            page.set_content(
                html_content,
                wait_until=options.wait_until,
                timeout=options.timeout,
            )

            # Additional wait time
            if options.wait_time > 0:
                time.sleep(options.wait_time)

            # Take screenshot
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(output_path),
                full_page=options.full_page,
                scale=options.scale,
            )

            return output_path

        finally:
            context.close()

    def render_multiple_urls(
        self,
        urls: List[str],
        output_dir: Path,
        options: Optional[RenderOptions] = None,
    ) -> List[Path]:
        """
        Render multiple URLs to images.

        Args:
            urls: List of URLs to render
            output_dir: Directory to save screenshots
            options: Rendering options

        Returns:
            List of paths to saved screenshots
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        screenshots = []

        for idx, url in enumerate(urls):
            # Create filename from URL or use index
            safe_name = url.replace("https://", "").replace("http://", "")
            safe_name = safe_name.replace("/", "_").replace(":", "_")
            if len(safe_name) > 100:
                safe_name = f"screenshot_{idx}"

            output_path = output_dir / f"{safe_name}.png"
            screenshot = self.render_url(url, output_path, options)
            screenshots.append(screenshot)

        return screenshots

    def execute_script(
        self,
        url: str,
        script: str,
        output_path: Path,
        options: Optional[RenderOptions] = None,
    ) -> tuple[Path, Any]:
        """
        Render URL, execute JavaScript, and capture screenshot.

        Args:
            url: URL to render
            script: JavaScript code to execute
            output_path: Path to save screenshot
            options: Rendering options

        Returns:
            Tuple of (screenshot_path, script_result)
        """
        if options is None:
            options = RenderOptions()

        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")

        context = self.browser.new_context(
            viewport={
                "width": options.viewport_width,
                "height": options.viewport_height,
            },
        )

        try:
            page = context.new_page()
            page.goto(url, wait_until=options.wait_until, timeout=options.timeout)

            # Execute script
            result = page.evaluate(script)

            # Wait if needed
            if options.wait_time > 0:
                time.sleep(options.wait_time)

            # Take screenshot
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(output_path),
                full_page=options.full_page,
            )

            return output_path, result

        finally:
            context.close()

    def render_with_auth(
        self,
        url: str,
        output_path: Path,
        username: str,
        password: str,
        options: Optional[RenderOptions] = None,
    ) -> Path:
        """
        Render a URL with HTTP authentication.

        Args:
            url: URL to render
            output_path: Path to save screenshot
            username: HTTP auth username
            password: HTTP auth password
            options: Rendering options

        Returns:
            Path to saved screenshot
        """
        if options is None:
            options = RenderOptions()

        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")

        context = self.browser.new_context(
            viewport={
                "width": options.viewport_width,
                "height": options.viewport_height,
            },
            http_credentials={
                "username": username,
                "password": password,
            },
        )

        try:
            page = context.new_page()
            page.goto(url, wait_until=options.wait_until, timeout=options.timeout)

            if options.wait_time > 0:
                time.sleep(options.wait_time)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(output_path),
                full_page=options.full_page,
            )

            return output_path

        finally:
            context.close()

    def get_page_html(
        self,
        url: str,
        options: Optional[RenderOptions] = None,
    ) -> str:
        """
        Get rendered HTML content from a URL.

        Useful for getting HTML after JavaScript execution.

        Args:
            url: URL to render
            options: Rendering options

        Returns:
            Rendered HTML content
        """
        if options is None:
            options = RenderOptions()

        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first or use context manager.")

        context = self.browser.new_context(
            viewport={
                "width": options.viewport_width,
                "height": options.viewport_height,
            },
        )

        try:
            page = context.new_page()
            page.goto(url, wait_until=options.wait_until, timeout=options.timeout)

            if options.wait_for_selector:
                page.wait_for_selector(options.wait_for_selector, timeout=options.timeout)

            if options.wait_time > 0:
                time.sleep(options.wait_time)

            return page.content()

        finally:
            context.close()
