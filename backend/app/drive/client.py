"""Thin wrapper around the Google Drive v3 / Sheets v4 APIs.

Authenticates as a Google Cloud service account (no browser, no OAuth consent
screen, no refresh token to babysit). This is purely for the backend's own
ingestion jobs; it has no relation to any human login. For the service
account to actually see anything, the user must share the relevant Drive
folders with the service account's client_email as Viewer.
"""

from __future__ import annotations

import io

from google.oauth2 import service_account
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


def _credentials() -> service_account.Credentials:
    if not settings.google_service_account_file:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_FILE is not set. Point it at the service account "
            "JSON key (kept outside git, e.g. backend/secrets/service-account.json)."
        )
    return service_account.Credentials.from_service_account_file(
        settings.google_service_account_file, scopes=SCOPES
    )


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
