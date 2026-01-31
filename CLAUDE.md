# ERR Downloader

Automated video downloader for ERR (Eesti Rahvusringhääling) content from lasteekraan.err.ee.

## Project Structure

```
err_downloader/
├── main.py           # CLI entry point (--discover, --add flags)
├── settings.py       # Pydantic-based YAML configuration
├── logger.py         # Loguru logging setup
├── err_api.py        # ERR API integration and download logic
├── downloader.py     # Download orchestration (sequential/threaded)
├── cache.py          # JSON-based download tracking
├── discovery.py      # URL discovery for new seasons
├── config.yaml       # User configuration (gitignored)
└── config.example.yaml
```

## Key Modules

- **err_api.py**: Core API functions - `fetch_video_api_data()`, `get_video_details()`, `download_mp4()`, `get_all_episodes_from_series()`
- **downloader.py**: Main workflow - `run_download_mode()`, processes URLs and manages stats
- **cache.py**: `DownloadCache` class tracks downloaded episodes in `.err_downloader_cache.json`
- **settings.py**: `Settings` class with nested configs (download, threading, retry, directories)
- **discovery.py**: Finds and adds new season URLs to config

## Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Normal download mode
python main.py

# Discover new season URLs
python main.py --discover

# Discover and auto-add to config
python main.py --discover --add
```

## Configuration

Copy `config.example.yaml` to `config.yaml`. Key settings:

- `directories.tv_shows` / `directories.movies`: Output paths
- `tv_shows` / `movies`: Lists of URLs to download
- `download.skip_existing`: Skip files already on disk
- `threading.use_threading`: Enable parallel downloads
- `retry.*`: Tenacity retry settings with exponential backoff

## Code Style

- No emojis in code, comments, or output
- English for code comments and documentation
- Type hints: use generic types, avoid `Any` unless necessary
- No redundant comments that just repeat what code does
- Readability over cleverness
- Follow consistent naming conventions
- Modular code: break down complex problems into smaller, manageable functions or classes
- Each function should have a clear purpose and not try to do too many things at once
- Avoid deep nesting of code blocks - refactor into smaller functions if necessary
- No duplicate logic or functions - reuse existing code where possible
- Handle errors gracefully, continue processing remaining items
- Optimize for performance only when necessary, avoid premature optimization

## Code Patterns

- **Status constants**: Functions return status strings (`drm_protected`, `download_skipped`, `cache_skipped`, etc.) defined in `settings.constants`
- **Retry decorator**: `@retry` from tenacity on download functions
- **Resume support**: Downloads check existing file size and use HTTP Range headers
- **Type hints**: Full annotations throughout
- **Estonian language**: User-facing messages and logging in Estonian

## Dependencies

- requests, pydantic, pydantic-settings, PyYAML, loguru, tenacity, tqdm
- Python 3.12.3 (see .python-version)

## Development

Linting with ruff (config in pyproject.toml):
```bash
ruff check .
ruff format .
```

## API Details

ERR API endpoint: `https://services.err.ee/api/v2/vodContent/getContentPageData?contentId={id}`

Content URLs format: `https://lasteekraan.err.ee/{content_id}/{slug}`
