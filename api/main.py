"""ChoirOS API - FastAPI backend for parsing and artifacts."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import parse, artifacts, auth
from shared.auth_middleware import AuthMiddleware

app = FastAPI(
    title="ChoirOS API",
    description="Backend for ChoirOS web desktop",
    version="0.1.0",
)

# Attach auth context when a session token is present.
app.add_middleware(AuthMiddleware)

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
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
