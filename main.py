import re
import os
from threading import TIMEOUT_MAX
import requests

TIMEOUT_MAX = 60


def get_video_details(content_id: int):
    url = f"https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={content_id}"
    response = requests.get(url, timeout=TIMEOUT_MAX)
    if response.status_code == 200:
        data = response.json()
        folder_name = data["data"]["mainContent"]["heading"]
        title_with_season_episode_year = (
            f"{data['data']['mainContent']['statsHeading']} {data['data']['mainContent']['year']}"
        )
        try:
            mp4_url = "https:" + data["data"]["mainContent"]["medias"][0]["src"]["file"].replace("\\", "")
            print(f"Got video details: {folder_name} - {title_with_season_episode_year} - {mp4_url}")
            return folder_name, title_with_season_episode_year, mp4_url
        except IndexError:
            print("Failed to get video details, no mp4 URL found")
            return None, None, None
    return None, None, None


def download_mp4(heading: str, file_title: str, mp4_url: str):
    folder_name = heading.replace(" ", "_")
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, f"{file_title}.mp4")
    response = requests.get(mp4_url, stream=True, timeout=TIMEOUT_MAX)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)


def run_download(video_content_id: int):
    name_folder, file_name, video_url = get_video_details(video_content_id)
    print(f'Got video details: "{file_name}" - "{video_url}"')
    if file_name and video_url:
        print(f"Downloading video: {file_name}")
        download_mp4(name_folder, file_name, video_url)
    else:
        print("Failed to get video details")


def extract_video_id(url):
    match = re.search(r"/(\d+)(?:/|$)", url)
    if not match:
        print("Failed to extract video ID from URL")
        return None
    video_id_match = match.group(1)
    print(f"Extracted video ID: {video_id_match}")
    return video_id_match


if __name__ == "__main__":
    ERR_URL = "https://lasteekraan.err.ee/1203172/naksitrallid"
    EPISODES_TO_DOWNLOAD = 18
    IS_TV_SHOW = False
    video_id = extract_video_id(ERR_URL)

    if IS_TV_SHOW:
        print(f"Downloading TV show with {EPISODES_TO_DOWNLOAD} episodes")
        for i in range(EPISODES_TO_DOWNLOAD):
            run_download(video_id)
            video_id += 3
    else:
        print("Downloading single video")
        run_download(video_id)
