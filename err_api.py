import re
import os
from typing import Optional, Tuple, List
import requests
from tqdm import tqdm
from requests.exceptions import RequestException
from loguru import logger
import shutil
import settings
from constants import DOWNLOAD_SUCCESS, DOWNLOAD_FAILED, DOWNLOAD_SKIPPED, DOWNLOAD_DRM_PROTECTED

API_BASE_URL = "https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={}"

session = requests.Session()


def is_drm_protected(media_data: dict) -> bool:
    """Check if media is DRM protected."""
    restrictions = media_data.get("restrictions", {})
    return restrictions.get("drm", False)


def fetch_video_api_data(content_id: int) -> Optional[dict]:
    """Fetch raw video data from ERR API."""
    try:
        url = API_BASE_URL.format(content_id)
        logger.info(f"Fetching video details for content_id: {content_id}")

        response = session.get(url, timeout=settings.TIMEOUT_MAX)
        response.raise_for_status()

        return response.json()
    except RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        return None


def parse_video_details(data: dict, content_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse video details from API response."""
    try:
        main_content = data.get("data", {}).get("mainContent", {})
        medias = main_content.get("medias", [])

        if not medias:
            logger.error("No media found in response")
            return None, None, None

        if is_drm_protected(medias[0]):
            heading = main_content.get("heading", "Unknown")
            logger.warning(f"Video on DRM-kaitstud ja seda ei saa alla laadida: {heading} (ID: {content_id})")
            logger.warning(f"Vaata videot ERR veebilehel: https://jupiter.err.ee/{content_id}")
            return DOWNLOAD_DRM_PROTECTED, DOWNLOAD_DRM_PROTECTED, DOWNLOAD_DRM_PROTECTED

        folder_name = main_content.get("heading", "").replace(".", "")
        title_with_season_episode_year = f"{main_content.get('statsHeading', '')} {main_content.get('year', '')}"
        mp4_url = "https:" + medias[0]["src"]["file"].replace("\\", "")

        logger.info(f"Video details: {title_with_season_episode_year}")
        logger.info(f"MP4 URL: {mp4_url}")

        return folder_name, title_with_season_episode_year, mp4_url
    except (IndexError, KeyError) as e:
        logger.error(f"Failed to extract media URL: {str(e)}")
        return None, None, None


def get_video_details(content_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch and parse video details from ERR API."""
    data = fetch_video_api_data(content_id)
    if not data:
        return None, None, None

    return parse_video_details(data, content_id)


def check_file_exists(file_path: str, file_title: str, location: str) -> bool:
    """Check if file exists and log if skipping."""
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 0:
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"File already exists in {location}, skipping: {file_title} ({file_size_mb:.2f} MB)")
            return True
    return False


def download_mp4(heading: str, file_title: str, mp4_url: str, content_type: str, skip_existing: bool = True) -> bool | str:
    """Download MP4 file with progress bar. Returns 'skipped' if file already exists."""

    try:
        base_dir = settings.TV_SHOWS_DIR if content_type == "tv_shows" else settings.MOVIES_DIR
        final_folder_path = os.path.join(base_dir, heading)
        final_file_path = os.path.join(final_folder_path, f"{file_title}.mp4")

        if skip_existing and check_file_exists(final_file_path, file_title, "NAS"):
            return DOWNLOAD_SKIPPED

        if not settings.DOWNLOAD_TO_NAS_DIRECTLY:
            temp_folder = os.path.join(settings.LOCAL_TEMP_DIR, heading)
            temp_file_path = os.path.join(temp_folder, f"{file_title}.mp4")
            if skip_existing and check_file_exists(temp_file_path, file_title, "temp"):
                return DOWNLOAD_SKIPPED

        logger.info(f"Starting download: {file_title}")
        response = requests.get(mp4_url, stream=True, timeout=settings.TIMEOUT_MAX)
        response.raise_for_status()

        if settings.DOWNLOAD_TO_NAS_DIRECTLY:
            download_path = final_file_path
            os.makedirs(final_folder_path, exist_ok=True)
        else:
            temp_folder = os.path.join(settings.LOCAL_TEMP_DIR, heading)
            os.makedirs(temp_folder, exist_ok=True)
            download_path = os.path.join(temp_folder, f"{file_title}.mp4")

        total = int(response.headers.get("content-length", 0))
        with open(download_path, "wb") as file:
            with tqdm(total=total, unit="B", unit_scale=True, desc=file_title) as pbar:
                for chunk in response.iter_content(chunk_size=settings.CHUNK_SIZE):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))

        if not settings.DOWNLOAD_TO_NAS_DIRECTLY:
            logger.info(f"Moving file to NAS: {file_title}")
            os.makedirs(final_folder_path, exist_ok=True)
            shutil.move(download_path, final_file_path)

        logger.success(f"Download completed: {file_title}")
        return DOWNLOAD_SUCCESS

    except RequestException as e:
        logger.error(f"Download failed - Network error: {str(e)}")
        return DOWNLOAD_FAILED
    except IOError as e:
        logger.error(f"Download failed - File error: {str(e)}")
        return DOWNLOAD_FAILED


def run_download(video_content_id: int, content_type: str, series_name: Optional[str] = None) -> bool | str:
    """Execute download for a single video."""
    if not isinstance(video_content_id, int) or video_content_id <= 0:
        logger.error("Invalid video content ID")
        return DOWNLOAD_FAILED

    folder_name, file_name, video_url = get_video_details(video_content_id)
    
    if folder_name == DOWNLOAD_DRM_PROTECTED:
        return DOWNLOAD_DRM_PROTECTED
    
    if all((folder_name, file_name, video_url)):
        final_folder = series_name if series_name else folder_name
        return download_mp4(final_folder, file_name, video_url, content_type, settings.SKIP_EXISTING)  # type: ignore

    logger.error(f"Failed to get video details for ID: {video_content_id}")
    return DOWNLOAD_FAILED


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
