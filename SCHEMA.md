# Document Structure Schema (Full)

## Overview

This document defines the **complete** schema for representing parsed document structures. This schema serves as the common format for both:
1. **Tool-based parsing** (traditional extraction using libraries like pdfplumber, BeautifulSoup, etc.)
2. **VLM-based parsing** (extraction via Vision Language Models analyzing rendered documents)

The equivalence testing framework compares outputs from both approaches using this shared schema.

> **Note**: For simpler use cases and faster iteration, see [SCHEMA_SIMPLE.md](./SCHEMA_SIMPLE.md) which defines a minimal schema that is a strict subset of this full schema.

## Design Principles

1. **Format-agnostic**: Support web pages, PDFs, plots, academic papers, and other document types
2. **Spatial awareness**: Include coordinate information for visual elements
3. **Hierarchical structure**: Represent document organization and nesting
4. **Relationship modeling**: Capture references between elements (citations, figure captions, links)
5. **Extensible**: Allow custom fields for domain-specific needs
6. **Standards-based**: Draw from Schema.org, JATS, and PDF specification standards

## Core Types

### Coordinate System

All spatial coordinates use a consistent coordinate system per page/screen:

```python
from pydantic import BaseModel, Field
from typing import Optional

class BoundingBox(BaseModel):
    """Bounding box coordinates for visual elements."""
    # Page or screen number (1-indexed)
    page: int

    # Coordinates in pixels or PDF points (72 DPI)
    # Origin is top-left corner
    x: float  # Left edge
    y: float  # Top edge
    width: float  # Width of box
    height: float  # Height of box

    # Optional: confidence score from extraction tool
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class BoundingBoxAlt(BaseModel):
    """Alternative bounding box representation for compatibility."""
    page: int
    x1: float  # Left
    y1: float  # Top
    x2: float  # Right
    y2: float  # Bottom
```

### Document Root

Top-level container for all document content:

```python
from enum import Enum
from typing import Optional, List
from datetime import datetime

class DocumentFormat(str, Enum):
    """Document format: the file format/extension/representation."""
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    MARKDOWN = "markdown"
    LATEX = "latex"
    DOCX = "docx"
    PPTX = "pptx"
    JUPYTER = "jupyter"
    OTHER = "other"


class DocumentCategory(str, Enum):
    """Document category: the semantic type/purpose of the document."""
    ACADEMIC_PAPER = "academic_paper"
    BLOG_POST = "blog_post"
    NEWS_ARTICLE = "news_article"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    BOOK_CHAPTER = "book_chapter"
    PRESENTATION = "presentation"
    REPORT = "report"
    TUTORIAL = "tutorial"
    PLOT_VISUALIZATION = "plot_visualization"
    INFOGRAPHIC = "infographic"
    WEBPAGE_GENERAL = "webpage_general"
    OTHER = "other"


class DocumentSource(BaseModel):
    """Source information for the document."""
    # Original source
    url: Optional[str] = None
    file_path: Optional[str] = None

    # Content hash for versioning
    content_hash: Optional[str] = None

    # Timestamp
    accessed_at: datetime


class Document(BaseModel):
    """Top-level container for all document content."""
    # Document metadata
    id: str
    format: DocumentFormat
    category: Optional[DocumentCategory] = None
    source: DocumentSource
    metadata: "DocumentMetadata"

    # Structural content
    content: List["ContentElement"] = Field(default_factory=list)

    # Extracted visual elements
    figures: List["Figure"] = Field(default_factory=list)
    tables: List["Table"] = Field(default_factory=list)

    # References and relationships
    links: List["Link"] = Field(default_factory=list)
    citations: List["Citation"] = Field(default_factory=list)
    relationships: List["Relationship"] = Field(default_factory=list)

    # Rendering information
    rendering: Optional["RenderingInfo"] = None

    # Extraction metadata
    extraction: Optional["ExtractionMetadata"] = None
```

### Document Metadata

Structured metadata following Schema.org and JATS standards:

```python
from typing import Dict, Any

class Author(BaseModel):
    """Author information."""
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    affiliation: List[str] = Field(default_factory=list)
    orcid: Optional[str] = None
    email: Optional[str] = None


class Organization(BaseModel):
    """Organization information."""
    name: str
    url: Optional[str] = None
    address: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Structured metadata following Schema.org and JATS standards."""
    # Core metadata
    title: Optional[str] = None
    subtitle: Optional[str] = None

    # Authorship
    authors: List[Author] = Field(default_factory=list)

    # Publishing information
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    publisher: Optional[Organization] = None

    # Identifiers
    doi: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    # Classification
    keywords: List[str] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    language: Optional[str] = None  # ISO 639-1 code

    # Abstract/summary
    abstract: Optional[str] = None

    # Custom metadata
    custom: Dict[str, Any] = Field(default_factory=dict)
```

