import re
import os
from typing import Optional, Tuple, List, Set, Dict
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from requests.exceptions import RequestException
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from settings import settings

API_BASE_URL = "https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={}"

session = requests.Session()
session.headers.update({"Connection": "keep-alive", "Accept-Encoding": "gzip, deflate"})
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=0)
session.mount("https://", adapter)
session.mount("http://", adapter)


def is_drm_protected(media_data: dict) -> bool:
    """Check if media is DRM protected."""
    restrictions = media_data.get("restrictions", {})
    return restrictions.get("drm", False)


def fetch_video_api_data(content_id: int) -> Optional[dict]:
    """Fetch raw video data from ERR API."""
    try:
        url = API_BASE_URL.format(content_id)
        logger.info(f"Fetching video details for content_id: {content_id}")

        response = session.get(url, timeout=settings.download.timeout_max)
        response.raise_for_status()

        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Sisu ei ole enam saadaval ERRis (404) - ID: {content_id}. Sisu on tõenäoliselt ERRist eemaldatud või arhiveeritud.")
        else:
            logger.error(f"HTTP error {e.response.status_code}: {str(e)}")
        return None
    except RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"Invalid JSON response: {str(e)}")
        return None


def build_file_title(main_content: dict, content_type: str) -> str:
    """Build file title with season/episode for TV shows or statsHeading for movies."""
    year = main_content.get("year", "")

    if content_type == settings.constants.content_type_tv_shows:
        season = main_content.get("season")
        episode = main_content.get("episode")

        if season is not None and episode is not None and season > 0 and episode > 0:
            return f"S{season:02d}E{episode:02d} {year}".strip()

    return f"{main_content.get('statsHeading', '')} {year}".strip()


def extract_mp4_url(medias: list) -> Optional[str]:
    """Extract MP4 URL from medias list."""
    try:
        return "https:" + medias[0]["src"]["file"].replace("\\", "")
    except (IndexError, KeyError) as e:
        logger.error(f"Failed to extract MP4 URL: {str(e)}")
        return None


