"""Thin wrapper around the Google Drive v3 / Sheets v4 APIs.

Uses a long-lived refresh token (obtained once via scripts/get_refresh_token.py)
so ingestion jobs can run without an interactive browser session. This is
separate from the frontend's NextAuth session, which authenticates the human
user for live requests.
"""

from __future__ import annotations

import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"


def _credentials() -> Credentials:
    if not settings.google_refresh_token:
        raise RuntimeError(
            "GOOGLE_REFRESH_TOKEN is not set. Run scripts/get_refresh_token.py once and "
            "add the result to .env / Codespaces secrets."
        )
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def _drive_service():
    return build("drive", "v3", credentials=_credentials())


def _sheets_service():
    return build("sheets", "v4", credentials=_credentials())


def list_files(folder_id: str, recursive: bool = True) -> list[dict]:
    """Lists files under a Drive folder, optionally recursing into subfolders."""
    service = _drive_service()
    files: list[dict] = []
    folders_to_scan = [folder_id]

    while folders_to_scan:
        current = folders_to_scan.pop()
        page_token = None
        while True:
            response = (
                service.files()
                .list(
                    q=f"'{current}' in parents and trashed = false",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                )
                .execute()
            )
            for f in response.get("files", []):
                if f["mimeType"] == FOLDER_MIME:
                    if recursive:
                        folders_to_scan.append(f["id"])
                else:
                    files.append(f)
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    return files


def get_file_metadata(file_id: str) -> dict:
    service = _drive_service()
    return service.files().get(fileId=file_id, fields="id, name, mimeType, modifiedTime").execute()


def download_file(file_id: str) -> bytes:
    """Downloads a binary file (PDF/DOCX) from Drive."""
    service = _drive_service()
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def export_gdoc(file_id: str, mime_type: str = "text/plain") -> str:
    """Exports a native Google Doc to plain text."""
    service = _drive_service()
    data = service.files().export(fileId=file_id, mimeType=mime_type).execute()
    return data.decode("utf-8") if isinstance(data, bytes) else data


def read_sheet_values(spreadsheet_id: str, range_name: str = "A:Z") -> list[list[str]]:
    """Reads cell values from a native Google Sheet."""
    service = _sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    return result.get("values", [])
