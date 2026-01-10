# ERR Downloader

## Description

Python-based downloader for ERR (Eesti Rahvusringhääling) video content. Automatically downloads TV show episodes and movies from lasteekraan.err.ee, with support for series monitoring and batch downloads.

## Features

- Downloads video content from ERR API
- Automatic episode detection for TV series
- Batch processing with optional threading support
- Progress tracking with detailed statistics
- DRM-protected content detection
- Automatic retry on network errors
- Configurable via YAML file
- Skip already downloaded files

## Requirements

- Python 3.12+
- Virtual environment (recommended)

## Setup

### 1. Clone the repository

```bash
git clone <repository_url>
cd err_downloader
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

### 5. Configure the application

Copy the example configuration file and adjust settings:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to set:
- Download directories for TV shows and movies
- URLs of TV shows to monitor
- URLs of movies to download
- Download behavior (threading, retry settings, etc.)

**Important:** The application will not run without a `config.yaml` file. All settings must be configured.

## Usage

After configuration, simply run:

```bash
python main.py
```

The script will:
1. Process all configured TV show URLs
2. Download new episodes if `download_all_episodes: true`
3. Process all configured movie URLs
4. Display summary statistics
