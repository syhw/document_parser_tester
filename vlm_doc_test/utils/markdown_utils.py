"""
Markdown parsing utilities for document extraction.

This module provides shared functions for converting markdown text
to structured ContentElement objects, used by multiple parsers.
"""

from typing import List, Optional

from ..schemas.schema_simple import ContentElement


def parse_markdown_to_content(
    markdown: str,
    id_prefix: str = "elem",
    merge_paragraphs: bool = True,
) -> List[ContentElement]:
    """
    Parse markdown text into structured content elements.

    Handles:
    - Heading levels (# through ######)
    - Paragraphs (consecutive non-heading lines)
    - Empty line handling

    Args:
        markdown: Markdown text to parse
        id_prefix: Prefix for element IDs (default: "elem")
        merge_paragraphs: If True, merge consecutive non-heading lines
                         into single paragraphs. If False, each line
                         becomes a separate paragraph.

    Returns:
        List of ContentElement objects with headings and paragraphs

    Example:
        >>> text = "# Title\\n\\nParagraph 1.\\nStill paragraph 1.\\n\\n## Section"
        >>> elements = parse_markdown_to_content(text)
        >>> len(elements)
        3
        >>> elements[0].type
        'heading'
        >>> elements[1].type
        'paragraph'
    """
    content = []
    lines = markdown.split('\n')
    element_id = 0

    if merge_paragraphs:
        # Accumulate consecutive lines into paragraphs
        current_paragraph: List[str] = []

        for line in lines:
            line = line.strip()

            if not line:
                # Empty line ends current paragraph
                if current_paragraph:
                    element_id += 1
                    content.append(ContentElement(
                        id=f"{id_prefix}_{element_id}",
                        type="paragraph",
                        content=" ".join(current_paragraph),
                    ))
                    current_paragraph = []
                continue

            if line.startswith('#'):
                # Heading - save pending paragraph first
                if current_paragraph:
                    element_id += 1
                    content.append(ContentElement(
                        id=f"{id_prefix}_{element_id}",
                        type="paragraph",
                        content=" ".join(current_paragraph),
                    ))
                    current_paragraph = []

                # Parse heading
                level = len(line) - len(line.lstrip('#'))
                heading_text = line.lstrip('#').strip()

                element_id += 1
                content.append(ContentElement(
                    id=f"{id_prefix}_{element_id}",
                    type="heading",
                    content=heading_text,
                    level=level,
                ))
            else:
                # Regular text - accumulate
                current_paragraph.append(line)

        # Add final paragraph
        if current_paragraph:
            element_id += 1
            content.append(ContentElement(
                id=f"{id_prefix}_{element_id}",
                type="paragraph",
                content=" ".join(current_paragraph),
            ))
    else:
        # Simple mode: each non-empty line is a separate element
        for line in lines:
            line = line.strip()
            if not line:
                continue

            element_id += 1

            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                text = line.lstrip('#').strip()
                content.append(ContentElement(
                    id=f"{id_prefix}_{element_id}",
                    type="heading",
                    content=text,
                    level=level,
                ))
            else:
                content.append(ContentElement(
                    id=f"{id_prefix}_{element_id}",
                    type="paragraph",
                    content=line,
                ))

    return content


def extract_title_from_markdown(markdown: str) -> Optional[str]:
    """
    Extract the first heading as the document title.

    Args:
        markdown: Markdown text

    Returns:
        Title string or None if no heading found
    """
    for line in markdown.split('\n'):
        line = line.strip()
        if line.startswith('#'):
            return line.lstrip('#').strip()
    return None


def count_headings_by_level(markdown: str) -> dict:
    """
    Count headings by level in markdown text.

    Args:
        markdown: Markdown text

    Returns:
        Dict mapping level (1-6) to count

    Example:
        >>> count_headings_by_level("# H1\\n## H2\\n## H2")
        {1: 1, 2: 2}
    """
    counts: dict = {}
    for line in markdown.split('\n'):
        line = line.strip()
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            if 1 <= level <= 6:
                counts[level] = counts.get(level, 0) + 1
    return counts
