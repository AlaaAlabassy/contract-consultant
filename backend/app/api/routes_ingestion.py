from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from app.config import settings
from app.ingestion.pipeline import run_ingestion

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

# In-memory status is sufficient for v1 (single-process, solo user). If this
# ever needs to survive a backend restart or run across multiple workers,
# move this into the Redis instance already in the stack.
_state = {"status": "idle", "summary": None}


def _run_and_record(folder_id: str) -> None:
    _state["status"] = "running"
    try:
        _state["summary"] = run_ingestion(folder_id)
        _state["status"] = "done"
    except Exception as exc:  # noqa: BLE001
        _state["status"] = "error"
        _state["summary"] = {"error": str(exc)}


@router.post("/run")
def trigger_ingestion(background_tasks: BackgroundTasks, folder_id: str | None = None):
    target_folder = folder_id or settings.google_drive_root_folder_id
    if not target_folder:
        return {"error": "No folder_id provided and GOOGLE_DRIVE_ROOT_FOLDER_ID is not set."}
    background_tasks.add_task(_run_and_record, target_folder)
    return {"status": "started", "folder_id": target_folder}


@router.get("/status")
def ingestion_status():
    return _state
