# Simple Document Schema

## Overview

This document defines a **simplified schema** that is a strict subset of the full schema defined in [SCHEMA.md](./SCHEMA.md). The simple schema is designed for:

- **Faster iteration** during development and testing
- **Simpler documents** that don't require full structural complexity
- **Quick prototyping** of parsing and VLM-based extraction
- **Learning and demos** with minimal boilerplate

## Design Principles

1. **Strict subset**: Every field in the simple schema exists in the full schema
2. **Standalone**: Can be used independently without the full schema
3. **Minimal required fields**: Only essential fields are required
4. **Easy upgrade path**: Simple schema outputs can be converted to full schema by adding optional fields
5. **Reduced nesting**: Flatter structure for easier manipulation

## Simple Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


class DocumentFormat(str, Enum):
    """Document format."""
    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    SVG = "svg"
    MARKDOWN = "markdown"
    OTHER = "other"


class DocumentCategory(str, Enum):
    """Document category."""
    ACADEMIC_PAPER = "academic_paper"
    BLOG_POST = "blog_post"
    NEWS_ARTICLE = "news_article"
    TUTORIAL = "tutorial"
    PLOT_VISUALIZATION = "plot_visualization"
    WEBPAGE_GENERAL = "webpage_general"
    OTHER = "other"


class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    page: int
    x: float
    y: float
    width: float
    height: float


class ContentElement(BaseModel):
    """Simple content element - just id, type, and text."""
    id: str
    type: str  # "heading", "paragraph", "section", etc.
    content: str
    bbox: Optional[BoundingBox] = None
    level: Optional[int] = None  # For headings, hierarchy


class Figure(BaseModel):
    """Simple figure with caption and location."""
    id: str
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Figure 1"
    bbox: Optional[BoundingBox] = None


class Table(BaseModel):
    """Simple table representation."""
    id: str
    caption: Optional[str] = None
    label: Optional[str] = None  # e.g., "Table 1"
    bbox: Optional[BoundingBox] = None
    # Raw content representation
    rows: List[List[str]] = Field(default_factory=list)


class Link(BaseModel):
    """Simple link with text and URL."""
    id: str
    text: str
    url: str


class Author(BaseModel):
    """Simple author representation."""
    name: str
    affiliation: Optional[str] = None


class DocumentMetadata(BaseModel):
    """Minimal document metadata."""
    title: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    date: Optional[datetime] = None
    keywords: List[str] = Field(default_factory=list)


class DocumentSource(BaseModel):
    """Document source information."""
    url: Optional[str] = None
    file_path: Optional[str] = None
    accessed_at: datetime


class SimpleDocument(BaseModel):
    """
    Simplified document representation.

    This is a strict subset of the full Document schema,
    containing only the most essential fields.
    """
    # Required fields
    id: str
    format: DocumentFormat
    source: DocumentSource

    # Optional categorization
    category: Optional[DocumentCategory] = None

    # Metadata
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    # Content (flat list of elements)
    content: List[ContentElement] = Field(default_factory=list)

    # Visual elements
    figures: List[Figure] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)

    # Links
    links: List[Link] = Field(default_factory=list)
```

## Field Mapping to Full Schema

This table shows how simple schema fields map to the full schema:

| Simple Schema | Full Schema | Notes |
|--------------|-------------|-------|
| `SimpleDocument` | `Document` | Subset of fields |
| `SimpleDocument.format` | `Document.format` | Identical |
| `SimpleDocument.category` | `Document.category` | Identical |
| `SimpleDocument.source` | `Document.source` | Subset (no `content_hash`) |
| `SimpleDocument.metadata` | `Document.metadata` | Subset (only title, authors, date, keywords) |
| `SimpleDocument.content` | `Document.content` | Simplified `ContentElement` (no hierarchy, attributes) |
| `SimpleDocument.figures` | `Document.figures` | Subset (no type, image_data, relationships) |
| `SimpleDocument.tables` | `Document.tables` | Subset (simple rows, no cell structure) |
| `SimpleDocument.links` | `Document.links` | Subset (no type, source_id, bbox) |
| `Author` | `Author` | Subset (name + affiliation only) |
| `BoundingBox` | `BoundingBox` | Identical (except no confidence) |

## What's Excluded from Simple Schema

To keep things simple, the following are **not included**:

- ❌ Citations and references
- ❌ Relationships between elements
- ❌ Rich text formatting (spans, styles)
- ❌ Content attributes (alignment, classes, etc.)
- ❌ Content hierarchy (parent_id, children_ids)
- ❌ Plot details (axes, legend, data series)
- ❌ Table cell structure (just simple rows of strings)
- ❌ Figure types and image data
- ❌ Rendering information
- ❌ Extraction metadata
- ❌ Format-specific extensions (web metadata, PDF pages)
- ❌ Category-specific extensions (academic paper structure)

## Usage Examples

### Example 1: Simple Blog Post

```python
from datetime import datetime

