import re
import os
from typing import Optional, Tuple, List
import requests
from tqdm import tqdm
from requests.exceptions import RequestException
from loguru import logger

import settings

API_BASE_URL = "https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={}"

session = requests.Session()


def get_video_details(content_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch video details from ERR API."""
    try:
        url = API_BASE_URL.format(content_id)
        logger.info(f"Fetching video details for content_id: {content_id}")

        response = session.get(url, timeout=settings.TIMEOUT_MAX)
        response.raise_for_status()

        data = response.json()
        folder_name = data["data"]["mainContent"]["heading"].replace(".", "")
        title_with_season_episode_year = f"{data['data']['mainContent']['statsHeading']} {data['data']['mainContent']['year']}"

        try:
            mp4_url = "https:" + data["data"]["mainContent"]["medias"][0]["src"]["file"].replace("\\", "")
            logger.info(f"Video details: {title_with_season_episode_year}")
            logger.info(f"MP4 URL: {mp4_url}")
            return folder_name, title_with_season_episode_year, mp4_url
        except (IndexError, KeyError) as e:
            logger.error(f"Failed to extract media URL: {str(e)}")
            return None, None, None

    except RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return None, None, None
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        return None, None, None


def download_mp4(heading: str, file_title: str, mp4_url: str, skip_existing: bool = True) -> bool:
    """Download MP4 file with progress bar."""
    try:
        folder_path = os.path.join(settings.MEDIA_DIR, heading)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, f"{file_title}.mp4")

        if skip_existing and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                file_size_mb = file_size / (1024 * 1024)
                logger.info(f"File already exists, skipping: {file_title} ({file_size_mb:.2f} MB)")
                return True

        logger.info(f"Starting download: {file_title}")
        response = requests.get(mp4_url, stream=True, timeout=settings.TIMEOUT_MAX)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        with open(file_path, "wb") as file:
            with tqdm(total=total, unit="B", unit_scale=True, desc=file_title) as pbar:
                for chunk in response.iter_content(chunk_size=settings.CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))

        logger.success(f"Download completed: {file_title}")
        return True

    except RequestException as e:
        logger.error(f"Download failed - Network error: {str(e)}")
        return False
    except IOError as e:
        logger.error(f"Download failed - File error: {str(e)}")
        return False


def run_download(video_content_id: int, series_name: Optional[str] = None) -> bool:
    """Execute download for a single video."""
    if not isinstance(video_content_id, int) or video_content_id <= 0:
        logger.error("Invalid video content ID")
        return False

    folder_name, file_name, video_url = get_video_details(video_content_id)
    if all((folder_name, file_name, video_url)):
        final_folder = series_name if series_name else folder_name
        return download_mp4(final_folder, file_name, video_url, settings.SKIP_EXISTING)  # type: ignore

    logger.error("Failed to get video details")
    return False


def extract_video_id(url: str) -> Optional[int]:
    """Extract video ID from ERR URL."""
    if not url or not isinstance(url, str):
        logger.error("Invalid URL provided")
        return None

    match = re.search(r"/(\d+)(?:/|$)", url)
    if not match:
        logger.error("Failed to extract video ID from URL")
        return None

    try:
        found_video_id = int(match.group(1))
        logger.info(f"Extracted video ID: {found_video_id}")
        return found_video_id
    except ValueError:
        logger.error("Invalid video ID format")
        return None


def get_all_episodes_from_series(series_id: int) -> Tuple[Optional[str], List[int]]:
    """Get all episode IDs from a series. Returns (series_name, episode_ids)."""
    try:
        url = API_BASE_URL.format(series_id)
        logger.info(f"Fetching series data for ID: {series_id}")

        response = session.get(url, timeout=settings.TIMEOUT_MAX)
        response.raise_for_status()

        data = response.json()
        series_name = data.get("data", {}).get("mainContent", {}).get("statsSeriesTitle", "").replace(".", "")
        episode_ids = []

        season_list = data.get("data", {}).get("seasonList", {})
        if season_list and "items" in season_list:
            total_seasons = len(season_list["items"])
            logger.info(f"Found {total_seasons} seasons")

            for season in season_list["items"]:
                season_name = season.get("name", "Unknown")
                season_count = 0

                if "contents" in season:
                    for content in season["contents"]:
                        episode_ids.append(content["id"])
                        season_count += 1
                elif "firstContentId" in season:
                    first_id = season["firstContentId"]
                    episode_ids.append(first_id)
                    season_count = 1

                logger.info(f"Season '{season_name}': {season_count} episodes")

            logger.success(f"Total: {len(episode_ids)} episodes from all seasons")

        return series_name, episode_ids

    except RequestException as e:
        logger.error(f"Failed to get series data: {str(e)}")
        return None, []
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to parse series data: {str(e)}")
        return None, []
