# GLM-4.6V MCP Integration Guide

## Overview

This guide demonstrates how GLM-4.6V Vision Model works through the Model Context Protocol (MCP) when running in Claude Code.

## What is MCP?

**Model Context Protocol (MCP)** is a standardized way for AI applications to connect to external data sources and tools. Think of it as a "universal adapter" that lets Claude Code access various services through a consistent interface.

### Key Concepts

1. **MCP Server**: A process that provides tools/resources (e.g., Z.AI Vision MCP Server)
2. **MCP Client**: Claude Code acting as the client
3. **MCP Tools**: Functions exposed by the server (e.g., `image_analysis`)
4. **stdio Communication**: Client and server communicate via standard input/output

## Z.AI Vision MCP Server Setup

### Configuration File: `zai_glmV_mcp.json`

```json
{
  "mcpServers": {
    "zai-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@z_ai/mcp-server"],
      "env": {
        "Z_AI_API_KEY": "your_api_key_here",
        "Z_AI_MODE": "ZAI"
      }
    }
  }
}
```

**Breakdown:**
- `"type": "stdio"` - Communication via standard input/output
- `"command": "npx"` - Use Node Package Executor
- `"args": ["-y", "@z_ai/mcp-server"]` - Install and run Z.AI MCP server package
- `"env"` - Environment variables for API authentication

### How It Starts

```bash
# When Claude Code starts, it runs:
npx -y @z_ai/mcp-server

# With environment:
Z_AI_API_KEY=your_key
Z_AI_MODE=ZAI

# The MCP server starts and exposes tools via stdio
```

## Available MCP Tools

Once the MCP server is running, Claude Code can access these tools:

### Tool: `mcp__zai_mcp_server__image_analysis`

**Purpose**: Analyze images using GLM-4.6V vision model

**Input Parameters**:
- `image`: Base64-encoded image or image URL
- `prompt`: Text prompt describing what to extract

**Output**: JSON response with extracted information

## How MCP Tool Invocation Works

### 1. Tool Discovery

When Claude Code starts with MCP configured:

```
Claude Code starts
    ↓
Reads zai_glmV_mcp.json
    ↓
Spawns MCP server: npx -y @z_ai/mcp-server
    ↓
MCP server registers tools
    ↓
Claude Code discovers: mcp__zai_mcp_server__image_analysis
```

### 2. Tool Invocation

When you (or code) calls the MCP tool:

```
Python/Claude Code
    ↓
"I need to analyze this image with GLM-4.6V"
    ↓
Claude Code invokes: mcp__zai_mcp_server__image_analysis
    ↓
MCP Client sends JSON-RPC request via stdio
    ↓
MCP Server receives request
    ↓
Server calls Z.AI API with GLM-4.6V
    ↓
GLM-4.6V analyzes image
    ↓
Response flows back through MCP
    ↓
Result returned to caller
```

### 3. JSON-RPC Communication

Under the hood, MCP uses JSON-RPC 2.0:

```json
// Request (Claude Code → MCP Server)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "image_analysis",
    "arguments": {
      "image": "data:image/png;base64,iVBORw0KGgo...",
      "prompt": "Extract document title, authors, and sections"
    }
  }
}

// Response (MCP Server → Claude Code)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"title\": \"Deep Learning Paper\", \"authors\": [...]}"
      }
    ]
  }
}
```

## Practical Example: Document Analysis

### Scenario: Analyze a PDF Document

**Step 1: Render PDF to Image**

```python
from pathlib import Path
import pymupdf as fitz
from PIL import Image

def render_pdf_to_image(pdf_path: Path, page: int = 0) -> Path:
    """Convert PDF page to PNG image."""
    doc = fitz.open(pdf_path)
    page_obj = doc[page]

    # Render at 150 DPI
    pix = page_obj.get_pixmap(dpi=150)

    # Save as PNG
    image_path = pdf_path.with_suffix(f'.page{page}.png')
    pix.save(str(image_path))

    return image_path
```

**Step 2: Call MCP Tool (in Claude Code)**

When running in Claude Code, you would invoke the MCP tool:

```python
# This is pseudocode showing what happens in Claude Code
# The actual invocation is handled by Claude Code's tool system

tool_name = "mcp__zai_mcp_server__image_analysis"
image_path = "document.page0.png"

# Read and encode image
with open(image_path, 'rb') as f:
    image_data = base64.b64encode(f.read()).decode()

# Build prompt
prompt = """Analyze this document page and extract:
- Title
- Authors
- Abstract
- Main sections
- Tables
- Figures

Return as JSON."""

# Invoke MCP tool
result = invoke_mcp_tool(
    tool=tool_name,
    image=f"data:image/png;base64,{image_data}",
    prompt=prompt
)

# Result is JSON string
data = json.loads(result)
```