## Content Structure

### Content Elements

Hierarchical content representation:

```python
from typing import Union, Literal

class ContentType(str, Enum):
    """Type of content element."""
    # Text blocks
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    BLOCKQUOTE = "blockquote"
    CODE_BLOCK = "code_block"

    # Inline elements
    TEXT = "text"
    EMPHASIS = "emphasis"
    STRONG = "strong"
    CODE = "code"

    # Structural
    SECTION = "section"
    ARTICLE = "article"
    ASIDE = "aside"
    HEADER = "header"
    FOOTER = "footer"
    NAV = "nav"

    # Other
    CAPTION = "caption"
    LABEL = "label"
    METADATA = "metadata"


class TextStyle(BaseModel):
    """Styling information for text spans."""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    font_size: Optional[float] = None
    font_family: Optional[str] = None
    color: Optional[str] = None


class TextSpan(BaseModel):
    """Styled text span within rich text."""
    text: str
    start: int  # Character offset
    end: int
    style: Optional[TextStyle] = None
    link: Optional[str] = None


class RichText(BaseModel):
    """Rich text with formatting information."""
    # Plain text version
    plain: str

    # Formatted version (HTML, Markdown, etc.)
    formatted: Optional[str] = None
    format: Optional[Literal["html", "markdown", "latex"]] = None

    # Inline elements
    spans: List[TextSpan] = Field(default_factory=list)


class ContentAttributes(BaseModel):
    """Attributes for content elements."""
    # Semantic attributes
    role: Optional[str] = None
    lang: Optional[str] = None

    # Visual attributes
    alignment: Optional[Literal["left", "center", "right", "justify"]] = None
    indentation: Optional[int] = None

    # HTML/CSS classes (for web content)
    classes: List[str] = Field(default_factory=list)

    # Custom attributes
    custom: Dict[str, Any] = Field(default_factory=dict)


class ContentElement(BaseModel):
    """Hierarchical content element."""
    # Unique identifier within document
    id: str

    # Element type
    type: ContentType

    # Hierarchical structure
    level: Optional[int] = None  # Heading level, list depth, etc.
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)

    # Content (either plain string or rich text)
    content: Union[str, RichText]

    # Spatial information
    bbox: Optional[BoundingBox] = None

    # Styling and attributes
    attributes: Optional[ContentAttributes] = None

    # Order in document
    sequence: Optional[int] = None
```

## Visual Elements

### Figures and Images

```python
class FigureType(str, Enum):
    """Type of figure."""
    PHOTOGRAPH = "photograph"
    DIAGRAM = "diagram"
    CHART = "chart"
    PLOT = "plot"
    MAP = "map"
    ILLUSTRATION = "illustration"
    SCREENSHOT = "screenshot"
    ICON = "icon"
    LOGO = "logo"
    OTHER = "other"


class ImageData(BaseModel):
    """Image data for figures."""
    # Image source
    url: Optional[str] = None
    embedded: Optional[str] = None  # Base64 encoded

    # Image properties
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None  # png, jpg, svg, etc.

    # File information
    file_size: Optional[int] = None
    checksum: Optional[str] = None


class Figure(BaseModel):
    """Figure or image element."""
    id: str
    type: FigureType

    # Content
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Figure 1", "Fig. 2a"
    alt_text: Optional[str] = None

    # Visual properties
    bbox: Optional[BoundingBox] = None
    image_data: Optional[ImageData] = None

    # Relationships
    referenced_by: List[str] = Field(default_factory=list)  # IDs of content elements that reference this
    related_to: List[str] = Field(default_factory=list)  # IDs of related figures

    # Extraction confidence
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
```

### Plots and Visualizations

Extended figure schema for data visualizations:

