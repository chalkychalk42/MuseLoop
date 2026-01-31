"""Configuration management via Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class MuseLoopConfig(BaseSettings):
    """Loads configuration from .env file and environment variables.

    All settings can be overridden via MUSELOOP_ prefixed env vars.
    """

    # LLM
    anthropic_api_key: str = ""
    llm_backend: str = "claude"
    claude_model: str = "claude-sonnet-4-20250514"

    # OpenAI-compatible (for Ollama, local models)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # Loop behavior
    max_iterations: int = 5
    quality_threshold: float = 0.7

    # Paths
    output_dir: str = "./output"
    prompts_dir: str = "./prompts"

    # External services
    comfyui_url: Optional[str] = "http://localhost:8188"
    replicate_api_key: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "env_prefix": "MUSELOOP_",
        "extra": "ignore",
    }

    def get_prompts_path(self) -> Path:
        return Path(self.prompts_dir).resolve()

    def get_output_path(self) -> Path:
        path = Path(self.output_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
