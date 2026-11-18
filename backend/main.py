"""API SOE/BPI. Ejecuta: .venv\\Scripts\\python -m uvicorn backend.main:app --port 8000"""
import os
from pathlib import Path


def cargar_env():
    f = Path(__file__).resolve().parent.parent / ".env"
    if f.exists():
        for linea in f.read_text(encoding="utf-8-sig").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


cargar_env()

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend.config import PRECOMPUTED_DIR, get_cors_origins  # noqa: E402
from backend.routers import bpi, filters, health, soe  # noqa: E402
from backend.store import DataStore  # noqa: E402


def create_app(directory: Path | str | None = None) -> FastAPI:
    """Build the app. ``directory`` overrides PRECOMPUTED_DIR (used by the tests)."""
    data_dir = Path(directory) if directory is not None else PRECOMPUTED_DIR

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Loaded once at startup; requests are served from memory (Req 15.3).
        app.state.store = DataStore.load(data_dir)
        yield

    app = FastAPI(title="Hackathon NFL UNAM - SOE/BPI", lifespan=lifespan)
    app.state.store = DataStore()  # empty until the lifespan runs
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    # health registers both GET /health (deploy contract) and GET /api/health.
    app.include_router(health.router)
    app.include_router(filters.router)
    app.include_router(soe.router)
    app.include_router(bpi.router)
    return app


app = create_app()