```python
class PlotType(str, Enum):
    """Type of plot or chart."""
    LINE = "line"
    SCATTER = "scatter"
    BAR = "bar"
    HISTOGRAM = "histogram"
    PIE = "pie"
    HEATMAP = "heatmap"
    BOX_PLOT = "box_plot"
    VIOLIN = "violin"
    CONTOUR = "contour"
    SURFACE_3D = "surface_3d"
    OTHER = "other"


class TickMark(BaseModel):
    """Tick mark on an axis."""
    value: Union[float, str]
    label: Optional[str] = None
    position: Optional[float] = None


class Axis(BaseModel):
    """Plot axis information."""
    name: Optional[str] = None
    label: Optional[str] = None
    unit: Optional[str] = None
    scale: Optional[Literal["linear", "log", "time", "category"]] = None
    range: Optional[Union[tuple[float, float], List[str]]] = None
    ticks: List[TickMark] = Field(default_factory=list)


class LegendItem(BaseModel):
    """Legend item."""
    label: str
    color: Optional[str] = None
    marker: Optional[str] = None
    line_style: Optional[str] = None


class Legend(BaseModel):
    """Plot legend."""
    title: Optional[str] = None
    items: List[LegendItem]
    position: Optional[Literal["top", "bottom", "left", "right", "inside"]] = None


class DataPointStats(BaseModel):
    """Summary statistics for a data series."""
    count: Optional[int] = None
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None


class DataPoint(BaseModel):
    """Data point in a plot."""
    x: Union[float, str]
    y: float
    z: Optional[float] = None  # For 3D plots
    label: Optional[str] = None
    error: Optional[Union[float, tuple[float, float]]] = None  # Error bars


class DataSeries(BaseModel):
    """Data series in a plot."""
    name: Optional[str] = None
    type: Optional[str] = None  # line, scatter, bar, etc.

    # Visual properties
    color: Optional[str] = None
    marker: Optional[str] = None
    line_style: Optional[str] = None

    # Data (if extractable)
    data_points: List[DataPoint] = Field(default_factory=list)

    # Summary statistics
    stats: Optional[DataPointStats] = None


class Plot(Figure):
    """Plot or chart visualization (extends Figure)."""
    type: Literal[FigureType.PLOT, FigureType.CHART]
    plot_type: PlotType

    # Plot components
    title: Optional[str] = None
    axes: List[Axis] = Field(default_factory=list)
    legend: Optional[Legend] = None
    data_series: List[DataSeries] = Field(default_factory=list)

    # Visual encoding
    color_scheme: Optional[str] = None

    # Accessibility
    description: Optional[str] = None
    data_table: Optional["Table"] = None  # Alternative representation
```

### Tables

```python
class TableCell(BaseModel):
    """Cell in a table."""
    content: Union[str, RichText]

    # Cell properties
    colspan: Optional[int] = None
    rowspan: Optional[int] = None

    # Spatial information
    bbox: Optional[BoundingBox] = None

    # Semantic information
    data_type: Optional[Literal["text", "number", "date", "boolean"]] = None
    alignment: Optional[Literal["left", "center", "right"]] = None

    # Styling
    attributes: Optional[ContentAttributes] = None


class TableRow(BaseModel):
    """Row in a table."""
    cells: List[TableCell]
    row_type: Optional[Literal["header", "data", "footer"]] = None


class TableHeader(BaseModel):
    """Header row(s) in a table."""
    cells: List[TableCell]
    level: Optional[int] = None  # For multi-level headers


class Table(BaseModel):
    """Table element."""
    id: str

    # Content
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Table 1"

    # Structure
    headers: List[TableHeader] = Field(default_factory=list)
    rows: List[TableRow]
    footer: Optional[TableRow] = None

    # Layout
    bbox: Optional[BoundingBox] = None
    num_columns: int
    num_rows: int

    # Properties
    has_header_row: Optional[bool] = None
    has_header_column: Optional[bool] = None
    is_numeric: Optional[bool] = None

    # Relationships
    referenced_by: List[str] = Field(default_factory=list)
```

## Relationships and References

### Links

```python
class LinkType(str, Enum):
    """Type of link."""
    INTERNAL = "internal"      # Same document
    EXTERNAL = "external"      # Different domain
    ANCHOR = "anchor"          # Same page (#fragment)
    DOWNLOAD = "download"      # File download
    EMAIL = "email"            # mailto:
    TELEPHONE = "telephone"    # tel:


class Link(BaseModel):
    """Link or hyperlink element."""
    id: str

    # Link properties
    source_id: Optional[str] = None  # ID of element containing link
    anchor_text: str
    href: str

    # Link type
    type: LinkType

    # Position
    bbox: Optional[BoundingBox] = None

    # Metadata
    title: Optional[str] = None
    rel: Optional[str] = None  # HTML rel attribute
```