doc = SimpleDocument(
    id="blog-001",
    format=DocumentFormat.HTML,
    category=DocumentCategory.BLOG_POST,
    source=DocumentSource(
        url="https://example.com/blog/post",
        accessed_at=datetime.now()
    ),
    metadata=DocumentMetadata(
        title="Getting Started with Python",
        authors=[Author(name="Jane Doe")],
        date=datetime(2025, 1, 15),
        keywords=["python", "tutorial", "programming"]
    ),
    content=[
        ContentElement(
            id="c1",
            type="heading",
            content="Getting Started with Python",
            level=1
        ),
        ContentElement(
            id="c2",
            type="paragraph",
            content="Python is a versatile programming language..."
        ),
        ContentElement(
            id="c3",
            type="paragraph",
            content="In this tutorial, we'll cover the basics..."
        )
    ],
    links=[
        Link(
            id="l1",
            text="Python Documentation",
            url="https://docs.python.org"
        )
    ]
)
```

### Example 2: Simple Academic Paper

```python
doc = SimpleDocument(
    id="paper-001",
    format=DocumentFormat.PDF,
    category=DocumentCategory.ACADEMIC_PAPER,
    source=DocumentSource(
        file_path="/papers/ml_paper.pdf",
        accessed_at=datetime.now()
    ),
    metadata=DocumentMetadata(
        title="Novel Approaches to Deep Learning",
        authors=[
            Author(name="John Smith", affiliation="MIT"),
            Author(name="Jane Doe", affiliation="Stanford")
        ],
        date=datetime(2025, 1, 20),
        keywords=["deep learning", "optimization"]
    ),
    content=[
        ContentElement(
            id="abstract",
            type="section",
            content="We present a novel optimization algorithm..."
        ),
        ContentElement(
            id="intro",
            type="heading",
            content="1. Introduction",
            level=1
        ),
        ContentElement(
            id="intro-p1",
            type="paragraph",
            content="Deep learning has revolutionized..."
        )
    ],
    figures=[
        Figure(
            id="fig1",
            label="Figure 1",
            caption="Training loss over epochs",
            bbox=BoundingBox(page=3, x=72, y=200, width=450, height=300)
        )
    ],
    tables=[
        Table(
            id="table1",
            label="Table 1",
            caption="Comparison of methods",
            rows=[
                ["Method", "Accuracy", "Speed"],
                ["SGD", "0.85", "Fast"],
                ["Adam", "0.89", "Medium"],
                ["Novel", "0.92", "Fast"]
            ]
        )
    ]
)
```

### Example 3: Simple Plot/Visualization

```python
doc = SimpleDocument(
    id="plot-001",
    format=DocumentFormat.PNG,
    category=DocumentCategory.PLOT_VISUALIZATION,
    source=DocumentSource(
        file_path="/plots/training_loss.png",
        accessed_at=datetime.now()
    ),
    metadata=DocumentMetadata(
        title="Training Loss Curve"
    ),
    figures=[
        Figure(
            id="main-plot",
            caption="Loss decreases over training epochs",
            bbox=BoundingBox(page=1, x=0, y=0, width=800, height=600)
        )
    ]
)
```

## Upgrading to Full Schema

When you need more detail, you can upgrade a `SimpleDocument` to a full `Document`:

```python
def upgrade_to_full_schema(simple_doc: SimpleDocument) -> Document:
    """Convert a SimpleDocument to a full Document."""
    return Document(
        id=simple_doc.id,
        format=simple_doc.format,
        category=simple_doc.category,
        source=simple_doc.source,
        metadata=upgrade_metadata(simple_doc.metadata),
        content=upgrade_content(simple_doc.content),
        figures=upgrade_figures(simple_doc.figures),
        tables=upgrade_tables(simple_doc.tables),
        links=upgrade_links(simple_doc.links),
        citations=[],  # Empty in simple schema
        relationships=[],  # Empty in simple schema
        rendering=None,  # Not tracked in simple schema
        extraction=None  # Not tracked in simple schema
    )

