"""
HTML parser using BeautifulSoup for web page extraction.

This parser extracts structured content from HTML documents including
text, headings, links, images, and tables with semantic structure.
"""

from bs4 import BeautifulSoup, Tag, NavigableString
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import re

from ..schemas.schema_simple import (
    SimpleDocument,
    DocumentSource,
    DocumentMetadata,
    ContentElement,
    Figure,
    Table,
    Link,
    Author,
)
from ..schemas.base import DocumentFormat, DocumentCategory, BoundingBox


class HTMLParser:
    """
    HTML parser using BeautifulSoup for web page extraction.

    Features:
    - Semantic structure detection (headings, paragraphs, sections)
    - Link extraction with anchor text
    - Image/figure detection
    - Table extraction with cell data
    - Metadata extraction (title, meta tags)
    - Clean text extraction (removes scripts, styles)
    """

    def __init__(self, parser: str = "lxml"):
        """
        Initialize HTML parser.

        Args:
            parser: BeautifulSoup parser to use ("lxml", "html.parser", etc.)
        """
        self.parser = parser
        self.soup = None
        self.element_counter = 0

    def parse(
        self,
        html_source: Union[str, Path],
        url: Optional[str] = None,
        category: Optional[DocumentCategory] = None,
        extract_links: bool = True,
        extract_images: bool = True,
        extract_tables: bool = True,
    ) -> SimpleDocument:
        """
        Parse HTML content into a SimpleDocument.

        Args:
            html_source: HTML string or path to HTML file
            url: Source URL (if applicable)
            category: Optional document category
            extract_links: Whether to extract hyperlinks
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables

        Returns:
            SimpleDocument with extracted content
        """
        # Load HTML
        if isinstance(html_source, (str, Path)) and Path(html_source).exists():
            html_path = Path(html_source)
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            file_path = str(html_path.absolute())
        else:
            html_content = str(html_source)
            file_path = None

        # Parse with BeautifulSoup
        self.soup = BeautifulSoup(html_content, self.parser)
        self.element_counter = 0

        # Generate document ID
        if url:
            doc_id = self._url_to_id(url)
        elif file_path:
            doc_id = Path(file_path).stem
        else:
            doc_id = "html_doc"

        # Extract metadata
        metadata = self._extract_metadata()

        # Extract main content
        content = self._extract_content()

        # Extract figures
        figures = []
        if extract_images:
            figures = self._extract_figures()

        # Extract tables
        tables = []
        if extract_tables:
            tables = self._extract_tables()

        # Extract links
        links = []
        if extract_links:
            links = self._extract_links()

        # Create document
        document = SimpleDocument(
            id=doc_id,
            format=DocumentFormat.HTML,
            category=category or self._infer_category(),
            source=DocumentSource(
                url=url,
                file_path=file_path,
                accessed_at=datetime.now(),
            ),
            metadata=metadata,
            content=content,
            figures=figures,
            tables=tables,
            links=links,
        )

        return document

    def _extract_metadata(self) -> DocumentMetadata:
        """Extract metadata from HTML head."""
        metadata = DocumentMetadata()

        # Extract title
        title_tag = self.soup.find('title')
        if title_tag:
            metadata.title = title_tag.get_text().strip()

        # Try to extract from meta tags
        meta_author = self.soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            author_name = meta_author['content']
            metadata.authors = [Author(name=author_name)]

        # Try Open Graph title if no title found
        if not metadata.title:
            og_title = self.soup.find('meta', attrs={'property': 'og:title'})
            if og_title and og_title.get('content'):
                metadata.title = og_title['content']

        # Extract keywords from meta tags
        meta_keywords = self.soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            keywords = meta_keywords['content'].split(',')
            metadata.keywords = [k.strip() for k in keywords if k.strip()]

        # Try to extract description as first keyword
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content') and not metadata.keywords:
            # Use first few words as keywords
            desc = meta_desc['content']
            words = desc.split()[:5]
            metadata.keywords = [' '.join(words)]

        return metadata

    def _extract_content(self) -> List[ContentElement]:
        """
        Extract main content elements (headings and paragraphs).

        Uses semantic HTML structure to identify content hierarchy.
        """
        content = []

        # Remove script and style tags
        for tag in self.soup(['script', 'style', 'noscript']):
            tag.decompose()

        # Find main content area (prioritize semantic tags)
        main_content = (
            self.soup.find('main') or
            self.soup.find('article') or
            self.soup.find('div', class_=re.compile(r'content|main|article', re.I)) or
            self.soup.find('body') or
            self.soup
        )

        # Extract headings and paragraphs in order
        for element in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            text = self._get_clean_text(element)
            if not text or len(text.strip()) < 3:
                continue

            element_id = self._get_element_id()

            if element.name.startswith('h'):
                # Heading
                level = int(element.name[1])
                content.append(ContentElement(
                    id=element_id,
                    type="heading",
                    content=text,
                    level=level,
                ))
            elif element.name == 'p':
                # Paragraph
                content.append(ContentElement(
                    id=element_id,
                    type="paragraph",
                    content=text,
                ))

        return content

    def _extract_figures(self) -> List[Figure]:
        """Extract images and figures with captions."""
        figures = []
        fig_counter = 0

        # Method 1: Look for <figure> tags with <img> and <figcaption>
        for figure_tag in self.soup.find_all('figure'):
            img = figure_tag.find('img')
            if img:
                fig_counter += 1
                caption_tag = figure_tag.find('figcaption')
                caption = caption_tag.get_text().strip() if caption_tag else None

                figures.append(Figure(
                    id=f"fig_{fig_counter}",
                    caption=caption,
                    label=f"Figure {fig_counter}" if caption else None,
                ))

        # Method 2: Standalone images with alt text
        for img in self.soup.find_all('img'):
            # Skip if already processed in a <figure>
            if img.find_parent('figure'):
                continue

            alt_text = img.get('alt', '').strip()
            if alt_text:
                fig_counter += 1
                figures.append(Figure(
                    id=f"fig_{fig_counter}",
                    caption=alt_text,
                ))

        return figures

    def _extract_tables(self) -> List[Table]:
        """Extract tables with cell data."""
        tables = []

        for idx, table_tag in enumerate(self.soup.find_all('table'), start=1):
            rows = []

            # Extract caption if present
            caption_tag = table_tag.find('caption')
            caption = caption_tag.get_text().strip() if caption_tag else None

            # Extract rows
            for tr in table_tag.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cells.append(self._get_clean_text(cell))
                if cells:
                    rows.append(cells)

            if rows:
                tables.append(Table(
                    id=f"table_{idx}",
                    caption=caption,
                    label=f"Table {idx}" if caption else None,
                    rows=rows,
                ))

        return tables

    def _extract_links(self) -> List[Link]:
        """Extract hyperlinks with anchor text."""
        links = []
        seen_urls = set()

        for idx, a_tag in enumerate(self.soup.find_all('a', href=True), start=1):
            href = a_tag['href']
            text = self._get_clean_text(a_tag)

            # Skip empty links or duplicates
            if not text or href in seen_urls:
                continue

            # Skip internal anchors
            if href.startswith('#'):
                continue

            seen_urls.add(href)

            links.append(Link(
                id=f"link_{idx}",
                text=text,
                url=href,
            ))

        return links

    def _get_clean_text(self, element: Tag) -> str:
        """Extract clean text from an element."""
        if isinstance(element, NavigableString):
            return str(element).strip()

        text = element.get_text(separator=' ', strip=True)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_element_id(self) -> str:
        """Generate unique element ID."""
        self.element_counter += 1
        return f"elem_{self.element_counter}"

    def _url_to_id(self, url: str) -> str:
        """Convert URL to a document ID."""
        # Extract domain and path
        url = url.replace('https://', '').replace('http://', '')
        url = url.replace('/', '_').replace('.', '_')
        # Limit length
        if len(url) > 50:
            url = url[:50]
        return url

    def _infer_category(self) -> Optional[DocumentCategory]:
        """
        Attempt to infer document category from HTML structure.

        This is a simple heuristic - can be improved.
        """
        # Look for common indicators
        if self.soup.find('article'):
            # Check for academic paper indicators
            if self.soup.find(class_=re.compile(r'abstract|citation|reference', re.I)):
                return DocumentCategory.ACADEMIC_PAPER

            # Check for blog indicators
            if self.soup.find(class_=re.compile(r'blog|post|author', re.I)):
                return DocumentCategory.BLOG_POST

            return DocumentCategory.WEBPAGE_GENERAL

        return None

    def parse_url(self, url: str, html_content: str, **kwargs) -> SimpleDocument:
        """
        Parse HTML content from a URL.

        This is a convenience method for web scraping workflows.

        Args:
            url: Source URL
            html_content: HTML content as string
            **kwargs: Additional arguments passed to parse()

        Returns:
            SimpleDocument with extracted content
        """
        return self.parse(html_content, url=url, **kwargs)
