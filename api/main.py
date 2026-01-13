"""ChoirOS API - FastAPI backend for parsing and artifacts."""

import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.routers import parse, artifacts

app = FastAPI(
    title="ChoirOS API",
    description="Backend for ChoirOS web desktop",
    version="0.1.0",
)

security = HTTPBasic()

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify HTTP Basic Auth credentials."""
    correct_username = os.environ.get("CHOIR_USER", "choir")
    correct_password = os.environ.get("CHOIR_PASSWORD", "choir")

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# CORS Configuration
# Use environment variable for allowed origins
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers with authentication
app.include_router(parse.router, prefix="/api/parse", tags=["parse"], dependencies=[Depends(verify_credentials)])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"], dependencies=[Depends(verify_credentials)])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
