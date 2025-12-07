# Document Structure Schema

## Overview

This document defines the canonical schema for representing parsed document structures. This schema serves as the common format for both:
1. **Tool-based parsing** (traditional extraction using libraries like pdfplumber, BeautifulSoup, etc.)
2. **VLM-based parsing** (extraction via Vision Language Models analyzing rendered documents)

The equivalence testing framework compares outputs from both approaches using this shared schema.

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

```typescript
interface BoundingBox {
  // Page or screen number (1-indexed)
  page: number;

  // Coordinates in pixels or PDF points (72 DPI)
  // Origin is top-left corner
  x: number;      // Left edge
  y: number;      // Top edge
  width: number;  // Width of box
  height: number; // Height of box

  // Optional: confidence score from extraction tool
  confidence?: number; // 0.0 - 1.0
}

// Alternative representation for compatibility
interface BoundingBoxAlt {
  page: number;
  x1: number; // Left
  y1: number; // Top
  x2: number; // Right
  y2: number; // Bottom
}
```

### Document Root

Top-level container for all document content:

```typescript
interface Document {
  // Document metadata
  id: string;
  format: DocumentFormat;
  category?: DocumentCategory;
  source: DocumentSource;
  metadata: DocumentMetadata;

  // Structural content
  content: ContentElement[];

  // Extracted visual elements
  figures: Figure[];
  tables: Table[];

  // References and relationships
  links: Link[];
  citations: Citation[];
  relationships: Relationship[];

  // Rendering information
  rendering: RenderingInfo;

  // Extraction metadata
  extraction: ExtractionMetadata;
}

// Document format: the file format/extension/representation
enum DocumentFormat {
  HTML = "html",
  PDF = "pdf",
  PNG = "png",
  JPG = "jpg",
  SVG = "svg",
  MARKDOWN = "markdown",
  LATEX = "latex",
  DOCX = "docx",
  PPTX = "pptx",
  JUPYTER = "jupyter",
  OTHER = "other"
}

// Document category: the semantic type/purpose of the document
enum DocumentCategory {
  ACADEMIC_PAPER = "academic_paper",
  BLOG_POST = "blog_post",
  NEWS_ARTICLE = "news_article",
  TECHNICAL_DOCUMENTATION = "technical_documentation",
  BOOK_CHAPTER = "book_chapter",
  PRESENTATION = "presentation",
  REPORT = "report",
  TUTORIAL = "tutorial",
  PLOT_VISUALIZATION = "plot_visualization",
  INFOGRAPHIC = "infographic",
  WEBPAGE_GENERAL = "webpage_general",
  OTHER = "other"
}

interface DocumentSource {
  // Original source
  url?: string;
  file_path?: string;

  // Content hash for versioning
  content_hash?: string;

  // Timestamp
  accessed_at: string; // ISO 8601
}
```

### Document Metadata

Structured metadata following Schema.org and JATS standards:

```typescript
interface DocumentMetadata {
  // Core metadata
  title?: string;
  subtitle?: string;

  // Authorship
  authors?: Author[];

  // Publishing information
  published_date?: string; // ISO 8601
  modified_date?: string;  // ISO 8601
  publisher?: Organization;

  // Identifiers
  doi?: string;
  isbn?: string;
  issn?: string;
  arxiv_id?: string;
  pmid?: string;
  url?: string;

  // Classification
  keywords?: string[];
  subjects?: string[];
  language?: string; // ISO 639-1 code

  // Abstract/summary
  abstract?: string;

  // Custom metadata
  custom?: Record<string, any>;
}

interface Author {
  name: string;
  given_name?: string;
  family_name?: string;
  affiliation?: string[];
  orcid?: string;
  email?: string;
}

interface Organization {
  name: string;
  url?: string;
  address?: string;
}
```

## Content Structure

### Content Elements

Hierarchical content representation:

