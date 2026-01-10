from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from loguru import logger

import settings
from logger import init_logging
from err_api import extract_video_id, get_all_episodes_from_series, run_download
from constants import DOWNLOAD_SKIPPED, DOWNLOAD_DRM_PROTECTED, CONTENT_TYPE_TV_SHOWS, CONTENT_TYPE_MOVIES, CONTENT_NOT_FOUND_404


def update_stats(stats: Dict, result: str | bool, video_info: str = "") -> None:
    """Update statistics based on download result."""
    stats["total_processed"] += 1
    if result == DOWNLOAD_DRM_PROTECTED:
        stats["drm_protected"] += 1
        if video_info:
            stats["drm_protected_list"].append(video_info)
    elif result == DOWNLOAD_SKIPPED:
        stats["skipped"] += 1
    elif result is True:
        stats["successful"] += 1
    else:
        stats["failed"] += 1
        if video_info:
            stats["failed_list"].append(video_info)


def download_episodes_threaded(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict) -> None:
    """Download episodes using ThreadPoolExecutor."""
    logger.info(f"Starting download of {len(episode_ids)} episodes with {settings.MAX_WORKERS} workers")
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        futures = {executor.submit(run_download, ep_id, content_type, series_name): (i, ep_id) for i, ep_id in enumerate(episode_ids, 1)}
        for future in as_completed(futures):
            _, ep_id = futures[future]
            result = future.result()
            video_info = f"{series_name} - Episode ID {ep_id}" if series_name else f"Episode ID {ep_id}"
            update_stats(stats, result, video_info)
            if not result:
                logger.error(f"Failed to download episode {ep_id}")


def download_episodes_sequential(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict) -> None:
    """Download episodes sequentially."""
    logger.info(f"Starting download of {len(episode_ids)} episodes (sequential)")
    for i, ep_id in enumerate(episode_ids, 1):
        logger.info(f"Processing episode {i}/{len(episode_ids)}")
        result = run_download(ep_id, content_type, series_name)
        video_info = f"{series_name} - Episode ID {ep_id}" if series_name else f"Episode ID {ep_id}"
        update_stats(stats, result, video_info)
        if not result:
            logger.error(f"Failed to download episode {ep_id}")


def process_url(url: str, content_type: str, stats: Dict) -> None:
    """Process a single URL for download."""
    logger.info(f"Processing URL: {url}")

    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Failed to extract video ID")
        stats["failed"] += 1
        stats["failed_list"].append(f"URL: {url} (failed to extract video ID)")
        return

    if settings.DOWNLOAD_ALL_EPISODES:
        logger.info("Fetching all episodes from series...")
        series_name, episode_ids = get_all_episodes_from_series(video_id)

        if episode_ids:
            if settings.USE_THREADING:
                download_episodes_threaded(episode_ids, content_type, series_name, stats)
            else:
                download_episodes_sequential(episode_ids, content_type, series_name, stats)
        elif series_name == CONTENT_NOT_FOUND_404:
            logger.warning(f"Sisu on ERRist eemaldatud ({CONTENT_NOT_FOUND_404}), vahele jäetud: {url}")
            stats["failed"] += 1
            stats["failed_list"].append(f"URL: {url} (sisu eemaldatud ERRist)")
        else:
            title_info = f" '{series_name}'" if series_name else ""
            logger.warning(f"No episodes found for{title_info} {url} (ID: {video_id}), trying single video...")
            result = run_download(video_id, content_type=content_type)
            video_info = f"Video ID {video_id} from {url}"
            update_stats(stats, result, video_info)
            if not result:
                logger.error(f"Failed to download video from {url}")
    else:
        logger.info("Downloading single video")
        result = run_download(video_id, content_type=content_type)
        video_info = f"Video ID {video_id} from {url}"
        update_stats(stats, result, video_info)
        if not result:
            logger.error(f"Failed to download video from {url}")


def print_summary(stats: Dict) -> None:
    """Print download summary statistics."""
    logger.info("=" * 60)
    logger.success("Allalaadimised lõpetatud!")
    logger.info("=" * 60)
    logger.info(f"Kokku töödeldud: {stats['total_processed']} videot")
    logger.info(f"Alla laaditud: {stats['successful']}")
    logger.info(f"Juba olemas (vahele jäetud): {stats['skipped']}")

    if stats["drm_protected_list"]:
        logger.info("")
        logger.info(f"DRM-kaitstud (vahele jäetud): {stats['drm_protected']}")
        for video in stats["drm_protected_list"]:
            logger.info(f"  - {video}")

    if stats["failed_list"]:
        logger.info("")
        logger.info(f"Ebaõnnestunud: {stats['failed']}")
        for video in stats["failed_list"]:
            logger.info(f"  - {video}")

    logger.info("=" * 60)


def main() -> None:
    """Main entry point for the ERR downloader."""
    init_logging(settings.LOGGER_LEVEL)

    ERR_MOVIE_URLS = [
        "https://lasteekraan.err.ee/1211395/lohe-zog",
        "https://lasteekraan.err.ee/1609882997/kuidas-taltsutada-lohet-talvepuhad",
        "https://lasteekraan.err.ee/1609883009/jouluvana-joulupuhkus",
    ]

    all_urls = settings.TV_SHOWS + ERR_MOVIE_URLS
    logger.info(f"Total URLs to process: {len(all_urls)} (TV Shows: {len(settings.TV_SHOWS)}, Movies: {len(ERR_MOVIE_URLS)})")

    stats = {"total_processed": 0, "successful": 0, "skipped": 0, "failed": 0, "drm_protected": 0, "drm_protected_list": [], "failed_list": []}

    for url in all_urls:
        content_type = CONTENT_TYPE_TV_SHOWS if url in settings.TV_SHOWS else CONTENT_TYPE_MOVIES
        process_url(url, content_type, stats)

    print_summary(stats)


if __name__ == "__main__":
    main()
