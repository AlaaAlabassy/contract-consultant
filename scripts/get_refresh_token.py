"""
One-time helper: run this locally (or in the Codespace terminal) to obtain a
Google OAuth refresh token for the backend's own Drive ingestion jobs.

This is separate from the frontend's NextAuth login - that one authenticates
the human user in the browser; this one lets the backend CLI/ingestion jobs
call the Drive API on their own, without a live browser session.

Usage:
    python scripts/get_refresh_token.py

Requires GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET to already be set in the
environment (or pass them via --client-id / --client-secret).
"""

import argparse
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", default=os.environ.get("GOOGLE_CLIENT_ID", ""))
    parser.add_argument("--client-secret", default=os.environ.get("GOOGLE_CLIENT_SECRET", ""))
    args = parser.parse_args()

    if not args.client_id or not args.client_secret:
        raise SystemExit("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET (env or flags) first.")

    client_config = {
        "installed": {
            "client_id": args.client_id,
            "client_secret": args.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    print("\nAdd this to your .env (or as a Codespaces secret) as GOOGLE_REFRESH_TOKEN:\n")
    print(creds.refresh_token)


if __name__ == "__main__":
    main()
