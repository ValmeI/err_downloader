"""Download cache module for tracking downloaded episodes."""

import json
import os
from typing import Dict, Optional
from loguru import logger


class DownloadCache:
    """Cache for tracking downloaded episodes with file path verification."""

    def __init__(self, cache_file: str):
        self.cache_file = os.path.expanduser(cache_file)
        self._downloads: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """Load cache from file."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    self._downloads = data.get("downloads", {})
                logger.debug(f"Loaded {len(self._downloads)} cached episodes from {self.cache_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._downloads = {}

    def save(self) -> None:
        """Save cache to file."""
        try:
            os.makedirs(os.path.dirname(self.cache_file) or ".", exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump({"downloads": self._downloads}, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    def is_downloaded(self, episode_id: int) -> Optional[str]:
        """Check if episode is downloaded and file exists.

        Returns the file path if cached and file exists, None otherwise.
        """
        key = str(episode_id)
        if key not in self._downloads:
            return None

        file_path = self._downloads[key]
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        # File was deleted, remove from cache
        logger.debug(f"Cached file no longer exists, removing from cache: {file_path}")
        self.remove(episode_id)
        return None

    def mark_downloaded(self, episode_id: int, file_path: str) -> None:
        """Mark episode as downloaded with its file path."""
        self._downloads[str(episode_id)] = file_path
        self.save()

    def remove(self, episode_id: int) -> None:
        """Remove episode from cache."""
        key = str(episode_id)
        if key in self._downloads:
            del self._downloads[key]
            self.save()
