# ERR Downloader

## Description

This is a Python-based project for downloading video files from the ERR service API. Given a `contentId`, the script fetches video details, creates a folder with the video header name, and downloads the corresponding MP4 file.

## Features

- Fetches video details (title and MP4 URL) using the ERR API.
- Creates a folder based on the video title.
- Downloads the MP4 file into the folder with a clean name.

## Requirements

- Python 3.12+
- Virtual environment (recommended)
- Required libraries: `requests`

## Setup

### 1. Clone the repository

```bash
git clone <repository_url>
cd ERR_DOWNLOADER
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

- On Linux/macOS:

  ```bash
  source .venv/bin/activate
  ```

- On Windows:

  ```bash
  .venv\Scripts\activate
  ```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

## Usage

1. Update the `video_content_id` in `main.py`:

   ```python
   video_content_id = 1609219331
   ```

2. Run the script:

   ```bash
   python main.py
   ```

3. The downloaded video file will be saved in a folder named after the video title.

## Example Output

Given `video_content_id = 1609219331`, the script will:

- Create a folder `Piia_seiklused`.
- Save the MP4 file as `Piia_seiklused/Piia_seiklused.mp4`.

## File Structure

```bash
ERR_DOWNLOADER/
|
├── .gitignore
├── .venv/                # Virtual Environment (ignored by Git)
├── README.md             # Documentation
├── requirements.txt      # Project dependencies
├── main.py               # Main script
└── Piia_seiklused/       # Downloaded video folder
    └── Piia_seiklused.mp4
```

## .gitignore Example

```bash
# Ignore virtual environment
.venv/

# Ignore downloaded video folders
Piia_seiklused_*/

# Ignore Python cache files
__pycache__/
*.pyc

# Ignore IDE files
.vscode/
.idea/

# Ignore logs
*.log
```

## Dependencies

Install dependencies using:

```bash
pip install -r requirements.txt
```

- `requests`: For fetching video details and downloading files.

## Python Version

Specify your Python version in `.python-version` for compatibility:
