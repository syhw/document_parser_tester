"""
Enhanced validation reporting framework.

Provides detailed, structured reports for document comparison results
with support for multiple output formats (text, JSON, HTML).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

from .equivalence import ComparisonResult, MatchQuality
from .visual_regression import VisualComparisonResult


class ReportFormat(str, Enum):
    """Report output formats."""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    test_name: str
    timestamp: datetime
    comparison_results: List[ComparisonResult] = field(default_factory=list)
    visual_results: List[VisualComparisonResult] = field(default_factory=list)
    passed: bool = True
    summary: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_comparison(self, result: ComparisonResult):
        """Add a comparison result to the report."""
        self.comparison_results.append(result)
        if result.match_quality in [MatchQuality.POOR, MatchQuality.FAILED]:
            self.passed = False

    def add_visual_comparison(self, result: VisualComparisonResult):
        """Add a visual comparison result to the report."""
        self.visual_results.append(result)
        if not result.passed:
            self.passed = False

    def calculate_summary(self):
        """Calculate summary statistics."""
        self.summary = {
            "total_comparisons": len(self.comparison_results),
            "total_visual_comparisons": len(self.visual_results),
            "passed": self.passed,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.comparison_results:
            scores = [r.score for r in self.comparison_results]
            self.summary["avg_score"] = sum(scores) / len(scores)
            self.summary["min_score"] = min(scores)
            self.summary["max_score"] = max(scores)

            quality_counts = {}
            for result in self.comparison_results:
                q = result.match_quality.value
                quality_counts[q] = quality_counts.get(q, 0) + 1
            self.summary["quality_distribution"] = quality_counts

        if self.visual_results:
            ssim_scores = [r.similarity_score for r in self.visual_results]
            self.summary["avg_visual_similarity"] = sum(ssim_scores) / len(ssim_scores)
            self.summary["visual_pass_rate"] = sum(
                1 for r in self.visual_results if r.passed
            ) / len(self.visual_results)


class ValidationReporter:
    """
    Enhanced validation reporter with multiple output formats.

    Generates detailed reports for document validation results.
    """

    def __init__(self):
        """Initialize reporter."""
        self.current_report: Optional[ValidationReport] = None

    def start_report(self, test_name: str) -> ValidationReport:
        """
        Start a new validation report.

        Args:
            test_name: Name of the test

        Returns:
            ValidationReport instance
        """
        self.current_report = ValidationReport(
            test_name=test_name,
            timestamp=datetime.now(),
        )
        return self.current_report

    def finalize_report(self, report: Optional[ValidationReport] = None) -> ValidationReport:
        """
        Finalize report by calculating summary.

        Args:
            report: Report to finalize (uses current_report if not provided)

        Returns:
            Finalized report
        """
        if report is None:
            report = self.current_report

        if report is None:
            raise ValueError("No report to finalize")

        report.calculate_summary()
        return report

    def generate_text_report(self, report: ValidationReport) -> str:
        """Generate text-format report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"Validation Report: {report.test_name}")
        lines.append("=" * 70)
        lines.append(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Overall Result: {'✅ PASSED' if report.passed else '❌ FAILED'}")
        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append("-" * 70)
        if "total_comparisons" in report.summary:
            lines.append(f"  Total Comparisons: {report.summary['total_comparisons']}")
        if "avg_score" in report.summary:
            lines.append(f"  Average Score: {report.summary['avg_score']:.2%}")
            lines.append(f"  Min Score: {report.summary['min_score']:.2%}")
            lines.append(f"  Max Score: {report.summary['max_score']:.2%}")
        if "quality_distribution" in report.summary:
            lines.append("  Quality Distribution:")
            for quality, count in report.summary['quality_distribution'].items():
                lines.append(f"    {quality}: {count}")
        lines.append("")

        # Visual comparisons
        if report.visual_results:
            lines.append("Visual Regression:")
            lines.append("-" * 70)
            lines.append(f"  Total Visual Tests: {report.summary['total_visual_comparisons']}")
            lines.append(f"  Pass Rate: {report.summary['visual_pass_rate']:.2%}")
            lines.append(f"  Avg SSIM: {report.summary['avg_visual_similarity']:.4f}")
            lines.append("")

        # Detailed results
        if report.comparison_results:
            lines.append("Detailed Comparison Results:")
            lines.append("-" * 70)
            for idx, result in enumerate(report.comparison_results, 1):
                lines.append(f"  {idx}. Quality: {result.match_quality.value.upper()}, Score: {result.score:.2%}")
                if result.warnings:
                    for warning in result.warnings:
                        lines.append(f"     ⚠️  {warning}")
            lines.append("")

        # Errors and warnings
        if report.errors:
            lines.append("Errors:")
            lines.append("-" * 70)
            for error in report.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")

        if report.warnings:
            lines.append("Warnings:")
            lines.append("-" * 70)
            for warning in report.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def generate_json_report(self, report: ValidationReport) -> str:
        """Generate JSON-format report."""
        data = {
            "test_name": report.test_name,
            "timestamp": report.timestamp.isoformat(),
            "passed": report.passed,
            "summary": report.summary,
            "errors": report.errors,
            "warnings": report.warnings,
            "comparisons": [
                {
                    "match_quality": r.match_quality.value,
                    "score": r.score,
                    "details": r.details,
                    "differences": r.differences,
                    "warnings": r.warnings,
                }
                for r in report.comparison_results
            ],
            "visual_comparisons": [
                {
                    "similarity_score": r.similarity_score,
                    "pixel_diff_percentage": r.diff_percentage,
                    "passed": r.passed,
                    "details": r.details,
                }
                for r in report.visual_results
            ],
        }

        return json.dumps(data, indent=2)

    def generate_markdown_report(self, report: ValidationReport) -> str:
        """Generate Markdown-format report."""
        lines = []
        lines.append(f"# Validation Report: {report.test_name}")
        lines.append("")
        lines.append(f"**Timestamp:** {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Result:** {'✅ PASSED' if report.passed else '❌ FAILED'}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        if "total_comparisons" in report.summary:
            lines.append(f"- **Total Comparisons:** {report.summary['total_comparisons']}")
        if "avg_score" in report.summary:
            lines.append(f"- **Average Score:** {report.summary['avg_score']:.2%}")
            lines.append(f"- **Score Range:** {report.summary['min_score']:.2%} - {report.summary['max_score']:.2%}")
        lines.append("")

        # Quality distribution table
        if "quality_distribution" in report.summary:
            lines.append("### Quality Distribution")
            lines.append("")
            lines.append("| Quality | Count |")
            lines.append("|---------|-------|")
            for quality, count in report.summary['quality_distribution'].items():
                lines.append(f"| {quality} | {count} |")
            lines.append("")

        # Visual regression
        if report.visual_results:
            lines.append("## Visual Regression")
            lines.append("")
            lines.append(f"- **Total Visual Tests:** {report.summary['total_visual_comparisons']}")
            lines.append(f"- **Pass Rate:** {report.summary['visual_pass_rate']:.2%}")
            lines.append(f"- **Average SSIM:** {report.summary['avg_visual_similarity']:.4f}")
            lines.append("")

        # Errors and warnings
        if report.errors:
            lines.append("## Errors")
            lines.append("")
            for error in report.errors:
                lines.append(f"- ❌ {error}")
            lines.append("")

        if report.warnings:
            lines.append("## Warnings")
            lines.append("")
            for warning in report.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

        return "\n".join(lines)

    def save_report(
        self,
        report: ValidationReport,
        output_path: Path,
        format: ReportFormat = ReportFormat.TEXT,
    ):
        """
        Save report to file.

        Args:
            report: Report to save
            output_path: Output file path
            format: Report format
        """
        if format == ReportFormat.TEXT:
            content = self.generate_text_report(report)
        elif format == ReportFormat.JSON:
            content = self.generate_json_report(report)
        elif format == ReportFormat.MARKDOWN:
            content = self.generate_markdown_report(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

        output_path.write_text(content, encoding='utf-8')
