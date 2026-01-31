"""Application settings using pydantic-settings."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

# Config file path - used across the application
CONFIG_PATH = Path(__file__).parent / "config.yaml"


class DownloadSettings(BaseModel):
    """Download-related settings."""

    timeout_max: int
    chunk_size: int
    download_all_episodes: bool
    skip_existing: bool


class ThreadingSettings(BaseModel):
    """Threading-related settings."""

    use_threading: bool
    max_workers: Optional[int]

    def get_max_workers(self) -> int:
        """Get max workers, auto-detecting if not set."""
        return self.max_workers if self.max_workers is not None else (os.cpu_count() or 4)


class RetrySettings(BaseModel):
    """Retry-related settings."""

    max_attempts: int
    wait_min: int
    wait_max: int
    wait_multiplier: int


class DirectorySettings(BaseModel):
    """Directory-related settings."""

    tv_shows: str
    movies: str


class ConstantsSettings(BaseModel):
    """Application constants."""

    download_skipped: str
    drm_protected: str
    content_not_found_404: str
    content_type_tv_shows: str
    content_type_movies: str


class Settings(BaseSettings):
    """Main settings class."""

    logger_level: str
    logger_file: Optional[str] = None  # Optional path to log file (e.g., "logs/downloader.log")
    download: DownloadSettings
    threading: ThreadingSettings
    retry: RetrySettings
    directories: DirectorySettings
    constants: ConstantsSettings
    tv_shows: List[str] = []
    movies: List[str] = []

    @field_validator("tv_shows", "movies", mode="before")
    @classmethod
    def convert_none_to_empty_list(cls, v):
        return v if v is not None else []

    @classmethod
    def load_from_yaml(cls, config_path: Path = CONFIG_PATH) -> "Settings":
        """Load settings from YAML file."""
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file '{config_path}' not found. Please copy 'config.example.yaml' to '{config_path}' and adjust settings.")

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data)


settings = Settings.load_from_yaml()
