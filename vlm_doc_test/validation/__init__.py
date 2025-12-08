"""
Validation module for comparing document extractions.

This module provides tools for comparing tool-based extraction with VLM-based
extraction, using fuzzy matching and deep comparison algorithms.
"""

from .equivalence import EquivalenceChecker, ComparisonResult, MatchQuality
from .visual_regression import VisualRegressionTester, VisualComparisonResult
from .reporter import ValidationReporter, ValidationReport, ReportFormat

__all__ = [
    "EquivalenceChecker",
    "ComparisonResult",
    "MatchQuality",
    "VisualRegressionTester",
    "VisualComparisonResult",
    "ValidationReporter",
    "ValidationReport",
    "ReportFormat",
]