```typescript
interface ContentElement {
  // Unique identifier within document
  id: string;

  // Element type
  type: ContentType;

  // Hierarchical structure
  level?: number; // Heading level, list depth, etc.
  parent_id?: string;
  children_ids?: string[];

  // Content
  content: string | RichText;

  // Spatial information
  bbox?: BoundingBox;

  // Styling and attributes
  attributes?: ContentAttributes;

  // Order in document
  sequence?: number;
}

enum ContentType {
  // Text blocks
  HEADING = "heading",
  PARAGRAPH = "paragraph",
  LIST_ITEM = "list_item",
  BLOCKQUOTE = "blockquote",
  CODE_BLOCK = "code_block",

  // Inline elements
  TEXT = "text",
  EMPHASIS = "emphasis",
  STRONG = "strong",
  CODE = "code",

  // Structural
  SECTION = "section",
  ARTICLE = "article",
  ASIDE = "aside",
  HEADER = "header",
  FOOTER = "footer",
  NAV = "nav",

  // Other
  CAPTION = "caption",
  LABEL = "label",
  METADATA = "metadata"
}

interface RichText {
  // Plain text version
  plain: string;

  // Formatted version (HTML, Markdown, etc.)
  formatted?: string;
  format?: "html" | "markdown" | "latex";

  // Inline elements
  spans?: TextSpan[];
}

interface TextSpan {
  text: string;
  start: number; // Character offset
  end: number;
  style?: TextStyle;
  link?: string;
}

interface TextStyle {
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strikethrough?: boolean;
  font_size?: number;
  font_family?: string;
  color?: string;
}

interface ContentAttributes {
  // Semantic attributes
  role?: string;
  lang?: string;

  // Visual attributes
  alignment?: "left" | "center" | "right" | "justify";
  indentation?: number;

  // HTML/CSS classes (for web content)
  classes?: string[];

  // Custom attributes
  custom?: Record<string, any>;
}
```

## Visual Elements

### Figures and Images

```typescript
interface Figure {
  id: string;
  type: FigureType;

  // Content
  caption?: string;
  label?: string; // e.g., "Figure 1", "Fig. 2a"
  alt_text?: string;

  // Visual properties
  bbox?: BoundingBox;
  image_data?: ImageData;

  // Relationships
  referenced_by?: string[]; // IDs of content elements that reference this
  related_to?: string[]; // IDs of related figures

  // Extraction confidence
  confidence?: number;
}

enum FigureType {
  PHOTOGRAPH = "photograph",
  DIAGRAM = "diagram",
  CHART = "chart",
  PLOT = "plot",
  MAP = "map",
  ILLUSTRATION = "illustration",
  SCREENSHOT = "screenshot",
  ICON = "icon",
  LOGO = "logo",
  OTHER = "other"
}

interface ImageData {
  // Image source
  url?: string;
  embedded?: string; // Base64 encoded

  // Image properties
  width?: number;
  height?: number;
  format?: string; // png, jpg, svg, etc.

  // File information
  file_size?: number;
  checksum?: string;
}
```

### Plots and Visualizations

Extended figure schema for data visualizations:

```typescript
interface Plot extends Figure {
  type: FigureType.PLOT | FigureType.CHART;
  plot_type: PlotType;

  // Plot components
  title?: string;
  axes?: Axis[];
  legend?: Legend;
  data_series?: DataSeries[];

  // Visual encoding
  color_scheme?: string;

  // Accessibility
  description?: string;
  data_table?: Table; // Alternative representation
}

enum PlotType {
  LINE = "line",
  SCATTER = "scatter",
  BAR = "bar",
  HISTOGRAM = "histogram",
  PIE = "pie",
  HEATMAP = "heatmap",
  BOX_PLOT = "box_plot",
  VIOLIN = "violin",
  CONTOUR = "contour",
  SURFACE_3D = "surface_3d",
  OTHER = "other"
}

interface Axis {
  name?: string;
  label?: string;
  unit?: string;
  scale?: "linear" | "log" | "time" | "category";
  range?: [number, number] | string[];
  ticks?: TickMark[];
}

interface TickMark {
  value: number | string;
  label?: string;
  position?: number;
}

interface Legend {
  title?: string;
  items: LegendItem[];
  position?: "top" | "bottom" | "left" | "right" | "inside";
}

interface LegendItem {
  label: string;
  color?: string;
  marker?: string;
  line_style?: string;
}

interface DataSeries {
  name?: string;
  type?: string; // line, scatter, bar, etc.

  // Visual properties
  color?: string;
  marker?: string;
  line_style?: string;

  // Data (if extractable)
  data_points?: DataPoint[];

  // Summary statistics
  stats?: {
    count?: number;
    min?: number;
    max?: number;
    mean?: number;
    median?: number;
  };
}

interface DataPoint {
  x: number | string;
  y: number;
  z?: number; // For 3D plots
  label?: string;
  error?: number | [number, number]; // Error bars
}
```

### Tables

```typescript
interface Table {
  id: string;

  // Content
  caption?: string;
  label?: string; // e.g., "Table 1"

  // Structure
  headers?: TableHeader[];
  rows: TableRow[];
  footer?: TableRow;

  // Layout
  bbox?: BoundingBox;
  num_columns: number;
  num_rows: number;

  // Properties
  has_header_row?: boolean;
  has_header_column?: boolean;
  is_numeric?: boolean;

  // Relationships
  referenced_by?: string[];
}

interface TableHeader {
  cells: TableCell[];
  level?: number; // For multi-level headers
}

interface TableRow {
  cells: TableCell[];
  row_type?: "header" | "data" | "footer";
}

interface TableCell {
  content: string | RichText;

  // Cell properties
  colspan?: number;
  rowspan?: number;

  // Spatial information
  bbox?: BoundingBox;

  // Semantic information
  data_type?: "text" | "number" | "date" | "boolean";
  alignment?: "left" | "center" | "right";

  // Styling
  attributes?: ContentAttributes;
}
```

## Relationships and References

### Links

```typescript
interface Link {
  id: string;

  // Link properties
  source_id?: string; // ID of element containing link
  anchor_text: string;
  href: string;

  // Link type
  type: LinkType;

  // Position
  bbox?: BoundingBox;

  // Metadata
  title?: string;
  rel?: string; // HTML rel attribute
}

enum LinkType {
  INTERNAL = "internal",     // Same document
  EXTERNAL = "external",     // Different domain
  ANCHOR = "anchor",         // Same page (#fragment)
  DOWNLOAD = "download",     // File download
  EMAIL = "email",          // mailto:
  TELEPHONE = "telephone"   // tel:
}
```

### Citations and References

```typescript
interface Citation {
  id: string;

  // Citation marker in text
  marker: string; // e.g., "[1]", "(Smith, 2020)", "¹"
  marker_bbox?: BoundingBox;

  // Location in document
  citing_element_id?: string;

  // Target reference
  reference_id?: string;

  // Citation type
  type?: CitationType;
}

enum CitationType {
  BIBLIOGRAPHIC = "bibliographic",
  FIGURE = "figure",
  TABLE = "table",
  EQUATION = "equation",
  SECTION = "section",
  FOOTNOTE = "footnote",
  ENDNOTE = "endnote"
}

interface Reference {
  id: string;

  // Bibliographic information
  type: ReferenceType;

  // Core fields
  title?: string;
  authors?: Author[];
  year?: number;

  // Publication details
  journal?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  publisher?: string;

  // Identifiers
  doi?: string;
  url?: string;
  isbn?: string;
  arxiv_id?: string;

  // Citation count
  cited_by?: string[]; // IDs of citations

  // Raw text
  raw_text?: string;
}

enum ReferenceType {
  JOURNAL_ARTICLE = "journal_article",
  BOOK = "book",
  BOOK_CHAPTER = "book_chapter",
  CONFERENCE_PAPER = "conference_paper",
  THESIS = "thesis",
  PREPRINT = "preprint",
  WEBPAGE = "webpage",
  SOFTWARE = "software",
  DATASET = "dataset",
  OTHER = "other"
}
```

### Relationships

General relationship model for arbitrary connections:

