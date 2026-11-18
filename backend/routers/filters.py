"""GET /api/filters: sorted distinct filter values from the in-memory store."""

from fastapi import APIRouter, Request

from backend.schemas import FiltersResponse
from backend.store import DataStore

router = APIRouter()


@router.get("/api/filters", response_model=FiltersResponse)
def get_filters(request: Request) -> FiltersResponse:
    store = getattr(request.app.state, "store", None)
    if store is None:
        store = DataStore()
    return FiltersResponse(**store.filter_values())
