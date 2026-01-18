"""
PDF Pipeline Comparison Framework.

This module provides a unified interface for comparing different PDF extraction
pipelines: PyMuPDF, pdfplumber, Marker-PDF, Docling+VLM, and remote VLM APIs.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import time

from ..schemas.schema_simple import SimpleDocument
from ..parsers import PDFParser, MarkerParser, DoclingParser


@dataclass
class PipelineMetrics:
    """Metrics for a PDF extraction pipeline."""
    pipeline_name: str
    success: bool
    time_seconds: float
    content_elements: int
    tables_extracted: int
    figures_extracted: int
    links_extracted: int
    total_text_length: int
    uses_local_model: bool
    uses_gpu: bool
    error: Optional[str] = None


@dataclass
class ComparisonResult:
    """Results from comparing multiple pipelines."""
    pdf_path: str
    pdf_size_mb: float
    page_count: Optional[int]
    pipelines: Dict[str, PipelineMetrics]
    fastest_pipeline: str
    most_content_pipeline: str
    comparison_time: datetime


class PDFPipelineComparison:
    """
    Compare different PDF extraction pipelines.

    Supported pipelines:
    1. PyMuPDF (fitz) - Fast, coordinate-aware
    2. pdfplumber - Table-focused
    3. Marker-PDF - High-fidelity markdown
    4. Docling+Granite Vision - Local VLM
    5. GLM-4.6V API - Remote VLM (optional)
    """

    def __init__(self):
        """Initialize comparison framework."""
        self.parsers = {}

    def _get_parser(self, pipeline: str):
        """Get or create parser for pipeline."""
        if pipeline not in self.parsers:
            if pipeline == "pymupdf":
                self.parsers[pipeline] = PDFParser()
            elif pipeline == "marker":
                self.parsers[pipeline] = MarkerParser()
            elif pipeline == "docling":
                self.parsers[pipeline] = DoclingParser()

        return self.parsers.get(pipeline)

    def compare_all(
        self,
        pdf_path: Path,
        pipelines: Optional[List[str]] = None,
    ) -> ComparisonResult:
        """
        Compare all available pipelines on a PDF.

        Args:
            pdf_path: Path to PDF file
            pipelines: List of pipelines to test (None = all)

        Returns:
            ComparisonResult with metrics
        """
        if pipelines is None:
            pipelines = ["pymupdf", "marker", "docling"]

        # Get PDF info
        pdf_size_bytes = pdf_path.stat().st_size
        pdf_size_mb = pdf_size_bytes / (1024 * 1024)

        # Get page count from PyMuPDF
        page_count = None
        try:
            import fitz
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            # PDF may be corrupted, password-protected, or inaccessible
            pass

        # Run each pipeline
        results = {}
        for pipeline_name in pipelines:
            metrics = self._run_pipeline(pipeline_name, pdf_path)
            results[pipeline_name] = metrics

        # Find fastest and most content
        successful_pipelines = {k: v for k, v in results.items() if v.success}

        if successful_pipelines:
            fastest = min(successful_pipelines.items(), key=lambda x: x[1].time_seconds)
            most_content = max(successful_pipelines.items(), key=lambda x: x[1].total_text_length)
            fastest_name = fastest[0]
            most_content_name = most_content[0]
        else:
            fastest_name = "none"
            most_content_name = "none"

        return ComparisonResult(
            pdf_path=str(pdf_path),
            pdf_size_mb=round(pdf_size_mb, 2),
            page_count=page_count,
            pipelines=results,
            fastest_pipeline=fastest_name,
            most_content_pipeline=most_content_name,
            comparison_time=datetime.now(),
        )

    def _run_pipeline(
        self,
        pipeline_name: str,
        pdf_path: Path,
    ) -> PipelineMetrics:
        """Run a single pipeline and collect metrics."""
        parser = self._get_parser(pipeline_name)

        if parser is None:
            return PipelineMetrics(
                pipeline_name=pipeline_name,
                success=False,
                time_seconds=0.0,
                content_elements=0,
                tables_extracted=0,
                figures_extracted=0,
                links_extracted=0,
                total_text_length=0,
                uses_local_model=False,
                uses_gpu=False,
                error="Parser not available",
            )

        try:
            # Time the extraction
            start = time.time()
            document = parser.parse(pdf_path)
            elapsed = time.time() - start

            # Collect metrics
            metrics = PipelineMetrics(
                pipeline_name=pipeline_name,
                success=True,
                time_seconds=round(elapsed, 3),
                content_elements=len(document.content),
                tables_extracted=len(document.tables),
                figures_extracted=len(document.figures),
                links_extracted=len(document.links),
                total_text_length=sum(len(e.content) for e in document.content),
                uses_local_model=pipeline_name == "docling",
                uses_gpu=pipeline_name in ["marker", "docling"],
            )

            return metrics

        except Exception as e:
            return PipelineMetrics(
                pipeline_name=pipeline_name,
                success=False,
                time_seconds=0.0,
                content_elements=0,
                tables_extracted=0,
                figures_extracted=0,
                links_extracted=0,
                total_text_length=0,
                uses_local_model=False,
                uses_gpu=False,
                error=str(e),
            )

    def generate_report(
        self,
        result: ComparisonResult,
        format: str = "text",
    ) -> str:
        """
        Generate comparison report.

        Args:
            result: Comparison result
            format: Report format ("text", "markdown", "json")

        Returns:
            Formatted report
        """
        if format == "text":
            return self._generate_text_report(result)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        elif format == "json":
            import json
            return json.dumps(self._comparison_to_dict(result), indent=2)
        else:
            raise ValueError(f"Unknown format: {format}")

    def _generate_text_report(self, result: ComparisonResult) -> str:
        """Generate plain text report."""
        lines = []
        lines.append("="*70)
        lines.append("PDF PIPELINE COMPARISON REPORT")
        lines.append("="*70)
        lines.append(f"\nPDF: {result.pdf_path}")
        lines.append(f"Size: {result.pdf_size_mb} MB")
        if result.page_count:
            lines.append(f"Pages: {result.page_count}")
        lines.append(f"Tested: {result.comparison_time.strftime('%Y-%m-%d %H:%M:%S')}")

        lines.append("\n" + "-"*70)
        lines.append("PIPELINE RESULTS")
        lines.append("-"*70)

        for pipeline_name, metrics in result.pipelines.items():
            lines.append(f"\n{pipeline_name.upper()}:")
            if metrics.success:
                lines.append(f"  ✓ Success")
                lines.append(f"  Time: {metrics.time_seconds}s")
                lines.append(f"  Content Elements: {metrics.content_elements}")
                lines.append(f"  Tables: {metrics.tables_extracted}")
                lines.append(f"  Figures: {metrics.figures_extracted}")
                lines.append(f"  Links: {metrics.links_extracted}")
                lines.append(f"  Total Text: {metrics.total_text_length} chars")
                lines.append(f"  Local Model: {'Yes' if metrics.uses_local_model else 'No'}")
                lines.append(f"  GPU: {'Yes' if metrics.uses_gpu else 'No'}")
            else:
                lines.append(f"  ✗ Failed: {metrics.error}")

        lines.append("\n" + "-"*70)
        lines.append("SUMMARY")
        lines.append("-"*70)
        lines.append(f"Fastest Pipeline: {result.fastest_pipeline}")
        lines.append(f"Most Content: {result.most_content_pipeline}")

        if result.fastest_pipeline in result.pipelines:
            fastest_time = result.pipelines[result.fastest_pipeline].time_seconds
            lines.append(f"Best Time: {fastest_time}s")

        lines.append("="*70)

        return "\n".join(lines)

    def _generate_markdown_report(self, result: ComparisonResult) -> str:
        """Generate markdown report."""
        lines = []
        lines.append("# PDF Pipeline Comparison Report\n")
        lines.append(f"**PDF:** `{result.pdf_path}`  ")
        lines.append(f"**Size:** {result.pdf_size_mb} MB  ")
        if result.page_count:
            lines.append(f"**Pages:** {result.page_count}  ")
        lines.append(f"**Tested:** {result.comparison_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

        lines.append("## Pipeline Results\n")
        lines.append("| Pipeline | Status | Time (s) | Content | Tables | Figures | Text Length |")
        lines.append("|----------|--------|----------|---------|--------|---------|-------------|")

        for pipeline_name, metrics in result.pipelines.items():
            status = "✓" if metrics.success else "✗"
            time_str = f"{metrics.time_seconds}" if metrics.success else "-"
            content_str = str(metrics.content_elements) if metrics.success else "-"
            tables_str = str(metrics.tables_extracted) if metrics.success else "-"
            figures_str = str(metrics.figures_extracted) if metrics.success else "-"
            text_str = str(metrics.total_text_length) if metrics.success else "-"

            lines.append(f"| {pipeline_name} | {status} | {time_str} | {content_str} | {tables_str} | {figures_str} | {text_str} |")

        lines.append("\n## Summary\n")
        lines.append(f"- **Fastest Pipeline:** {result.fastest_pipeline}")
        lines.append(f"- **Most Content:** {result.most_content_pipeline}")

        return "\n".join(lines)

    def _comparison_to_dict(self, result: ComparisonResult) -> Dict[str, Any]:
        """Convert comparison result to dictionary."""
        return {
            "pdf_path": result.pdf_path,
            "pdf_size_mb": result.pdf_size_mb,
            "page_count": result.page_count,
            "pipelines": {
                name: {
                    "success": m.success,
                    "time_seconds": m.time_seconds,
                    "content_elements": m.content_elements,
                    "tables_extracted": m.tables_extracted,
                    "figures_extracted": m.figures_extracted,
                    "links_extracted": m.links_extracted,
                    "total_text_length": m.total_text_length,
                    "uses_local_model": m.uses_local_model,
                    "uses_gpu": m.uses_gpu,
                    "error": m.error,
                }
                for name, m in result.pipelines.items()
            },
            "fastest_pipeline": result.fastest_pipeline,
            "most_content_pipeline": result.most_content_pipeline,
            "comparison_time": result.comparison_time.isoformat(),
        }

    def batch_compare(
        self,
        pdf_paths: List[Path],
        output_dir: Path,
        pipelines: Optional[List[str]] = None,
    ) -> List[ComparisonResult]:
        """
        Compare multiple PDFs across pipelines.

        Args:
            pdf_paths: List of PDF paths
            output_dir: Directory to save reports
            pipelines: List of pipelines to test

        Returns:
            List of comparison results
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for pdf_path in pdf_paths:
            result = self.compare_all(pdf_path, pipelines)
            results.append(result)

            # Save individual report
            report_path = output_dir / f"{pdf_path.stem}_comparison.md"
            report = self.generate_report(result, format="markdown")
            report_path.write_text(report, encoding='utf-8')

        # Generate summary report
        summary_path = output_dir / "summary.md"
        summary = self._generate_batch_summary(results)
        summary_path.write_text(summary, encoding='utf-8')

        return results

    def _generate_batch_summary(self, results: List[ComparisonResult]) -> str:
        """Generate summary for batch comparison."""
        lines = []
        lines.append("# Batch PDF Pipeline Comparison Summary\n")
        lines.append(f"**Total PDFs Tested:** {len(results)}\n")

        # Count wins per pipeline
        pipeline_wins = {}
        for result in results:
            fastest = result.fastest_pipeline
            pipeline_wins[fastest] = pipeline_wins.get(fastest, 0) + 1

        lines.append("## Fastest Pipeline Count\n")
        for pipeline, count in sorted(pipeline_wins.items(), key=lambda x: -x[1]):
            lines.append(f"- **{pipeline}:** {count} PDFs")

        lines.append("\n## Individual Results\n")
        for result in results:
            lines.append(f"### {Path(result.pdf_path).name}")
            lines.append(f"- Size: {result.pdf_size_mb} MB")
            lines.append(f"- Fastest: {result.fastest_pipeline}")
            if result.fastest_pipeline in result.pipelines:
                time = result.pipelines[result.fastest_pipeline].time_seconds
                lines.append(f"- Best Time: {time}s")
            lines.append("")

        return "\n".join(lines)
