"""Download module for ERR video downloading."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, Tuple

from loguru import logger

from settings import settings
from err_api import extract_video_id, get_all_episodes_from_series, run_download
from cache import DownloadCache

cache = DownloadCache(settings.cache_file)

DownloadResult = Union[Tuple[str, str], str, bool]


def update_stats(stats: Dict, result: DownloadResult, video_info: str = "") -> None:
    """Update statistics based on download result."""
    stats["total_processed"] += 1

    status = result[0] if isinstance(result, tuple) else result

    if status == settings.constants.drm_protected:
        stats["drm_protected"] += 1
        if video_info:
            stats["drm_protected_list"].append(video_info)
    elif status == settings.constants.download_skipped:
        stats["skipped"] += 1
    elif status == settings.constants.cache_skipped:
        stats["skipped"] += 1
    elif status == "success":
        stats["successful"] += 1
        if video_info:
            stats["successful_list"].append(video_info)
    else:
        stats["failed"] += 1
        if video_info:
            stats["failed_list"].append(video_info)


def handle_download_result(result: DownloadResult, video_id: int, video_info: str, stats: Dict) -> None:
    """Process download result: update stats and cache successful downloads."""
    update_stats(stats, result, video_info)

    if isinstance(result, tuple) and len(result) == 2:
        status, file_path = result
        if status in ("success", settings.constants.download_skipped):
            cache.mark_downloaded(video_id, file_path)
    elif not result:
        logger.error(f"Failed to download: {video_info}")


def filter_cached_episodes(episode_ids: List[int], series_name: Optional[str], stats: Dict) -> List[int]:
    """Filter out cached episodes and update stats for skipped ones."""
    episodes_to_download = []
    for ep_id in episode_ids:
        if cache.is_downloaded(ep_id):
            logger.info(f"[{series_name}] Cached, skipping: Episode ID {ep_id}")
            video_info = f"{series_name} - Episode ID {ep_id}" if series_name else f"Episode ID {ep_id}"
            update_stats(stats, settings.constants.cache_skipped, video_info)
        else:
            episodes_to_download.append(ep_id)
    return episodes_to_download


def download_episodes_threaded(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict) -> None:
    """Download episodes using ThreadPoolExecutor."""
    episodes_to_download = filter_cached_episodes(episode_ids, series_name, stats)

    if not episodes_to_download:
        logger.info(f"[{series_name}] All {len(episode_ids)} episodes already cached")
        return

    logger.info(
        f"[{series_name}] Starting download of {len(episodes_to_download)} episodes with {settings.threading.get_max_workers()} workers ({len(episode_ids) - len(episodes_to_download)} cached)"
    )
    with ThreadPoolExecutor(max_workers=settings.threading.get_max_workers()) as executor:
        futures = {executor.submit(run_download, ep_id, content_type, series_name): ep_id for ep_id in episodes_to_download}
        for future in as_completed(futures):
            ep_id = futures[future]
            result = future.result()
            video_info = f"{series_name} - Episode ID {ep_id}" if series_name else f"Episode ID {ep_id}"
            handle_download_result(result, ep_id, video_info, stats)


def download_episodes_sequential(episode_ids: List[int], content_type: str, series_name: Optional[str], stats: Dict) -> None:
    """Download episodes sequentially."""
    logger.info(f"[{series_name}] Starting download of {len(episode_ids)} episodes")
    cached_count = 0

    for i, ep_id in enumerate(episode_ids, 1):
        video_info = f"{series_name} - Episode ID {ep_id}" if series_name else f"Episode ID {ep_id}"

        if cache.is_downloaded(ep_id):
            logger.info(f"[{series_name}] Cached, skipping: Episode ID {ep_id}")
            update_stats(stats, settings.constants.cache_skipped, video_info)
            cached_count += 1
            continue

        logger.info(f"[{series_name}] Processing episode {i}/{len(episode_ids)}")
        result = run_download(ep_id, content_type, series_name)
        handle_download_result(result, ep_id, video_info, stats)

    if cached_count > 0:
        logger.info(f"[{series_name}] Skipped {cached_count} cached episodes")


def download_single_video(video_id: int, content_type: str, video_info: str, stats: Dict) -> None:
    """Download a single video with cache check."""
    if cache.is_downloaded(video_id):
        logger.info(f"Cached, skipping: {video_info}")
        update_stats(stats, settings.constants.cache_skipped, video_info)
        return

    result = run_download(video_id, content_type=content_type)
    handle_download_result(result, video_id, video_info, stats)


def process_url(url: str, content_type: str, stats: Dict) -> None:
    """Process a single URL for download."""
    logger.info("=" * 80)
    logger.success(f"Processing URL: {url}")

    video_id = extract_video_id(url)
    if not video_id:
        logger.error("Failed to extract video ID")
        stats["failed"] += 1
        stats["failed_list"].append(f"URL: {url} (failed to extract video ID)")
        return

    if settings.download.download_all_episodes:
        logger.info("Fetching all episodes from series...")
        series_name, episode_ids = get_all_episodes_from_series(video_id)

        if episode_ids:
            if settings.threading.use_threading:
                download_episodes_threaded(episode_ids, content_type, series_name, stats)
            else:
                download_episodes_sequential(episode_ids, content_type, series_name, stats)
        elif series_name == settings.constants.content_not_found_404:
            logger.warning(f"Sisu on ERRist eemaldatud ({settings.constants.content_not_found_404}), vahele jäetud: {url}")
            stats["failed"] += 1
            stats["failed_list"].append(f"URL: {url} (sisu eemaldatud ERRist)")
        else:
            title_info = f" '{series_name}'" if series_name else ""
            logger.warning(f"No episodes found for{title_info} {url} (ID: {video_id}), trying single video...")
            download_single_video(video_id, content_type, f"Video ID {video_id} from {url}", stats)
    else:
        logger.info("Downloading single video")
        download_single_video(video_id, content_type, f"Video ID {video_id} from {url}", stats)


def print_summary(stats: Dict) -> None:
    """Print download summary statistics."""
    logger.info("=" * 80)
    logger.success("Allalaadimised lõpetatud!")
    logger.info("=" * 80)
    logger.info(f"Kokku töödeldud: {stats['total_processed']} videot")

    if stats["successful_list"]:
        logger.info("")
        logger.success(f"Alla laaditud: {stats['successful']}")
        for video in stats["successful_list"]:
            logger.success(f"  - {video}")
    else:
        logger.success(f"Alla laaditud: {stats['successful']}")

    logger.info("")
    logger.info(f"Juba olemas (vahele jäetud): {stats['skipped']}")

    if stats["drm_protected_list"]:
        logger.info("")
        logger.info(f"DRM-kaitstud (vahele jäetud): {stats['drm_protected']}")
        for video in stats["drm_protected_list"]:
            logger.info(f"  - {video}")

    if stats["failed_list"]:
        logger.info("")
        logger.warning(f"Ebaõnnestunud: {stats['failed']}")
        for video in stats["failed_list"]:
            logger.warning(f"  - {video}")

    logger.info("=" * 80)


def run_download_mode() -> int:
    """Run download mode."""
    all_urls = settings.tv_shows + settings.movies
    logger.info(f"Total URLs to process: {len(all_urls)} (TV Shows: {len(settings.tv_shows)}, Movies: {len(settings.movies)})")

    stats = {
        "total_processed": 0,
        "successful": 0,
        "skipped": 0,
        "failed": 0,
        "drm_protected": 0,
        "drm_protected_list": [],
        "failed_list": [],
        "successful_list": [],
    }

    try:
        for url in all_urls:
            content_type = settings.constants.content_type_tv_shows if url in settings.tv_shows else settings.constants.content_type_movies
            process_url(url, content_type, stats)

        print_summary(stats)

        if stats["failed"] > 0:
            logger.warning(f"Completed with {stats['failed']} failures:")
            for failed_item in stats["failed_list"]:
                logger.warning(f"  - {failed_item}")

    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        return 1

    return 0