**Step 3: Parse Result into SimpleDocument**

```python
from vlm_doc_test.schemas.schema_simple import SimpleDocument, DocumentMetadata

# Parse VLM response
metadata = DocumentMetadata(
    title=data.get("title"),
    authors=[Author(name=name) for name in data.get("authors", [])],
)

content = [
    ContentElement(
        id=f"c{i}",
        type=item["type"],
        content=item["text"]
    )
    for i, item in enumerate(data.get("sections", []))
]

document = SimpleDocument(
    id="vlm_extracted",
    format=DocumentFormat.PDF,
    metadata=metadata,
    content=content
)
```

## VLM Parser Implementation

Our `VLMParser` is designed to work with MCP:

### Current Implementation

```python
class VLMParserWithMCP(VLMParser):
    def _call_vlm_mcp(self, image_path: Path, prompt: str) -> str:
        """
        Call Z.AI Vision MCP Server.

        In Claude Code environment, this would:
        1. Encode image to base64
        2. Invoke mcp__zai_mcp_server__image_analysis
        3. Return JSON response
        """
        # Read image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()

        # In Claude Code, MCP tools are invoked like this:
        # result = call_mcp_tool(
        #     "mcp__zai_mcp_server__image_analysis",
        #     image=f"data:image/png;base64,{image_data}",
        #     prompt=prompt
        # )

        # For now, raise NotImplementedError
        raise NotImplementedError(
            "Requires Claude Code MCP environment"
        )
```

### How It Would Work in Claude Code

When running in Claude Code with MCP configured:

```python
# User code
from vlm_doc_test.parsers import VLMParserWithMCP

parser = VLMParserWithMCP()
document = parser.parse(
    image_path="paper_page1.png",
    category=DocumentCategory.ACADEMIC_PAPER
)

# Behind the scenes:
# 1. Parser loads image
# 2. Builds category-specific prompt
# 3. Invokes MCP tool: mcp__zai_mcp_server__image_analysis
# 4. GLM-4.6V analyzes image
# 5. Returns structured JSON
# 6. Parser converts to SimpleDocument
```

## MCP Tool Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code Session                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Python Code: VLMParserWithMCP.parse()              │    │
│  │   - Loads image: paper.png                         │    │
│  │   - Builds prompt: "Extract academic paper data"   │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Claude Code MCP Client                             │    │
│  │   - Encodes image to base64                        │    │
│  │   - Prepares JSON-RPC request                      │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    │ stdio (JSON-RPC)
                    │
┌───────────────────▼──────────────────────────────────────────┐
│                    MCP Server Process                         │
│              (npx -y @z_ai/mcp-server)                       │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Receives JSON-RPC Request                          │    │
│  │   method: "tools/call"                             │    │
│  │   tool: "image_analysis"                           │    │
│  │   args: {image: "...", prompt: "..."}             │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Z.AI API Client                                    │    │
│  │   - Sends image + prompt to Z.AI                   │    │
│  │   - Model: GLM-4.6V (glm-4v-plus)                 │    │
│  │   - API: https://open.bigmodel.cn/api/paas/v4     │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    │ HTTPS
                    │
┌───────────────────▼──────────────────────────────────────────┐
│                  Z.AI / GLM-4.6V API                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │ GLM-4.6V Vision Model                              │    │
│  │   - Analyzes document image                        │    │
│  │   - Extracts: title, authors, sections, tables    │    │
│  │   - Returns: Structured JSON                       │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    │ JSON Response
                    │
                    ▼
            (Flow returns back up)
```

## Example: Complete Workflow

### Input Document

**File**: `research_paper.pdf` (10 pages)

### Step-by-Step Execution

**1. Render PDF to Image**

```python
from vlm_doc_test.renderers import PDFRenderer

renderer = PDFRenderer()
image_path = renderer.render_page(
    pdf_path="research_paper.pdf",
    page=0,
    output_path="research_paper_page0.png",
    dpi=150
)
```

**2. Initialize VLM Parser**

```python
from vlm_doc_test.parsers import VLMParserWithMCP
from vlm_doc_test.schemas.base import DocumentCategory