```typescript
interface Relationship {
  id: string;

  // Relationship type
  type: RelationshipType | string; // Extensible

  // Connected elements
  source_id: string;
  target_id: string;

  // Relationship properties
  label?: string;
  properties?: Record<string, any>;

  // Confidence
  confidence?: number;
}

enum RelationshipType {
  // Hierarchical
  PARENT_CHILD = "parent_child",
  CONTAINS = "contains",

  // Sequential
  FOLLOWS = "follows",
  PRECEDES = "precedes",

  // Referential
  REFERENCES = "references",
  CITED_BY = "cited_by",
  DESCRIBES = "describes",

  // Associative
  RELATED_TO = "related_to",
  SAME_AS = "same_as",
  SIMILAR_TO = "similar_to",

  // Compositional
  PART_OF = "part_of",
  HAS_PART = "has_part",

  // Custom
  CUSTOM = "custom"
}
```

## Format-Specific Extensions

### HTML/Web Pages

Additional fields when `format = DocumentFormat.HTML`:

```typescript
interface WebMetadataExtension {
  // Web-specific metadata
  web_metadata?: WebMetadata;

  // DOM structure (optional, for HTML parsing)
  dom_structure?: DOMNode;

  // SEO elements
  seo?: SEOData;
}

// Add to Document.metadata.custom when format = HTML
// e.g., metadata.custom.web_metadata = {...}

interface WebMetadata {
  // URL structure
  canonical_url?: string;
  base_url?: string;

  // HTTP metadata
  status_code?: number;
  content_type?: string;
  headers?: Record<string, string>;

  // Page properties
  viewport?: {
    width: number;
    height: number;
  };

  // Open Graph
  og_data?: Record<string, string>;

  // Twitter Card
  twitter_data?: Record<string, string>;
}

interface DOMNode {
  tag: string;
  attributes?: Record<string, string>;
  children?: DOMNode[];
  text?: string;

  // Mapping to content elements
  content_id?: string;
}

interface SEOData {
  meta_description?: string;
  meta_keywords?: string[];
  h1_tags?: string[];
  schema_markup?: any; // JSON-LD data
}
```

### PDF Documents

Additional fields when `format = DocumentFormat.PDF`:

```typescript
interface PDFMetadataExtension {
  // PDF-specific metadata
  pdf_metadata?: PDFMetadata;

  // Page structure
  pages?: PDFPage[];
}

// Add to Document.metadata.custom when format = PDF
// e.g., metadata.custom.pdf_metadata = {...}
// e.g., document.custom.pages = [...]

interface PDFMetadata {
  // PDF properties
  pdf_version?: string;
  page_count: number;

  // PDF metadata fields
  producer?: string;
  creator?: string;
  creation_date?: string;
  modification_date?: string;

  // Document properties
  is_tagged?: boolean; // PDF/UA
  is_encrypted?: boolean;
  is_linearized?: boolean;

  // Page layout
  page_layout?: "single" | "continuous" | "two_column";
  page_mode?: "full_screen" | "thumbnails" | "outlines";
}

interface PDFPage {
  page_number: number;

  // Page dimensions (in PDF points, 72 DPI)
  width: number;
  height: number;
  rotation?: number; // 0, 90, 180, 270

  // Content on this page
  content_ids: string[];
  figure_ids: string[];
  table_ids: string[];

  // Text blocks with coordinates
  text_blocks?: TextBlock[];

  // Raw page data
  raw_text?: string;
}

interface TextBlock {
  text: string;
  bbox: BoundingBox;

  // Font information
  font_name?: string;
  font_size?: number;

  // Text properties
  is_bold?: boolean;
  is_italic?: boolean;
  color?: string;

  // Reading order
  sequence?: number;

  // Confidence
  confidence?: number;
}
```

## Category-Specific Extensions

### Academic Papers

Additional fields when `category = DocumentCategory.ACADEMIC_PAPER`:

