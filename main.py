import sys
from typing import List

from loguru import logger

import settings
from logger import init_logging
from err_api import extract_video_id, get_all_episodes_from_series, run_download


def main() -> None:
    """Main entry point for the ERR downloader."""
    init_logging(settings.LOGGER_LEVEL)
    
    ERR_MOVIE_URLS = [
        "https://lasteekraan.err.ee/1609851079/musteerium-veisemae-kiirrongil",
    ]

    all_urls = settings.TV_SHOWS + ERR_MOVIE_URLS
    logger.info(f"Total URLs to process: {len(all_urls)} (TV Shows: {len(settings.TV_SHOWS)}, Movies: {len(ERR_MOVIE_URLS)})")

    for err_url in all_urls:
        logger.info(f"Processing URL: {err_url}")

        video_id = extract_video_id(err_url)
        if not video_id:
            logger.error("Failed to extract video ID")
            sys.exit(1)

        if settings.DOWNLOAD_ALL_EPISODES:
            logger.info("Fetching all episodes from series...")
            series_name, episode_ids = get_all_episodes_from_series(video_id)

            if episode_ids:
                logger.info(f"Starting download of {len(episode_ids)} episodes")
                for i, ep_id in enumerate(episode_ids, 1):
                    logger.info(f"Episode {i}/{len(episode_ids)} (ID: {ep_id})")
                    if not run_download(ep_id, series_name):
                        logger.error(f"Failed to download episode {ep_id}")
            else:
                logger.warning("No episodes found, trying single video...")
                if not run_download(video_id):
                    sys.exit(1)
        else:
            logger.info("Downloading single video")
            if not run_download(video_id):
                sys.exit(1)

    logger.success("All downloads completed!")


if __name__ == "__main__":
    main()
