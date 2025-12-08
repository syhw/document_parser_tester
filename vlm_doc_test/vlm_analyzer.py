"""
VLM-based document analyzer using Instructor.

This module uses vision-language models (VLMs) to analyze document images
and extract structured information, then validates the output against our
Pydantic schemas using Instructor.
"""

import instructor
from openai import OpenAI
from pathlib import Path
from typing import Optional, Union, List
import base64
from io import BytesIO
from PIL import Image

from .schemas.schema_simple import SimpleDocument, ContentElement, Figure, Table
from .schemas.base import DocumentFormat, DocumentCategory, BoundingBox
from .config import get_config


class VLMAnalyzer:
    """
    VLM-based document analyzer with Instructor integration.

    Uses vision-language models to analyze document images and extract
    structured information validated against Pydantic schemas.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize VLM analyzer.

        Args:
            api_key: API key (defaults to config)
            base_url: API base URL (defaults to config)
            model: Model name (defaults to config)
        """
        config = get_config()

        # Use provided values or fall back to config
        self.api_key = api_key or config.glm_api_key or config.openai_api_key
        self.base_url = base_url or config.glm_api_base or config.openai_api_base
        self.model = model or config.default_model

        if not self.api_key:
            raise ValueError(
                "No API key provided. Set GLM_API_KEY or OPENAI_API_KEY "
                "in environment or pass api_key parameter."
            )

        # Create OpenAI client (works with OpenAI-compatible APIs)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Patch with Instructor for structured outputs
        self.instructor_client = instructor.from_openai(self.client)

        self.config = config

    def _encode_image(self, image_path: Union[str, Path, Image.Image]) -> str:
        """
        Encode image to base64 for API.

        Args:
            image_path: Path to image file or PIL Image

        Returns:
            Base64-encoded image string
        """
        if isinstance(image_path, (str, Path)):
            with open(image_path, "rb") as f:
                image_data = f.read()
        elif isinstance(image_path, Image.Image):
            buffer = BytesIO()
            image_path.save(buffer, format="PNG")
            image_data = buffer.getvalue()
        else:
            raise TypeError(f"Unsupported image type: {type(image_path)}")

        return base64.b64encode(image_data).decode("utf-8")

    def analyze_document_image(
        self,
        image_path: Union[str, Path, Image.Image],
        document_id: str,
        category: Optional[DocumentCategory] = None,
        extract_bboxes: bool = False,
    ) -> SimpleDocument:
        """
        Analyze a document image using VLM and extract structured content.

        Args:
            image_path: Path to document image or PIL Image
            document_id: Unique identifier for the document
            category: Optional document category
            extract_bboxes: Whether to request bounding box coordinates (if supported)

        Returns:
            SimpleDocument with VLM-extracted content
        """
        # Encode image
        image_base64 = self._encode_image(image_path)

        # Create prompt for VLM
        prompt = self._create_analysis_prompt(extract_bboxes)

        # Use Instructor to get structured output
        try:
            # Note: This uses Instructor's response_model feature
            # The VLM output will be validated against SimpleDocument schema
            response = self.instructor_client.chat.completions.create(
                model=self.model,
                response_model=SimpleDocument,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Instructor automatically validates and returns SimpleDocument
            document = response

            # Update document ID and category if provided
            document.id = document_id
            if category:
                document.category = category

            return document

        except Exception as e:
            raise RuntimeError(f"VLM analysis failed: {e}") from e

    def _create_analysis_prompt(self, extract_bboxes: bool = False) -> str:
        """
        Create the analysis prompt for the VLM.

        Args:
            extract_bboxes: Whether to request bounding box information

        Returns:
            Prompt string
        """
        bbox_instruction = ""
        if extract_bboxes:
            bbox_instruction = (
                "\n\nFor each content element, figure, and table, provide bounding box "
                "coordinates (x, y, width, height) in pixels with the origin at the "
                "top-left corner of the image. Set page=1 for single-page images."
            )

        prompt = f"""Analyze this document image and extract structured information.

Extract the following:

1. **Metadata**:
   - Title (if present)
   - Authors (if present)
   - Date (if present)
   - Keywords (if identifiable)

2. **Content Elements**:
   - Identify all text blocks (headings and paragraphs)
   - For headings, classify the hierarchical level (1, 2, 3, etc.)
   - Preserve the reading order
   - Extract the actual text content

3. **Figures**:
   - Identify all images, charts, plots, diagrams
   - Extract captions if present
   - Note labels (e.g., "Figure 1")

4. **Tables**:
   - Identify all tables
   - Extract table data as rows of cells
   - Extract captions if present
   - Note labels (e.g., "Table 1")

5. **Links**:
   - Identify hyperlinks if visible
   - Extract link text and URL if readable
{bbox_instruction}

Provide the output in structured JSON format matching the schema.
Be precise and thorough. If information is not present, omit it or use empty values.
"""
        return prompt

    def extract_table_from_image(
        self,
        image_path: Union[str, Path, Image.Image],
        table_id: str = "table_1",
    ) -> Table:
        """
        Extract a single table from an image using VLM.

        This is useful for focused table extraction from cropped images.

        Args:
            image_path: Path to table image
            table_id: Identifier for the table

        Returns:
            Table object with extracted data
        """
        image_base64 = self._encode_image(image_path)

        prompt = """Extract the table from this image.

Return:
- All rows and columns as a 2D array
- Caption if present
- Label if present (e.g., "Table 1")
- Bounding box if the table is part of a larger image

Ensure all cells are accurately extracted, maintaining row and column structure.
Empty cells should be represented as empty strings.
"""

        try:
            response = self.instructor_client.chat.completions.create(
                model=self.model,
                response_model=Table,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            table = response
            table.id = table_id
            return table

        except Exception as e:
            raise RuntimeError(f"Table extraction failed: {e}") from e

    def validate_extraction(
        self,
        tool_document: SimpleDocument,
        vlm_document: SimpleDocument,
    ) -> dict:
        """
        Compare tool-based extraction with VLM-based extraction.

        This is a basic comparison - for detailed equivalence checking,
        use the validation module.

        Args:
            tool_document: Document from tool-based extraction (PyMuPDF, etc.)
            vlm_document: Document from VLM analysis

        Returns:
            Dictionary with comparison results
        """
        results = {
            "metadata_match": {},
            "content_counts": {},
            "differences": [],
        }

        # Compare metadata
        results["metadata_match"]["title"] = (
            tool_document.metadata.title == vlm_document.metadata.title
        )
        results["metadata_match"]["author_count"] = (
            len(tool_document.metadata.authors) == len(vlm_document.metadata.authors)
        )

        # Compare content counts
        results["content_counts"] = {
            "tool": {
                "total": len(tool_document.content),
                "headings": len([c for c in tool_document.content if c.type == "heading"]),
                "paragraphs": len([c for c in tool_document.content if c.type == "paragraph"]),
            },
            "vlm": {
                "total": len(vlm_document.content),
                "headings": len([c for c in vlm_document.content if c.type == "heading"]),
                "paragraphs": len([c for c in vlm_document.content if c.type == "paragraph"]),
            },
        }

        # Note differences
        if results["content_counts"]["tool"]["total"] != results["content_counts"]["vlm"]["total"]:
            results["differences"].append(
                f"Content element count mismatch: "
                f"{results['content_counts']['tool']['total']} (tool) vs "
                f"{results['content_counts']['vlm']['total']} (VLM)"
            )

        results["figures_match"] = len(tool_document.figures) == len(vlm_document.figures)
        results["tables_match"] = len(tool_document.tables) == len(vlm_document.tables)

        return results