### Citations and References

```python
class CitationType(str, Enum):
    """Type of citation."""
    BIBLIOGRAPHIC = "bibliographic"
    FIGURE = "figure"
    TABLE = "table"
    EQUATION = "equation"
    SECTION = "section"
    FOOTNOTE = "footnote"
    ENDNOTE = "endnote"


class Citation(BaseModel):
    """Citation marker in document."""
    id: str

    # Citation marker in text
    marker: str  # e.g., "[1]", "(Smith, 2020)", "¹"
    marker_bbox: Optional[BoundingBox] = None

    # Location in document
    citing_element_id: Optional[str] = None

    # Target reference
    reference_id: Optional[str] = None

    # Citation type
    type: Optional[CitationType] = None


class ReferenceType(str, Enum):
    """Type of reference."""
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PAPER = "conference_paper"
    THESIS = "thesis"
    PREPRINT = "preprint"
    WEBPAGE = "webpage"
    SOFTWARE = "software"
    DATASET = "dataset"
    OTHER = "other"


class Reference(BaseModel):
    """Bibliographic reference."""
    id: str

    # Bibliographic information
    type: ReferenceType

    # Core fields
    title: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    year: Optional[int] = None

    # Publication details
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None

    # Identifiers
    doi: Optional[str] = None
    url: Optional[str] = None
    isbn: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Citation count
    cited_by: List[str] = Field(default_factory=list)  # IDs of citations

    # Raw text
    raw_text: Optional[str] = None
```

### Relationships

General relationship model for arbitrary connections:

```python
class RelationshipType(str, Enum):
    """Type of relationship between elements."""
    # Hierarchical
    PARENT_CHILD = "parent_child"
    CONTAINS = "contains"

    # Sequential
    FOLLOWS = "follows"
    PRECEDES = "precedes"

    # Referential
    REFERENCES = "references"
    CITED_BY = "cited_by"
    DESCRIBES = "describes"

    # Associative
    RELATED_TO = "related_to"
    SAME_AS = "same_as"
    SIMILAR_TO = "similar_to"

    # Compositional
    PART_OF = "part_of"
    HAS_PART = "has_part"

    # Custom
    CUSTOM = "custom"


class Relationship(BaseModel):
    """Relationship between document elements."""
    id: str

    # Relationship type
    type: Union[RelationshipType, str]  # Extensible

    # Connected elements
    source_id: str
    target_id: str

    # Relationship properties
    label: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)

    # Confidence
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
```

## Format-Specific Extensions

### HTML/Web Pages

Additional fields when `format = DocumentFormat.HTML`:

```python
class Viewport(BaseModel):
    """Viewport dimensions."""
    width: int
    height: int


class WebMetadata(BaseModel):
    """Web-specific metadata."""
    # URL structure
    canonical_url: Optional[str] = None
    base_url: Optional[str] = None

    # HTTP metadata
    status_code: Optional[int] = None
    content_type: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    # Page properties
    viewport: Optional[Viewport] = None

    # Open Graph
    og_data: Dict[str, str] = Field(default_factory=dict)

    # Twitter Card
    twitter_data: Dict[str, str] = Field(default_factory=dict)


class DOMNode(BaseModel):
    """DOM node in HTML structure."""
    tag: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    children: List["DOMNode"] = Field(default_factory=list)
    text: Optional[str] = None

    # Mapping to content elements
    content_id: Optional[str] = None


class SEOData(BaseModel):
    """SEO metadata."""
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)
    h1_tags: List[str] = Field(default_factory=list)
    schema_markup: Optional[Any] = None  # JSON-LD data


class WebMetadataExtension(BaseModel):
    """Extension for web documents.

    Add to Document.metadata.custom when format = HTML
    e.g., metadata.custom.web_metadata = {...}
    """
    # Web-specific metadata
    web_metadata: Optional[WebMetadata] = None

    # DOM structure (optional, for HTML parsing)
    dom_structure: Optional[DOMNode] = None

    # SEO elements
    seo: Optional[SEOData] = None
```

### PDF Documents

Additional fields when `format = DocumentFormat.PDF`:

