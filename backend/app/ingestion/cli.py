"""Manual ingestion trigger for development/testing.

Usage (inside the backend container/Codespace):
    python -m app.ingestion.cli                     # uses GOOGLE_DRIVE_ROOT_FOLDER_ID
    python -m app.ingestion.cli --folder-id <id>     # ingest a specific folder
"""

from __future__ import annotations

import argparse
import json
import logging

from app.config import settings
from app.ingestion.pipeline import run_ingestion

logging.basicConfig(level=logging.INFO)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder-id", default=settings.google_drive_root_folder_id)
    args = parser.parse_args()

    if not args.folder_id:
        raise SystemExit("No folder id given and GOOGLE_DRIVE_ROOT_FOLDER_ID is not set.")

    summary = run_ingestion(args.folder_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
