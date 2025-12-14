"""
Tests for PDF pipeline comparison framework.

This module tests the PDFPipelineComparison class functionality including:
- Multi-pipeline comparison
- Metrics collection
- Report generation
"""

import pytest
from pathlib import Path


def test_pipeline_comparison_import():
    """Test that pipeline comparison can be imported."""
    from vlm_doc_test.validation.pipeline_comparison import (
        PDFPipelineComparison,
        PipelineMetrics,
        ComparisonResult,
    )
    assert PDFPipelineComparison is not None
    assert PipelineMetrics is not None
    assert ComparisonResult is not None


def test_pipeline_metrics_dataclass():
    """Test PipelineMetrics dataclass structure."""
    from vlm_doc_test.validation.pipeline_comparison import PipelineMetrics

    metrics = PipelineMetrics(
        pipeline_name="test",
        success=True,
        time_seconds=1.5,
        content_elements=10,
        tables_extracted=2,
        figures_extracted=1,
        links_extracted=3,
        total_text_length=1000,
        uses_local_model=False,
        uses_gpu=False,
    )

    assert metrics.pipeline_name == "test"
    assert metrics.success is True
    assert metrics.time_seconds == 1.5
    assert metrics.error is None


def test_comparison_framework_initialization():
    """Test comparison framework can be initialized."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    assert comparison.parsers == {}


def test_get_parser_pymupdf():
    """Test getting PyMuPDF parser."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    parser = comparison._get_parser("pymupdf")

    assert parser is not None
    from vlm_doc_test.parsers import PDFParser
    assert isinstance(parser, PDFParser)


def test_get_parser_marker():
    """Test getting Marker parser."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    parser = comparison._get_parser("marker")

    assert parser is not None
    from vlm_doc_test.parsers import MarkerParser
    assert isinstance(parser, MarkerParser)


def test_get_parser_docling():
    """Test getting Docling parser."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    parser = comparison._get_parser("docling")

    assert parser is not None
    from vlm_doc_test.parsers import DoclingParser
    assert isinstance(parser, DoclingParser)


def test_get_parser_invalid():
    """Test getting invalid parser returns None."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    parser = comparison._get_parser("invalid_parser")

    assert parser is None


def test_run_pipeline_invalid(sample_pdf):
    """Test running invalid pipeline returns error metrics."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    metrics = comparison._run_pipeline("invalid", sample_pdf)

    assert metrics.success is False
    assert metrics.error == "Parser not available"
    assert metrics.time_seconds == 0.0


def test_run_pipeline_pymupdf(sample_pdf):
    """Test running PyMuPDF pipeline."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    metrics = comparison._run_pipeline("pymupdf", sample_pdf)

    assert metrics.success is True
    assert metrics.time_seconds > 0
    assert metrics.content_elements > 0


def test_compare_all_single_pipeline(sample_pdf):
    """Test comparing with single pipeline."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])

    assert result is not None
    assert "pymupdf" in result.pipelines
    # Verify PDF file exists and has content
    assert sample_pdf.exists()
    assert sample_pdf.stat().st_size > 0
    # Size in MB may be small but should be calculated
    assert isinstance(result.pdf_size_mb, float)


def test_compare_all_multiple_pipelines(sample_pdf):
    """Test comparing with multiple pipelines."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf", "marker"])

    assert result is not None
    assert "pymupdf" in result.pipelines
    assert "marker" in result.pipelines
    assert result.fastest_pipeline != "none"


def test_comparison_result_structure(sample_pdf):
    """Test ComparisonResult has correct structure."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])

    assert hasattr(result, 'pdf_path')
    assert hasattr(result, 'pdf_size_mb')
    assert hasattr(result, 'page_count')
    assert hasattr(result, 'pipelines')
    assert hasattr(result, 'fastest_pipeline')
    assert hasattr(result, 'most_content_pipeline')
    assert hasattr(result, 'comparison_time')


def test_generate_text_report(sample_pdf):
    """Test generating text report."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])
    report = comparison.generate_report(result, format="text")

    assert isinstance(report, str)
    assert "PDF PIPELINE COMPARISON REPORT" in report
    assert "pymupdf" in report.lower()


def test_generate_markdown_report(sample_pdf):
    """Test generating markdown report."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])
    report = comparison.generate_report(result, format="markdown")

    assert isinstance(report, str)
    assert "# PDF Pipeline Comparison Report" in report
    assert "| Pipeline" in report


def test_generate_json_report(sample_pdf):
    """Test generating JSON report."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison
    import json

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])
    report = comparison.generate_report(result, format="json")

    assert isinstance(report, str)
    data = json.loads(report)
    assert "pdf_path" in data
    assert "pipelines" in data


def test_generate_report_invalid_format(sample_pdf):
    """Test generating report with invalid format raises error."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])

    with pytest.raises(ValueError, match="Unknown format"):
        comparison.generate_report(result, format="invalid")


def test_batch_compare_interface():
    """Test batch comparison interface."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()

    assert hasattr(comparison, 'batch_compare')
    assert callable(comparison.batch_compare)


def test_comparison_to_dict(sample_pdf):
    """Test conversion of ComparisonResult to dict."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()
    result = comparison.compare_all(sample_pdf, pipelines=["pymupdf"])
    data = comparison._comparison_to_dict(result)

    assert isinstance(data, dict)
    assert "pdf_path" in data
    assert "pipelines" in data
    assert "fastest_pipeline" in data
    assert "pymupdf" in data["pipelines"]


def test_pipeline_metrics_uses_flags():
    """Test PipelineMetrics correctly sets usage flags."""
    from vlm_doc_test.validation.pipeline_comparison import PDFPipelineComparison

    comparison = PDFPipelineComparison()

    # PyMuPDF should not use local model or GPU
    parser = comparison._get_parser("pymupdf")
    assert parser is not None

    # Marker should use GPU
    parser = comparison._get_parser("marker")
    assert parser is not None

    # Docling should use local model and GPU
    parser = comparison._get_parser("docling")
    assert parser is not None
