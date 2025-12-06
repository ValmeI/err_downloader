import sys
from typing import List

from loguru import logger

import settings
from logger import init_logging
from err_api import extract_video_id, get_all_episodes_from_series, run_download


def main() -> None:
    """Main entry point for the ERR downloader."""
    init_logging(settings.LOGGER_LEVEL)

    ERR_URLS: List[str] = [
        "https://lasteekraan.err.ee/1608695959/lepatriinu-ja-musta-kassi-imelised-lood",
        "https://lasteekraan.err.ee/1039236/must-ja-valge-koer",
        "https://lasteekraan.err.ee/1609367503/varviklotsid",
        "https://lasteekraan.err.ee/1609246718/numbriklotsid",
        "https://lasteekraan.err.ee/1608967400/peeter-pikk-korv",
        "https://lasteekraan.err.ee/1608940043/pips-ja-popi",
        "https://lasteekraan.err.ee/1609218548/tegus-timmu",
        "https://lasteekraan.err.ee/1608776887/vilda",
        "https://lasteekraan.err.ee/1038651/karu-karla",
        "https://lasteekraan.err.ee/1127112/ninjakunstnik",
        "https://lasteekraan.err.ee/1608551665/tuta-asjad",
        "https://lasteekraan.err.ee/1038778/porsas-peppa",
    ]

    for err_url in ERR_URLS:
        logger.info(f"Processing URL: {err_url}")

        video_id = extract_video_id(err_url)
        if not video_id:
            logger.error("Failed to extract video ID")
            sys.exit(1)

        if settings.DOWNLOAD_ALL_EPISODES:
            logger.info("Fetching all episodes from series...")
            episode_ids = get_all_episodes_from_series(video_id)

            if episode_ids:
                logger.info(f"Starting download of {len(episode_ids)} episodes")
                for i, ep_id in enumerate(episode_ids, 1):
                    logger.info(f"Episode {i}/{len(episode_ids)} (ID: {ep_id})")
                    if not run_download(ep_id):
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
