from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from loguru import logger

import settings
from logger import init_logging
from err_api import extract_video_id, get_all_episodes_from_series, run_download
from constants import (
    DOWNLOAD_SKIPPED,
    DOWNLOAD_DRM_PROTECTED,
    CONTENT_TYPE_TV_SHOWS,
    CONTENT_TYPE_MOVIES,
)


def update_stats(stats: Dict[str, int], result: bool | str) -> None:
    """Update statistics based on download result."""
    stats["total_processed"] += 1
    if result == DOWNLOAD_DRM_PROTECTED:
        stats["drm_protected"] += 1
    elif result == DOWNLOAD_SKIPPED:
        stats["skipped"] += 1
    elif result == True:
        stats["successful"] += 1
    else:
        stats["failed"] += 1


def download_episodes_threaded(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict[str, int]) -> None:
    """Download episodes using ThreadPoolExecutor."""
    logger.info(f"Starting download of {len(episode_ids)} episodes with {settings.MAX_WORKERS} workers")
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        futures = {executor.submit(run_download, ep_id, content_type, series_name): (i, ep_id) for i, ep_id in enumerate(episode_ids, 1)}
        for future in as_completed(futures):
            _, ep_id = futures[future]
            result = future.result()
            update_stats(stats, result)
            if not result:
                logger.error(f"Failed to download episode {ep_id}")


def download_episodes_sequential(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict[str, int]) -> None:
    """Download episodes sequentially."""
    logger.info(f"Starting download of {len(episode_ids)} episodes (sequential)")
    for i, ep_id in enumerate(episode_ids, 1):
        logger.info(f"Processing episode {i}/{len(episode_ids)}")
        result = run_download(ep_id, content_type, series_name)
        update_stats(stats, result)
        if not result:
            logger.error(f"Failed to download episode {ep_id}")


def process_url(url: str, content_type: str, stats: Dict[str, int]) -> None:
    """Process a single URL for download."""
    logger.info(f"Processing URL: {url}")
    
    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Failed to extract video ID")
        stats["failed"] += 1
        return

    if settings.DOWNLOAD_ALL_EPISODES:
        logger.info("Fetching all episodes from series...")
        series_name, episode_ids = get_all_episodes_from_series(video_id)

        if episode_ids:
            if settings.USE_THREADING:
                download_episodes_threaded(episode_ids, content_type, series_name, stats)
            else:
                download_episodes_sequential(episode_ids, content_type, series_name, stats)
        else:
            logger.warning("No episodes found, trying single video...")
            result = run_download(video_id, content_type=content_type)
            update_stats(stats, result)
            if not result:
                logger.error(f"Failed to download video from {url}")
    else:
        logger.info("Downloading single video")
        result = run_download(video_id, content_type=content_type)
        update_stats(stats, result)
        if not result:
            logger.error(f"Failed to download video from {url}")


def print_summary(stats: Dict[str, int]) -> None:
    """Print download summary statistics."""
    logger.info("=" * 60)
    logger.success("Allalaadimised lõpetatud!")
    logger.info("=" * 60)
    logger.info(f"Kokku töödeldud: {stats['total_processed']} videot")
    logger.info(f"Alla laaditud: {stats['successful']}")
    logger.info(f"Juba olemas (vahele jäetud): {stats['skipped']}")
    logger.info(f"DRM-kaitstud (vahele jäetud): {stats['drm_protected']}")
    logger.info(f"Ebaõnnestunud: {stats['failed']}")
    logger.info("=" * 60)


def main() -> None:
    """Main entry point for the ERR downloader."""
    init_logging(settings.LOGGER_LEVEL)

    ERR_MOVIE_URLS = [
        "https://lasteekraan.err.ee/1609882991/kiri-jouluvanale",
        "https://lasteekraan.err.ee/1609883591/nassu",
        "https://lasteekraan.err.ee/1609882928/loomade-joululood",
        "https://lasteekraan.err.ee/1609883009/jouluvana-joulupuhkus",
        "https://lasteekraan.err.ee/1609535498/pakapikkudega-kodus",
        "https://lasteekraan.err.ee/1203292/oksa-onu",
        "https://lasteekraan.err.ee/1609549379/arthur-paastab-joulud",
        "https://lasteekraan.err.ee/1609194620/mutiharra-mutik-kuninglikel-pidustustel",
        "https://lasteekraan.err.ee/1609549457/kiisu-mcmiisu",
        "https://lasteekraan.err.ee/1609877765/miisu-joulud",
        "https://lasteekraan.err.ee/1609188260/terry-pratchetti-joululugu-lumetitt",
        "https://lasteekraan.err.ee/1608431150/turbode-joulud-pohjanabal",
        "https://lasteekraan.err.ee/1609870333/muksikud",
    ]

    all_urls = settings.TV_SHOWS + ERR_MOVIE_URLS
    logger.info(f"Total URLs to process: {len(all_urls)} (TV Shows: {len(settings.TV_SHOWS)}, Movies: {len(ERR_MOVIE_URLS)})")

    stats = {"total_processed": 0, "successful": 0, "skipped": 0, "failed": 0, "drm_protected": 0}

    for url in all_urls:
        content_type = CONTENT_TYPE_TV_SHOWS if url in settings.TV_SHOWS else CONTENT_TYPE_MOVIES
        process_url(url, content_type, stats)

    print_summary(stats)


if __name__ == "__main__":
    main()