def parse_video_details(data: dict, content_id: int, content_type: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
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
            logger.warning(f"Vaata videot {heading} ERR veebilehel: https://jupiter.err.ee/{content_id}")
            return settings.constants.drm_protected, settings.constants.drm_protected, settings.constants.drm_protected

        folder_name = main_content.get("heading", "").replace(".", "")
        file_title = build_file_title(main_content, content_type)
        mp4_url = extract_mp4_url(medias)

        if not mp4_url:
            return None, None, None

        logger.info(f"Video details: [{folder_name}] {file_title}")
        logger.info(f"MP4 URL: {mp4_url}")

        return folder_name, file_title, mp4_url
    except (IndexError, KeyError) as e:
        logger.error(f"Failed to parse video details: {str(e)}")
        return None, None, None


def get_video_details(content_id: int, content_type: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch and parse video details from ERR API."""
    data = fetch_video_api_data(content_id)
    if not data:
        return None, None, None

    return parse_video_details(data, content_id, content_type)


def get_file_paths(heading: str, file_title: str, content_type: str) -> Tuple[str, str]:
    """Calculate file paths for final location.
    Returns: (final_folder_path, final_file_path)
    """
    base_dir = settings.directories.tv_shows if content_type == settings.constants.content_type_tv_shows else settings.directories.movies
    final_folder_path = os.path.join(base_dir, heading)
    final_file_path = os.path.join(final_folder_path, f"{file_title}.mp4")

    return final_folder_path, final_file_path


def check_file_exists(file_path: str, file_title: str, heading: str) -> bool:
    """Check if file exists and log if skipping."""
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        if file_size > 0:
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"File already exists, skipping: [{heading}] {file_title} ({file_size_mb:.2f} MB)")
            return True
    return False


def should_skip_download(final_file_path: str, file_title: str, heading: str, skip_existing: bool) -> bool:
    """Check if download should be skipped because file already exists."""
    if not skip_existing:
        return False

    return check_file_exists(final_file_path, file_title, heading)


@retry(
    stop=stop_after_attempt(settings.retry.max_attempts),
    wait=wait_exponential(multiplier=settings.retry.wait_multiplier, min=settings.retry.wait_min, max=settings.retry.wait_max),
    retry=retry_if_exception_type((RequestException, IOError)),
)
def download_file_with_progress(url: str, file_path: str, file_title: str) -> bool:
    """Download file from URL with progress bar and resume support."""
    try:
        existing_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        headers = {"Range": f"bytes={existing_size}-"} if existing_size > 0 else {}

        if existing_size > 0:
            logger.info(f"Resuming from {existing_size / (1024*1024):.1f} MB")

        response = requests.get(url, stream=True, timeout=(10, 30), headers=headers)

        # Server ei toeta resume -> alusta algusest
        if existing_size > 0 and response.status_code == 200:
            existing_size = 0
            logger.warning("Server doesn't support resume, starting fresh")

        response.raise_for_status()

        # Kogusuurus
        if response.status_code == 206:
            content_range = response.headers.get("Content-Range", "")
            total = int(content_range.split("/")[-1]) if "/" in content_range else 0
        else:
            total = int(response.headers.get("content-length", 0))

        mode = "ab" if existing_size > 0 else "wb"

        with open(file_path, mode) as file:
            with tqdm(total=total, initial=existing_size, unit="B", unit_scale=True, desc=file_title) as pbar:
                for chunk in response.iter_content(chunk_size=settings.download.chunk_size):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))
        return True
    except RequestException as e:
        logger.error(f"Download failed - Network error: {str(e)}")
        raise
    except IOError as e:
        logger.error(f"Download failed - File error: {str(e)}")
        raise


def download_mp4(heading: str, file_title: str, mp4_url: str, content_type: str, skip_existing: bool = True) -> tuple[str, str] | str | bool:
    """Download MP4 file. Returns (status, file_path) tuple, or False on failure."""
    final_folder_path, final_file_path = get_file_paths(heading, file_title, content_type)

    if should_skip_download(final_file_path, file_title, heading, skip_existing):
        return (settings.constants.download_skipped, final_file_path)

    logger.info(f"Starting download: [{heading}] {file_title}")

    os.makedirs(final_folder_path, exist_ok=True)

    try:
        download_file_with_progress(mp4_url, final_file_path, file_title)
        logger.success(f"Download completed: [{heading}] {file_title}")
        return ("success", final_file_path)
    except Exception:
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
            logger.warning(f"Deleted partial file: {final_file_path}")
        return False


def run_download(video_content_id: int, content_type: str, series_name: Optional[str] = None) -> str | bool:
    """Execute download for a single video."""
    if not isinstance(video_content_id, int) or video_content_id <= 0:
        logger.error("Invalid video content ID")
        return False

    folder_name, file_name, video_url = get_video_details(video_content_id, content_type)

    if folder_name == settings.constants.drm_protected:
        return settings.constants.drm_protected

    if all((folder_name, file_name, video_url)):
        final_folder = series_name if series_name else folder_name
        return download_mp4(final_folder, file_name, video_url, content_type, settings.download.skip_existing)  # type: ignore

    logger.error(f"Failed to get video details for ID: {video_content_id}")
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

        response = session.get(url, timeout=settings.download.timeout_max)
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

    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(
                f"Sarja ei ole enam saadaval ERRis ({settings.constants.content_not_found_404}) - ID: {series_id}. Sari {url} on tõenäoliselt ERRist eemaldatud või arhiveeritud."
            )
            return settings.constants.content_not_found_404, []
        else:
            logger.error(f"Failed to get series data: HTTP error {e.response.status_code}: {str(e)}")
        return None, []
    except RequestException as e:
        logger.error(f"Failed to get series data: {str(e)}")
        return None, []
    except (ValueError, KeyError) as e:
        logger.error(f"Failed to parse series data: {str(e)}")
        return None, []


def extract_show_slug(url: str) -> str:
    """Extract show slug from URL (e.g., 'tuta-asjad')."""
    match = re.search(r"/\d+/([^/]+)/?$", url)
    return match.group(1) if match else ""


def get_season_urls_from_api(content_id: int, show_slug: str) -> Set[str]:
    """Fetch seasonList from ERR API and return all season URLs."""
    found_urls: Set[str] = set()

    try:
        url = API_BASE_URL.format(content_id)
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return found_urls

        data = response.json()
        season_list = data.get("data", {}).get("seasonList", {})

        for season in season_list.get("items", []):
            first_id = season.get("firstContentId")
            if first_id:
                new_url = f"https://lasteekraan.err.ee/{first_id}/{show_slug}"
                found_urls.add(new_url)

    except Exception as e:
        logger.debug(f"API error for {content_id}: {e}")

    return found_urls


def discover_missing_urls(tv_show_urls: List[str]) -> Dict[str, Set[str]]:
    """
    Discover missing season URLs for TV shows.

    Returns dict mapping show_slug -> set of missing URLs.
    """
    # Group URLs by show slug
    existing_by_show: Dict[str, Set[str]] = {}
    existing_ids: Set[str] = set()

    for url in tv_show_urls:
        slug = extract_show_slug(url)
        if slug:
            if slug not in existing_by_show:
                existing_by_show[slug] = set()
            existing_by_show[slug].add(url)

        vid = extract_video_id(url)
        if vid:
            existing_ids.add(str(vid))

    missing_by_show: Dict[str, Set[str]] = {}

    for slug, existing_urls in existing_by_show.items():
        logger.info(f"Kontrollin: {slug.replace('-', ' ')}")

        # Check each existing URL's API for season links
        found_urls: Set[str] = set()
        for url in existing_urls:
            vid = extract_video_id(url)
            if vid:
                season_urls = get_season_urls_from_api(vid, slug)
                found_urls.update(season_urls)

        # Find missing URLs
        missing: Set[str] = set()
        for url in found_urls:
            vid = extract_video_id(url)
            if vid and str(vid) not in existing_ids:
                missing.add(url)

        if missing:
            missing_by_show[slug] = missing
            logger.success(f"Leitud {len(missing)} uut URL-i: {slug.replace('-', ' ')}")
            for url in sorted(missing):
                logger.success(f"  🆕 {url}")

    return missing_by_show