```python
class PDFMetadata(BaseModel):
    """PDF-specific metadata."""
    # PDF properties
    pdf_version: Optional[str] = None
    page_count: int

    # PDF metadata fields
    producer: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None

    # Document properties
    is_tagged: Optional[bool] = None  # PDF/UA
    is_encrypted: Optional[bool] = None
    is_linearized: Optional[bool] = None

    # Page layout
    page_layout: Optional[Literal["single", "continuous", "two_column"]] = None
    page_mode: Optional[Literal["full_screen", "thumbnails", "outlines"]] = None


class TextBlock(BaseModel):
    """Text block with formatting in PDF."""
    text: str
    bbox: BoundingBox

    # Font information
    font_name: Optional[str] = None
    font_size: Optional[float] = None

    # Text properties
    is_bold: Optional[bool] = None
    is_italic: Optional[bool] = None
    color: Optional[str] = None

    # Reading order
    sequence: Optional[int] = None

    # Confidence
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class PDFPage(BaseModel):
    """PDF page information."""
    page_number: int

    # Page dimensions (in PDF points, 72 DPI)
    width: float
    height: float
    rotation: Optional[int] = None  # 0, 90, 180, 270

    # Content on this page
    content_ids: List[str] = Field(default_factory=list)
    figure_ids: List[str] = Field(default_factory=list)
    table_ids: List[str] = Field(default_factory=list)

    # Text blocks with coordinates
    text_blocks: List[TextBlock] = Field(default_factory=list)

    # Raw page data
    raw_text: Optional[str] = None


class PDFMetadataExtension(BaseModel):
    """Extension for PDF documents.

    Add to Document.metadata.custom when format = PDF
    e.g., metadata.custom.pdf_metadata = {...}
    e.g., document.custom.pages = [...]
    """
    # PDF-specific metadata
    pdf_metadata: Optional[PDFMetadata] = None

    # Page structure
    pages: List[PDFPage] = Field(default_factory=list)
```

## Category-Specific Extensions

### Academic Papers

Additional fields when `category = DocumentCategory.ACADEMIC_PAPER`:

```python
class TranslatedTitle(BaseModel):
    """Translated title in another language."""
    language: str
    title: str


class TitleGroup(BaseModel):
    """Title group for academic paper."""
    title: str
    subtitle: Optional[str] = None
    translated_titles: List[TranslatedTitle] = Field(default_factory=list)


class Affiliation(BaseModel):
    """Author affiliation."""
    id: str
    institution: str
    department: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class Correspondence(BaseModel):
    """Corresponding author information."""
    author_id: str
    email: str
    address: Optional[str] = None


class PaperDates(BaseModel):
    """Important dates for paper."""
    received: Optional[str] = None
    accepted: Optional[str] = None
    published: Optional[str] = None


class FundingInfo(BaseModel):
    """Funding information."""
    agency: str
    grant_number: Optional[str] = None
    recipient: Optional[str] = None


class FrontMatter(BaseModel):
    """Front matter of academic paper."""
    title_group: Optional[TitleGroup] = None
    authors: List[Author]
    affiliations: List[Affiliation] = Field(default_factory=list)
    correspondence: Optional[Correspondence] = None
    dates: Optional[PaperDates] = None
    funding: List[FundingInfo] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class AbstractSection(BaseModel):
    """Section within a structured abstract."""
    label: Optional[str] = None  # Background, Methods, Results, Conclusions
    content: str


class Abstract(BaseModel):
    """Abstract of academic paper."""
    type: Optional[Literal["structured", "unstructured"]] = None
    sections: List[AbstractSection] = Field(default_factory=list)
    plain_text: Optional[str] = None


class Section(BaseModel):
    """Section in document body."""
    id: str
    label: Optional[str] = None  # "Introduction", "Methods", etc.
    title: Optional[str] = None
    level: int  # 1, 2, 3, etc.

    # Content
    content_ids: List[str]
    subsections: List["Section"] = Field(default_factory=list)

    # Position
    bbox: Optional[BoundingBox] = None


class Appendix(BaseModel):
    """Appendix section."""
    id: str
    label: str  # "Appendix A", etc.
    title: Optional[str] = None
    content_ids: List[str]


class Body(BaseModel):
    """Body of academic paper."""
    sections: List[Section]


class BackMatter(BaseModel):
    """Back matter of academic paper."""
    # Acknowledgments
    acknowledgments: Optional[str] = None

    # References
    references: List[Reference]

    # Appendices
    appendices: List[Appendix] = Field(default_factory=list)

    # Author contributions
    author_contributions: Dict[str, str] = Field(default_factory=dict)

    # Conflict of interest
    conflict_of_interest: Optional[str] = None

    # Data availability
    data_availability: Optional[str] = None


class AcademicPaperExtension(BaseModel):
    """Extension for academic papers.

    Add to Document.metadata.custom when category = ACADEMIC_PAPER
    e.g., metadata.custom.academic = {...}
    """
    # Paper-specific structure (following JATS)
    front_matter: Optional[FrontMatter] = None
    abstract: Optional[Abstract] = None
    body: Optional[Body] = None
    back_matter: Optional[BackMatter] = None
```

