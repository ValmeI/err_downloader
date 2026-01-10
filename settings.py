"""Application settings as simple constants."""

import os

LOGGER_LEVEL = "INFO"
TIMEOUT_MAX = 60
CHUNK_SIZE = 1048576  # 1MB
DOWNLOAD_ALL_EPISODES = True
SKIP_EXISTING = True
USE_THREADING = False
MAX_WORKERS = os.cpu_count() or 4

RETRY_MAX_ATTEMPTS = 3
RETRY_WAIT_MIN = 5
RETRY_WAIT_MAX = 30
RETRY_WAIT_MULTIPLIER = 1

TV_SHOWS_DIR = "/Volumes/NAS_Files/Downloads/Lastele TV Shows"
MOVIES_DIR = "/Volumes/NAS_Files/Downloads/Lastele"

# TV shows to always check for new episodes
TV_SHOWS = [
    "https://lasteekraan.err.ee/1609890665/mystery-lane-i-ponevad-juhtumid",
    "https://lasteekraan.err.ee/1608695959/lepatriinu-ja-musta-kassi-imelised-lood",
    "https://lasteekraan.err.ee/1039236/must-ja-valge-koer",
    "https://lasteekraan.err.ee/1608967400/peeter-pikk-korv",
    "https://lasteekraan.err.ee/1608940043/pips-ja-popi",
    "https://lasteekraan.err.ee/1608776887/vilda",
    "https://lasteekraan.err.ee/1038651/karu-karla",
    "https://lasteekraan.err.ee/1127112/ninjakunstnik",
    "https://lasteekraan.err.ee/1608551665/tuta-asjad",
    "https://lasteekraan.err.ee/1038778/porsas-peppa",
]
