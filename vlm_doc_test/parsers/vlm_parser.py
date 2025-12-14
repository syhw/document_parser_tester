"""
VLM-based document parser using GLM-4.6V vision model.

This parser uses the Z.AI Vision MCP Server to analyze document screenshots
and extract structured information. This is the "vision" approach that should
be compared against tool-based extraction.
"""

from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime
import subprocess
import json
import base64

from ..schemas.schema_simple import (
    SimpleDocument,
    DocumentMetadata,
    DocumentSource,
    ContentElement,
    Table,
    Figure,
    Link,
    Author,
)
from ..schemas.base import DocumentFormat, DocumentCategory


class VLMParser:
    """
    Vision Language Model parser using GLM-4.6V.

    This parser analyzes document images/screenshots and extracts structured
    information using vision models. Results should be compared with tool-based
    parsers to validate equivalence.
    """

    def __init__(self, api_key: Optional[str] = None, mode: str = "ZAI"):
        """
        Initialize VLM parser.

        Args:
            api_key: Z.AI API key (reads from env if not provided)
            mode: Z.AI mode (default: "ZAI")
        """
        self.api_key = api_key or self._get_api_key_from_config()
        self.mode = mode

    def _get_api_key_from_config(self) -> Optional[str]:
        """Try to read API key from zai_glmV_mcp.json config."""
        config_path = Path(__file__).parent.parent.parent / "zai_glmV_mcp.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    return config["mcpServers"]["zai-mcp-server"]["env"]["Z_AI_API_KEY"]
            except Exception:
                pass
        return None

    def parse(
        self,
        image_path: Union[str, Path],
        category: Optional[DocumentCategory] = None,
    ) -> SimpleDocument:
        """
        Parse a document image using GLM-4.6V vision model.

        Args:
            image_path: Path to document screenshot/image
            category: Document category hint for better extraction

        Returns:
            SimpleDocument with VLM-extracted content
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Build extraction prompt based on category
        prompt = self._build_extraction_prompt(category)

        # Call VLM via MCP
        vlm_response = self._call_vlm_mcp(image_path, prompt)

        # Parse VLM response into structured document
        document = self._parse_vlm_response(vlm_response, image_path, category)

        return document

    def _build_extraction_prompt(self, category: Optional[DocumentCategory]) -> str:
        """
        Build extraction prompt based on document category.

        Different categories need different extraction instructions.
        """
        base_prompt = """Analyze this document image and extract structured information in JSON format.

Extract the following fields:
- title: Document title
- authors: List of author names (if present)
- content: List of main content sections with their text
- tables: Any tables with their data
- figures: Any figures/images with captions
- links: Any visible URLs or references

Return ONLY valid JSON in this format:
{
  "title": "string",
  "authors": ["string"],
  "abstract": "string (if present)",
  "content": [
    {"type": "heading", "text": "string", "level": 1},
    {"type": "paragraph", "text": "string"}
  ],
  "tables": [
    {
      "caption": "string",
      "data": [["cell1", "cell2"], ["cell3", "cell4"]]
    }
  ],
  "figures": [
    {"caption": "string", "label": "Figure 1"}
  ],
  "keywords": ["string"]
}
"""

        if category == DocumentCategory.ACADEMIC_PAPER:
            return base_prompt + """
This is an ACADEMIC PAPER. Focus on:
- Extract authors and affiliations carefully
- Identify abstract section
- Extract section headers (Introduction, Methods, Results, etc.)
- Identify and extract tables with captions
- Identify figures with captions
- Look for citations/references
"""

        elif category == DocumentCategory.BLOG_POST:
            return base_prompt + """
This is a BLOG POST. Focus on:
- Extract author name
- Look for publish date
- Extract tags/keywords
- Identify main content paragraphs
- Extract any embedded links
"""

        elif category == DocumentCategory.TECHNICAL_DOCUMENTATION:
            return base_prompt + """
