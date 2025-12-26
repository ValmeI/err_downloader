import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

import settings
from logger import init_logging
from err_api import extract_video_id, get_all_episodes_from_series, run_download


def main() -> None:
    """Main entry point for the ERR downloader."""
    init_logging(settings.LOGGER_LEVEL)

    ERR_MOVIE_URLS = ["https://lasteekraan.err.ee/1609882991/kiri-jouluvanale",
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
                      "https://lasteekraan.err.ee/1609870333/muksikud"
                      ]

    all_urls = settings.TV_SHOWS + ERR_MOVIE_URLS
    logger.info(f"Total URLs to process: {len(all_urls)} (TV Shows: {len(settings.TV_SHOWS)}, Movies: {len(ERR_MOVIE_URLS)})")

    for err_url in all_urls:
        logger.info(f"Processing URL: {err_url}")
        
        content_type = "tv_shows" if err_url in settings.TV_SHOWS else "movies"

        video_id = extract_video_id(err_url)
        if not video_id:
            logger.error("Failed to extract video ID")
            sys.exit(1)

        if settings.DOWNLOAD_ALL_EPISODES:
            logger.info("Fetching all episodes from series...")
            series_name, episode_ids = get_all_episodes_from_series(video_id)

            if episode_ids:
                if settings.USE_THREADING:
                    logger.info(f"Starting download of {len(episode_ids)} episodes with {settings.MAX_WORKERS} workers")
                    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
                        futures = {executor.submit(run_download, ep_id, content_type, series_name): (i, ep_id) for i, ep_id in enumerate(episode_ids, 1)}
                        for future in as_completed(futures):
                            _, ep_id = futures[future]
                            if not future.result():
                                logger.error(f"Failed to download episode {ep_id}")
                else:
                    logger.info(f"Starting download of {len(episode_ids)} episodes (sequential)")
                    for i, ep_id in enumerate(episode_ids, 1):
                        logger.info(f"Processing episode {i}/{len(episode_ids)}")
                        if not run_download(ep_id, content_type, series_name):
                            logger.error(f"Failed to download episode {ep_id}")
            else:
                logger.warning("No episodes found, trying single video...")
                if not run_download(video_id, content_type=content_type):
                    logger.error(f"Failed to download video from {err_url}, continuing with next URL...")
                    continue
        else:
            logger.info("Downloading single video")
            if not run_download(video_id, content_type=content_type):
                logger.error(f"Failed to download video from {err_url}, continuing with next URL...")
                continue

    logger.success("All downloads completed!")


if __name__ == "__main__":
    main()
