from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_ingestion import router as ingestion_router
from app.api.routes_qa import router as qa_router
from app.api.routes_risk import router as risk_router

app = FastAPI(title="مستشار العقود - Contract Consultant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router)
app.include_router(qa_router)
app.include_router(risk_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