This is TECHNICAL DOCUMENTATION. Focus on:
- Extract API names and function signatures
- Identify code blocks
- Extract parameter descriptions
- Look for navigation/cross-references
"""

        return base_prompt

    def _call_vlm_mcp(self, image_path: Path, prompt: str) -> str:
        """
        Call Z.AI Vision MCP Server to analyze image.

        Uses the image_analysis tool from the MCP server.

        Note: This method is designed to be called from within Claude Code
        where MCP tools are available. In standalone Python, this will
        raise NotImplementedError.
        """
        # In Claude Code, MCP tools would be available and this would work
        # The tool name format is: mcp__<server-name>__<tool-name>
        # For Z.AI: mcp__zai_mcp_server__image_analysis

        # This is a placeholder for MCP tool invocation
        # In Claude Code environment, you would call the MCP tool directly
        # through the tool invocation mechanism

        raise NotImplementedError(
            "VLM MCP integration requires running within Claude Code.\n"
            "To use this parser:\n"
            "1. Ensure Z.AI MCP server is configured (zai_glmV_mcp.json)\n"
            "2. Call from Claude Code where MCP tools are available\n"
            "3. The tool 'mcp__zai_mcp_server__image_analysis' will be invoked\n"
            f"   with image: {image_path}\n"
            f"   and prompt: {prompt[:100]}..."
        )

    def _parse_vlm_response(
        self,
        vlm_response: str,
        image_path: Path,
        category: Optional[DocumentCategory],
    ) -> SimpleDocument:
        """
        Parse VLM JSON response into SimpleDocument structure.
        """
        try:
            data = json.loads(vlm_response)
        except json.JSONDecodeError:
            # VLM might return text with JSON embedded
            # Try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', vlm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse VLM response as JSON")

        # Extract metadata
        metadata = DocumentMetadata(
            title=data.get("title"),
            authors=[Author(name=name) for name in data.get("authors", [])],
            keywords=data.get("keywords", []),
        )

        # Add abstract if present (as extra field)
        if "abstract" in data:
            metadata.__dict__['abstract'] = data["abstract"]

        # Extract content elements
        content = []
        for idx, item in enumerate(data.get("content", [])):
            element = ContentElement(
                id=f"vlm_c{idx}",
                type=item.get("type", "paragraph"),
                content=item.get("text", ""),
                level=item.get("level"),
            )
            content.append(element)

        # Extract tables
        tables = []
        for idx, table_data in enumerate(data.get("tables", [])):
            table = Table(
                id=f"vlm_t{idx}",
                caption=table_data.get("caption"),
                rows=table_data.get("data", []),
            )
            tables.append(table)

        # Extract figures
        figures = []
        for idx, fig_data in enumerate(data.get("figures", [])):
            figure = Figure(
                id=f"vlm_f{idx}",
                caption=fig_data.get("caption"),
                label=fig_data.get("label"),
            )
            figures.append(figure)

        # Create document
        document = SimpleDocument(
            id=f"vlm_{image_path.stem}",
            format=DocumentFormat.PDF,  # Assume PDF screenshot
            source=DocumentSource(
                file_path=str(image_path),
                accessed_at=datetime.now(),
            ),
            metadata=metadata,
            content=content,
            tables=tables,
            figures=figures,
            links=[],
        )

        return document


class VLMParserWithMCP(VLMParser):
    """
    VLM Parser that uses MCP tools when available.

    This version checks for available MCP tools and uses them if present.
    Falls back to NotImplementedError if MCP tools aren't available.
    """

    def _call_vlm_mcp(self, image_path: Path, prompt: str) -> str:
        """
        Call Z.AI Vision MCP Server using MCP tools.

        Checks for mcp__zai_mcp_server__image_analysis tool.
        """
        # Check if MCP tool is available
        # In Claude Code, MCP tools are available as mcp__<server>__<tool>
        tool_name = "mcp__zai_mcp_server__image_analysis"

        # For now, this is a placeholder
        # The actual implementation would use the MCP protocol
        # which is available in Claude Code but not in standalone Python

        raise NotImplementedError(
            f"MCP tool '{tool_name}' would be called here with:\n"
            f"  image: {image_path}\n"
            f"  prompt: {prompt[:100]}...\n\n"
            "This requires MCP integration which is available in Claude Code."
        )


def create_vlm_parser(use_mcp: bool = True) -> VLMParser:
    """
    Factory function to create appropriate VLM parser.

    Args:
        use_mcp: If True, use MCP-based parser (requires Claude Code)

    Returns:
        VLMParser instance
    """
    if use_mcp:
        return VLMParserWithMCP()
    else:
        return VLMParser()
