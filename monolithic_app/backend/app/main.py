from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Monolithic Chat App", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Serve the frontend located at monolithic_app/frontend/public
FRONTEND_DIR = PROJECT_ROOT / "frontend" / "public"
ASSETS_DIR = FRONTEND_DIR / "assets"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
def index() -> FileResponse:
    if not FRONTEND_DIR.exists():
        return FileResponse(str(PROJECT_ROOT / "backend" / "README.md"))
    return FileResponse(str(FRONTEND_DIR / "index.html"))
