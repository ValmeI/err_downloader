import os
import requests
from icecream import ic

def get_video_details(video_content_id: int):
    url = f"https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={video_content_id}"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        
        return data["data"]["mainContent"]["heading"], "https:" + data["data"]["medias"][0]["src"]["file"]
    return None, None


def download_mp4(heading: str, mp4_url: str):
    folder_name = heading.replace(" ", "_")
    os.makedirs(folder_name, exist_ok=True)
    file_path = os.path.join(folder_name, f"{folder_name}.mp4")
    response = requests.get(mp4_url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)


if __name__ == "__main__":
    video_content_id = 1609219331
    heading, mp4_url = get_video_details(video_content_id)
    print(heading, mp4_url)
    #if heading and mp4_url:
        #download_mp4(heading, mp4_url)