def upgrade_metadata(simple_meta: DocumentMetadata) -> FullDocumentMetadata:
    """Upgrade simple metadata to full metadata."""
    return FullDocumentMetadata(
        title=simple_meta.title,
        authors=[
            FullAuthor(
                name=a.name,
                affiliation=[a.affiliation] if a.affiliation else []
            )
            for a in simple_meta.authors
        ],
        published_date=simple_meta.date,
        keywords=simple_meta.keywords,
        # All other fields remain None/empty
    )

# Similar upgrade functions for content, figures, tables, links...
```

## Testing with Simple Schema

The simple schema is perfect for initial testing:

```python
import pytest
from vlm_test import VLMTester, SimpleDocument

def test_simple_blog_post_parsing():
    """Test parsing a simple blog post."""
    # Parse with tool
    tool_output = parse_blog_post_simple("fixtures/simple_blog.html")

    # Render and parse with VLM
    tester = VLMTester(model="glm-4.5v")
    screenshot = tester.render_webpage("fixtures/simple_blog.html")
    vlm_output = tester.parse_simple(screenshot)

    # Check equivalence on simple schema
    assert tool_output.metadata.title == vlm_output.metadata.title
    assert len(tool_output.content) == len(vlm_output.content)
    assert tool_output.content[0].content == vlm_output.content[0].content
```

## VLM Prompting for Simple Schema

When using VLMs to extract the simple schema, use straightforward prompts:

```python
SIMPLE_SCHEMA_PROMPT = """
Analyze this document image and extract the following information in JSON format:

{
  "metadata": {
    "title": "document title",
    "authors": [{"name": "Author Name", "affiliation": "Institution"}],
    "date": "2025-01-15T00:00:00",
    "keywords": ["keyword1", "keyword2"]
  },
  "content": [
    {
      "id": "c1",
      "type": "heading" or "paragraph" or "section",
      "content": "text content",
      "level": 1 (for headings only)
    }
  ],
  "figures": [
    {
      "id": "fig1",
      "label": "Figure 1",
      "caption": "figure caption",
      "bbox": {"page": 1, "x": 100, "y": 200, "width": 400, "height": 300}
    }
  ],
  "tables": [
    {
      "id": "table1",
      "label": "Table 1",
      "caption": "table caption",
      "rows": [["col1", "col2"], ["data1", "data2"]]
    }
  ],
  "links": [
    {
      "id": "l1",
      "text": "link text",
      "url": "https://example.com"
    }
  ]
}

Extract only what you can clearly see. Leave fields empty if not present.
"""
```

## When to Use Simple vs Full Schema

### Use Simple Schema When:
- ✅ Prototyping and testing basic functionality
- ✅ Processing straightforward documents (blog posts, simple articles)
- ✅ You don't need detailed structural information
- ✅ You want faster VLM responses (fewer fields to extract)
- ✅ You're just starting to build your parser
- ✅ Performance and simplicity matter more than completeness

### Use Full Schema When:
- ✅ Processing complex documents (academic papers, technical reports)
- ✅ You need detailed relationships (citations, cross-references)
- ✅ You need rich formatting information
- ✅ You need hierarchical content structure
- ✅ You're validating production-quality parsing
- ✅ You need format-specific or category-specific metadata
- ✅ Completeness and detail matter more than simplicity

## Validation

Both schemas support Pydantic validation:

```python
# Validate simple document
doc_dict = {
    "id": "doc-001",
    "format": "html",
    "source": {
        "url": "https://example.com",
        "accessed_at": "2025-12-07T10:00:00"
    },
    "metadata": {
        "title": "Test Document"
    },
    "content": [
        {"id": "c1", "type": "heading", "content": "Title"}
    ]
}

doc = SimpleDocument(**doc_dict)  # Validates automatically

# Export to JSON
json_str = doc.model_dump_json(indent=2)

# Load from JSON
doc2 = SimpleDocument.model_validate_json(json_str)
```

## Compatibility Notes

1. **JSON Serialization**: Both simple and full schemas serialize to JSON compatibly
2. **Field Names**: All field names in simple schema match the full schema exactly
3. **Type Compatibility**: Simple schema types are compatible with full schema types
4. **Migration**: Can gradually add fields from simple to full schema as needed

## Version History

- **v1.0.0** (2025-12-07): Initial simple schema definition
  - Core document structure
  - Minimal metadata
  - Flat content representation
  - Basic figures, tables, links