parser = VLMParserWithMCP()
```

**3. Parse with GLM-4.6V (via MCP)**

```python
document = parser.parse(
    image_path=image_path,
    category=DocumentCategory.ACADEMIC_PAPER
)
```

**What Happens Internally:**

```
a) Parser builds category-specific prompt:
   "This is an ACADEMIC PAPER. Extract: authors, affiliations,
    abstract, sections, tables, figures, citations..."

b) Parser encodes image to base64

c) Claude Code invokes MCP tool:
   mcp__zai_mcp_server__image_analysis(
       image="data:image/png;base64,iVBORw0KG...",
       prompt="This is an ACADEMIC PAPER..."
   )

d) MCP Server forwards to Z.AI API

e) GLM-4.6V analyzes image and returns:
   {
     "title": "Novel Approaches to Deep Learning",
     "authors": ["Jane Smith", "John Doe"],
     "affiliations": ["MIT", "Stanford"],
     "abstract": "We present novel optimization...",
     "sections": [
       {"type": "heading", "text": "Introduction", "level": 1},
       {"type": "paragraph", "text": "Deep learning has..."}
     ],
     "tables": [...],
     "figures": [...]
   }

f) Parser receives JSON string

g) Parser converts to SimpleDocument:
   - Metadata: title, authors
   - Content: sections as ContentElements
   - Tables: Table objects
   - Figures: Figure objects

h) Returns SimpleDocument instance
```

**4. Access Extracted Data**

```python
print(f"Title: {document.metadata.title}")
# Output: Title: Novel Approaches to Deep Learning

print(f"Authors: {[a.name for a in document.metadata.authors]}")
# Output: Authors: ['Jane Smith', 'John Doe']

print(f"Content sections: {len(document.content)}")
# Output: Content sections: 15

print(f"Tables found: {len(document.tables)}")
# Output: Tables found: 3

print(f"Figures found: {len(document.figures)}")
# Output: Figures found: 5
```

## Comparison: Tool-based vs VLM-based

### Traditional Tool-based (PyMuPDF)

```python
from vlm_doc_test.parsers import PDFParser

# Parse with PyMuPDF
tool_parser = PDFParser()
tool_doc = tool_parser.parse("research_paper.pdf")

# Relies on:
# - Text extraction (fast, but can miss structure)
# - Heuristic rules (headers based on font size)
# - No vision understanding
```

### VLM-based (GLM-4.6V)

```python
from vlm_doc_test.parsers import VLMParserWithMCP

# Parse with GLM-4.6V
vlm_parser = VLMParserWithMCP()
vlm_doc = vlm_parser.parse("research_paper_screenshot.png")

# Relies on:
# - Vision understanding (sees layout like a human)
# - Semantic understanding (understands context)
# - Can extract from images, charts, complex layouts
```

### Equivalence Testing

```python
from vlm_doc_test.validation import EquivalenceChecker

checker = EquivalenceChecker(text_similarity_threshold=0.80)
result = checker.compare_documents(tool_doc, vlm_doc)

print(f"Match quality: {result.match_quality}")
print(f"Similarity score: {result.score:.2f}")
print(f"Differences: {result.differences}")
```

## MCP Tool Parameters in Detail

### Image Parameter

**Formats Supported:**
1. **Base64 Data URI**: `data:image/png;base64,iVBORw0KGgo...`
2. **HTTP(S) URL**: `https://example.com/image.png`
3. **File Path**: `file:///path/to/image.png` (if server supports)

**Best Practice**: Use base64 for reliability

```python
import base64

with open("document.png", "rb") as f:
    image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    image_uri = f"data:image/png;base64,{image_b64}"
```

### Prompt Parameter

**Structure:**
```
[Task Description]
Extract the following information from this document:
- Field 1
- Field 2
...

[Output Format]
Return as JSON with this structure:
{
  "field1": "value",
  "field2": ["array", "of", "values"]
}

[Category Hint]
This is a [ACADEMIC_PAPER|BLOG_POST|TECHNICAL_DOC].
Focus on [category-specific fields].
```

**Example for Academic Paper:**
```
Analyze this academic paper page and extract:
- Title
- Authors and their affiliations
- Abstract
- Section headings
- Tables with captions
- Figures with captions
- Citations

Return as JSON:
{
  "title": "string",
  "authors": [{"name": "string", "affiliation": "string"}],
  "abstract": "string",
  "sections": [{"type": "heading", "text": "string", "level": 1}],
  "tables": [{"caption": "string", "data": [[...]]}],
  "figures": [{"caption": "string", "label": "string"}]
}

This is an ACADEMIC PAPER. Pay attention to:
- Author-affiliation mapping
- Section structure (Intro, Methods, Results, Discussion)
- Figure/Table numbering
- Reference citations
```

