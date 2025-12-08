"""
Tests for visual regression testing.
"""

import pytest
import numpy as np
from PIL import Image
from pathlib import Path
from ..validation import VisualRegressionTester


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample test image."""
    img_path = tmp_path / "test_image.png"

    # Create a simple image with colored rectangles
    img = Image.new('RGB', (200, 200), color='white')
    pixels = img.load()

    # Blue rectangle
    for x in range(50, 150):
        for y in range(50, 150):
            pixels[x, y] = (0, 0, 255)

    img.save(img_path)
    return img_path


@pytest.fixture
def identical_image(sample_image, tmp_path):
    """Create an identical copy of the sample image."""
    img_path = tmp_path / "identical.png"
    img = Image.open(sample_image)
    img.save(img_path)
    return img_path


@pytest.fixture
def slightly_different_image(sample_image, tmp_path):
    """Create a slightly different version of the sample image."""
    img_path = tmp_path / "slightly_different.png"

    img = Image.open(sample_image)
    pixels = img.load()

    # Add a small red dot
    for x in range(10, 20):
        for y in range(10, 20):
            pixels[x, y] = (255, 0, 0)

    img.save(img_path)
    return img_path


@pytest.fixture
def very_different_image(tmp_path):
    """Create a very different image."""
    img_path = tmp_path / "very_different.png"

    # Create a completely different image
    img = Image.new('RGB', (200, 200), color='black')
    pixels = img.load()

    # Yellow circle
    center_x, center_y = 100, 100
    radius = 50
    for x in range(200):
        for y in range(200):
            if (x - center_x)**2 + (y - center_y)**2 < radius**2:
                pixels[x, y] = (255, 255, 0)

    img.save(img_path)
    return img_path


def test_visual_regression_identical(sample_image, identical_image):
    """Test comparison of identical images."""
    tester = VisualRegressionTester()
    result = tester.compare_images(sample_image, identical_image)

    assert result.passed is True
    assert result.similarity_score == 1.0
    assert result.pixel_diff_count == 0
    assert result.diff_percentage == 0.0


def test_visual_regression_slightly_different(sample_image, slightly_different_image):
    """Test comparison of slightly different images."""
    tester = VisualRegressionTester(
        ssim_threshold=0.90,
        pixel_diff_threshold=5.0,  # Allow 5% diff
    )
    result = tester.compare_images(sample_image, slightly_different_image)

    assert result.similarity_score < 1.0
    assert result.pixel_diff_count > 0
    assert result.diff_percentage < 10.0  # Should be small difference


def test_visual_regression_very_different(sample_image, very_different_image):
    """Test comparison of very different images."""
    tester = VisualRegressionTester()
    result = tester.compare_images(sample_image, very_different_image)

    assert result.passed is False
    assert result.similarity_score < 0.95
    assert result.diff_percentage > 1.0


def test_visual_regression_diff_image(sample_image, slightly_different_image):
    """Test diff image creation."""
    tester = VisualRegressionTester()
    result = tester.compare_images(
        sample_image,
        slightly_different_image,
        create_diff=True,
    )

    assert result.diff_image is not None
    assert result.diff_image.shape[0] == 200  # Height
    assert result.diff_image.shape[1] == 200  # Width


def test_visual_regression_custom_thresholds():
    """Test custom threshold configuration."""
    tester = VisualRegressionTester(
        ssim_threshold=0.98,
        pixel_diff_threshold=0.5,
    )

    assert tester.ssim_threshold == 0.98
    assert tester.pixel_diff_threshold == 0.5


def test_visual_regression_save_diff(sample_image, slightly_different_image, tmp_path):
    """Test saving diff image."""
    tester = VisualRegressionTester()
    result = tester.compare_images(
        sample_image,
        slightly_different_image,
        create_diff=True,
    )

    diff_path = tmp_path / "diff.png"
    tester.save_diff_image(result.diff_image, diff_path)

    assert diff_path.exists()

    # Verify it's a valid image
    img = Image.open(diff_path)
    assert img.size == (200, 200)


def test_visual_regression_create_baseline(sample_image, tmp_path):
    """Test baseline creation."""
    baseline_dir = tmp_path / "baselines"
    tester = VisualRegressionTester()

    baseline_path = tester.create_baseline(
        sample_image,
        baseline_dir,
        name="test_baseline.png",
    )

    assert baseline_path.exists()
    assert baseline_path.parent == baseline_dir
    assert baseline_path.name == "test_baseline.png"


def test_visual_regression_ignore_regions(sample_image, tmp_path):
    """Test ignore regions functionality."""
    # Create image with difference in ignore region
    modified = tmp_path / "modified.png"
    img = Image.open(sample_image)
    pixels = img.load()

    # Add red square in top-left (will be ignored)
    for x in range(10, 30):
        for y in range(10, 30):
            pixels[x, y] = (255, 0, 0)

    img.save(modified)

    # Test without ignore regions
    tester1 = VisualRegressionTester()
    result1 = tester1.compare_images(sample_image, modified)

    # Test with ignore regions
    tester2 = VisualRegressionTester(
        ignore_regions=[(10, 10, 20, 20)],  # Ignore the red square
    )
    result2 = tester2.compare_images(sample_image, modified)

    # Second result should be better
    assert result2.similarity_score >= result1.similarity_score


def test_visual_regression_size_mismatch(sample_image, tmp_path):
    """Test handling of different sized images."""
    # Create image with different size
    different_size = tmp_path / "different_size.png"
    img = Image.new('RGB', (300, 300), color='white')
    img.save(different_size)

    tester = VisualRegressionTester()
    result = tester.compare_images(sample_image, different_size)

    # Should handle size difference (resize to match)
    assert result is not None
    assert "baseline_size" in result.details