## Rendering Information

Information about how the document was rendered for VLM analysis:

```python
class RendererViewport(BaseModel):
    """Viewport configuration for rendering."""
    width: int
    height: int


class RendererConfig(BaseModel):
    """Configuration for document renderer."""
    # Browser/engine
    browser: Optional[Literal["chromium", "firefox", "webkit"]] = None

    # Viewport
    viewport: Optional[RendererViewport] = None

    # PDF rendering
    dpi: Optional[int] = None

    # Wait conditions
    wait_until: Optional[Literal["load", "domcontentloaded", "networkidle"]] = None
    wait_time: Optional[int] = None  # milliseconds

    # Custom options
    custom: Dict[str, Any] = Field(default_factory=dict)


class Screenshot(BaseModel):
    """Screenshot of rendered document page."""
    page: int

    # Image data
    image_url: Optional[str] = None
    image_data: Optional[str] = None  # Base64

    # Image properties
    width: int
    height: int
    format: Literal["png", "jpg", "webp"]

    # File info
    file_size: Optional[int] = None
    checksum: Optional[str] = None


class RenderingInfo(BaseModel):
    """Information about document rendering for VLM analysis."""
    # Rendering method
    method: Literal["playwright", "pdf2image", "matplotlib", "custom"]

    # Renderer configuration
    config: Optional[RendererConfig] = None

    # Screenshots
    screenshots: List[Screenshot] = Field(default_factory=list)

    # Timestamp
    rendered_at: str  # ISO 8601
```

## Extraction Metadata

Information about the extraction process:

```python
class Library(BaseModel):
    """Library dependency information."""
    name: str
    version: str


class ToolInfo(BaseModel):
    """Information about extraction tool."""
    name: str
    version: Optional[str] = None

    # Libraries used
    libraries: List[Library] = Field(default_factory=list)

    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)


class VLMPrompt(BaseModel):
    """VLM prompt and response."""
    prompt: str
    response: str

    # For multi-request strategies
    purpose: Optional[str] = None  # "extract_metadata", "extract_figures", etc.

    # Tokens
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class VLMInfo(BaseModel):
    """Information about VLM extraction."""
    model: str  # e.g., "glm-4.6v"
    provider: Optional[str] = None

    # API details
    api_version: Optional[str] = None
    endpoint: Optional[str] = None

    # Request details
    prompts: List[VLMPrompt] = Field(default_factory=list)

    # Response details
    total_tokens: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

    # Cost
    cost_usd: Optional[float] = None

    # Features used
    features: List[str] = Field(default_factory=list)  # ["grounding", "thinking", etc.]


class ExtractionMetadata(BaseModel):
    """Metadata about the extraction process."""
    # Extraction method
    method: Literal["tool", "vlm"]

    # Tool information
    tool: Optional[ToolInfo] = None

    # VLM information
    vlm: Optional[VLMInfo] = None

    # Timing
    extracted_at: str  # ISO 8601
    duration_ms: Optional[int] = None

    # Quality metrics
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    completeness: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Warnings and errors
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
```

## Validation Schema