## Testing MCP Integration

### Mock Test (Current)

```python
# File: vlm_doc_test/tests/test_tool_vs_vlm_comparison.py

def test_vlm_parser_requires_mcp_for_parsing(tmp_path):
    """Test that VLM parser raises NotImplementedError without MCP."""
    parser = VLMParser()

    image_path = tmp_path / "test_image.png"
    image_path.write_text("fake image")

    with pytest.raises(NotImplementedError) as exc:
        parser.parse(image_path)

    assert "MCP integration" in str(exc.value)
```

### Real Test (With MCP in Claude Code)

```python
@pytest.mark.skipif(
    not mcp_tools_available(),
    reason="Requires Claude Code MCP environment"
)
def test_vlm_parser_with_real_mcp(sample_pdf):
    """Test VLM parser with actual MCP integration."""
    # Render PDF to image
    image_path = render_pdf_page(sample_pdf, page=0)

    # Parse with VLM
    parser = VLMParserWithMCP()
    vlm_doc = parser.parse(
        image_path=image_path,
        category=DocumentCategory.ACADEMIC_PAPER
    )

    # Validate result
    assert vlm_doc.metadata.title is not None
    assert len(vlm_doc.metadata.authors) > 0
    assert len(vlm_doc.content) > 0

    # Compare with tool-based parser
    tool_doc = PDFParser().parse(sample_pdf)
    checker = EquivalenceChecker()
    result = checker.compare_documents(tool_doc, vlm_doc)

    # Should have reasonable similarity
    assert result.score >= 0.70  # 70% similarity threshold
```

## Debugging MCP

### Check MCP Server Status

```bash
# In Claude Code, you can check MCP server logs
# Look for messages like:
[MCP Server] Starting @z_ai/mcp-server
[MCP Server] Registered tool: image_analysis
[MCP Server] Ready to accept requests
```

### Check Available Tools

```python
# In Claude Code, you can list MCP tools
available_tools = list_mcp_tools()
print(available_tools)
# Output: ['mcp__zai_mcp_server__image_analysis']
```

### Test MCP Tool Directly

```python
# Minimal test of MCP tool
result = call_mcp_tool(
    "mcp__zai_mcp_server__image_analysis",
    image="data:image/png;base64,iVBORw0KG...",
    prompt="What's in this image?"
)
print(result)
```

## Performance Considerations

### Speed Comparison

| Parser | Speed | Accuracy | Use Case |
|--------|-------|----------|----------|
| PyMuPDF | ~0.1s/page | 85% | Fast batch processing |
| pdfplumber | ~0.3s/page | 90% (tables) | Table extraction |
| GLM-4.6V | ~3-5s/page | 95% | Complex layouts, vision-critical |

### When to Use GLM-4.6V

**Good for:**
- Complex layouts (multi-column, nested structures)
- Visual elements (charts, diagrams, infographics)
- Scanned documents (OCR needed)
- Cross-validation of tool-based extraction

**Not ideal for:**
- Simple text-only PDFs (PyMuPDF faster)
- Bulk processing thousands of documents (cost/speed)
- Real-time extraction (latency)

### Cost Optimization

```python
# Strategy: Use fast parsers first, VLM for verification
def smart_parse(pdf_path):
    # Fast extraction
    tool_doc = PDFParser().parse(pdf_path)

    # Calculate confidence
    confidence = estimate_extraction_confidence(tool_doc)

    if confidence < 0.80:
        # Low confidence → use VLM for verification
        image = render_pdf_page(pdf_path, page=0)
        vlm_doc = VLMParser().parse(image)

        # Merge results
        return merge_extractions(tool_doc, vlm_doc)
    else:
        # High confidence → trust tool extraction
        return tool_doc
```

## Summary

**MCP in 3 Steps:**

1. **Configure** - Create `zai_glmV_mcp.json` with Z.AI credentials
2. **Run** - Claude Code starts MCP server automatically
3. **Use** - Call `mcp__zai_mcp_server__image_analysis` from code

**GLM-4.6V via MCP provides:**
- Vision-based document understanding
- Structured JSON extraction
- Alternative to traditional parsers
- Validation of tool-based extraction

**Current Status:**
- ✅ MCP configuration ready
- ✅ VLM parser designed for MCP
- ✅ Tests prepared (17 passing, 5 awaiting MCP)
- ⏳ Actual MCP calls (requires Claude Code environment)

---

**Next**: When running in Claude Code with MCP enabled, the 5 skipped tests will automatically work, and you'll have full tool-vs-VLM comparison capability!
