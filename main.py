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
        mp4_url = "https:" + data["data"]["mainContent"]["medias"][0]["src"]["file"].replace("\\", "")
        return folder_name, title_with_season_episode_year, mp4_url
    return None, None


def download_mp4(heading: str, file_title: str, mp4_url: str):
    create_folder_name = heading.replace(" ", "_")
    os.makedirs(create_folder_name, exist_ok=True)
    file_path = os.path.join(create_folder_name, f"{file_title}.mp4")
    response = requests.get(mp4_url, stream=True, timeout=TIMEOUT_MAX)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)


if __name__ == "__main__":
    # get this video ID from https://err.ee url ID example: https://lasteekraan.err.ee/1609219331
    video_content_id = 1608776893
    print(f"Starting download video content id: {video_content_id}")
    folder_name, file_name, video_url = get_video_details(video_content_id)
    print(f'Got video details: "{file_name}" - "{video_url}"')
    if file_name and video_url:
        print(f"Downloading video: {file_name}")
        download_mp4(folder_name, file_name, video_url)
    else:
        print("Failed to get video details")
