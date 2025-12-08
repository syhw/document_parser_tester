"""
Visual regression testing utilities.

This module provides tools for comparing document renderings visually
using image comparison techniques including SSIM and pixel diff.
"""

from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim
from dataclasses import dataclass


@dataclass
class VisualComparisonResult:
    """Result of visual comparison between two images."""
    similarity_score: float  # 0.0 to 1.0 (SSIM)
    pixel_diff_count: int
    total_pixels: int
    diff_percentage: float
    passed: bool
    diff_image: Optional[np.ndarray] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class VisualRegressionTester:
    """
    Visual regression testing for document renderings.

    Uses SSIM (Structural Similarity Index) for perceptual comparison
    and pixel-level diff for detecting exact changes.
    """

    def __init__(
        self,
        ssim_threshold: float = 0.95,
        pixel_diff_threshold: float = 0.01,
        ignore_regions: Optional[list] = None,
    ):
        """
        Initialize visual regression tester.

        Args:
            ssim_threshold: Minimum SSIM score to consider images similar (0-1)
            pixel_diff_threshold: Maximum allowed pixel difference percentage
            ignore_regions: List of (x, y, width, height) regions to ignore
        """
        self.ssim_threshold = ssim_threshold
        self.pixel_diff_threshold = pixel_diff_threshold
        self.ignore_regions = ignore_regions or []

    def compare_images(
        self,
        baseline_path: Path,
        current_path: Path,
        create_diff: bool = True,
    ) -> VisualComparisonResult:
        """
        Compare two images for visual regression.

        Args:
            baseline_path: Path to baseline (expected) image
            current_path: Path to current (actual) image
            create_diff: Whether to create a diff image

        Returns:
            VisualComparisonResult with comparison details
        """
        # Load images
        baseline = Image.open(baseline_path).convert('RGB')
        current = Image.open(current_path).convert('RGB')

        # Ensure same size
        if baseline.size != current.size:
            # Resize current to match baseline
            current = current.resize(baseline.size, Image.Resampling.LANCZOS)

        # Convert to numpy arrays
        baseline_arr = np.array(baseline)
        current_arr = np.array(current)

        # Apply ignore regions (mask them)
        if self.ignore_regions:
            baseline_arr = self._apply_ignore_regions(baseline_arr)
            current_arr = self._apply_ignore_regions(current_arr)

        # Calculate SSIM
        ssim_score = self._calculate_ssim(baseline_arr, current_arr)

        # Calculate pixel diff
        diff_count, total_pixels, diff_percentage = self._calculate_pixel_diff(
            baseline_arr, current_arr
        )

        # Create diff image if requested
        diff_image = None
        if create_diff:
            diff_image = self._create_diff_image(baseline_arr, current_arr)

        # Determine if test passed
        passed = (
            ssim_score >= self.ssim_threshold and
            diff_percentage <= self.pixel_diff_threshold
        )

        return VisualComparisonResult(
            similarity_score=ssim_score,
            pixel_diff_count=diff_count,
            total_pixels=total_pixels,
            diff_percentage=diff_percentage,
            passed=passed,
            diff_image=diff_image,
            details={
                "baseline_size": baseline.size,
                "current_size": current.size,
                "ssim_threshold": self.ssim_threshold,
                "pixel_diff_threshold": self.pixel_diff_threshold,
            },
        )

    def _calculate_ssim(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> float:
        """
        Calculate SSIM between two images.

        SSIM measures perceptual similarity and is more aligned with
        human perception than simple pixel diff.
        """
        # Convert to grayscale for SSIM calculation
        if len(img1.shape) == 3:
            img1_gray = np.mean(img1, axis=2).astype(np.uint8)
            img2_gray = np.mean(img2, axis=2).astype(np.uint8)
        else:
            img1_gray = img1
            img2_gray = img2

        # Calculate SSIM
        score, _ = ssim(
            img1_gray,
            img2_gray,
            full=True,
            data_range=255,
        )

        return float(score)

    def _calculate_pixel_diff(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> Tuple[int, int, float]:
        """
        Calculate pixel-level difference.

        Returns:
            (diff_count, total_pixels, diff_percentage)
        """
        # Calculate absolute difference
        diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))

        # Count pixels with any difference (across any channel)
        if len(diff.shape) == 3:
            diff_mask = np.any(diff > 0, axis=2)
        else:
            diff_mask = diff > 0

        diff_count = np.sum(diff_mask)
        total_pixels = diff_mask.size
        diff_percentage = (diff_count / total_pixels) * 100

        return int(diff_count), int(total_pixels), float(diff_percentage)

    def _create_diff_image(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> np.ndarray:
        """
        Create a visual diff image highlighting differences.

        Differences are shown in red.
        """
        # Calculate absolute difference
        diff = np.abs(img1.astype(np.int16) - img2.astype(np.int16))

        # Create RGB diff image
        if len(diff.shape) == 2:
            # Grayscale - convert to RGB
            diff_rgb = np.stack([diff, diff, diff], axis=2)
        else:
            diff_rgb = diff

        # Normalize to 0-255
        diff_rgb = (diff_rgb / diff_rgb.max() * 255).astype(np.uint8) if diff_rgb.max() > 0 else diff_rgb.astype(np.uint8)

        # Highlight differences in red
        diff_mask = np.any(diff_rgb > 10, axis=2)
        result = img2.copy()
        result[diff_mask] = [255, 0, 0]  # Red for differences

        return result

    def _apply_ignore_regions(self, img: np.ndarray) -> np.ndarray:
        """
        Apply ignore regions by masking them to a neutral color.

        Args:
            img: Image array

        Returns:
            Image array with ignore regions masked
        """
        img_copy = img.copy()

        for x, y, width, height in self.ignore_regions:
            # Mask region with gray
            img_copy[y:y+height, x:x+width] = 128

        return img_copy

    def save_diff_image(
        self,
        diff_image: np.ndarray,
        output_path: Path,
    ):
        """Save diff image to file."""
        Image.fromarray(diff_image.astype(np.uint8)).save(output_path)

    def create_baseline(
        self,
        image_path: Path,
        baseline_dir: Path,
        name: Optional[str] = None,
    ) -> Path:
        """
        Create a baseline image for future comparisons.

        Args:
            image_path: Path to current image
            baseline_dir: Directory to store baselines
            name: Optional custom name (uses image filename if not provided)

        Returns:
            Path to created baseline
        """
        baseline_dir.mkdir(parents=True, exist_ok=True)

        if name is None:
            name = image_path.name

        baseline_path = baseline_dir / name

        # Copy image to baseline directory
        import shutil
        shutil.copy(image_path, baseline_path)

        return baseline_path
