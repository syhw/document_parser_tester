"""
Category-specific validators for document parsing.

This module provides validators that check if documents correctly extract
category-specific fields based on their semantic content type.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

from ..schemas.schema_simple import SimpleDocument


class ValidationSeverity(str, Enum):
    """Severity level for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    field: str
    severity: ValidationSeverity
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None


@dataclass
class ValidationResult:
    """Result of category validation."""
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    category: str

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class CategoryValidator:
    """Base class for category-specific validators."""

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings become errors
        """
        self.strict = strict

    def validate(self, document: SimpleDocument) -> ValidationResult:
        """
        Validate document against category requirements.

        Args:
            document: Document to validate

        Returns:
            ValidationResult with pass/fail and issues
        """
        raise NotImplementedError

    def _add_issue(
        self,
        issues: List[ValidationIssue],
        field: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        expected: Any = None,
        actual: Any = None,
    ):
        """Helper to add validation issue."""
        if self.strict and severity == ValidationSeverity.WARNING:
            severity = ValidationSeverity.ERROR

        issues.append(ValidationIssue(
            field=field,
            severity=severity,
            message=message,
            expected=expected,
            actual=actual,
        ))

    def _calculate_score(self, issues: List[ValidationIssue], total_checks: int) -> float:
        """Calculate validation score based on issues."""
        if total_checks == 0:
            return 1.0

        error_count = len([i for i in issues if i.severity == ValidationSeverity.ERROR])
        warning_count = len([i for i in issues if i.severity == ValidationSeverity.WARNING])

        # Errors count as 1.0, warnings as 0.5
        penalty = error_count + (warning_count * 0.5)
        score = max(0.0, 1.0 - (penalty / total_checks))

        return score


class AcademicPaperValidator(CategoryValidator):
    """
    Validator for academic papers.

    Checks for:
    - Title
    - Authors (at least one)
    - Abstract (optional but expected)
    - Section structure (Introduction, Methods, Results, etc.)
    - Figures with captions
    - Tables with captions
    - Citations/references
    """

    def validate(self, document: SimpleDocument) -> ValidationResult:
        issues = []
        total_checks = 7

        # 1. Title
        if not document.metadata.title or len(document.metadata.title.strip()) == 0:
            self._add_issue(
                issues, "metadata.title",
                "Academic papers must have a title",
                ValidationSeverity.ERROR
            )
        elif len(document.metadata.title) < 10:
            self._add_issue(
                issues, "metadata.title",
                "Title seems too short for an academic paper",
                ValidationSeverity.WARNING,
                expected=">= 10 chars",
                actual=len(document.metadata.title)
            )

        # 2. Authors
        if not document.metadata.authors or len(document.metadata.authors) == 0:
            self._add_issue(
                issues, "metadata.authors",
                "Academic papers should have at least one author",
                ValidationSeverity.WARNING  # WARNING not ERROR - author extraction is hard
            )

        # 3. Abstract
        abstract = getattr(document.metadata, 'abstract', None)
        if not abstract or len(abstract.strip()) == 0:
            self._add_issue(
                issues, "metadata.abstract",
                "Academic papers should have an abstract",
                ValidationSeverity.WARNING
            )
        elif len(abstract) < 50:
            self._add_issue(
                issues, "metadata.abstract",
                "Abstract seems too short",
                ValidationSeverity.WARNING,
                expected=">= 50 chars",
                actual=len(abstract)
            )

        # 4. Content structure
        if len(document.content) == 0:
            self._add_issue(
                issues, "content",
                "Academic papers must have content",
                ValidationSeverity.ERROR
            )

        # 5. Check for section-like structure
        content_text = " ".join(e.content.lower() for e in document.content if e.content)
        expected_sections = ["introduction", "method", "result", "conclusion", "abstract"]
        found_sections = [s for s in expected_sections if s in content_text]

        if len(found_sections) == 0:
            self._add_issue(
                issues, "content.structure",
                "No typical academic paper sections found (Introduction, Methods, Results, etc.)",
                ValidationSeverity.WARNING,
                expected="at least one section keyword",
                actual="none found"
            )

        # 6. Figures
        if len(document.figures) == 0:
            self._add_issue(
                issues, "figures",
                "Academic papers typically have figures",
                ValidationSeverity.INFO
            )

        # 7. Tables
        if len(document.tables) == 0:
            self._add_issue(
                issues, "tables",
                "Academic papers often have tables",
                ValidationSeverity.INFO
            )

        # Calculate score
        score = self._calculate_score(issues, total_checks)
        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            category="academic_paper"
        )


class BlogPostValidator(CategoryValidator):
    """
    Validator for blog posts.

    Checks for:
    - Title
    - Author (optional)
    - Publish date (optional)
    - Tags/keywords (optional)
    - Main content
    - Links (typically present)
    """

    def validate(self, document: SimpleDocument) -> ValidationResult:
        issues = []
        total_checks = 5

        # 1. Title
        if not document.metadata.title or len(document.metadata.title.strip()) == 0:
            self._add_issue(
                issues, "metadata.title",
                "Blog posts must have a title",
                ValidationSeverity.ERROR
            )

        # 2. Author
        if not document.metadata.authors or len(document.metadata.authors) == 0:
            self._add_issue(
                issues, "metadata.authors",
                "Blog posts typically have an author",
                ValidationSeverity.WARNING
            )

        # 3. Publish date
        publish_date = getattr(document.metadata, 'publish_date', None)
        if not publish_date:
            self._add_issue(
                issues, "metadata.publish_date",
                "Blog posts typically have a publish date",
                ValidationSeverity.WARNING
            )

        # 4. Content
        if len(document.content) == 0:
            self._add_issue(
                issues, "content",
                "Blog posts must have content",
                ValidationSeverity.ERROR
            )
        elif len(document.content) < 3:
            self._add_issue(
                issues, "content",
                "Blog post seems too short",
                ValidationSeverity.WARNING,
                expected=">= 3 paragraphs",
                actual=len(document.content)
            )

        # 5. Tags/keywords
        if not document.metadata.keywords or len(document.metadata.keywords) == 0:
            self._add_issue(
                issues, "metadata.keywords",
                "Blog posts often have tags/keywords",
                ValidationSeverity.INFO
            )

        # Calculate score
        score = self._calculate_score(issues, total_checks)
        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            category="blog_post"
        )


class TechnicalDocsValidator(CategoryValidator):
    """
    Validator for technical documentation.

    Checks for:
    - Title
    - Content with code blocks (expected)
    - Links (navigation, cross-references)
    - Section structure
    """

    def validate(self, document: SimpleDocument) -> ValidationResult:
        issues = []
        total_checks = 4

        # 1. Title
        if not document.metadata.title or len(document.metadata.title.strip()) == 0:
            self._add_issue(
                issues, "metadata.title",
                "Technical documentation should have a title",
                ValidationSeverity.WARNING
            )

        # 2. Content
        if len(document.content) == 0:
            self._add_issue(
                issues, "content",
                "Technical documentation must have content",
                ValidationSeverity.ERROR
            )

        # 3. Check for code-related content
        content_text = " ".join(e.content.lower() for e in document.content if e.content)
        code_indicators = ["```", "function", "class", "import", "def ", "const ", "var "]
        has_code = any(indicator in content_text for indicator in code_indicators)

        if not has_code:
            self._add_issue(
                issues, "content.code",
                "Technical documentation typically contains code examples",
                ValidationSeverity.WARNING
            )

        # 4. Links (for navigation)
        if len(document.links) == 0:
            self._add_issue(
                issues, "links",
                "Technical documentation typically has navigation links",
                ValidationSeverity.INFO
            )

        # Calculate score
        score = self._calculate_score(issues, total_checks)
        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            category="technical_docs"
        )


class NewsArticleValidator(CategoryValidator):
    """
    Validator for news articles.

    Checks for:
    - Headline/title
    - Author/byline
    - Publish date
    - Content
    """

    def validate(self, document: SimpleDocument) -> ValidationResult:
        issues = []
        total_checks = 4

        # 1. Headline
        if not document.metadata.title or len(document.metadata.title.strip()) == 0:
            self._add_issue(
                issues, "metadata.title",
                "News articles must have a headline",
                ValidationSeverity.ERROR
            )

        # 2. Author/byline
        if not document.metadata.authors or len(document.metadata.authors) == 0:
            self._add_issue(
                issues, "metadata.authors",
                "News articles typically have an author byline",
                ValidationSeverity.WARNING
            )

        # 3. Publish date
        publish_date = getattr(document.metadata, 'publish_date', None)
        if not publish_date:
            self._add_issue(
                issues, "metadata.publish_date",
                "News articles should have a publish date",
                ValidationSeverity.WARNING
            )

        # 4. Content
        if len(document.content) == 0:
            self._add_issue(
                issues, "content",
                "News articles must have content",
                ValidationSeverity.ERROR
            )

        # Calculate score
        score = self._calculate_score(issues, total_checks)
        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            category="news_article"
        )


class ReportValidator(CategoryValidator):
    """
    Validator for business/technical reports.

    Checks for:
    - Title
    - Structured content
    - Tables and/or figures
    - Section organization
    """

    def validate(self, document: SimpleDocument) -> ValidationResult:
        issues = []
        total_checks = 4

        # 1. Title
        if not document.metadata.title or len(document.metadata.title.strip()) == 0:
            self._add_issue(
                issues, "metadata.title",
                "Reports must have a title",
                ValidationSeverity.ERROR
            )

        # 2. Content
        if len(document.content) == 0:
            self._add_issue(
                issues, "content",
                "Reports must have content",
                ValidationSeverity.ERROR
            )

        # 3. Tables and/or figures
        if len(document.tables) == 0 and len(document.figures) == 0:
            self._add_issue(
                issues, "tables_figures",
                "Reports typically contain tables or figures",
                ValidationSeverity.WARNING
            )

        # 4. Check for report-like structure
        content_text = " ".join(e.content.lower() for e in document.content if e.content)
        report_keywords = ["summary", "executive", "recommendation", "analysis", "finding"]
        has_report_structure = any(keyword in content_text for keyword in report_keywords)

        if not has_report_structure:
            self._add_issue(
                issues, "content.structure",
                "Reports typically have sections like Summary, Analysis, Recommendations",
                ValidationSeverity.INFO
            )

        # Calculate score
        score = self._calculate_score(issues, total_checks)
        passed = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            category="report"
        )


# Registry of validators
CATEGORY_VALIDATORS: Dict[str, type] = {
    "academic_paper": AcademicPaperValidator,
    "blog_post": BlogPostValidator,
    "technical_docs": TechnicalDocsValidator,
    "news_article": NewsArticleValidator,
    "report": ReportValidator,
}


def get_category_validator(category: str, strict: bool = False) -> CategoryValidator:
    """
    Get validator for a specific category.

    Args:
        category: Document category
        strict: If True, warnings become errors

    Returns:
        CategoryValidator instance

    Raises:
        ValueError: If category not supported
    """
    validator_class = CATEGORY_VALIDATORS.get(category)
    if validator_class is None:
        raise ValueError(
            f"No validator for category '{category}'. "
            f"Supported: {list(CATEGORY_VALIDATORS.keys())}"
        )

    return validator_class(strict=strict)


def validate_document(
    document: SimpleDocument,
    category: str,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate a document against category requirements.

    Args:
        document: Document to validate
        category: Expected category
        strict: If True, warnings become errors

    Returns:
        ValidationResult
    """
    validator = get_category_validator(category, strict=strict)
    return validator.validate(document)
