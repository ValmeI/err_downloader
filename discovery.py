"""URL discovery module for finding new season URLs."""

from typing import Dict, Set

import yaml
from loguru import logger

from settings import CONFIG_PATH
from err_api import discover_missing_urls


def add_urls_to_config(missing_by_show: Dict[str, Set[str]]) -> int:
    """Add missing URLs to config.yaml."""

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    added = 0
    tv_shows = config.get("tv_shows") or []

    for urls in missing_by_show.values():
        for url in urls:
            if url not in tv_shows:
                tv_shows.append(url)
                added += 1
                logger.info(f"Lisatud: {url}")

    if added > 0:
        config["tv_shows"] = tv_shows
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.success(f"Config.yaml uuendatud! Lisatud {added} URL-i.")

    return added


def run_discovery(tv_show_urls: list, add_to_config: bool) -> int:
    """Run URL discovery mode."""
    logger.info("Otsin uusi hooaegade URL-e...")

    missing = discover_missing_urls(tv_show_urls)

    if not missing:
        logger.success("Kõik URL-id on juba config.yaml-is!")
        return 0

    total = sum(len(urls) for urls in missing.values())
    logger.info(f"Leitud kokku {total} uut URL-i")

    if add_to_config:
        add_urls_to_config(missing)
    else:
        logger.info("Lisamiseks käivita: python main.py --discover --add")

    return 0
