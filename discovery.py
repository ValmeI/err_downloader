"""URL discovery module for finding new season URLs."""

from typing import Dict, List, Set

from loguru import logger

from settings import settings, update_config, CONFIG_PATH
from err_api import discover_missing_urls, extract_show_slug


def add_urls_to_config(missing_by_show: Dict[str, Set[str]]) -> int:
    """Add missing URLs to config yaml file, routed to tv_shows or movies by slug."""
    tv_shows = list(settings.tv_shows)
    movies = list(settings.movies)
    movie_slugs = {extract_show_slug(url) for url in settings.movies}
    added = 0

    for urls in missing_by_show.values():
        for url in urls:
            target = movies if extract_show_slug(url) in movie_slugs else tv_shows
            if url not in target:
                target.append(url)
                added += 1
                logger.info(f"Lisatud: {url}")

    if added > 0:
        tv_shows.sort(key=extract_show_slug)
        movies.sort(key=extract_show_slug)
        update_config({"tv_shows": tv_shows, "movies": movies})
        logger.success(f"Config.yaml uuendatud! Lisatud {added} URL-i.")

    return added


def run_discovery(tv_show_urls: List[str], movie_urls: List[str], add_to_config: bool) -> int:
    """Run URL discovery mode."""
    logger.info("Otsin uusi hooaegade URL-e...")

    missing = discover_missing_urls(tv_show_urls, movie_urls)

    if not missing:
        logger.success(f"Kõik URL-id on juba {CONFIG_PATH}-is!")
        return 0

    total = sum(len(urls) for urls in missing.values())
    logger.info(f"Leitud kokku {total} uut URL-i")

    if add_to_config:
        add_urls_to_config(missing)
    else:
        logger.info("Lisamiseks käivita: python main.py --discover --add")

    return 0
