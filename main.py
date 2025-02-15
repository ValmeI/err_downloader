import re
import os
import sys
from typing import Optional, Tuple
import requests
from tqdm import tqdm
from requests.exceptions import RequestException

TIMEOUT_MAX = 60


def get_video_details(content_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        url = f"https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={content_id}"
        response = requests.get(url, timeout=TIMEOUT_MAX)
        response.raise_for_status()
        
        data = response.json()
        folder_name = data["data"]["mainContent"]["heading"].replace(".", "")
        title_with_season_episode_year = (
            f"{data['data']['mainContent']['statsHeading']} {data['data']['mainContent']['year']}"
        )
        
        try:
            mp4_url = "https:" + data["data"]["mainContent"]["medias"][0]["src"]["file"].replace("\\", "")
            print(f"Got video details: - {title_with_season_episode_year} - {mp4_url}")
            return folder_name, title_with_season_episode_year, mp4_url
        except (IndexError, KeyError) as e:
            print(f"Failed to get video details: {str(e)}")
            return None, None, None
            
    except RequestException as e:
        print(f"Network error occurred: {str(e)}")
        return None, None, None
    except ValueError as e:
        print(f"Invalid JSON response: {str(e)}")
        return None, None, None


def download_mp4(heading: str, file_title: str, mp4_url: str) -> bool:
    try:
        folder_name = heading
        os.makedirs(folder_name, exist_ok=True)
        file_path = os.path.join(folder_name, f"{file_title}.mp4")
        
        response = requests.get(mp4_url, stream=True, timeout=TIMEOUT_MAX)
        response.raise_for_status()
        
        total = int(response.headers.get("content-length", 0))
        with open(file_path, "wb") as file:
            with tqdm(total=total, unit="B", unit_scale=True, desc=file_title) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        pbar.update(len(chunk))
        return True
        
    except RequestException as e:
        print(f"Download failed: Network error - {str(e)}")
        return False
    except IOError as e:
        print(f"Download failed: File error - {str(e)}")
        return False


def run_download(video_content_id: int) -> bool:
    if not isinstance(video_content_id, int) or video_content_id <= 0:
        print("Invalid video content ID")
        return False
        
    name_folder, file_name, video_url = get_video_details(video_content_id)
    if all((name_folder, file_name, video_url)):
        print(f"Downloading video: {file_name}")
        return download_mp4(name_folder, file_name, video_url)
    print("Failed to get video details")
    return False


def extract_video_id(url: str) -> Optional[int]:
    if not url or not isinstance(url, str):
        print("Invalid URL provided")
        return None
        
    match = re.search(r"/(\d+)(?:/|$)", url)
    if not match:
        print("Failed to extract video ID from URL")
        return None
        
    try:
        found_video_id = int(match.group(1))
        print(f"Extracted video ID: {found_video_id}")
        return found_video_id
    except ValueError:
        print("Invalid video ID format")
        return None


if __name__ == "__main__":
    ERR_URL = "https://jupiter.err.ee/1609111700/metsloomade-elu"
    EPISODES_TO_DOWNLOAD = 18
    IS_TV_SHOW = False
    
    video_id = extract_video_id(ERR_URL)
    if not video_id:
        sys.exit(1)

    if IS_TV_SHOW:
        print(f"Downloading TV show with {EPISODES_TO_DOWNLOAD} episodes")
        for i in range(EPISODES_TO_DOWNLOAD):
            if not run_download(video_id):
                print(f"Failed to download episode {i + 1}")
            video_id += 3
    else:
        print("Downloading single video")
        if not run_download(video_id):
            sys.exit(1)
