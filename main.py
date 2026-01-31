"""ERR video downloader - main entry point."""

import sys
import argparse

from settings import settings
from logger import init_logging
from discovery import run_discovery
from downloader import run_download_mode


def main() -> int:
    """Main entry point for the ERR downloader."""
    parser = argparse.ArgumentParser(description="ERR video downloader")
    parser.add_argument("--discover", action="store_true", help="Otsi uusi hooaegade URL-e")
    parser.add_argument("--add", action="store_true", help="Lisa leitud URL-id config.yaml-i (kasuta koos --discover)")
    args = parser.parse_args()

    init_logging(settings.logger_level, settings.logger_file)

    if args.discover:
        return run_discovery(settings.tv_shows, args.add)
    else:
        return run_download_mode()


if __name__ == "__main__":
    sys.exit(main())