```typescript
interface AcademicPaperExtension {
  // Paper-specific structure (following JATS)
  front_matter?: FrontMatter;
  abstract?: Abstract;
  body?: Body;
  back_matter?: BackMatter;
}

// Add to Document.metadata.custom when category = ACADEMIC_PAPER
// e.g., metadata.custom.academic = {...}

interface FrontMatter {
  title_group?: {
    title: string;
    subtitle?: string;
    translated_titles?: Array<{
      language: string;
      title: string;
    }>;
  };

  authors: Author[];

  affiliations?: Affiliation[];

  correspondence?: {
    author_id: string;
    email: string;
    address?: string;
  };

  dates?: {
    received?: string;
    accepted?: string;
    published?: string;
  };

  funding?: FundingInfo[];

  keywords?: string[];
}

interface Affiliation {
  id: string;
  institution: string;
  department?: string;
  city?: string;
  country?: string;
}

interface FundingInfo {
  agency: string;
  grant_number?: string;
  recipient?: string;
}

interface Abstract {
  type?: "structured" | "unstructured";
  sections?: Array<{
    label?: string; // Background, Methods, Results, Conclusions
    content: string;
  }>;
  plain_text?: string;
}

interface Body {
  sections: Section[];
}

interface Section {
  id: string;
  label?: string; // "Introduction", "Methods", etc.
  title?: string;
  level: number; // 1, 2, 3, etc.

  // Content
  content_ids: string[];
  subsections?: Section[];

  // Position
  bbox?: BoundingBox;
}

interface BackMatter {
  // Acknowledgments
  acknowledgments?: string;

  // References
  references: Reference[];

  // Appendices
  appendices?: Appendix[];

  // Author contributions
  author_contributions?: Record<string, string>;

  // Conflict of interest
  conflict_of_interest?: string;

  // Data availability
  data_availability?: string;
}

interface Appendix {
  id: string;
  label: string; // "Appendix A", etc.
  title?: string;
  content_ids: string[];
}
```

## Rendering Information

Information about how the document was rendered for VLM analysis:

```typescript
interface RenderingInfo {
  // Rendering method
  method: "playwright" | "pdf2image" | "matplotlib" | "custom";

  // Renderer configuration
  config?: RendererConfig;

  // Screenshots
  screenshots?: Screenshot[];

  // Timestamp
  rendered_at: string; // ISO 8601
}

interface RendererConfig {
  // Browser/engine
  browser?: "chromium" | "firefox" | "webkit";

  // Viewport
  viewport?: {
    width: number;
    height: number;
  };

  // PDF rendering
  dpi?: number;

  // Wait conditions
  wait_until?: "load" | "domcontentloaded" | "networkidle";
  wait_time?: number; // milliseconds

  // Custom options
  custom?: Record<string, any>;
}

interface Screenshot {
  page: number;

  // Image data
  image_url?: string;
  image_data?: string; // Base64

  // Image properties
  width: number;
  height: number;
  format: "png" | "jpg" | "webp";

  // File info
  file_size?: number;
  checksum?: string;
}
```

## Extraction Metadata

Information about the extraction process:

```typescript
interface ExtractionMetadata {
  // Extraction method
  method: "tool" | "vlm";

  // Tool information
  tool?: ToolInfo;

  // VLM information
  vlm?: VLMInfo;

  // Timing
  extracted_at: string; // ISO 8601
  duration_ms?: number;

  // Quality metrics
  confidence?: number;
  completeness?: number; // 0.0 - 1.0

  // Warnings and errors
  warnings?: string[];
  errors?: string[];
}

interface ToolInfo {
  name: string;
  version?: string;

  // Libraries used
  libraries?: Array<{
    name: string;
    version: string;
  }>;

  // Configuration
  config?: Record<string, any>;
}

interface VLMInfo {
  model: string; // e.g., "glm-4.5v"
  provider?: string;

  // API details
  api_version?: string;
  endpoint?: string;

  // Request details
  prompts?: VLMPrompt[];

  // Response details
  total_tokens?: number;
  input_tokens?: number;
  output_tokens?: number;

  // Cost
  cost_usd?: number;

  // Features used
  features?: string[]; // ["grounding", "thinking", etc.]
}

interface VLMPrompt {
  prompt: string;
  response: string;

  // For multi-request strategies
  purpose?: string; // "extract_metadata", "extract_figures", etc.

  // Tokens
  input_tokens?: number;
  output_tokens?: number;
}
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
      "model": "glm-4.5v",
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

## Version History

- **v1.0.0** (2025-12-07): Initial schema definition
  - Core types and interfaces
  - Web page, PDF, and academic paper support
  - Plot and visualization structures
  - Relationship modeling
