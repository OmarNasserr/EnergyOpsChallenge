from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.services.event_services import (
    handle_event_creation,
    handle_timeline_retrieval,
)
from app.db.session import get_async_session
from app.dto.event import ContractTimelineResponse, EventPayload, EventResponse

router = APIRouter(
    responses={404: {"description": "Not found"}},
    tags=["Events"],
)


@router.post("/event", response_model=EventResponse, status_code=status.HTTP_200_OK)
async def create_event_endpoint(
    payload: EventPayload,
    db: AsyncSession = Depends(get_async_session),
) -> EventResponse:
    """
    Import a single event into the system.

    Validates the event against business rules and returns accepted/rejected status.
    """
    return await handle_event_creation(db, payload)


@router.get(
    "/{contract_number}/contract_timeline",
    response_model=ContractTimelineResponse,
    status_code=status.HTTP_200_OK,
)
async def get_timeline_endpoint(
    contract_number: str,
    db: AsyncSession = Depends(get_async_session),
) -> ContractTimelineResponse:
    """
    Retrieve the timeline of all components for a contract.

    Returns start and end dates for each component.
    Returns 404 if contract not found.
    """
    return await handle_timeline_retrieval(db, contract_number)
