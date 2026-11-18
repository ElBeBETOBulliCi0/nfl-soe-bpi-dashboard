"""Configuración: rutas y orígenes CORS."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PRECOMPUTED_DIR = PROJECT_ROOT / "backend" / "precomputed"

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:3000"


def parse_origins(raw: str | None) -> list[str]:
    """Convierte una lista separada por comas en orígenes; vacío usa el valor por defecto."""
    origins = [o.strip() for o in (raw or "").split(",") if o.strip()]
    if not origins:
        origins = [o.strip() for o in DEFAULT_CORS_ORIGINS.split(",")]
    return origins


def get_cors_origins() -> list[str]:
    """Lee CORS_ORIGINS en cada llamada, así un cambio de entorno se refleja al crear la app."""
    return parse_origins(os.environ.get("CORS_ORIGINS"))