JSON Schema definitions for validation:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://github.com/yourusername/vlm-test/schemas/document.json",
  "title": "Document",
  "description": "Root schema for parsed document structure",
  "type": "object",
  "required": ["id", "type", "source", "metadata", "content"],
  "properties": {
    "id": {
      "type": "string",
      "description": "Unique document identifier"
    },
    "type": {
      "type": "string",
      "enum": ["web_page", "pdf", "academic_paper", "plot", "presentation", "report", "other"]
    },
    "source": {
      "$ref": "#/definitions/DocumentSource"
    },
    "metadata": {
      "$ref": "#/definitions/DocumentMetadata"
    },
    "content": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/ContentElement"
      }
    },
    "figures": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Figure"
      }
    },
    "tables": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Table"
      }
    },
    "links": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Link"
      }
    },
    "citations": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Citation"
      }
    },
    "relationships": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Relationship"
      }
    },
    "rendering": {
      "$ref": "#/definitions/RenderingInfo"
    },
    "extraction": {
      "$ref": "#/definitions/ExtractionMetadata"
    }
  },
  "definitions": {
    "...": "Full definitions would follow..."
  }
}
```

## Example Documents

### Example 1: Simple Web Article

```json
{
  "id": "doc-001",
  "format": "html",
  "category": "tutorial",
  "source": {
    "url": "https://example.com/article",
    "accessed_at": "2025-12-07T10:30:00Z"
  },
  "metadata": {
    "title": "Introduction to Machine Learning",
    "authors": [
      {
        "name": "Jane Smith",
        "affiliation": ["University of Example"]
      }
    ],
    "published_date": "2025-01-15",
    "keywords": ["machine learning", "AI", "tutorial"]
  },
  "content": [
    {
      "id": "c1",
      "type": "heading",
      "level": 1,
      "content": "Introduction to Machine Learning",
      "bbox": {
        "page": 1,
        "x": 50,
        "y": 100,
        "width": 800,
        "height": 40
      },
      "sequence": 0
    },
    {
      "id": "c2",
      "type": "paragraph",
      "content": "Machine learning is a subset of artificial intelligence...",
      "bbox": {
        "page": 1,
        "x": 50,
        "y": 160,
        "width": 800,
        "height": 120
      },
      "sequence": 1
    }
  ],
  "figures": [
    {
      "id": "f1",
      "type": "diagram",
      "label": "Figure 1",
      "caption": "Machine learning workflow",
      "bbox": {
        "page": 1,
        "x": 50,
        "y": 300,
        "width": 600,
        "height": 400
      },
      "image_data": {
        "url": "https://example.com/images/ml-workflow.png",
        "width": 600,
        "height": 400,
        "format": "png"
      }
    }
  ],
  "links": [
    {
      "id": "l1",
      "anchor_text": "learn more",
      "href": "https://example.com/learn-more",
      "type": "external",
      "source_id": "c2"
    }
  ],
  "rendering": {
    "method": "playwright",
    "config": {
      "browser": "chromium",
      "viewport": {
        "width": 1920,
        "height": 1080
      }
    },
    "rendered_at": "2025-12-07T10:30:05Z"
  },
  "extraction": {
    "method": "tool",
    "tool": {
      "name": "beautifulsoup",
      "version": "4.12.0"
    },
    "extracted_at": "2025-12-07T10:30:10Z"
  }
}
```

### Example 2: Academic Paper with Plot

```json
{
  "id": "paper-arxiv-2501.12345",
  "format": "pdf",
  "category": "academic_paper",
  "source": {
    "url": "https://arxiv.org/pdf/2501.12345.pdf",
    "accessed_at": "2025-12-07T11:00:00Z"
  },
  "metadata": {
    "title": "Novel Approaches to Deep Learning Optimization",
    "authors": [
      {
        "name": "John Doe",
        "given_name": "John",
        "family_name": "Doe",
        "affiliation": ["MIT"],
        "orcid": "0000-0001-2345-6789"
      }
    ],
    "doi": "10.48550/arxiv.2501.12345",
    "arxiv_id": "2501.12345",
    "published_date": "2025-01-20",
    "abstract": "We present a novel optimization algorithm...",
    "keywords": ["deep learning", "optimization", "gradient descent"]
  },
  "content": [
    {
      "id": "abstract",
      "type": "section",
      "level": 0,
      "content": "We present a novel optimization algorithm...",
      "sequence": 0
    },
    {
      "id": "intro-heading",
      "type": "heading",
      "level": 1,
      "content": "1. Introduction",
      "sequence": 1
    }
  ],
  "figures": [
    {
      "id": "fig1",
      "type": "plot",
      "label": "Figure 1",
      "caption": "Training loss over epochs for different optimizers",
      "bbox": {
        "page": 3,
        "x": 72,
        "y": 200,
        "width": 450,
        "height": 300
      },
      "plot_type": "line",
      "axes": [
        {
          "name": "x",
          "label": "Epoch",
          "scale": "linear",
          "range": [0, 100]
        },
        {
          "name": "y",
          "label": "Loss",
          "scale": "log",
          "range": [0.001, 1.0]
        }
      ],
      "legend": {
        "items": [
          {
            "label": "SGD",
            "color": "blue",
            "line_style": "solid"
          },
          {
            "label": "Adam",
            "color": "red",
            "line_style": "dashed"
          },
          {
            "label": "Novel Method",
            "color": "green",
            "line_style": "solid"
          }
        ]
      },
      "referenced_by": ["intro-para-3"]
    }
  ],
  "citations": [
    {
      "id": "cite1",
      "marker": "[1]",
      "citing_element_id": "intro-para-3",
      "reference_id": "ref1",
      "type": "bibliographic"
    }
  ],
  "references": [
    {
      "id": "ref1",
      "type": "journal_article",
      "title": "Adam: A Method for Stochastic Optimization",
      "authors": [
        {
          "name": "Kingma, D.P."
        },
        {
          "name": "Ba, J."
        }
      ],
      "year": 2014,
      "journal": "ICLR",
      "arxiv_id": "1412.6980"
    }
  ],
  "extraction": {
    "method": "vlm",
    "vlm": {
      "model": "glm-4.6v",
      "provider": "z.ai",
      "prompts": [
        {
          "purpose": "extract_metadata",
          "prompt": "Extract the title, authors, abstract, and keywords...",
          "input_tokens": 1500,
          "output_tokens": 300
        },
        {
          "purpose": "extract_figures",
          "prompt": "Identify all figures and extract their captions, labels, and types...",
          "input_tokens": 2000,
          "output_tokens": 500
        }
      ],
      "total_tokens": 4300,
      "cost_usd": 0.0081,
      "features": ["grounding"]
    },
    "extracted_at": "2025-12-07T11:05:00Z"
  }
}
```

## Usage Guidelines

### For Tool-Based Parsers

1. Extract all available fields, even if confidence is low
2. Use `confidence` field to indicate extraction quality
3. Preserve coordinate information when available
4. Map tool-specific outputs to this schema
5. Include extraction metadata for debugging

### For VLM-Based Parsers

1. Use structured prompts that request JSON output matching this schema
2. Split complex documents into multiple VLM requests (metadata, content, figures, etc.)
3. Use grounding features to extract bounding boxes
4. Request confidence scores for extracted elements
5. Store prompts and responses in `extraction.vlm` for reproducibility

### For Equivalence Checking

1. Compare elements by `id` or semantic matching
2. Use fuzzy matching for text content (allow for OCR errors)
3. Check structural similarity (hierarchies, relationships)
4. Validate spatial information with tolerance
5. Report differences with specific field paths

## Extension Points

The schema can be extended for domain-specific needs:

1. **Custom Content Types**: Add new `ContentType` enum values
2. **Custom Relationships**: Add new `RelationshipType` values or use `type: "custom"`
3. **Custom Metadata**: Use `metadata.custom` for domain-specific fields
4. **Custom Attributes**: Use `attributes.custom` for element-specific properties
5. **Document Subtypes**: Extend base `Document` interface for new document types

## Relationship with Simple Schema

This full schema has a simplified version defined in [SCHEMA_SIMPLE.md](./SCHEMA_SIMPLE.md):

- **Simple Schema**: Minimal subset for quick prototyping and simple documents
- **Full Schema**: Complete specification for complex documents

### Key Differences

| Aspect | Simple Schema | Full Schema |
|--------|--------------|-------------|
| **Content Elements** | Flat list, plain text only | Hierarchical with rich text, attributes |
| **Figures** | Just caption and bbox | Full type, image data, relationships |
| **Tables** | Simple rows of strings | Complete cell structure with formatting |
| **Metadata** | Title, authors, date, keywords | Complete publication info, identifiers |
| **Citations** | Not included | Full citation and reference support |
| **Relationships** | Not included | Complete relationship modeling |
| **Format Extensions** | Not included | HTML, PDF-specific metadata |
| **Category Extensions** | Not included | Academic paper, presentation structure |

### Migration Path

The simple schema is designed to be easily upgraded to the full schema:

```python
# Start with simple schema for prototyping
simple_doc = SimpleDocument(...)

# Upgrade when you need more detail
full_doc = upgrade_to_full_schema(simple_doc)
```

See [SCHEMA_SIMPLE.md](./SCHEMA_SIMPLE.md) for complete documentation and examples.

## Version History

- **v1.0.0** (2025-12-07): Initial schema definition
  - Core types and interfaces
  - Web page, PDF, and academic paper support
  - Plot and visualization structures
  - Relationship modeling
