from datetime import datetime
from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, UUID4, ConfigDict, Field


class EventPayload(BaseModel):
    """Request payload for creating an event."""

    type: str
    contract_number: str
    date: date_type = Field(..., description="Event date in ISO format (YYYY-MM-DD)")
    created_at: datetime


class EventResponse(BaseModel):
    """Response for event creation."""

    status: str
    message: str


class ComponentTimeline(BaseModel):
    """Timeline for a single component."""

    start: Optional[date_type] = None
    end: Optional[date_type] = None


class ContractTimelineResponse(BaseModel):
    """Response for contract timeline retrieval."""

    contract_number: str
    components: dict[str, ComponentTimeline]
