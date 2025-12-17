"""ChoirOS API - FastAPI backend for parsing and artifacts."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import parse, artifacts

app = FastAPI(
    title="ChoirOS API",
    description="Backend for ChoirOS web desktop",
    version="0.1.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",  # Fallback when 5173 is in use
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(parse.router, prefix="/api/parse", tags=["parse"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
