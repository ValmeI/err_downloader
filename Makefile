.PHONY: install run discover remote lint format

install:
	pip install -r requirements.txt

run:
	python main.py

discover:
	python main.py --discover --add

# macOS SMB to the NAS is unreliable; run on homelab (NFS mount, stable).
remote:
	ssh homelab.local /opt/err_downloader/run_downloader.sh

lint:
	ruff check .

format:
	ruff format .
