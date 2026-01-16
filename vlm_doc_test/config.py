"""
Configuration management for VLM API credentials and settings.

Loads configuration from environment variables or .env file.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class VLMConfig:
    """Configuration for VLM API access."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        # GLM-4.6V API configuration
        self.glm_api_key: Optional[str] = os.getenv("GLM_API_KEY")
        self.glm_api_base: str = os.getenv(
            "GLM_API_BASE",
            "https://open.bigmodel.cn/api/paas/v4"
        )

        # OpenAI-compatible fallback (for testing with other providers)
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.openai_api_base: Optional[str] = os.getenv("OPENAI_API_BASE")

        # Default model settings
        self.default_model: str = os.getenv("VLM_DEFAULT_MODEL", "glm-4v-plus")
        self.max_tokens: int = int(os.getenv("VLM_MAX_TOKENS", "8000"))
        self.temperature: float = float(os.getenv("VLM_TEMPERATURE", "0.1"))

        # Retry settings
        self.max_retries: int = int(os.getenv("VLM_MAX_RETRIES", "3"))
        self.retry_delay: float = float(os.getenv("VLM_RETRY_DELAY", "1.0"))

    def has_glm_credentials(self) -> bool:
        """Check if GLM API credentials are configured."""
        return self.glm_api_key is not None

    def has_openai_credentials(self) -> bool:
        """Check if OpenAI API credentials are configured."""
        return self.openai_api_key is not None

    def validate(self) -> tuple[bool, str]:
        """
        Validate configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.has_glm_credentials() and not self.has_openai_credentials():
            return False, (
                "No VLM API credentials found. Please set GLM_API_KEY or "
                "OPENAI_API_KEY in environment variables or .env file."
            )
        return True, ""


# Global configuration instance
config = VLMConfig()


def get_config() -> VLMConfig:
    """Get the global configuration instance."""
    return config
