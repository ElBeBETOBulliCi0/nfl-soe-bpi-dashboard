"""Health endpoints. `/health` (root, required by the deploy contract) and
`/api/health` share one handler, so their bodies are identical."""

from fastapi import APIRouter, Request

from backend.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    store = getattr(request.app.state, "store", None)
    return HealthResponse(status="ok", data_loaded=bool(store.data_loaded) if store else False)
