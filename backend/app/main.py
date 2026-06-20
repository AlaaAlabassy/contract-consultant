from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_ingestion import router as ingestion_router

app = FastAPI(title="مستشار العقود - Contract Consultant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
